"""Recuperation des donnees OpenStreetMap via OSMnx."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import osmnx as ox

from backend.cache import DiskCache
from backend.models import CustomLayer

logger = logging.getLogger(__name__)

# La distance maximale acceptee par l'API est de 25 km, soit une bbox de
# 50 x 50 km (2500 km2). On laisse une petite marge au-dessus du plafond
# OSMnx par defaut pour que la limite applicative soit la seule contraignante.
ox.settings.max_query_area_size = 3_000_000_000
ox.settings.requests_timeout = 30
ox.settings.log_console = False


class MapDataFetcher:
    """Telecharge graphe routier et geometries OSM, avec cache disque."""

    @staticmethod
    def _fetch_graph_sync(point, dist):
        key = f"graph_{point[0]}_{point[1]}_{dist}"
        cached = DiskCache.get(key)
        if cached is not None:
            return cached

        try:
            graph = ox.graph_from_point(
                point,
                dist=dist,
                dist_type="bbox",
                network_type="all",
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
        key = f"feat_{name}_{point[0]}_{point[1]}_{dist}_{tag_str}"

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
    ) -> Dict[str, Any]:
        """Recupere toutes les couches en parallele (threads)."""
        point = (lat, lon)

        tasks = {
            "graph": asyncio.to_thread(cls._fetch_graph_sync, point, dist),
            "water": asyncio.to_thread(
                cls._fetch_features_sync,
                point,
                dist,
                {"natural": "water", "waterway": "riverbank"},
                "water",
            ),
            "parks": asyncio.to_thread(
                cls._fetch_features_sync,
                point,
                dist,
                {"leisure": "park", "landuse": "grass"},
                "parks",
            ),
        }

        if custom_layers:
            for index, layer in enumerate(custom_layers):
                if layer.enabled and layer.tags:
                    tasks[f"custom_{index}"] = asyncio.to_thread(
                        cls._fetch_features_sync,
                        point,
                        dist,
                        layer.tags,
                        f"custom_{layer.label}",
                    )

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        data: Dict[str, Any] = {}
        for key, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.warning("Tache %s en echec: %s", key, result)
                data[key] = None
            else:
                data[key] = result

        return data
