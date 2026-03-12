from typing import Optional

import certifi
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import settings
from app.core.exceptions import DatabaseUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)

_client: Optional[AsyncMongoClient] = None
_db: Optional[AsyncDatabase] = None


async def connect_to_mongo() -> None:
    global _client, _db
    _client = AsyncMongoClient(
        settings.MONGODB_URI,
        connectTimeoutMS=settings.MONGODB_CONNECT_TIMEOUT_MS,
        serverSelectionTimeoutMS=settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
        tlsCAFile=certifi.where(),
    )
    _db = _client[settings.MONGODB_DB_NAME]
    await logger.ainfo("Connected to MongoDB", db=settings.MONGODB_DB_NAME)


async def close_mongo_connection() -> None:
    global _client, _db
    if _client is not None:
        await _client.close()
        _client = None
        _db = None
        await logger.ainfo("MongoDB connection closed")


async def create_indexes() -> None:
    if _db is None:
        raise DatabaseUnavailableError("DB not initialised")

    raw = _db["raw_records"]
    await raw.create_index([("source_name", 1), ("ingested_at", -1)])
    await raw.create_index("content_hash", unique=True, sparse=True)
    # Enables efficient lookup of all raw records for a specific Madlan listing
    # (e.g. to track price history across multiple scrape runs).
    await raw.create_index(
        [("source_name", 1), ("raw_payload.listing_id", 1)],
        sparse=True,
        name="madlan_listing_id_lookup",
    )

    jobs = _db["scrape_jobs"]
    await jobs.create_index("status")
    await jobs.create_index("source_name")
    await jobs.create_index([("created_at", -1)])

    sources = _db["source_registry"]
    await sources.create_index("name", unique=True)

    logs = _db["pipeline_logs"]
    await logs.create_index("job_id")
    await logs.create_index([("created_at", -1)])

    await logger.ainfo("MongoDB indexes created")


async def ping_database() -> bool:
    if _client is None:
        return False
    try:
        await _client.admin.command("ping")
        return True
    except Exception:
        return False


def get_database() -> AsyncDatabase:
    if _db is None:
        raise DatabaseUnavailableError("Database connection has not been established")
    return _db
