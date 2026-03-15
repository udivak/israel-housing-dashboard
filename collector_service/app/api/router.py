from fastapi import APIRouter

from app.api.routes import collect, docs, health, jobs, records, sources
from app.core.config import settings

api_router = APIRouter(prefix=settings.API_PREFIX)
api_router.include_router(collect.router)
api_router.include_router(jobs.router)
api_router.include_router(records.router)
api_router.include_router(sources.router)
api_router.include_router(docs.router)

health_router = APIRouter()
health_router.include_router(health.router)
