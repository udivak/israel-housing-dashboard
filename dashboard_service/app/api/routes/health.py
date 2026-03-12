"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health() -> dict:
    """Health check for load balancers and monitoring."""
    return {"status": "ok", "service": "dashboard-map-service"}
