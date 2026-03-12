"""MongoDB spatial queries using $geoWithin and $box."""

from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongo import get_db


class GeoRepository:
    """Repository for geospatial bounding box queries."""

    def __init__(self) -> None:
        self._db = get_db()

    def _get_collection(self, layer_id: str) -> AsyncIOMotorCollection:
        """Resolve layer_id to MongoDB collection."""
        return self._db[layer_id]

    async def find_features_in_bbox(
        self,
        layer_id: str,
        min_lat: float,
        max_lat: float,
        min_lng: float,
        max_lng: float,
        limit: int = 10_000,
    ) -> list[dict]:
        """
        Find documents whose geometry is within the bounding box.
        Uses MongoDB $geoWithin with $box for 2dsphere index.
        Box format: [[minLng, minLat], [maxLng, maxLat]] per MongoDB docs.
        """
        coll = self._get_collection(layer_id)
        box = [[min_lng, min_lat], [max_lng, max_lat]]
        cursor = coll.find(
            {"geometry": {"$geoWithin": {"$box": box}}},
            {"_id": 0},
        ).limit(limit)
        return await cursor.to_list(length=limit)
