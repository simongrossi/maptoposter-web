import os
import pickle
import hashlib
from pathlib import Path
from typing import Any, Optional

CACHE_DIR = Path(".cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

class DiskCache:
    """
    Robust file-based cache using MD5 hashes of keys.
    """
    @staticmethod
    def _hash_key(key: str) -> str:
        """Generate MD5 hash for the key to avoid filename collisions."""
        return hashlib.md5(key.encode("utf-8")).hexdigest()

    @staticmethod
    def get(key: str) -> Optional[Any]:
        hashed = DiskCache._hash_key(key)
        path = CACHE_DIR / f"{hashed}.pkl"
        if not path.exists():
            return None
        try:
            with open(path, "rb") as f:
                # print(f"DEBUG: Cache hit for {key} -> {hashed}")
                return pickle.load(f)
        except Exception as e:
            print(f"Cache read error for {key}: {e}")
            return None

    @staticmethod
    def set(key: str, value: Any) -> None:
        hashed = DiskCache._hash_key(key)
        path = CACHE_DIR / f"{hashed}.pkl"
        try:
            with open(path, "wb") as f:
                pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL)
                # print(f"DEBUG: Cache saved for {key} -> {hashed}")
        except Exception as e:
            print(f"Cache write error for {key}: {e}")
