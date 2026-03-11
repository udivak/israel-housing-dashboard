from typing import Any, Optional

from pymongo.asynchronous.database import AsyncDatabase


class SourcesRepository:
    def __init__(self, db: AsyncDatabase) -> None:
        self._col = db["source_registry"]

    async def upsert(self, source: dict[str, Any]) -> None:
        await self._col.update_one(
            {"name": source["name"]},
            {"$setOnInsert": source},
            upsert=True,
        )

    async def get_by_name(self, name: str) -> Optional[dict[str, Any]]:
        return await self._col.find_one({"name": name})

    async def list_sources(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        cursor = self._col.find({}).skip(offset).limit(limit)
        return await cursor.to_list(length=limit)

    async def count(self) -> int:
        return await self._col.count_documents({})
