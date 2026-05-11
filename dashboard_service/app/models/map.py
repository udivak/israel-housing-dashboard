"""Pydantic models for map data endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class MapFilters(BaseModel):
    city: str | None = None
    neighborhood: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    min_rooms: float | None = None
    max_rooms: float | None = None
    min_area: float | None = None
    max_area: float | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None
    property_type: str | None = None
    source: str | None = None


class ClusterCell(BaseModel):
    h3: str
    lat: float
    lng: float
    count: int
    median_price: float | None = None
    median_price_per_sqm: float | None = None
    min_price: float | None = None
    max_price: float | None = None


class ClusterResponse(BaseModel):
    type: Literal["clusters"] = "clusters"
    resolution: int
    cells: list[ClusterCell]


class PointFeature(BaseModel):
    id: str
    lat: float
    lng: float
    price: float | None = None
    price_per_sqm: float | None = None
    rooms: float | None = None
    area_sqm: float | None = None
    city: str | None = None
    neighborhood: str | None = None
    transaction_date: datetime | None = None
    coord_source: str | None = None


class PointsResponse(BaseModel):
    type: Literal["points"] = "points"
    truncated: bool = False
    features: list[PointFeature]


MapDataResponse = ClusterResponse | PointsResponse


class BBoxParams(BaseModel):
    min_lat: float = Field(..., ge=-90, le=90)
    max_lat: float = Field(..., ge=-90, le=90)
    min_lng: float = Field(..., ge=-180, le=180)
    max_lng: float = Field(..., ge=-180, le=180)
    zoom: int = Field(..., ge=0, le=22)
