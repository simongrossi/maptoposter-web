"""Cache disque local (graphes OSM, geometries, coordonnees).

Le worker est le seul ecrivain de ce cache, monte sur un volume Docker dedie.
Les ecritures sont atomiques pour resister a un arret brutal du conteneur.
"""

from __future__ import annotations

import hashlib
import os
import pickle
import tempfile
from pathlib import Path
from typing import Any, Optional

from backend.settings import settings  # noqa: F401  (charge/valide la config)

CACHE_DIR = Path(os.getenv("CACHE_DIR", ".cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class DiskCache:
    """Cache fichier robuste, cle hashee en SHA-256."""

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    @staticmethod
    def _path(key: str) -> Path:
        return CACHE_DIR / f"{DiskCache._hash_key(key)}.pkl"

    @staticmethod
    def get(key: str) -> Optional[Any]:
        path = DiskCache._path(key)
        if not path.exists():
            return None
        try:
            with open(path, "rb") as handle:
                return pickle.load(handle)
        except Exception as exc:
            print(f"Cache read error for {key}: {exc}")
            return None

    @staticmethod
    def set(key: str, value: Any) -> None:
        path = DiskCache._path(key)
        tmp_path: str | None = None
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(CACHE_DIR), prefix=".tmp-", suffix=".pkl"
            )
            with os.fdopen(fd, "wb") as handle:
                pickle.dump(value, handle, protocol=pickle.HIGHEST_PROTOCOL)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, path)
            tmp_path = None
        except Exception as exc:
            print(f"Cache write error for {key}: {exc}")
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
