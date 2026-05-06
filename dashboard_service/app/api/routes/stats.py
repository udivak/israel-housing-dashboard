"""Statistics endpoints for dashboard charts and KPIs."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query

from app.db.repositories.stats_repository import StatsRepository
from app.models.map import MapFilters

router = APIRouter(prefix="/stats", tags=["Stats"])


def _build_filters(
    city: str | None,
    neighborhood: str | None,
    min_price: float | None,
    max_price: float | None,
    min_rooms: float | None,
    max_rooms: float | None,
    from_date: datetime | None,
    to_date: datetime | None,
    property_type: str | None,
    source: str | None,
) -> MapFilters:
    return MapFilters(
        city=city, neighborhood=neighborhood,
        min_price=min_price, max_price=max_price,
        min_rooms=min_rooms, max_rooms=max_rooms,
        from_date=from_date, to_date=to_date,
        property_type=property_type, source=source,
    )


@router.get("/summary")
async def summary(
    city: str | None = Query(None),
    neighborhood: str | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    min_rooms: float | None = Query(None, ge=0),
    max_rooms: float | None = Query(None, ge=0),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    property_type: str | None = Query(None),
    source: str | None = Query(None),
):
    filters = _build_filters(city, neighborhood, min_price, max_price, min_rooms, max_rooms,
                             from_date, to_date, property_type, source)
    return await StatsRepository().summary(filters)


@router.get("/timeseries")
async def timeseries(
    granularity: str = Query("month", pattern="^(month|quarter|year)$"),
    city: str | None = Query(None),
    neighborhood: str | None = Query(None),
):
    filters = MapFilters(city=city, neighborhood=neighborhood)
    return await StatsRepository().timeseries(granularity, filters)


@router.get("/by-region")
async def by_region(
    level: str = Query("city", pattern="^(city|neighborhood)$"),
    metric: str = Query("avg_price_per_sqm", pattern="^(avg_price_per_sqm|avg_price|count)$"),
    limit: int = Query(50, ge=1, le=500),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
):
    filters = MapFilters(from_date=from_date, to_date=to_date)
    return await StatsRepository().by_region(level=level, metric=metric, limit=limit, filters=filters)


@router.get("/distribution")
async def distribution(
    field: str = Query("price", pattern="^(price|price_per_sqm|rooms|area_sqm|year_built)$"),
    bins: int = Query(30, ge=5, le=100),
    city: str | None = Query(None),
    neighborhood: str | None = Query(None),
):
    filters = MapFilters(city=city, neighborhood=neighborhood)
    return await StatsRepository().distribution(field=field, bins=bins, filters=filters)


@router.get("/yoy-by-city")
async def yoy_by_city(top: int = Query(20, ge=5, le=100)):
    return await StatsRepository().yoy_by_city(top=top)


@router.get("/source-breakdown")
async def source_breakdown():
    return await StatsRepository().source_breakdown()


@router.get("/property-type-breakdown")
async def property_type_breakdown(
    city: str | None = Query(None),
    neighborhood: str | None = Query(None),
):
    filters = MapFilters(city=city, neighborhood=neighborhood)
    return await StatsRepository().property_type_breakdown(filters)


@router.get("/seasonality")
async def seasonality(
    city: str | None = Query(None),
):
    filters = MapFilters(city=city)
    return await StatsRepository().seasonality(filters)
