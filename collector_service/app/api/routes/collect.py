from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.models.api import JobAcceptedResponse, StandardResponse
from app.services.collection_service import CollectionService

router = APIRouter(prefix="/collect", tags=["Collection"])


def _get_service(request: Request) -> CollectionService:
    return request.app.state.collection_service


@router.post(
    "/source/{source_name}",
    response_model=StandardResponse[JobAcceptedResponse],
    status_code=202,
)
async def collect_source(
    source_name: str,
    service: CollectionService = Depends(_get_service),
) -> StandardResponse[JobAcceptedResponse]:
    job_id = await service.trigger_collection(source_name)
    return StandardResponse(
        success=True,
        data=JobAcceptedResponse(job_id=job_id),
        message=f"Collection job accepted for source: {source_name}",
    )


@router.post(
    "/all",
    response_model=StandardResponse[JobAcceptedResponse],
    status_code=202,
)
async def collect_all(
    service: CollectionService = Depends(_get_service),
) -> StandardResponse[JobAcceptedResponse]:
    job_id = await service.trigger_all()
    return StandardResponse(
        success=True,
        data=JobAcceptedResponse(job_id=job_id),
        message="Collection job accepted for all active sources",
    )
