import pytest
from backend.renderer import MapRenderer
from backend.models import CustomLayer
from typing import Dict, Any

def test_renderer_initialization():
    """Test renderer initializes with a theme."""
    theme = {"bg": "#fff", "water": "#00f", "road_primary": "#000"}
    renderer = MapRenderer(theme)
    assert renderer.theme == theme

# Unit testing the actual 'render' method is hard without real Data/Geopandas objects.
# We would need to mock the entire 'data' dictionary with valid GeoDataFrames.
# For Phase 5 'Safety Net', ensuring the class initializes is a good start.
# A more advanced test would mock OSM fetcher data.
