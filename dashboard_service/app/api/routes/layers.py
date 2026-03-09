"""Map layer metadata endpoints."""

from fastapi import APIRouter

from app.models.layer import LayerConfig
from app.services.layer_service import LayerService

router = APIRouter(prefix="/layers", tags=["Layers"])


@router.get(
    "",
    response_model=list[LayerConfig],
    summary="List available map layers",
    description="Returns all available map layers with styling metadata for MapLibre/Deck.gl.",
)
async def list_layers() -> list[LayerConfig]:
    """Get all map layers and their styling configuration."""
    service = LayerService()
    return await service.get_all_layers()
