from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db.mongo import ping_database

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@router.get("/ready")
async def ready() -> JSONResponse:
    if await ping_database():
        return JSONResponse({"status": "ready"})
    return JSONResponse({"status": "unavailable", "detail": "MongoDB unreachable"}, status_code=503)
