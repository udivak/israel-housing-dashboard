"""Strict Pydantic v2 models for GeoJSON per RFC 7946."""

from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field


# --- Geometry types ---


class Point(BaseModel):
    """GeoJSON Point geometry."""

    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float] = Field(
        ...,
        description="[longitude, latitude] per RFC 7946",
        min_length=2,
        max_length=2,
    )


class LineString(BaseModel):
    """GeoJSON LineString geometry."""

    type: Literal["LineString"] = "LineString"
    coordinates: list[tuple[float, float]] = Field(
        ...,
        description="Array of [longitude, latitude] positions",
        min_length=2,
    )


class Polygon(BaseModel):
    """GeoJSON Polygon geometry (exterior ring, optional interior rings)."""

    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[tuple[float, float]]] = Field(
        ...,
        description="First element is exterior ring, rest are holes",
        min_length=1,
    )


class MultiPoint(BaseModel):
    """GeoJSON MultiPoint geometry."""

    type: Literal["MultiPoint"] = "MultiPoint"
    coordinates: list[tuple[float, float]] = Field(..., min_length=1)


class MultiLineString(BaseModel):
    """GeoJSON MultiLineString geometry."""

    type: Literal["MultiLineString"] = "MultiLineString"
    coordinates: list[list[tuple[float, float]]] = Field(..., min_length=1)


class MultiPolygon(BaseModel):
    """GeoJSON MultiPolygon geometry."""

    type: Literal["MultiPolygon"] = "MultiPolygon"
    coordinates: list[list[list[tuple[float, float]]]] = Field(..., min_length=1)


Geometry = Union[Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon]


# --- Feature & FeatureCollection ---


class Feature(BaseModel):
    """GeoJSON Feature with geometry and optional properties."""

    type: Literal["Feature"] = "Feature"
    geometry: Optional[Geometry] = Field(..., description="GeoJSON geometry or null")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict)
    id: Optional[Union[str, int]] = Field(default=None, description="Optional feature identifier")


class FeatureCollection(BaseModel):
    """GeoJSON FeatureCollection - the standard response format for map features."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[Feature] = Field(default_factory=list)
