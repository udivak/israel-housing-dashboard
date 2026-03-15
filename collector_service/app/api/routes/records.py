from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from app.core.exceptions import RecordNotFoundError
from app.db.repositories.raw_records import RawRecordsRepository
from app.models.api import PaginatedResponse, StandardResponse
from app.models.records import RawRecord

router = APIRouter(prefix="/records", tags=["Records"])


def _get_repo(request: Request) -> RawRecordsRepository:
    return request.app.state.raw_records_repo


@router.get("", response_model=StandardResponse[PaginatedResponse[RawRecord]])
async def list_records(
    source_name: Optional[str] = Query(None),
    parsing_status: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
    ingested_after: Optional[datetime] = Query(None),
    ingested_before: Optional[datetime] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repo: RawRecordsRepository = Depends(_get_repo),
) -> StandardResponse[PaginatedResponse[RawRecord]]:
    docs = await repo.find(
        source_name=source_name,
        parsing_status=parsing_status,
        job_id=job_id,
        ingested_after=ingested_after,
        ingested_before=ingested_before,
        limit=limit,
        offset=offset,
    )
    total = await repo.count(
        source_name=source_name,
        parsing_status=parsing_status,
        job_id=job_id,
        ingested_after=ingested_after,
        ingested_before=ingested_before,
    )
    items = [RawRecord.model_validate(d) for d in docs]
    return StandardResponse(
        success=True,
        data=PaginatedResponse(items=items, total=total, limit=limit, offset=offset),
    )


@router.get("/count", response_model=StandardResponse[dict])
async def count_records(
    source_name: Optional[str] = Query(None),
    parsing_status: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
    ingested_after: Optional[datetime] = Query(None),
    ingested_before: Optional[datetime] = Query(None),
    repo: RawRecordsRepository = Depends(_get_repo),
) -> StandardResponse[dict]:
    total = await repo.count(
        source_name=source_name,
        parsing_status=parsing_status,
        job_id=job_id,
        ingested_after=ingested_after,
        ingested_before=ingested_before,
    )
    return StandardResponse(success=True, data={"total": total})


@router.get("/{record_id}", response_model=StandardResponse[RawRecord])
async def get_record(
    record_id: str,
    repo: RawRecordsRepository = Depends(_get_repo),
) -> StandardResponse[RawRecord]:
    doc = await repo.find_by_id(record_id)
    if doc is None:
        raise RecordNotFoundError(record_id)
    return StandardResponse(success=True, data=RawRecord.model_validate(doc))
