"""Map feature data endpoints with BBox queries."""

from fastapi import APIRouter, Query

from app.core.exceptions import InvalidBBoxError, LayerNotFoundError
from app.models.geojson import FeatureCollection
from app.models.requests import BBoxQueryParams
from app.services.geo_service import GeoService
from app.services.layer_service import LayerService

router = APIRouter(prefix="/map", tags=["Map Data"])


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
