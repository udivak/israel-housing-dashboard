"""Zoom-aware map data orchestration."""

from __future__ import annotations

import h3

from app.db.repositories.features_repository import FeaturesRepository, MAX_POINTS
from app.models.map import (
    ClusterCell,
    ClusterResponse,
    MapFilters,
    PointFeature,
    PointsResponse,
)

# Zoom -> H3 resolution. Tuned for Israel scale.
#   z 0-8  : country / large-city view
#   z 9-11 : city / neighborhood
#   z 12-13: block
#   z 14+  : individual properties
ZOOM_TO_H3: list[tuple[int, int, int]] = [
    (0, 8, 5),
    (9, 11, 7),
    (12, 13, 8),
]
POINT_ZOOM_THRESHOLD = 14


def resolution_for_zoom(zoom: int) -> int | None:
    """Return H3 resolution for the given zoom, or None if zoom shows points."""
    for lo, hi, res in ZOOM_TO_H3:
        if lo <= zoom <= hi:
            return res
    return None  # points


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

        resolution = resolution_for_zoom(zoom) or 5
        return await self._fetch_clusters(
            resolution, min_lat, max_lat, min_lng, max_lng, filters
        )

    async def _fetch_clusters(
        self,
        resolution: int,
        min_lat: float,
        max_lat: float,
        min_lng: float,
        max_lng: float,
        filters: MapFilters | None,
    ) -> ClusterResponse:
        rows = await self._repo.cluster_by_h3(
            resolution, min_lat, max_lat, min_lng, max_lng, filters
        )
        cells: list[ClusterCell] = []
        for r in rows:
            cell_id = r["_id"]
            if not cell_id:
                continue
            try:
                lat, lng = h3.cell_to_latlng(cell_id)
            except Exception:
                continue
            cells.append(
                ClusterCell(
                    h3=cell_id,
                    lat=lat,
                    lng=lng,
                    count=r["count"],
                    median_price=r.get("avg_price"),
                    median_price_per_sqm=r.get("avg_price_per_sqm"),
                    min_price=r.get("min_price"),
                    max_price=r.get("max_price"),
                )
            )
        return ClusterResponse(resolution=resolution, cells=cells)

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
            geom = d.get("geometry") or {}
            coords = geom.get("coordinates")
            if not coords or len(coords) < 2:
                continue
            features.append(
                PointFeature(
                    id=str(d.get("_id")),
                    lng=float(coords[0]),
                    lat=float(coords[1]),
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
