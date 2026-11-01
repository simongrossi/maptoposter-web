"""Recuperation des donnees OpenStreetMap via OSMnx."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import osmnx as ox

from backend.cache import DiskCache
from backend.models import CustomLayer
from backend.settings import settings

logger = logging.getLogger(__name__)

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
    def _graph_cache_key(point, dist: float) -> str:
        # Le type de reseau fait partie de la cle : sinon un graphe `all`
        # precedemment cache serait reutilise apres passage a `drive`.
        return (
            f"graph_v2_{settings.osm_network_type}_"
            f"{point[0]}_{point[1]}_{dist}"
        )

    @staticmethod
    def _fetch_graph_sync(point, dist):
        key = MapDataFetcher._graph_cache_key(point, dist)
        cached = DiskCache.get(key)
        if cached is not None:
            return cached

        try:
            graph = ox.graph_from_point(
                point,
                dist=dist,
                dist_type="bbox",
                network_type=settings.osm_network_type,
                truncate_by_edge=True,
            )
            DiskCache.set(key, graph)
            return graph
        except Exception as exc:
            logger.warning("Echec de recuperation du graphe OSM: %s", exc)
            return None

    @staticmethod
    def _fetch_features_sync(point, dist, tags, name):
        tag_str = "-".join(f"{key}:{value}" for key, value in sorted(tags.items()))
        key = f"feat_v2_{name}_{point[0]}_{point[1]}_{dist}_{tag_str}"

        cached = DiskCache.get(key)
        if cached is not None:
            return cached

        try:
            features = ox.features_from_point(point, tags=tags, dist=dist)
            if features.empty:
                return None
            DiskCache.set(key, features)
            return features
        except Exception as exc:
            logger.warning("Echec de recuperation des couches %s: %s", name, exc)
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

        return data
