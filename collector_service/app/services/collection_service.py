import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from pymongo.asynchronous.database import AsyncDatabase  # type: ignore[import-untyped]

from app.core.exceptions import JobAlreadyRunningError, SourceNotFoundError
from app.core.logging import get_logger
from app.db.repositories.jobs import JobsRepository
from app.db.repositories.logs import PipelineLogsRepository
from app.db.repositories.raw_records import RawRecordsRepository
from app.models.jobs import JobStatus
from app.models.records import ParsingStatus, RetrievalMethod
from app.scrapers.tax_authority import TaxAuthorityScraper
from app.services.source_registry import SourceRegistry

logger = get_logger(__name__)


class CollectionService:
    def __init__(self, db: "AsyncDatabase", registry: SourceRegistry) -> None:
        self._db = db
        self._registry = registry
        self._jobs_repo = JobsRepository(db)
        self._raw_repo = RawRecordsRepository(db)
        self._logs_repo = PipelineLogsRepository(db)

    async def trigger_collection(self, source_name: str) -> str:
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

        asyncio.create_task(self._run_job(job_id, source_name))
        return job_id

    async def _run_job(self, job_id: str, source_name: str) -> None:
        await self._jobs_repo.transition(
            job_id, JobStatus.RUNNING, {"started_at": datetime.now(UTC)}
        )
        bound_log = logger.bind(job_id=job_id, source_name=source_name)
        await bound_log.ainfo("Job started")

        try:
            scraper = await self._registry.get_scraper(source_name)

            if isinstance(scraper, TaxAuthorityScraper):
                # Incremental path: flush city records to DB as they arrive so that
                # a mid-job failure does not discard already-collected data.
                inserted_total = 0
                skipped_total = 0

                async def _flush(city_records: list[dict[str, Any]]) -> None:
                    nonlocal inserted_total, skipped_total
                    raw = self._build_raw_records_from_items(
                        city_records, job_id, scraper
                    )
                    ins, skip = await self._raw_repo.bulk_upsert(raw)
                    inserted_total += ins
                    skipped_total += skip
                    await self._jobs_repo.transition(
                        job_id,
                        JobStatus.RUNNING,
                        {
                            "records_inserted": inserted_total,
                            "records_skipped": skipped_total,
                        },
                    )
                    await bound_log.ainfo(
                        "Incremental flush",
                        flushed=len(city_records),
                        inserted=ins,
                        skipped=skip,
                        total_inserted=inserted_total,
                    )

                scraper._flush_callback = _flush  # type: ignore[attr-defined]
                result = await scraper.run()

                if result.status == "failed":
                    raise RuntimeError(result.error or "Scraper returned failed status")

                await self._jobs_repo.transition(
                    job_id,
                    JobStatus.COMPLETED,
                    {
                        "completed_at": datetime.now(UTC),
                        "records_inserted": inserted_total,
                        "records_skipped": skipped_total,
                    },
                )
                await bound_log.ainfo(
                    "Job completed",
                    inserted=inserted_total,
                    skipped=skipped_total,
                )

            else:
                # Batch path for all other scrapers (unchanged behaviour)
                result = await scraper.run()

                if result.status == "failed":
                    raise RuntimeError(result.error or "Scraper returned failed status")

                raw_records = self._build_raw_records(result, job_id, scraper)
                inserted, skipped = await self._raw_repo.bulk_upsert(raw_records)

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

    def _build_raw_records(self, result, job_id: str, scraper) -> list[dict]:
        return self._build_raw_records_from_items(result.records, job_id, scraper)

    def _build_raw_records_from_items(
        self, items: list[dict], job_id: str, scraper
    ) -> list[dict]:
        records = []
        for item in items:
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

    async def trigger_all(self) -> str:
        parent_doc = {
            "source_name": "all",
            "status": JobStatus.PENDING,
            "created_at": datetime.now(UTC),
            "started_at": None,
            "completed_at": None,
            "records_inserted": 0,
            "records_skipped": 0,
            "error_message": None,
            "sub_job_ids": [],
        }
        parent_job_id = await self._jobs_repo.create(parent_doc)
        asyncio.create_task(self._run_all(parent_job_id))
        return parent_job_id

    async def _run_all(self, parent_job_id: str) -> None:
        await self._jobs_repo.transition(
            parent_job_id, JobStatus.RUNNING, {"started_at": datetime.now(UTC)}
        )

        active_sources = self._registry.list_active_source_names()
        sub_job_ids: list[str] = []
        sub_statuses: list[JobStatus] = []

        for source_name in active_sources:
            try:
                sub_job_id = await self.trigger_collection(source_name)
                sub_job_ids.append(sub_job_id)
            except JobAlreadyRunningError:
                await logger.awarning(
                    "Skipping source — job already running", source_name=source_name
                )

        await self._jobs_repo.transition(
            parent_job_id,
            JobStatus.RUNNING,
            {"sub_job_ids": sub_job_ids},
        )

        # Poll until all sub-jobs finish
        while True:
            pending = []
            for sub_id in sub_job_ids:
                doc = await self._jobs_repo.find_by_id(sub_id)
                if doc and doc["status"] in (JobStatus.PENDING, JobStatus.RUNNING):
                    pending.append(sub_id)
                elif doc:
                    sub_statuses.append(doc["status"])
            if not pending:
                break
            await asyncio.sleep(2)

        any_failed = any(s == JobStatus.FAILED for s in sub_statuses)
        final_status = JobStatus.PARTIAL if any_failed else JobStatus.COMPLETED
        await self._jobs_repo.transition(
            parent_job_id,
            final_status,
            {"completed_at": datetime.now(UTC)},
        )
