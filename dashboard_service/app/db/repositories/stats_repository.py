"""Aggregations for dashboard statistics."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from app.db.mongo import get_db
from app.models.map import MapFilters
from app.db.repositories.features_repository import _filters_to_query

COLLECTION_NAME = os.getenv("FEATURES_COLLECTION", "features_enriched")


class StatsRepository:
    def __init__(self) -> None:
        self._coll = get_db()[COLLECTION_NAME]

    async def summary(self, filters: MapFilters | None = None) -> dict[str, Any]:
        """KPIs: count, avg price, avg ₪/m², date range, distinct cities."""
        match = _filters_to_query(filters)
        pipeline = [
            {"$match": match} if match else {"$match": {}},
            {
                "$group": {
                    "_id": None,
                    "count": {"$sum": 1},
                    "avg_price": {"$avg": "$price"},
                    "avg_price_per_sqm": {"$avg": "$price_per_sqm"},
                    "min_date": {"$min": "$transaction_date"},
                    "max_date": {"$max": "$transaction_date"},
                    "distinct_cities": {"$addToSet": "$city"},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "count": 1,
                    "avg_price": 1,
                    "avg_price_per_sqm": 1,
                    "min_date": 1,
                    "max_date": 1,
                    "distinct_cities_count": {"$size": "$distinct_cities"},
                }
            },
        ]
        rows = await self._coll.aggregate(pipeline).to_list(length=1)
        return rows[0] if rows else {"count": 0}

    async def timeseries(
        self,
        granularity: str = "month",
        filters: MapFilters | None = None,
    ) -> list[dict[str, Any]]:
        """Avg price + volume by time bucket."""
        match = _filters_to_query(filters)
        match.setdefault("transaction_date", {"$ne": None})

        date_format = {"month": "%Y-%m", "quarter": "%Y-Q", "year": "%Y"}.get(granularity, "%Y-%m")
        if granularity == "quarter":
            id_expr = {
                "$concat": [
                    {"$toString": {"$year": "$transaction_date"}},
                    "-Q",
                    {"$toString": {"$ceil": {"$divide": [{"$month": "$transaction_date"}, 3]}}},
                ]
            }
        else:
            id_expr = {"$dateToString": {"format": date_format, "date": "$transaction_date"}}

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": id_expr,
                    "avg_price": {"$avg": "$price"},
                    "avg_price_per_sqm": {"$avg": "$price_per_sqm"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
            {"$project": {"_id": 0, "bucket": "$_id", "avg_price": 1, "avg_price_per_sqm": 1, "count": 1}},
        ]
        return await self._coll.aggregate(pipeline, allowDiskUse=True).to_list(length=None)

    async def by_region(
        self,
        level: str = "city",
        metric: str = "avg_price_per_sqm",
        limit: int = 50,
        filters: MapFilters | None = None,
    ) -> list[dict[str, Any]]:
        """Top regions by metric (city or neighborhood)."""
        if level not in ("city", "neighborhood"):
            level = "city"
        if metric not in ("avg_price_per_sqm", "avg_price", "count"):
            metric = "avg_price_per_sqm"
        match = _filters_to_query(filters)
        match.setdefault(level, {"$ne": None})
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": f"${level}",
                    "avg_price": {"$avg": "$price"},
                    "avg_price_per_sqm": {"$avg": "$price_per_sqm"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {metric: -1}},
            {"$limit": limit},
            {"$project": {"_id": 0, "region": "$_id", "avg_price": 1, "avg_price_per_sqm": 1, "count": 1}},
        ]
        return await self._coll.aggregate(pipeline, allowDiskUse=True).to_list(length=None)

    async def distribution(
        self,
        field: str,
        bins: int = 30,
        filters: MapFilters | None = None,
    ) -> list[dict[str, Any]]:
        """Histogram of `field`. Uses $bucketAuto."""
        if field not in ("price", "price_per_sqm", "rooms", "area_sqm", "year_built"):
            field = "price"
        match = _filters_to_query(filters)
        match.setdefault(field, {"$ne": None})
        pipeline = [
            {"$match": match},
            {
                "$bucketAuto": {
                    "groupBy": f"${field}",
                    "buckets": bins,
                    "output": {"count": {"$sum": 1}},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "min": "$_id.min",
                    "max": "$_id.max",
                    "count": 1,
                }
            },
        ]
        return await self._coll.aggregate(pipeline, allowDiskUse=True).to_list(length=None)

    async def yoy_by_city(self, top: int = 20) -> list[dict[str, Any]]:
        """Year-over-year price change %, by city. Compares last full year vs prev."""
        pipeline = [
            {"$match": {"city": {"$ne": None}, "transaction_date": {"$ne": None}, "price_per_sqm": {"$ne": None}}},
            {
                "$group": {
                    "_id": {"city": "$city", "year": {"$year": "$transaction_date"}},
                    "avg_price_per_sqm": {"$avg": "$price_per_sqm"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.year": -1}},
            {
                "$group": {
                    "_id": "$_id.city",
                    "yearly": {"$push": {"year": "$_id.year", "avg": "$avg_price_per_sqm", "count": "$count"}},
                }
            },
            {"$match": {"$expr": {"$gte": [{"$size": "$yearly"}, 2]}}},
            {
                "$project": {
                    "_id": 0,
                    "city": "$_id",
                    "current": {"$arrayElemAt": ["$yearly", 0]},
                    "previous": {"$arrayElemAt": ["$yearly", 1]},
                }
            },
            {
                "$project": {
                    "city": 1,
                    "current_year": "$current.year",
                    "current_avg": "$current.avg",
                    "current_count": "$current.count",
                    "previous_year": "$previous.year",
                    "previous_avg": "$previous.avg",
                    "yoy_pct": {
                        "$multiply": [
                            {"$divide": [{"$subtract": ["$current.avg", "$previous.avg"]}, "$previous.avg"]},
                            100,
                        ]
                    },
                }
            },
            {"$match": {"current_count": {"$gte": 30}}},
            {"$sort": {"yoy_pct": -1}},
            {"$limit": top},
        ]
        return await self._coll.aggregate(pipeline, allowDiskUse=True).to_list(length=None)

    async def source_breakdown(self) -> list[dict[str, Any]]:
        """Count per source_name + most-recent ingestion date."""
        pipeline = [
            {
                "$group": {
                    "_id": "$source_name",
                    "count": {"$sum": 1},
                    "max_date": {"$max": "$transaction_date"},
                }
            },
            {"$project": {"_id": 0, "source": "$_id", "count": 1, "max_date": 1}},
            {"$sort": {"count": -1}},
        ]
        return await self._coll.aggregate(pipeline).to_list(length=None)

    async def property_type_breakdown(self, filters: MapFilters | None = None) -> list[dict[str, Any]]:
        match = _filters_to_query(filters)
        match.setdefault("deal_nature", {"$ne": None})
        pipeline = [
            {"$match": match},
            {"$group": {"_id": "$deal_nature", "count": {"$sum": 1}, "avg_price": {"$avg": "$price"}}},
            {"$sort": {"count": -1}},
            {"$project": {"_id": 0, "type": "$_id", "count": 1, "avg_price": 1}},
        ]
        return await self._coll.aggregate(pipeline).to_list(length=None)

    async def seasonality(self, filters: MapFilters | None = None) -> list[dict[str, Any]]:
        match = _filters_to_query(filters)
        match.setdefault("transaction_date", {"$ne": None})
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": {"$month": "$transaction_date"},
                    "count": {"$sum": 1},
                    "avg_price": {"$avg": "$price"},
                }
            },
            {"$sort": {"_id": 1}},
            {"$project": {"_id": 0, "month": "$_id", "count": 1, "avg_price": 1}},
        ]
        return await self._coll.aggregate(pipeline).to_list(length=None)
