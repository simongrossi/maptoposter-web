import os
import json
import asyncio
from typing import Dict, Any, Tuple
from pathlib import Path
from geopy.geocoders import Nominatim
from backend.cache import DiskCache

THEMES_DIR = Path("themes")
FONTS_DIR = Path("fonts")

def load_fonts() -> Dict[str, str]:
    """Load font paths."""
    fonts = {
        'bold': str(FONTS_DIR / 'Roboto-Bold.ttf'),
        'regular': str(FONTS_DIR / 'Roboto-Regular.ttf'),
        'light': str(FONTS_DIR / 'Roboto-Light.ttf')
    }
    # Verify existence
    for _, path in fonts.items():
        if not os.path.exists(path):
            return {} # Return empty to fallback to system fonts
    return fonts

def load_theme(theme_name: str) -> Dict[str, Any]:
    """Load theme configuration."""
    if not theme_name:
        theme_name = "feature_based"
    
    path = THEMES_DIR / f"{theme_name}.json"
    if not path.exists():
        # Fallback default
        return {
            "name": "Feature-Based Shading",
            "bg": "#FFFFFF",
            "text": "#000000",
            "gradient_color": "#FFFFFF",
            "water": "#C0C0C0",
            "parks": "#F0F0F0",
            "road_motorway": "#0A0A0A",
            "road_primary": "#1A1A1A",
            "road_default": "#3A3A3A"
        }
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading theme {theme_name}: {e}")
        return {}

async def get_coordinates(city: str, country: str) -> Tuple[float, float]:
    """
    Async wrapper for geocoding with caching.
    """
    key = f"coords_{city.lower()}_{country.lower()}"
    cached = DiskCache.get(key)
    if cached:
        return cached

    # Run blocking synchronous geocoding in a thread
    def _geocode():
        geolocator = Nominatim(user_agent="city_map_poster_backend", timeout=10)
        loc = geolocator.geocode(f"{city}, {country}")
        return (loc.latitude, loc.longitude) if loc else None

    # Use asyncio.to_thread for I/O bound blocking call
    coords = await asyncio.to_thread(_geocode)
    
    if coords:
        DiskCache.set(key, coords)
        return coords
    else:
        raise ValueError(f"Could not find coordinates for {city}, {country}")
