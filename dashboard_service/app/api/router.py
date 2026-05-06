"""API router combining all routes under /api/v1."""

from fastapi import APIRouter

from app.api.routes import layers, map_data, predict, properties, stats

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(layers.router)
api_router.include_router(map_data.router)
api_router.include_router(predict.router)
api_router.include_router(properties.router)
api_router.include_router(stats.router)
