from fastapi import APIRouter

from app.api.routes import collect, jobs, records
from app.db.mongo import ping_database

api_router = APIRouter(prefix="/api")
api_router.include_router(collect.router)
api_router.include_router(jobs.router)
api_router.include_router(records.router)

health_router = APIRouter(tags=["Health"])


@health_router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@health_router.get("/ready")
async def ready() -> dict:
    ok = await ping_database()
    if not ok:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ok"}
