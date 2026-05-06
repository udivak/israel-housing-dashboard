"""Zoom-aware map data orchestration (lat/lon grid clustering)."""

from __future__ import annotations

from app.db.repositories.features_repository import FeaturesRepository, MAX_POINTS
from app.models.map import (
    ClusterCell,
    ClusterResponse,
    MapFilters,
    PointFeature,
    PointsResponse,
)

# Zoom -> decimal places for lat/lon rounding.
#   z 0-8  : 1 decimal (~11 km cells)
#   z 9-11 : 2 decimals (~1.1 km cells)
#   z 12-13: 3 decimals (~110 m cells)
#   z >=14 : individual points
ZOOM_TO_DECIMALS: list[tuple[int, int, int]] = [
    (0, 8, 1),
    (9, 11, 2),
    (12, 13, 3),
]
POINT_ZOOM_THRESHOLD = 14


def decimals_for_zoom(zoom: int) -> int | None:
    for lo, hi, dec in ZOOM_TO_DECIMALS:
        if lo <= zoom <= hi:
            return dec
    return None


class MapService:
    def __init__(self) -> None:
        self._repo = FeaturesRepository()

    async def get_map_data(
        self,
        min_lat: float,
        max_lat: float,
        min_lng: float,
        max_lng: float,
        zoom: int,
        filters: MapFilters | None = None,
    ) -> ClusterResponse | PointsResponse:
        if zoom >= POINT_ZOOM_THRESHOLD:
            return await self._fetch_points(min_lat, max_lat, min_lng, max_lng, filters)

        decimals = decimals_for_zoom(zoom) or 1
        return await self._fetch_clusters(
            decimals, min_lat, max_lat, min_lng, max_lng, filters
        )

    async def _fetch_clusters(
        self,
        decimals: int,
        min_lat: float,
        max_lat: float,
        min_lng: float,
        max_lng: float,
        filters: MapFilters | None,
    ) -> ClusterResponse:
        rows = await self._repo.cluster_by_grid(
            decimals, min_lat, max_lat, min_lng, max_lng, filters
        )
        cells: list[ClusterCell] = []
        for r in rows:
            key = r["_id"] or {}
            lat = key.get("lat")
            lng = key.get("lon")
            if lat is None or lng is None:
                continue
            cell_id = f"{lat:.{decimals}f},{lng:.{decimals}f}"
            cells.append(
                ClusterCell(
                    h3=cell_id,  # reuse field name for client compatibility
                    lat=float(lat),
                    lng=float(lng),
                    count=r["count"],
                    median_price=r.get("avg_price"),
                    median_price_per_sqm=r.get("avg_price_per_sqm"),
                    min_price=r.get("min_price"),
                    max_price=r.get("max_price"),
                )
            )
        return ClusterResponse(resolution=decimals, cells=cells)

    async def _fetch_points(
        self,
        min_lat: float,
        max_lat: float,
        min_lng: float,
        max_lng: float,
        filters: MapFilters | None,
    ) -> PointsResponse:
        docs = await self._repo.points_in_bbox(
            min_lat, max_lat, min_lng, max_lng, filters
        )
        features: list[PointFeature] = []
        for d in docs:
            lat, lng = d.get("lat"), d.get("lon")
            if lat is None or lng is None:
                continue
            features.append(
                PointFeature(
                    id=str(d.get("_id")),
                    lng=float(lng),
                    lat=float(lat),
                    price=d.get("price"),
                    price_per_sqm=d.get("price_per_sqm"),
                    rooms=d.get("rooms"),
                    area_sqm=d.get("area_sqm"),
                    city=d.get("city"),
                    neighborhood=d.get("neighborhood"),
                    transaction_date=d.get("transaction_date"),
                )
            )
        return PointsResponse(
            features=features,
            truncated=len(features) >= MAX_POINTS,
        )
