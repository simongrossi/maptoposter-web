import pytest

pytest.importorskip("matplotlib")
pytest.importorskip("osmnx")

from backend.models import CustomLayer  # noqa: E402
from backend.renderer import MapRenderer  # noqa: E402


def test_renderer_initialization():
    """Le renderer s'initialise avec un theme."""
    theme = {"bg": "#fff", "water": "#00f", "road_primary": "#000"}
    renderer = MapRenderer(theme)
    assert renderer.theme == theme


# Le rendu complet necessite de vraies GeoDataFrames OSMnx ; il est couvert
# par les tests d'integration du worker.
