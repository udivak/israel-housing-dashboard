"""Transforms MongoDB documents into strict GeoJSON FeatureCollections."""

from app.db.repositories.geo_repository import GeoRepository
from app.models.geojson import Feature, FeatureCollection


class GeoService:
    """Business logic for geospatial feature retrieval and GeoJSON transformation."""

    def __init__(self) -> None:
        self._repo = GeoRepository()

    async def get_features_in_bbox(
        self,
        layer_id: str,
        min_lat: float,
        max_lat: float,
        min_lng: float,
        max_lng: float,
    ) -> FeatureCollection:
        """
        Fetch documents in bbox and convert to RFC 7946 FeatureCollection.
        MongoDB docs must have a 'geometry' field conforming to GeoJSON.
        """
        docs = await self._repo.find_features_in_bbox(
            layer_id=layer_id,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lng=min_lng,
            max_lng=max_lng,
        )
        features = [self._doc_to_feature(d) for d in docs]
        return FeatureCollection(features=features)

    def _doc_to_feature(self, doc: dict) -> Feature:
        """Convert a MongoDB document to a GeoJSON Feature."""
        geometry = doc.get("geometry")
        properties = {k: v for k, v in doc.items() if k != "geometry"}
        return Feature(geometry=geometry, properties=properties or {})
