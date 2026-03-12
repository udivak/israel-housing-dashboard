from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError


class RawRecordsRepository:
    def __init__(self, db: AsyncDatabase) -> None:
        self._col = db["raw_records"]

    async def upsert(self, record: dict[str, Any]) -> tuple[str, bool]:
        """Insert a record; return (id, inserted). inserted=False means it was a dedup skip."""
        try:
            result = await self._col.insert_one(record)
            return str(result.inserted_id), True
        except DuplicateKeyError:
            existing = await self._col.find_one({"content_hash": record["content_hash"]}, {"_id": 1})
            return str(existing["_id"]) if existing else "", False

    async def bulk_upsert(self, records: list[dict[str, Any]]) -> tuple[int, int]:
        """Insert many records. Returns (inserted_count, skipped_count)."""
        inserted = 0
        skipped = 0
        for record in records:
            _, was_inserted = await self.upsert(record)
            if was_inserted:
                inserted += 1
            else:
                skipped += 1
        return inserted, skipped

    async def find(
        self,
        source_name: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if source_name:
            query["source_name"] = source_name
        cursor = self._col.find(query).skip(offset).limit(limit)
        return await cursor.to_list(length=limit)

    async def count(self, source_name: str | None = None) -> int:
        query: dict[str, Any] = {}
        if source_name:
            query["source_name"] = source_name
        return await self._col.count_documents(query)
