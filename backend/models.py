"""Modeles Pydantic : validation stricte de toutes les entrees client.

Les plafonds (distance, dimensions, DPI, nombre de couches, taille des
metadonnees) protegent le worker contre les demandes qui provoqueraient un
epuisement memoire ou un rendu demesure.
"""

from __future__ import annotations

import re
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.settings import settings

THEME_ID_RE = re.compile(r"^[a-z0-9_]{1,64}$")
HEX_COLOR_RE = r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$"
PAPER_SIZE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 x_.-]{0,31}$")
CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")
# Charset volontairement restrictif : empeche l'injection de syntaxe Overpass
# QL via les cles/valeurs de tags OSM fournies par le client.
OSM_TAG_KEY_RE = re.compile(r"^[A-Za-z0-9_:.\-]{1,40}$")
OSM_TAG_VALUE_RE = re.compile(r"^[A-Za-z0-9_:.\- /]{1,64}$")

OSM_TAG_VALUE = Union[str, int, float, bool, List[str]]


class CustomLayer(BaseModel):
    """Couche OSM supplementaire demandee par l'utilisateur."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    label: str = Field(min_length=1, max_length=40)
    tags: Dict[str, OSM_TAG_VALUE] = Field(min_length=1, max_length=8)
    color: str = Field(pattern=HEX_COLOR_RE)
    width: float = Field(default=1.0, ge=0.1, le=10.0)
    enabled: bool = True

    @field_validator("label")
    @classmethod
    def validate_label(cls, label: str) -> str:
        if CONTROL_CHARS_RE.search(label):
            raise ValueError("Caractere de controle interdit dans le libelle.")
        return label

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, tags: Dict[str, OSM_TAG_VALUE]) -> Dict[str, OSM_TAG_VALUE]:
        for key, value in tags.items():
            if not OSM_TAG_KEY_RE.fullmatch(key):
                raise ValueError("Cle de tag OSM invalide.")
            if isinstance(value, list):
                if len(value) > 10:
                    raise ValueError("Une liste de valeurs OSM est limitee a 10 entrees.")
                if any(
                    not isinstance(item, str)
                    or not OSM_TAG_VALUE_RE.fullmatch(item)
                    for item in value
                ):
                    raise ValueError("Valeur de tag OSM invalide.")
            elif isinstance(value, str):
                if not OSM_TAG_VALUE_RE.fullmatch(value):
                    raise ValueError("Valeur de tag OSM invalide.")
        return tags


class CustomColors(BaseModel):
    """Surcharges de couleurs d'un theme."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    bg: Optional[str] = Field(default=None, pattern=HEX_COLOR_RE)
    water: Optional[str] = Field(default=None, pattern=HEX_COLOR_RE)
    parks: Optional[str] = Field(default=None, pattern=HEX_COLOR_RE)
    roads: Optional[str] = Field(default=None, pattern=HEX_COLOR_RE)
    text: Optional[str] = Field(default=None, pattern=HEX_COLOR_RE)


class PosterRequest(BaseModel):
    """Requete de generation d'une affiche."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    city: str = Field(min_length=1, max_length=120)
    country: str = Field(min_length=1, max_length=120)
    style: str = Field(default="feature_based", pattern=THEME_ID_RE)
    all_themes: bool = False

    distance: int = Field(
        default=10000, ge=1000, le=settings.max_distance_m
    )
    width: float = Field(
        default=12.0, ge=1.0, le=settings.max_dimension_inches
    )
    height: float = Field(
        default=16.0, ge=1.0, le=settings.max_dimension_inches
    )

    country_label: Optional[str] = Field(default=None, max_length=120)
    name_label: Optional[str] = Field(default=None, max_length=120)
    custom_layers: Optional[List[CustomLayer]] = Field(default=None, max_length=10)
    custom_colors: Optional[CustomColors] = None

    format: Literal["png", "svg", "pdf"] = "png"
    dpi: int = Field(default=300, ge=72, le=settings.max_dpi)
    margins: float = Field(default=0.0, ge=0.0, le=5.0)
    paper_size: str = Field(default="custom", max_length=32)

    @field_validator("city", "country", "country_label", "name_label")
    @classmethod
    def validate_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if CONTROL_CHARS_RE.search(value):
            raise ValueError("Caractere de controle interdit dans le libelle.")
        return value

    @field_validator("paper_size")
    @classmethod
    def validate_paper_size(cls, value: str) -> str:
        if not PAPER_SIZE_RE.fullmatch(value):
            raise ValueError("Format de papier invalide.")
        return value

    @model_validator(mode="after")
    def validate_output_size(self) -> "PosterRequest":
        pixels = self.width * self.height * self.dpi * self.dpi
        if pixels > settings.max_output_pixels:
            raise ValueError(
                "La resolution demandee est trop elevee "
                f"({int(pixels)} pixels, maximum {settings.max_output_pixels}). "
                "Reduisez les dimensions ou le DPI."
            )
        return self
