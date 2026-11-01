"""Recuperation des donnees OpenStreetMap via OSMnx."""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import osmnx as ox

from backend.cache import DiskCache
from backend.models import CustomLayer
from backend.settings import settings

logger = logging.getLogger(__name__)

# Certains VPS ont un IPv6 casse : urllib3/requests tente IPv6 en premier et
# attend le timeout avant de basculer, ce qui donne l'impression que le
# telechargement OSM est fige. Forcer IPv4 evite cette attente.
if settings.osm_force_ipv4:
    try:
        import urllib3.util.connection as _urllib3_connection

        _urllib3_connection.allowed_gai_family = lambda: socket.AF_INET
        logger.info("OSMnx/Overpass : IPv4 force")
    except Exception as exc:  # pragma: no cover - depend d'urllib3
        logger.warning("Impossible de forcer IPv4: %s", exc)

# Cache HTTP interne d'OSMnx : il doit pointer vers un repertoire inscriptible
# par l'utilisateur `app`, sinon chaque reponse Overpass echoue a la sauvegarde
# (PermissionError) et la requete est perdue.
_cache_root = Path(os.getenv("CACHE_DIR", ".cache"))
_osmnx_cache_dir = Path(
    os.getenv("OSMNX_CACHE_DIR", str(_cache_root / "osmnx"))
)
_osmnx_cache_dir.mkdir(parents=True, exist_ok=True)

ox.settings.cache_folder = str(_osmnx_cache_dir)
ox.settings.use_cache = True
ox.settings.requests_timeout = settings.osm_request_timeout
ox.settings.overpass_url = settings.overpass_url
# La distance maximale acceptee par l'API est de 25 km, soit une bbox de
# 50 x 50 km (2500 km2). On laisse une petite marge au-dessus du plafond
# OSMnx par defaut pour que la limite applicative soit la seule contraignante.
ox.settings.max_query_area_size = 3_000_000_000
ox.settings.log_console = False


class MapDataFetcher:
    """Telecharge graphe routier et geometries OSM, avec cache disque."""

    @staticmethod
    def network_type_for(dist: float) -> str:
        """Choisit le reseau adapte a la taille de la zone.

        `auto` conserve le detail pieton/cyclable des petites zones (ou le
        cout est faible) et bascule sur le reseau carrossable pour les grandes
        zones, beaucoup plus rapide.
        """
        if settings.osm_network_type == "auto":
            return "all" if dist <= 5000 else "drive"
        return settings.osm_network_type

    @staticmethod
    def _graph_cache_key(point, dist: float) -> str:
        # Le type de reseau fait partie de la cle : sinon un graphe `all`
        # precedemment cache serait reutilise apres passage a `drive`.
        return (
            f"graph_v3_{MapDataFetcher.network_type_for(dist)}_"
            f"{point[0]}_{point[1]}_{dist}"
        )

    @staticmethod
    def _fetch_graph_sync(point, dist):
        key = MapDataFetcher._graph_cache_key(point, dist)
        network_type = MapDataFetcher.network_type_for(dist)
        cached = DiskCache.get(key)
        if cached is not None:
            logger.info(
                "Graphe OSM en cache (type=%s, dist=%s)",
                network_type,
                dist,
            )
            return cached

        started_at = time.monotonic()
        try:
            graph = ox.graph_from_point(
                point,
                dist=dist,
                dist_type="bbox",
                network_type=network_type,
                truncate_by_edge=True,
            )
            DiskCache.set(key, graph)
            logger.info(
                "Graphe OSM telecharge en %.1fs (type=%s, %s noeuds)",
                time.monotonic() - started_at,
                network_type,
                len(graph),
            )
            return graph
        except Exception as exc:
            logger.warning(
                "Echec de recuperation du graphe OSM apres %.1fs: %s",
                time.monotonic() - started_at,
                exc,
            )
            return None

    @staticmethod
    def _fetch_features_sync(point, dist, tags, name):
        tag_str = "-".join(f"{key}:{value}" for key, value in sorted(tags.items()))
        key = f"feat_v2_{name}_{point[0]}_{point[1]}_{dist}_{tag_str}"

        cached = DiskCache.get(key)
        if cached is not None:
            return cached

        started_at = time.monotonic()
        try:
            features = ox.features_from_point(point, tags=tags, dist=dist)
            if features.empty:
                return None
            DiskCache.set(key, features)
            logger.info(
                "Couche OSM %s telechargee en %.1fs",
                name,
                time.monotonic() - started_at,
            )
            return features
        except Exception as exc:
            logger.warning(
                "Echec de recuperation des couches %s apres %.1fs: %s",
                name,
                time.monotonic() - started_at,
                exc,
            )
            return None

    @classmethod
    async def fetch_all(
        cls,
        lat: float,
        lon: float,
        dist: float,
        custom_layers: Optional[List[CustomLayer]] = None,
        on_graph_ready: Optional[Callable[[], None]] = None,
    ) -> Dict[str, Any]:
        """Recupere le graphe puis les couches, en parallele.

        `on_graph_ready` est appele des que le graphe routier est pret, pour
        permettre a Celery de publier une progression intermediaire.
        """
        point = (lat, lon)

        # Les couches demarrent en parallele du graphe (le graphe est le plus
        # long) mais on attend d'abord le graphe pour publier la progression.
        feature_tasks = {
            "water": asyncio.create_task(
                asyncio.to_thread(
                    cls._fetch_features_sync,
                    point,
                    dist,
                    {"natural": "water", "waterway": "riverbank"},
                    "water",
                )
            ),
            "parks": asyncio.create_task(
                asyncio.to_thread(
                    cls._fetch_features_sync,
                    point,
                    dist,
                    {"leisure": "park", "landuse": "grass"},
                    "parks",
                )
            ),
        }

        if custom_layers:
            for index, layer in enumerate(custom_layers):
                if layer.enabled and layer.tags:
                    feature_tasks[f"custom_{index}"] = asyncio.create_task(
                        asyncio.to_thread(
                            cls._fetch_features_sync,
                            point,
                            dist,
                            layer.tags,
                            f"custom_{layer.label}",
                        )
                    )

        try:
            graph = await asyncio.to_thread(cls._fetch_graph_sync, point, dist)
        except Exception as exc:  # pragma: no cover - depend d'OSMnx
            logger.warning("Graphe OSM indisponible: %s", exc)
            graph = None

        if graph is None:
            for task in feature_tasks.values():
                task.cancel()
            return {"graph": None}

        if on_graph_ready:
            try:
                on_graph_ready()
            except Exception as exc:  # pragma: no cover - depend de Celery
                logger.warning("Mise a jour de progression impossible: %s", exc)

        results = await asyncio.gather(
            *feature_tasks.values(), return_exceptions=True
        )

        data: Dict[str, Any] = {"graph": graph}
        for key, result in zip(feature_tasks.keys(), results):
            if isinstance(result, Exception):
                logger.warning("Tache %s en echec: %s", key, result)
                data[key] = None
            else:
                data[key] = result

        logger.info(
            "Donnees OSM pretes (%s noeuds, %s couches)",
            len(graph),
            len(feature_tasks),
        )
        return data
