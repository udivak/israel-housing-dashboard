"""Map feature data endpoints with BBox queries."""

from datetime import datetime

from fastapi import APIRouter, Query

from app.core.exceptions import InvalidBBoxError, LayerNotFoundError
from app.models.geojson import FeatureCollection
from app.models.map import ClusterResponse, MapFilters, PointsResponse
from app.models.requests import BBoxQueryParams
from app.services.geo_service import GeoService
from app.services.layer_service import LayerService
from app.services.map_service import MapService

router = APIRouter(prefix="/map", tags=["Map Data"])


@router.get(
    "/data",
    summary="Zoom-aware map data (clusters or points)",
    description="""
    Returns either H3 cluster aggregates (low/mid zoom) or individual property points
    (zoom >= 14), inside the given bounding box. The response shape is determined by
    the `type` field: either `clusters` or `points`.

    Filters are optional and combine with AND semantics.
    """,
    response_model=ClusterResponse | PointsResponse,
)
async def get_map_data(
    min_lat: float = Query(..., ge=-90, le=90),
    max_lat: float = Query(..., ge=-90, le=90),
    min_lng: float = Query(..., ge=-180, le=180),
    max_lng: float = Query(..., ge=-180, le=180),
    zoom: int = Query(..., ge=0, le=22),
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
):
    if min_lat >= max_lat or min_lng >= max_lng:
        raise InvalidBBoxError("min must be strictly less than max for both lat and lng")

    filters = MapFilters(
        city=city,
        neighborhood=neighborhood,
        min_price=min_price,
        max_price=max_price,
        min_rooms=min_rooms,
        max_rooms=max_rooms,
        min_area=min_area,
        max_area=max_area,
        from_date=from_date,
        to_date=to_date,
        property_type=property_type,
        source=source,
    )
    return await MapService().get_map_data(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lng=min_lng,
        max_lng=max_lng,
        zoom=zoom,
        filters=filters,
    )


@router.get(
    "/features",
    response_model=FeatureCollection,
    summary="Get map features by bounding box",
    description="""
    Returns a GeoJSON FeatureCollection of features within the specified bounding box.
    Uses MongoDB $geoWithin with $box for high-performance spatial queries.

    **BBox Parameters:**
    - `min_lat`, `max_lat`: Latitude bounds (-90 to 90)
    - `min_lng`, `max_lng`: Longitude bounds (-180 to 180)
    - `layer_id`: The data layer/collection to query (e.g., 'properties', 'districts')

    **Example Request:**
    ```
    GET /api/v1/map/features?min_lat=32.0&max_lat=32.1&min_lng=34.7&max_lng=34.8&layer_id=properties
    ```

    **Example Response (GeoJSON FeatureCollection):**
    ```json
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": {"type": "Point", "coordinates": [34.78, 32.05]},
          "properties": {"name": "Sample Property", "price": 500000}
        }
      ]
    }
    ```
    """,
    responses={
        200: {"description": "GeoJSON FeatureCollection"},
        400: {"description": "Invalid bounding box parameters"},
        404: {"description": "Layer not found"},
    },
)
async def get_map_features(
    min_lat: float = Query(..., ge=-90, le=90, description="Minimum latitude (south boundary)"),
    max_lat: float = Query(..., ge=-90, le=90, description="Maximum latitude (north boundary)"),
    min_lng: float = Query(..., ge=-180, le=180, description="Minimum longitude (west boundary)"),
    max_lng: float = Query(..., ge=-180, le=180, description="Maximum longitude (east boundary)"),
    layer_id: str = Query(..., min_length=1, description="Layer/collection ID to query"),
) -> FeatureCollection:
    """Fetch GeoJSON features within the bounding box for the given layer."""
    try:
        params = BBoxQueryParams(
            min_lat=min_lat,
            max_lat=max_lat,
            min_lng=min_lng,
            max_lng=max_lng,
            layer_id=layer_id,
        )
    except ValueError as e:
        raise InvalidBBoxError(str(e))

    layer_service = LayerService()
    layer = await layer_service.get_layer_by_id(layer_id)
    if layer is None:
        raise LayerNotFoundError(layer_id)

    geo_service = GeoService()
    return await geo_service.get_features_in_bbox(
        layer_id=params.layer_id,
        min_lat=params.min_lat,
        max_lat=params.max_lat,
        min_lng=params.min_lng,
        max_lng=params.max_lng,
    )
