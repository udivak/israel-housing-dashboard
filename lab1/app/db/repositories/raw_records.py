from datetime import datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import DESCENDING
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError


class RawRecordsRepository:
    def __init__(self, db: AsyncDatabase) -> None:
        self._col = db["raw_records"]

    async def upsert(self, record: dict[str, Any]) -> tuple[str, bool]:
        """Insert a record; return (id, inserted). inserted=False means dedup skip."""
        try:
            result = await self._col.insert_one(record)
            return str(result.inserted_id), True
        except DuplicateKeyError:
            existing = await self._col.find_one({"content_hash": record["content_hash"]}, {"_id": 1})
            return str(existing["_id"]) if existing else "", False

    async def bulk_upsert(
        self,
        records: list[dict[str, Any]],
        allow_duplicates: bool = False,
    ) -> tuple[int, int]:
        """Insert many records. Returns (inserted_count, skipped_count).

        When allow_duplicates=True the content_hash unique index is bypassed and
        every record is inserted as a new document, even if identical data was
        already collected in a previous run.  This satisfies the lab requirement of
        providing an explicit option to re-ingest the same data.
        """
        if allow_duplicates:
            # Strip content_hash so the sparse unique index is not triggered
            plain = [{k: v for k, v in r.items() if k != "content_hash"} for r in records]
            if not plain:
                return 0, 0
            result = await self._col.insert_many(plain, ordered=False)
            return len(result.inserted_ids), 0

        inserted = 0
        skipped = 0
        for record in records:
            _, was_inserted = await self.upsert(record)
            if was_inserted:
                inserted += 1
            else:
                skipped += 1
        return inserted, skipped

    def _build_query(
        self,
        source_name: str | None,
        parsing_status: str | None,
        job_id: str | None,
        ingested_after: datetime | None,
        ingested_before: datetime | None,
    ) -> dict[str, Any]:
        query: dict[str, Any] = {}
        if source_name:
            query["source_name"] = source_name
        if parsing_status:
            query["parsing_status"] = parsing_status
        if job_id:
            query["job_id"] = job_id
        if ingested_after or ingested_before:
            date_filter: dict[str, datetime] = {}
            if ingested_after:
                date_filter["$gte"] = ingested_after
            if ingested_before:
                date_filter["$lte"] = ingested_before
            query["ingested_at"] = date_filter
        return query

    async def find(
        self,
        source_name: str | None = None,
        parsing_status: str | None = None,
        job_id: str | None = None,
        ingested_after: datetime | None = None,
        ingested_before: datetime | None = None,
        sort_by: str = "ingested_at",
        sort_order: int = DESCENDING,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        query = self._build_query(source_name, parsing_status, job_id, ingested_after, ingested_before)
        cursor = self._col.find(query).sort(sort_by, sort_order).skip(offset).limit(limit)
        return await cursor.to_list(length=limit)

    async def find_by_id(self, record_id: str) -> dict[str, Any] | None:
        try:
            return await self._col.find_one({"_id": ObjectId(record_id)})
        except InvalidId:
            return None

    async def count(
        self,
        source_name: str | None = None,
        parsing_status: str | None = None,
        job_id: str | None = None,
        ingested_after: datetime | None = None,
        ingested_before: datetime | None = None,
    ) -> int:
        query = self._build_query(source_name, parsing_status, job_id, ingested_after, ingested_before)
        return await self._col.count_documents(query)
