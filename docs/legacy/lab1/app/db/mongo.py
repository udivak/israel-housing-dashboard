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
    kwargs: dict = {
        "connectTimeoutMS": settings.MONGODB_CONNECT_TIMEOUT_MS,
        "serverSelectionTimeoutMS": settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
    }
    # Only use TLS CA bundle for Atlas (SRV) or explicit TLS connections;
    # plain local mongodb:// connections must not pass tlsCAFile.
    if "mongodb+srv" in settings.MONGODB_URI or "tls=true" in settings.MONGODB_URI.lower():
        kwargs["tlsCAFile"] = certifi.where()

    _client = AsyncMongoClient(settings.MONGODB_URI, **kwargs)
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
    # Sparse so that records inserted with allow_duplicates=True (no content_hash)
    # do not conflict with the unique constraint.
    await raw.create_index("content_hash", unique=True, sparse=True)

    jobs = _db["scrape_jobs"]
    await jobs.create_index("status")
    await jobs.create_index("source_name")
    await jobs.create_index([("created_at", -1)])

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
