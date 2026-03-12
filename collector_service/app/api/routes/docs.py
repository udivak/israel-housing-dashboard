from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings

router = APIRouter(tags=["Documentation"])

_BASE = settings.API_PREFIX


@router.get("/guide", summary="API usage guide")
async def guide() -> JSONResponse:
    """Returns a human-readable description of every endpoint exposed by this service."""
    return JSONResponse(
        {
            "service": settings.SERVICE_NAME,
            "base_prefix": _BASE,
            "description": (
                "The collector service is responsible for triggering data collection "
                "jobs from external housing-data sources, tracking their progress, "
                "and exposing the registered source catalogue."
            ),
            "sections": [
                {
                    "name": "Health & Readiness",
                    "description": (
                        "Lightweight probes used by infrastructure to verify the service "
                        "is alive and that its dependencies (MongoDB) are reachable. "
                        "These endpoints live outside the versioned prefix."
                    ),
                    "endpoints": [
                        {
                            "method": "GET",
                            "path": "/health",
                            "description": "Liveness probe. Returns {status: ok} when the process is running.",
                            "example_response": {"status": "ok"},
                        },
                        {
                            "method": "GET",
                            "path": "/ready",
                            "description": (
                                "Readiness probe. Returns {status: ready} only when MongoDB "
                                "is reachable. Returns HTTP 503 otherwise."
                            ),
                            "example_response": {"status": "ready"},
                        },
                    ],
                },
                {
                    "name": "Sources",
                    "description": "Inspect the catalogue of registered data sources.",
                    "endpoints": [
                        {
                            "method": "GET",
                            "path": f"{_BASE}/sources",
                            "description": "List all registered data sources with pagination.",
                            "query_params": {
                                "limit": "Max results to return (1–100, default 20)",
                                "offset": "Number of results to skip (default 0)",
                            },
                            "example_response": {
                                "success": True,
                                "data": {
                                    "sources": [
                                        {"name": "odata_il", "display_name": "OData IL", "status": "active"},
                                        {"name": "madlan", "display_name": "Madlan", "status": "active"},
                                    ],
                                    "total": 2,
                                    "limit": 20,
                                    "offset": 0,
                                },
                            },
                        },
                        {
                            "method": "GET",
                            "path": f"{_BASE}/collections/status",
                            "description": (
                                "Per-source summary: current status, last job result, "
                                "last run time, and number of records inserted."
                            ),
                            "query_params": {
                                "limit": "Max results to return (1–100, default 20)",
                                "offset": "Number of results to skip (default 0)",
                            },
                            "example_response": {
                                "success": True,
                                "data": [
                                    {
                                        "source_name": "odata_il",
                                        "display_name": "OData IL",
                                        "status": "active",
                                        "last_job_status": "completed",
                                        "last_job_id": "664abc123def456789012345",
                                        "last_run_at": "2026-03-11T08:00:00Z",
                                        "last_records_inserted": 312,
                                    }
                                ],
                            },
                        },
                    ],
                },
                {
                    "name": "Collection",
                    "description": (
                        "Trigger data-collection jobs. All trigger calls are fire-and-forget: "
                        "they return HTTP 202 immediately with a job_id that you can poll "
                        "via the Jobs endpoints."
                    ),
                    "endpoints": [
                        {
                            "method": "POST",
                            "path": f"{_BASE}/collect/source/{{source_name}}",
                            "description": (
                                "Trigger collection for a single named source. "
                                "Replace {source_name} with a name from GET /sources "
                                "(e.g. odata_il, madlan)."
                            ),
                            "path_params": {
                                "source_name": "The registered source identifier (e.g. 'odata_il', 'madlan')"
                            },
                            "example_request": "POST /api/collect/source/odata_il",
                            "example_response": {
                                "success": True,
                                "message": "Collection job accepted for source: odata_il",
                                "data": {"job_id": "664abc123def456789012345"},
                            },
                        },
                        {
                            "method": "POST",
                            "path": f"{_BASE}/collect/all",
                            "description": "Trigger collection for every active source simultaneously.",
                            "example_request": "POST /api/collect/all",
                            "example_response": {
                                "success": True,
                                "message": "Collection job accepted for all active sources",
                                "data": {"job_id": "664abc123def456789012345"},
                            },
                        },
                    ],
                },
                {
                    "name": "Jobs",
                    "description": "Track the status and results of collection jobs.",
                    "endpoints": [
                        {
                            "method": "GET",
                            "path": f"{_BASE}/jobs",
                            "description": "List collection jobs with optional status filter and pagination.",
                            "query_params": {
                                "status": "Filter by status: pending | running | completed | failed (optional)",
                                "limit": "Max results to return (1–100, default 20)",
                                "offset": "Number of results to skip (default 0)",
                            },
                            "example_response": {
                                "success": True,
                                "data": [
                                    {
                                        "id": "664abc123def456789012345",
                                        "source_name": "odata_il",
                                        "status": "completed",
                                        "records_inserted": 312,
                                        "created_at": "2026-03-11T08:00:00Z",
                                        "completed_at": "2026-03-11T08:01:12Z",
                                    }
                                ],
                            },
                        },
                        {
                            "method": "GET",
                            "path": f"{_BASE}/jobs/{{job_id}}",
                            "description": "Fetch the full detail of a single job by its ID.",
                            "path_params": {"job_id": "MongoDB ObjectId returned by a collection trigger"},
                            "example_response": {
                                "success": True,
                                "data": {
                                    "id": "664abc123def456789012345",
                                    "source_name": "odata_il",
                                    "status": "completed",
                                    "records_inserted": 312,
                                    "error": None,
                                    "created_at": "2026-03-11T08:00:00Z",
                                    "completed_at": "2026-03-11T08:01:12Z",
                                },
                            },
                        },
                    ],
                },
            ],
            "typical_workflow": [
                f"1. GET  {_BASE}/sources               → discover available source names",
                f"2. POST {_BASE}/collect/source/<name> → trigger a collection, note job_id",
                f"3. GET  {_BASE}/jobs/<job_id>         → poll until status is completed or failed",
                f"4. GET  {_BASE}/collections/status    → view a per-source summary dashboard",
            ],
            "interactive_docs": "/docs",
        }
    )
