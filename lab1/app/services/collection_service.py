import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from pymongo.asynchronous.database import AsyncDatabase

from app.core.exceptions import JobAlreadyRunningError
from app.core.logging import get_logger
from app.db.repositories.jobs import JobsRepository
from app.db.repositories.logs import PipelineLogsRepository
from app.db.repositories.raw_records import RawRecordsRepository
from app.models.jobs import JobStatus
from app.models.records import ParsingStatus
from app.services.source_registry import SourceRegistry

logger = get_logger(__name__)


@dataclass
class CollectOptions:
    """Runtime options forwarded from the GUI / API request."""

    allow_duplicates: bool = False
    scraper_overrides: dict[str, Any] = field(default_factory=dict)


class CollectionService:
    def __init__(self, db: "AsyncDatabase", registry: SourceRegistry) -> None:
        self._db = db
        self._registry = registry
        self._jobs_repo = JobsRepository(db)
        self._raw_repo = RawRecordsRepository(db)
        self._logs_repo = PipelineLogsRepository(db)

    async def trigger_collection(
        self,
        source_name: str,
        options: Optional[CollectOptions] = None,
    ) -> str:
        running = await self._jobs_repo.find_running_for_source(source_name)
        if running is not None:
            raise JobAlreadyRunningError(source_name)

        job_doc = {
            "source_name": source_name,
            "status": JobStatus.PENDING,
            "created_at": datetime.now(UTC),
            "started_at": None,
            "completed_at": None,
            "records_inserted": 0,
            "records_skipped": 0,
            "error_message": None,
            "sub_job_ids": [],
        }
        job_id = await self._jobs_repo.create(job_doc)
        asyncio.create_task(self._run_job(job_id, source_name, options or CollectOptions()))
        return job_id

    async def _run_job(
        self,
        job_id: str,
        source_name: str,
        options: CollectOptions,
    ) -> None:
        await self._jobs_repo.transition(
            job_id, JobStatus.RUNNING, {"started_at": datetime.now(UTC)}
        )
        bound_log = logger.bind(job_id=job_id, source_name=source_name)
        await bound_log.ainfo("Job started", allow_duplicates=options.allow_duplicates)

        try:
            scraper = await self._registry.get_scraper(source_name, options.scraper_overrides)
            result = await scraper.run()

            if result.status == "failed":
                raise RuntimeError(result.error or "Scraper returned failed status")

            raw_records = self._build_raw_records(result, job_id, scraper)
            inserted, skipped = await self._raw_repo.bulk_upsert(
                raw_records,
                allow_duplicates=options.allow_duplicates,
            )

            await self._jobs_repo.transition(
                job_id,
                JobStatus.COMPLETED,
                {
                    "completed_at": datetime.now(UTC),
                    "records_inserted": inserted,
                    "records_skipped": skipped,
                },
            )
            await bound_log.ainfo("Job completed", inserted=inserted, skipped=skipped)

        except Exception as exc:
            error_msg = str(exc)
            await self._jobs_repo.transition(
                job_id,
                JobStatus.FAILED,
                {"completed_at": datetime.now(UTC), "error_message": error_msg},
            )
            await self._logs_repo.append(
                {
                    "job_id": job_id,
                    "level": "error",
                    "message": error_msg,
                    "created_at": datetime.now(UTC),
                    "details": {"source_name": source_name},
                }
            )
            await bound_log.aerror("Job failed", error=error_msg)

    def _build_raw_records(self, result: Any, job_id: str, scraper: Any) -> list[dict]:
        records = []
        for item in result.records:
            records.append(
                {
                    "source_name": scraper.source_name,
                    "source_url": getattr(scraper, "source_url", ""),
                    "ingested_at": datetime.now(UTC),
                    "retrieval_method": scraper.retrieval_method,
                    "raw_payload": item.get("raw_payload", item),
                    "parsing_status": ParsingStatus.RAW,
                    "content_hash": item.get("content_hash", ""),
                    "schema_version": "v1",
                    "tags": [],
                    "job_id": job_id,
                }
            )
        return records
