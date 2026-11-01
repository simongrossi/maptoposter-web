"""Utilitaires : themes, polices, geocodage et slugs de fichiers."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Tuple

from backend.cache import DiskCache
from backend.settings import settings

logger = logging.getLogger(__name__)

THEMES_DIR = Path(os.getenv("THEMES_DIR", "themes"))
FONTS_DIR = Path(os.getenv("FONTS_DIR", "fonts"))
THEME_ID_RE = re.compile(r"^[a-z0-9_]{1,64}$")
_SAFE_SLUG_RE = re.compile(r"[^a-z0-9]+")

DEFAULT_THEME: Dict[str, Any] = {
    "name": "Feature-Based Shading",
    "bg": "#FFFFFF",
    "text": "#000000",
    "gradient_color": "#FFFFFF",
    "water": "#C0C0C0",
    "parks": "#F0F0F0",
    "road_motorway": "#0A0A0A",
    "road_primary": "#1A1A1A",
    "road_secondary": "#2A2A2A",
    "road_tertiary": "#3A3A3A",
    "road_residential": "#4A4A4A",
    "road_default": "#3A3A3A",
}


def load_fonts() -> Dict[str, str]:
    """Chemins des polices locales, ou dict vide pour utiliser la police systeme."""
    fonts = {
        "bold": str(FONTS_DIR / "Roboto-Bold.ttf"),
        "regular": str(FONTS_DIR / "Roboto-Regular.ttf"),
        "light": str(FONTS_DIR / "Roboto-Light.ttf"),
    }
    for path in fonts.values():
        if not os.path.exists(path):
            return {}
    return fonts


def _theme_path(theme_name: str) -> Path | None:
    if not theme_name or not THEME_ID_RE.fullmatch(theme_name):
        return None
    base = THEMES_DIR.resolve()
    path = (base / f"{theme_name}.json").resolve()
    try:
        path.relative_to(base)
    except ValueError:
        return None
    return path


def load_theme(theme_name: str) -> Dict[str, Any]:
    """Charge un theme JSON sans permettre de sortie du repertoire themes/."""
    path = _theme_path(theme_name)
    if path is None or not path.exists():
        return dict(DEFAULT_THEME)

    try:
        with open(path, "r", encoding="utf-8") as handle:
            theme = json.load(handle)
        if not isinstance(theme, dict):
            raise ValueError("le fichier ne contient pas un objet JSON")
        return theme
    except Exception as exc:
        logger.warning("Theme illisible %s: %s", theme_name, exc)
        return dict(DEFAULT_THEME)


def list_themes() -> list[str]:
    """Liste triee des identifiants de themes valides."""
    if not THEMES_DIR.exists():
        return []
    themes = []
    for path in THEMES_DIR.glob("*.json"):
        if path.is_file() and THEME_ID_RE.fullmatch(path.stem):
            themes.append(path.stem)
    return sorted(themes)


def safe_slug(value: str, fallback: str = "map") -> str:
    """Slug ASCII sur pour un nom de fichier / une cle S3."""
    normalized = (
        unicodedata.normalize("NFKD", str(value))
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    slug = _SAFE_SLUG_RE.sub("_", normalized.lower()).strip("_")
    return (slug[:48].strip("_") or fallback)


async def get_coordinates(city: str, country: str) -> Tuple[float, float]:
    """Geocodage Nominatim avec cache disque (appel bloquant dans un thread)."""
    key = "coords_" + hashlib.sha256(
        f"{city.strip().lower()}|{country.strip().lower()}".encode("utf-8")
    ).hexdigest()[:32]
    cached = DiskCache.get(key)
    if cached and len(cached) == 2:
        return float(cached[0]), float(cached[1])

    def _geocode() -> tuple[float, float] | None:
        # Import local : l'API n'a pas besoin de geopy pour demarrer.
        from geopy.geocoders import Nominatim

        geolocator = Nominatim(
            user_agent=settings.nominatim_user_agent,
            timeout=settings.geocode_timeout,
        )
        location = geolocator.geocode(f"{city}, {country}", exactly_one=True)
        if not location:
            return None
        return (float(location.latitude), float(location.longitude))

    coords = await asyncio.to_thread(_geocode)
    if not coords:
        raise ValueError(f"Could not find coordinates for {city}, {country}")

    latitude, longitude = coords
    if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
        raise ValueError("Coordonnees invalides retournees par le geocodeur.")

    DiskCache.set(key, (latitude, longitude))
    return latitude, longitude
