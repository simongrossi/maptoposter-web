from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class CustomLayer(BaseModel):
    label: str
    tags: Dict[str, Any]
    color: str
    width: float = 1.0
    enabled: bool = True

class CustomColors(BaseModel):
    """Overrides for theme colors."""
    bg: Optional[str] = None
    water: Optional[str] = None
    parks: Optional[str] = None
    roads: Optional[str] = None # Applied to all road types for simplicity or specific override? User asked for customization.
    text: Optional[str] = None

class PosterRequest(BaseModel):
    city: str
    country: str
    style: str = "feature_based"  # Refers to theme
    distance: int = 10000
    width: float = 12.0
    height: float = 16.0
    country_label: Optional[str] = None
    name_label: Optional[str] = None
    custom_layers: Optional[List[CustomLayer]] = None
    custom_colors: Optional[CustomColors] = None
    format: str = "png"
    
    # Advanced Print Settings
    dpi: int = 300
    margins: float = 0.0 # inches
    paper_size: str = "custom" # metadata
