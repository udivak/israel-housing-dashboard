"""Queries against the normalized records collection (lat/lon based)."""

from __future__ import annotations

import os
from typing import Any

from app.db.mongo import get_db
from app.models.map import MapFilters

# normalized_records lives in the israel-housing cluster (see .env).
COLLECTION_NAME = os.getenv("FEATURES_COLLECTION", "normalized_records")
MAX_POINTS = int(os.getenv("MAP_POINTS_LIMIT", "2000"))


# Trim residential outliers — entire buildings, land, data errors.
_RESIDENTIAL = {
    "price": {"$gt": 100_000, "$lt": 50_000_000},
    "price_per_sqm": {"$gt": 1000, "$lt": 200_000},
    "area_sqm": {"$gt": 15, "$lt": 1000},
}


def _bbox_match(min_lat: float, max_lat: float, min_lng: float, max_lng: float) -> dict[str, Any]:
    return {
        "lat": {"$gte": min_lat, "$lte": max_lat, "$ne": None},
        "lon": {"$gte": min_lng, "$lte": max_lng, "$ne": None},
        **_RESIDENTIAL,
    }


def _filters_to_query(f: MapFilters | None) -> dict[str, Any]:
    if f is None:
        return {}
    q: dict[str, Any] = {}
    if f.city:
        q["city_name"] = f.city
    if f.neighborhood:
        q["neighborhood"] = f.neighborhood
    if f.property_type:
        q["deal_nature"] = f.property_type
    if f.source:
        q["source"] = f.source
    if f.min_price is not None or f.max_price is not None:
        q["price"] = {}
        if f.min_price is not None:
            q["price"]["$gte"] = f.min_price
        if f.max_price is not None:
            q["price"]["$lte"] = f.max_price
    if f.min_rooms is not None or f.max_rooms is not None:
        q["rooms"] = {}
        if f.min_rooms is not None:
            q["rooms"]["$gte"] = f.min_rooms
        if f.max_rooms is not None:
            q["rooms"]["$lte"] = f.max_rooms
    if f.min_area is not None or f.max_area is not None:
        q["area_sqm"] = {}
        if f.min_area is not None:
            q["area_sqm"]["$gte"] = f.min_area
        if f.max_area is not None:
            q["area_sqm"]["$lte"] = f.max_area
    if f.from_date is not None or f.to_date is not None:
        q["transaction_date"] = {}
        if f.from_date is not None:
            q["transaction_date"]["$gte"] = f.from_date
        if f.to_date is not None:
            q["transaction_date"]["$lte"] = f.to_date
    return q


class FeaturesRepository:
    def __init__(self) -> None:
        self._coll = get_db()[COLLECTION_NAME]

    async def cluster_by_grid(
        self,
        decimals: int,
        min_lat: float,
        max_lat: float,
        min_lng: float,
        max_lng: float,
        filters: MapFilters | None = None,
    ) -> list[dict[str, Any]]:
        """Group features in BBox by rounded lat/lon (grid cell)."""
        match = _bbox_match(min_lat, max_lat, min_lng, max_lng) | _filters_to_query(filters)
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": {
                        "lat": {"$round": ["$lat", decimals]},
                        "lon": {"$round": ["$lon", decimals]},
                    },
                    "count": {"$sum": 1},
                    "avg_price": {"$avg": "$price"},
                    "avg_price_per_sqm": {"$avg": "$price_per_sqm"},
                    "min_price": {"$min": "$price"},
                    "max_price": {"$max": "$price"},
                }
            },
            {"$limit": 5000},
        ]
        return await self._coll.aggregate(pipeline, allowDiskUse=True).to_list(length=None)

    async def points_in_bbox(
        self,
        min_lat: float,
        max_lat: float,
        min_lng: float,
        max_lng: float,
        filters: MapFilters | None = None,
        limit: int = MAX_POINTS,
    ) -> list[dict[str, Any]]:
        match = _bbox_match(min_lat, max_lat, min_lng, max_lng) | _filters_to_query(filters)
        projection = {
            "_id": 1,
            "lat": 1,
            "lon": 1,
            "price": 1,
            "price_per_sqm": 1,
            "rooms": 1,
            "area_sqm": 1,
            "city_name": 1,
            "neighborhood": 1,
            "transaction_date": 1,
        }
        cursor = self._coll.find(match, projection).limit(limit)
        return await cursor.to_list(length=limit)

    async def count_in_bbox(
        self,
        min_lat: float,
        max_lat: float,
        min_lng: float,
        max_lng: float,
        filters: MapFilters | None = None,
    ) -> int:
        match = _bbox_match(min_lat, max_lat, min_lng, max_lng) | _filters_to_query(filters)
        return await self._coll.count_documents(match)
