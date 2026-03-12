from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import JobNotFoundError
from app.db.repositories.jobs import JobsRepository
from app.models.api import StandardResponse
from app.models.jobs import ScrapeJob

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _get_jobs_repo(request: Request) -> JobsRepository:
    return request.app.state.jobs_repo


@router.get("/all", response_model=StandardResponse[list[ScrapeJob]])
async def list_all_jobs(
    repo: JobsRepository = Depends(_get_jobs_repo),
) -> StandardResponse[list[ScrapeJob]]:
    docs = await repo.list_jobs(limit=1000)
    jobs = [ScrapeJob.model_validate(d) for d in docs]
    return StandardResponse(success=True, data=jobs)


@router.get("/{job_id}", response_model=StandardResponse[ScrapeJob])
async def get_job(
    job_id: str,
    repo: JobsRepository = Depends(_get_jobs_repo),
) -> StandardResponse[ScrapeJob]:
    doc = await repo.find_by_id(job_id)
    if doc is None:
        raise JobNotFoundError(job_id)
    return StandardResponse(success=True, data=ScrapeJob.model_validate(doc))


@router.get("", response_model=StandardResponse[list[ScrapeJob]])
async def list_jobs(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repo: JobsRepository = Depends(_get_jobs_repo),
) -> StandardResponse[list[ScrapeJob]]:
    docs = await repo.list_jobs(status=status, limit=limit, offset=offset)
    jobs = [ScrapeJob.model_validate(d) for d in docs]
    return StandardResponse(success=True, data=jobs)
