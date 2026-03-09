"""Models for map layer metadata and styling."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class LayerConfig(BaseModel):
    """Map layer configuration with styling and source metadata."""

    id: str = Field(..., description="Unique layer identifier")
    name: str = Field(..., description="Display name for the layer")
    type: Literal["fill", "line", "circle", "symbol"] = Field(
        default="fill",
        description="MapLibre layer type",
    )
    color: str = Field(default="#3388ff", description="Hex color for fills/lines")
    source: str = Field(..., description="MongoDB collection or data source name")
    min_zoom: Optional[float] = Field(default=None, description="Minimum zoom level to show")
    max_zoom: Optional[float] = Field(default=None, description="Maximum zoom level to show")
    opacity: float = Field(default=0.8, ge=0, le=1)
