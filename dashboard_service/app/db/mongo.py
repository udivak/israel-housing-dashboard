"""Async MongoDB connection via Motor with 2dsphere index setup."""

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_client() -> AsyncIOMotorClient:
    """Return the MongoDB client. Raises if not connected."""
    if _client is None:
        raise RuntimeError("MongoDB client not initialized")
    return _client


def get_db() -> AsyncIOMotorDatabase:
    """Return the database instance. Raises if not connected."""
    if _db is None:
        raise RuntimeError("MongoDB database not initialized")
    return _db


async def connect_mongo() -> None:
    """Connect to MongoDB and initialize the database."""
    global _client, _db
    _client = AsyncIOMotorClient(settings.mongo_uri)
    _db = _client[settings.db_name]
    await ensure_geo_indexes()


async def disconnect_mongo() -> None:
    """Close the MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None


async def ensure_geo_indexes() -> None:
    """
    Create 2dsphere indexes on geometry fields for spatial queries.
    Add collection names here as you introduce new geo collections.
    """
    db = get_db()
    geo_collections = [
        "properties",
        "districts",
        "parcels",
    ]
    for coll_name in geo_collections:
        try:
            coll = db[coll_name]
            await coll.create_index([("geometry", "2dsphere")])
        except Exception:
            pass  # Collection may not exist yet; index creation will run when data is added
