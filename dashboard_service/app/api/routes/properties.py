"""Property search and detail endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query

from app.db.repositories.features_repository import _filters_to_query
from app.db.repositories.search_repository import SearchRepository
from app.models.map import MapFilters


def _id_or_str(s: str) -> Any:
    """Try ObjectId, fall back to raw string."""
    try:
        return ObjectId(s)
    except (InvalidId, TypeError):
        return s

router = APIRouter(prefix="/properties", tags=["Properties"])


def _serialize(doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    return out


@router.get("/search")
async def search_properties(
    city: str | None = Query(None),
    neighborhood: str | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    min_rooms: float | None = Query(None, ge=0),
    max_rooms: float | None = Query(None, ge=0),
    min_area: float | None = Query(None, ge=0),
    max_area: float | None = Query(None, ge=0),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    property_type: str | None = Query(None),
    source: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    sort: str = Query("transaction_date_desc"),
):
    filters = MapFilters(
        city=city, neighborhood=neighborhood,
        min_price=min_price, max_price=max_price,
        min_rooms=min_rooms, max_rooms=max_rooms,
        min_area=min_area, max_area=max_area,
        from_date=from_date, to_date=to_date,
        property_type=property_type, source=source,
    )
    match = _filters_to_query(filters)
    sort_map = {
        "transaction_date_desc": [("transaction_date", -1)],
        "transaction_date_asc": [("transaction_date", 1)],
        "price_desc": [("price", -1)],
        "price_asc": [("price", 1)],
        "price_per_sqm_desc": [("price_per_sqm", -1)],
        "price_per_sqm_asc": [("price_per_sqm", 1)],
    }
    repo = SearchRepository()
    rows, total = await repo.search_properties(
        match=match, sort=sort_map.get(sort, sort_map["transaction_date_desc"]),
        page=page, size=size,
    )
    return {
        "page": page,
        "size": size,
        "total": total,
        "results": [_serialize(r) for r in rows],
    }


@router.get("/autocomplete")
async def autocomplete(q: str = Query(..., min_length=2), limit: int = Query(10, ge=1, le=50)):
    repo = SearchRepository()
    return {"suggestions": await repo.autocomplete(q, limit=limit)}


@router.get("/{property_id}")
async def get_property(property_id: str):
    repo = SearchRepository()
    doc = await repo.get_by_id(_id_or_str(property_id))
    if doc is None:
        raise HTTPException(404, f"Property {property_id} not found")
    return _serialize(doc)


@router.get("/{property_id}/similar")
async def get_similar(
    property_id: str,
    radius: float = Query(500, ge=50, le=10000, description="Radius in meters"),
    limit: int = Query(10, ge=1, le=50),
):
    repo = SearchRepository()
    target_id = _id_or_str(property_id)
    target = await repo.get_by_id(target_id)
    if target is None:
        raise HTTPException(404, f"Property {property_id} not found")
    lat = target.get("lat")
    lng = target.get("lon")
    if lat is None or lng is None:
        raise HTTPException(400, "Property has no coordinates")
    coords = [lng, lat]
    rows = await repo.similar_in_radius(
        lng=coords[0], lat=coords[1], radius_meters=radius,
        limit=limit, exclude_id=target["_id"],
    )
    return {"results": [_serialize(r) for r in rows]}
