"""Repository for layer configuration data."""

from app.db.mongo import get_db
from app.models.layer import LayerConfig


class LayerRepository:
    """Fetches layer configurations from MongoDB or built-in defaults."""

    LAYERS_COLLECTION = "layer_configs"

    def __init__(self) -> None:
        self._db = get_db()

    async def get_all_layers(self) -> list[LayerConfig]:
        """Fetch all layer configurations. Falls back to defaults if collection empty."""
        coll = self._db[self.LAYERS_COLLECTION]
        cursor = coll.find({}, {"_id": 0})
        docs = await cursor.to_list(length=100)
        if docs:
            return [LayerConfig.model_validate(d) for d in docs]
        return self._default_layers()

    def _default_layers(self) -> list[LayerConfig]:
        """Default layer configs when DB has none."""
        return [
            LayerConfig(
                id="properties",
                name="Properties",
                type="fill",
                color="#3388ff",
                source="properties",
                opacity=0.7,
            ),
            LayerConfig(
                id="districts",
                name="Districts",
                type="line",
                color="#ff6b6b",
                source="districts",
                opacity=0.9,
            ),
        ]
