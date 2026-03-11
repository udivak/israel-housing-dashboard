from fastapi import APIRouter

from app.api.routes import collect, health, jobs, sources
from app.core.config import settings

api_router = APIRouter(prefix=settings.API_V1_PREFIX)
api_router.include_router(collect.router)
api_router.include_router(jobs.router)
api_router.include_router(sources.router)

health_router = APIRouter()
health_router.include_router(health.router)
