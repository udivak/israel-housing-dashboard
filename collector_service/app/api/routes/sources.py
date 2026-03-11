from fastapi import APIRouter, Depends, Query, Request

from app.db.repositories.jobs import JobsRepository
from app.models.api import StandardResponse
from app.models.jobs import ScrapeJob, JobStatus
from app.models.source import SourceDefinition, SourceListResponse
from app.services.source_registry import SourceRegistry

router = APIRouter(tags=["Sources"])


def _get_registry(request: Request) -> SourceRegistry:
    return request.app.state.source_registry


def _get_jobs_repo(request: Request) -> JobsRepository:
    return request.app.state.jobs_repo


@router.get("/sources", response_model=StandardResponse[SourceListResponse])
async def list_sources(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    registry: SourceRegistry = Depends(_get_registry),
) -> StandardResponse[SourceListResponse]:
    docs = await registry.list_sources(limit=limit, offset=offset)
    total = await registry.count_sources()
    sources = [SourceDefinition.model_validate(d) for d in docs]
    return StandardResponse(
        success=True,
        data=SourceListResponse(sources=sources, total=total, limit=limit, offset=offset),
    )


@router.get("/collections/status", response_model=StandardResponse[list[dict]])
async def collections_status(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    registry: SourceRegistry = Depends(_get_registry),
    jobs_repo: JobsRepository = Depends(_get_jobs_repo),
) -> StandardResponse[list[dict]]:
    source_docs = await registry.list_sources(limit=100, offset=0)
    results = []
    for doc in source_docs:
        name = doc["name"]
        recent = await jobs_repo.list_jobs(limit=1, offset=0)
        latest: dict | None = None
        for job in recent:
            if job.get("source_name") == name:
                latest = job
                break
        if latest is None:
            all_jobs = await jobs_repo.list_jobs(limit=200, offset=0)
            for job in all_jobs:
                if job.get("source_name") == name:
                    latest = job
                    break
        results.append(
            {
                "source_name": name,
                "display_name": doc.get("display_name", name),
                "status": doc.get("status"),
                "last_job_status": latest["status"] if latest else None,
                "last_job_id": str(latest["_id"]) if latest else None,
                "last_run_at": latest.get("completed_at") if latest else None,
                "last_records_inserted": latest.get("records_inserted", 0) if latest else 0,
            }
        )
    return StandardResponse(success=True, data=results[offset : offset + limit])
