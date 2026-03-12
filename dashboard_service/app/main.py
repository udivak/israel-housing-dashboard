"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes import health
from app.db.mongo import connect_mongo, disconnect_mongo


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(api_router)
