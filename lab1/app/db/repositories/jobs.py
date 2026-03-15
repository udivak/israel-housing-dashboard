from datetime import UTC, datetime
from typing import Any, Optional

from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase


class JobsRepository:
    def __init__(self, db: AsyncDatabase) -> None:
        self._col = db["scrape_jobs"]

    async def create(self, doc: dict[str, Any]) -> str:
        result = await self._col.insert_one(doc)
        return str(result.inserted_id)

    async def transition(
        self,
        job_id: str,
        status: str,
        update: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {"status": status}
        if update:
            payload.update(update)
        await self._col.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": payload},
        )

    async def find_by_id(self, job_id: str) -> Optional[dict[str, Any]]:
        return await self._col.find_one({"_id": ObjectId(job_id)})

    async def list_jobs(
        self,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if status:
            query["status"] = status
        cursor = self._col.find(query).sort("created_at", -1).skip(offset).limit(limit)
        return await cursor.to_list(length=limit)

    async def find_running_for_source(self, source_name: str) -> Optional[dict[str, Any]]:
        return await self._col.find_one({"source_name": source_name, "status": "running"})

    async def recover_stale_jobs(self) -> int:
        result = await self._col.update_many(
            {"status": {"$in": ["pending", "running"]}},
            {
                "$set": {
                    "status": "failed",
                    "completed_at": datetime.now(UTC),
                    "error_message": "Recovered on service restart — job interrupted",
                }
            },
        )
        return result.modified_count
