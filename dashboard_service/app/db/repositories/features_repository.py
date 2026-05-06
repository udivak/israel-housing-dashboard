"""Queries against `features_enriched` for map clustering and point fetches."""

from __future__ import annotations

import os
from typing import Any

from app.db.mongo import get_db
from app.models.map import MapFilters

COLLECTION_NAME = os.getenv("FEATURES_COLLECTION", "features_enriched")
MAX_POINTS = int(os.getenv("MAP_POINTS_LIMIT", "2000"))


def _bbox_match(min_lat: float, max_lat: float, min_lng: float, max_lng: float) -> dict[str, Any]:
    box = [[min_lng, min_lat], [max_lng, max_lat]]
    return {"geometry": {"$geoWithin": {"$box": box}}}


def _filters_to_query(f: MapFilters | None) -> dict[str, Any]:
    if f is None:
        return {}
    q: dict[str, Any] = {}
    if f.city:
        q["city"] = f.city
    if f.neighborhood:
        q["neighborhood"] = f.neighborhood
    if f.property_type:
        q["deal_nature"] = f.property_type
    if f.source:
        q["source_name"] = f.source
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

    async def cluster_by_h3(
        self,
        resolution: int,
        min_lat: float,
        max_lat: float,
        min_lng: float,
        max_lng: float,
        filters: MapFilters | None = None,
    ) -> list[dict[str, Any]]:
        """Group features in BBox by h3_r{resolution}, return cell stats."""
        h3_field = f"$h3_r{resolution}"
        match = _bbox_match(min_lat, max_lat, min_lng, max_lng) | _filters_to_query(filters)
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": h3_field,
                    "count": {"$sum": 1},
                    "avg_price": {"$avg": "$price"},
                    "avg_price_per_sqm": {"$avg": "$price_per_sqm"},
                    "min_price": {"$min": "$price"},
                    "max_price": {"$max": "$price"},
                }
            },
            {"$match": {"_id": {"$ne": None}}},
            {"$limit": 5000},
        ]
        cursor = self._coll.aggregate(pipeline, allowDiskUse=True)
        return await cursor.to_list(length=None)

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
            "geometry": 1,
            "price": 1,
            "price_per_sqm": 1,
            "rooms": 1,
            "area_sqm": 1,
            "city": 1,
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
