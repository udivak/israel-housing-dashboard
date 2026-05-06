"""FastAPI application entry point."""

import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.api.routes import health
from app.db.mongo import connect_mongo, disconnect_mongo

logger = logging.getLogger("dashboard_service")
logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle: connect DB on startup, disconnect on shutdown."""
    await connect_mongo()
    yield
    await disconnect_mongo()


app = FastAPI(
    title="Dashboard & Map Visualization Service",
    description="Geospatial API for real-estate intelligence map frontends",
    version="1.0.0",
    lifespan=lifespan,
)

# allow_credentials=False is required when allow_origins=["*"] — the
# combination with credentials=True breaks browsers' CORS check.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Ensure 500s carry CORS headers and a useful body."""
    logger.error("Unhandled exception on %s %s: %s\n%s",
                 request.method, request.url.path, exc, traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": exc.__class__.__name__},
        headers={"Access-Control-Allow-Origin": "*"},
    )


app.include_router(health.router)
app.include_router(api_router)
