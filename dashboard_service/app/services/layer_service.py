"""Business logic for layer management."""

from typing import Optional

from app.db.repositories.layer_repository import LayerRepository
from app.models.layer import LayerConfig


class LayerService:
    """Service for layer configuration retrieval."""

    def __init__(self) -> None:
        self._repo = LayerRepository()

    async def get_all_layers(self) -> list[LayerConfig]:
        """Return all available map layers with styling metadata."""
        return await self._repo.get_all_layers()

    async def get_layer_by_id(self, layer_id: str) -> Optional[LayerConfig]:
        """Return a single layer by id, or None if not found."""
        layers = await self._repo.get_all_layers()
        return next((l for l in layers if l.id == layer_id), None)
