"""Search and property detail queries against features_enriched."""

from __future__ import annotations

import os
from typing import Any

from app.db.mongo import get_db

COLLECTION_NAME = os.getenv("FEATURES_COLLECTION", "features_enriched")


class SearchRepository:
    def __init__(self) -> None:
        self._coll = get_db()[COLLECTION_NAME]

    async def autocomplete(self, q: str, limit: int = 10) -> list[dict[str, Any]]:
        """Return top suggestion buckets matching `q` across city/neighborhood/street."""
        if not q or len(q) < 2:
            return []
        regex = {"$regex": f"^{q}", "$options": "i"}
        suggestions: list[dict[str, Any]] = []
        for field in ("city", "neighborhood", "street"):
            cursor = self._coll.aggregate(
                [
                    {"$match": {field: regex}},
                    {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                    {"$limit": limit},
                ]
            )
            async for row in cursor:
                if row["_id"]:
                    suggestions.append({"type": field, "value": row["_id"], "count": row["count"]})
        suggestions.sort(key=lambda r: r["count"], reverse=True)
        return suggestions[:limit]

    async def search_properties(
        self,
        match: dict[str, Any],
        sort: list[tuple[str, int]] | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        skip = max(0, (page - 1) * size)
        total = await self._coll.count_documents(match)
        cursor = self._coll.find(match).sort(sort or [("transaction_date", -1)]).skip(skip).limit(size)
        rows = await cursor.to_list(length=size)
        return rows, total

    async def get_by_id(self, _id: Any) -> dict[str, Any] | None:
        return await self._coll.find_one({"_id": _id})

    async def similar_in_radius(
        self,
        lng: float,
        lat: float,
        radius_meters: float = 500,
        limit: int = 10,
        exclude_id: Any | None = None,
    ) -> list[dict[str, Any]]:
        match: dict[str, Any] = {
            "geometry": {
                "$nearSphere": {
                    "$geometry": {"type": "Point", "coordinates": [lng, lat]},
                    "$maxDistance": radius_meters,
                }
            }
        }
        if exclude_id is not None:
            match["_id"] = {"$ne": exclude_id}
        cursor = self._coll.find(match).limit(limit)
        return await cursor.to_list(length=limit)
