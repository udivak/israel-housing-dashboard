from typing import Any

from pymongo.asynchronous.database import AsyncDatabase


class PipelineLogsRepository:
    def __init__(self, db: AsyncDatabase) -> None:
        self._col = db["pipeline_logs"]

    async def append(self, entry: dict[str, Any]) -> str:
        result = await self._col.insert_one(entry)
        return str(result.inserted_id)

    async def find_by_job(self, job_id: str, limit: int = 100) -> list[dict[str, Any]]:
        cursor = self._col.find({"job_id": job_id}).sort("created_at", 1).limit(limit)
        return await cursor.to_list(length=limit)
