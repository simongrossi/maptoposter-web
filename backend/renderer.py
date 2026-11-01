import matplotlib

matplotlib.use("Agg")

import matplotlib.colors as mcolors
import numpy as np
import osmnx as ox
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from shapely.geometry import Point
from typing import Dict, Any, List, Optional

from backend.models import CustomLayer
from backend.utils import load_fonts

class MapRenderer:
    def __init__(self, theme: Dict[str, Any]):
        self.theme = theme or {}
        self.fonts = load_fonts()

    def _get_font(self, type: str, size: float):
        if self.fonts and type in self.fonts:
            return FontProperties(fname=self.fonts[type], size=size)
        return FontProperties(
            family="monospace",
            weight="bold" if "bold" in type else "normal",
            size=size,
        )

    def _get_edge_colors(self, G):
        colors = []
        for _, _, data in G.edges(data=True):
            highway = data.get("highway", "unclassified")
            if isinstance(highway, list):
                highway = highway[0] if highway else "unclassified"

            if highway in ["motorway", "motorway_link"]:
                color = self.theme.get("road_motorway", "#000000")
            elif highway in ["trunk", "trunk_link", "primary", "primary_link"]:
                color = self.theme.get("road_primary", "#111111")
            elif highway in ["secondary", "secondary_link"]:
                color = self.theme.get("road_secondary", "#222222")
            elif highway in ["tertiary", "tertiary_link"]:
                color = self.theme.get("road_tertiary", "#333333")
            elif highway in ["residential", "living_street"]:
                color = self.theme.get("road_residential", "#444444")
            else:
                color = self.theme.get("road_default", "#333333")
            colors.append(color)
        return colors

    def _get_edge_widths(self, G):
        widths = []
        for _, _, data in G.edges(data=True):
            highway = data.get("highway", "unclassified")
            if isinstance(highway, list):
                highway = highway[0] if highway else "unclassified"

            if highway in ["motorway", "motorway_link"]:
                width = 1.2
            elif highway in ["trunk", "trunk_link", "primary", "primary_link"]:
                width = 1.0
            elif highway in ["secondary", "secondary_link"]:
                width = 0.8
            elif highway in ["tertiary", "tertiary_link"]:
                width = 0.6
            else:
                width = 0.4
            widths.append(width)
        return widths

    def _create_gradient(self, ax, color, location="bottom"):
        vals = np.linspace(0, 1, 256).reshape(-1, 1)
        gradient = np.hstack((vals, vals))
        rgb = mcolors.to_rgb(color)
        my_colors = np.zeros((256, 4))
        my_colors[:, :3] = rgb

        if location == "bottom":
            my_colors[:, 3] = np.linspace(1, 0, 256)
            extent_y_factor = (0, 0.25)
        else:
            my_colors[:, 3] = np.linspace(0, 1, 256)
            extent_y_factor = (0.75, 1.0)

        custom_cmap = mcolors.ListedColormap(my_colors)
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        y_range = ylim[1] - ylim[0]

        y_bottom = ylim[0] + y_range * extent_y_factor[0]
        y_top = ylim[0] + y_range * extent_y_factor[1]

        ax.imshow(
            gradient,
            extent=[xlim[0], xlim[1], y_bottom, y_top],
            aspect="auto",
            cmap=custom_cmap,
            zorder=10,
            origin="lower",
        )

    def render(
        self,
        data: Dict[str, Any],
        city: str,
        country: str,
        point: tuple,
        dist: float,
        width_in: float,
        height_in: float,
        custom_layers_config: Optional[List[CustomLayer]] = None,
        text_CONFIG: Optional[Dict[str, str]] = None,
        margins: float = 0.0,
    ) -> Figure:
        G = data.get("graph")
        if not G:
            raise ValueError("Graph data missing")

        background = self.theme.get("bg", "#FFFFFF")
        text_color = self.theme.get("text", "#000000")
        gradient_color = self.theme.get("gradient_color", background)

        fig = Figure(figsize=(width_in, height_in), facecolor=background)
        ax = fig.add_subplot(111)
        ax.set_facecolor(background)

        # Marges relatives (en pouces), clampees pour eviter un rendu vide.
        m_x = margins / width_in
        m_y = margins / height_in
        if m_x > 0.4:
            m_x = 0.4
        if m_y > 0.4:
            m_y = 0.4

        fig.subplots_adjust(left=m_x, right=1 - m_x, bottom=m_y, top=1 - m_y)

        G_proj = ox.project_graph(G)

        water = data.get("water")
        if water is not None and not water.empty:
            try:
                water_proj = ox.projection.project_gdf(water)
            except Exception:
                water_proj = water.to_crs(G_proj.graph["crs"])
            water_proj = water_proj[
                water_proj.geometry.type.isin(["Polygon", "MultiPolygon"])
            ]
            if not water_proj.empty:
                water_proj.plot(
                    ax=ax,
                    facecolor=self.theme.get("water", "#C0C0C0"),
                    edgecolor="none",
                    zorder=1,
                )

        parks = data.get("parks")
        if parks is not None and not parks.empty:
            try:
                parks_proj = ox.projection.project_gdf(parks)
            except Exception:
                parks_proj = parks.to_crs(G_proj.graph["crs"])
            parks_proj = parks_proj[
                parks_proj.geometry.type.isin(["Polygon", "MultiPolygon"])
            ]
            if not parks_proj.empty:
                parks_proj.plot(
                    ax=ax,
                    facecolor=self.theme.get("parks", "#F0F0F0"),
                    edgecolor="none",
                    zorder=2,
                )

        ec = self._get_edge_colors(G_proj)
        ew = self._get_edge_widths(G_proj)
        ox.plot_graph(
            G_proj,
            ax=ax,
            bgcolor=background,
            node_size=0,
            edge_color=ec,
            edge_linewidth=ew,
            show=False,
            close=False,
        )

        if custom_layers_config:
            for index, layer in enumerate(custom_layers_config):
                features = data.get(f"custom_{index}")
                if features is not None and not features.empty:
                    try:
                        features_proj = ox.projection.project_gdf(features)
                    except Exception:
                        features_proj = features.to_crs(G_proj.graph["crs"])
                    features_proj.plot(
                        ax=ax,
                        color=layer.color,
                        linewidth=layer.width,
                        alpha=0.9,
                        zorder=5,
                    )

        center_proj = ox.projection.project_geometry(
            Point(point[1], point[0]), crs="EPSG:4326", to_crs=G_proj.graph["crs"]
        )[0]
        cx, cy = center_proj.x, center_proj.y
        aspect = width_in / height_in

        half_x = dist
        half_y = dist
        if aspect > 1:
            half_y = half_x / aspect
        else:
            half_x = half_y * aspect

        ax.set_xlim(cx - half_x, cx + half_x)
        ax.set_ylim(cy - half_y, cy + half_y)
        ax.set_aspect("equal")

        self._create_gradient(ax, gradient_color, "bottom")
        self._create_gradient(ax, gradient_color, "top")

        labels = text_CONFIG or {}
        scale = width_in / 12.0

        city_label = labels.get("name_label") or city
        spaced_city = "  ".join(list(city_label.upper()))
        font_main = self._get_font("bold", 60 * scale)
        if len(city_label) > 10:
            font_main.set_size(max(60 * scale * (10 / len(city_label)), 10))

        # parse_math=False : un libelle utilisateur contenant "$" ne doit pas
        # etre interprete comme du mathtext par Matplotlib.
        ax.text(
            0.5,
            0.14,
            spaced_city,
            transform=ax.transAxes,
            color=text_color,
            ha="center",
            fontproperties=font_main,
            zorder=11,
            parse_math=False,
        )

        country_label = labels.get("country_label") or country
        font_sub = self._get_font("light", 22 * scale)
        ax.text(
            0.5,
            0.10,
            country_label.upper(),
            transform=ax.transAxes,
            color=text_color,
            ha="center",
            fontproperties=font_sub,
            zorder=11,
            parse_math=False,
        )

        lat, lon = point
        coords_str = (
            f"{lat:.4f}° N / {lon:.4f}° E"
            if lat >= 0
            else f"{abs(lat):.4f}° S / {lon:.4f}° E"
        )
        coords_str = coords_str.replace("E", "W") if lon < 0 else coords_str
        font_coords = self._get_font("regular", 14 * scale)
        ax.text(
            0.5,
            0.07,
            coords_str,
            transform=ax.transAxes,
            color=text_color,
            alpha=0.7,
            ha="center",
            fontproperties=font_coords,
            zorder=11,
            parse_math=False,
        )

        ax.plot(
            [0.4, 0.6],
            [0.125, 0.125],
            transform=ax.transAxes,
            color=text_color,
            linewidth=1 * scale,
            zorder=11,
        )

        return fig
