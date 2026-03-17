from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.models.api import JobAcceptedResponse, StandardResponse
from app.services.collection_service import CollectOptions, CollectionService

router = APIRouter(prefix="/collect", tags=["Collection"])


class CBSOptions(BaseModel):
    """Runtime parameters for the CBS price-index scraper."""

    series_ids: str = "40010,70000,140235"
    start_period: str = ""


class OdataOptions(BaseModel):
    """Runtime parameters for the OData-IL land-registry scraper."""

    resource_id: str = "5eb859da-6236-4b67-bcd1-ec4b90875739"


class CollectRequest(BaseModel):
    """Request body accepted by the collect endpoints.

    allow_duplicates — when True, bypasses the content_hash unique index so that
        previously ingested records are inserted again as new documents.  This
        satisfies the lab requirement of providing an explicit option to re-ingest.

    cbs_options / odata_options — source-specific search/filter parameters that
        override the global settings for this single collection run.
    """

    allow_duplicates: bool = False
    cbs_options: CBSOptions = CBSOptions()
    odata_options: OdataOptions = OdataOptions()


def _get_service(request: Request) -> CollectionService:
    return request.app.state.collection_service


def _build_options(source_name: str, body: CollectRequest) -> CollectOptions:
    """Map request body into CollectOptions + per-scraper override dict."""
    overrides: dict = {}
    normalized = source_name.replace("-", "_")
    if normalized == "cbs_housing":
        overrides = {
            "series_ids": body.cbs_options.series_ids,
            "start_period": body.cbs_options.start_period,
        }
    elif normalized == "odata_il_nadlan":
        overrides = {"resource_id": body.odata_options.resource_id}
    return CollectOptions(allow_duplicates=body.allow_duplicates, scraper_overrides=overrides)


@router.post(
    "/source/{source_name}",
    response_model=StandardResponse[JobAcceptedResponse],
    status_code=202,
)
async def collect_source(
    source_name: str,
    body: CollectRequest,
    service: CollectionService = Depends(_get_service),
) -> StandardResponse[JobAcceptedResponse]:
    options = _build_options(source_name, body)
    job_id = await service.trigger_collection(source_name, options)
    return StandardResponse(
        success=True,
        data=JobAcceptedResponse(job_id=job_id),
        message=f"Collection job accepted for source: {source_name}",
    )
