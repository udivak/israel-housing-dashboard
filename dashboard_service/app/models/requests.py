"""Pydantic validation for API request parameters."""

from pydantic import BaseModel, Field, field_validator


class BBoxQueryParams(BaseModel):
    """Bounding box query parameters for map feature requests."""

    min_lat: float = Field(..., ge=-90, le=90, description="Minimum latitude (south)")
    max_lat: float = Field(..., ge=-90, le=90, description="Maximum latitude (north)")
    min_lng: float = Field(..., ge=-180, le=180, description="Minimum longitude (west)")
    max_lng: float = Field(..., ge=-180, le=180, description="Maximum longitude (east)")
    layer_id: str = Field(..., min_length=1, description="Layer/collection identifier")

    @field_validator("max_lat")
    @classmethod
    def max_lat_gte_min_lat(cls, v: float, info) -> float:
        if "min_lat" in info.data and v < info.data["min_lat"]:
            raise ValueError("max_lat must be >= min_lat")
        return v

    @field_validator("max_lng")
    @classmethod
    def max_lng_gte_min_lng(cls, v: float, info) -> float:
        if "min_lng" in info.data and v < info.data["min_lng"]:
            raise ValueError("max_lng must be >= min_lng")
        return v
