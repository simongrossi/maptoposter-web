import asyncio
import osmnx as ox
from typing import Dict, List, Optional, Any
from backend.cache import DiskCache
from backend.models import CustomLayer

class MapDataFetcher:
    """
    Handles fetching geospatial data from OpenStreetMap via OSMnx.
    """
    
    @staticmethod
    def _fetch_graph_sync(point, dist):
        key = f"graph_{point[0]}_{point[1]}_{dist}"
        cached = DiskCache.get(key)
        if cached:
            return cached
        
        try:
            # truncate_by_edge=True prevents edge artifacts at the boundary
            G = ox.graph_from_point(point, dist=dist, dist_type='bbox', network_type='all', truncate_by_edge=True)
            DiskCache.set(key, G)
            return G
        except Exception as e:
            print(f"Error fetching graph: {e}")
            return None

    @staticmethod
    def _fetch_features_sync(point, dist, tags, name):
        # Create a deterministic key based on tags
        tag_str = "-".join([f"{k}:{v}" for k,v in sorted(tags.items())])
        key = f"feat_{name}_{point[0]}_{point[1]}_{dist}_{tag_str}"
        
        cached = DiskCache.get(key)
        if cached is not None:
            return cached
            
        try:
            feats = ox.features_from_point(point, tags=tags, dist=dist)
            if feats.empty:
                return None
            DiskCache.set(key, feats)
            return feats
        except Exception as e:
            print(f"Error fetching features {name}: {e}")
            return None

    @classmethod
    async def fetch_all(cls, lat: float, lon: float, dist: float, custom_layers: List[CustomLayer] = None) -> Dict[str, Any]:
        """
        Fetches all required map data in parallel.
        """
        point = (lat, lon)
        
        # Define tasks
        tasks = {
            "graph": asyncio.to_thread(cls._fetch_graph_sync, point, dist),
            "water": asyncio.to_thread(cls._fetch_features_sync, point, dist, {'natural': 'water', 'waterway': 'riverbank'}, "water"),
            "parks": asyncio.to_thread(cls._fetch_features_sync, point, dist, {'leisure': 'park', 'landuse': 'grass'}, "parks")
        }
        
        # Add custom layers tasks
        if custom_layers:
            for i, layer in enumerate(custom_layers):
                if layer.enabled and layer.tags:
                    tasks[f"custom_{i}"] = asyncio.to_thread(
                        cls._fetch_features_sync, point, dist, layer.tags, f"custom_{layer.label}"
                    )

        # Run all in parallel
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        # Map results back to keys
        data = {}
        keys = list(tasks.keys())
        for k, res in zip(keys, results):
            if isinstance(res, Exception):
                print(f"Task {k} failed: {res}")
                data[k] = None
            else:
                data[k] = res
                
        return data
