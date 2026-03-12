from fastapi import Request
from fastapi.responses import JSONResponse


class SourceNotFoundError(Exception):
    def __init__(self, source_name: str) -> None:
        self.source_name = source_name
        super().__init__(f"Source not found: {source_name}")


class JobNotFoundError(Exception):
    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        super().__init__(f"Job not found: {job_id}")


class JobAlreadyRunningError(Exception):
    def __init__(self, source_name: str) -> None:
        self.source_name = source_name
        super().__init__(f"A job is already running for source: {source_name}")


class DatabaseUnavailableError(Exception):
    pass


class ScraperError(Exception):
    def __init__(self, source_name: str, detail: str) -> None:
        self.source_name = source_name
        super().__init__(f"Scraper failed for {source_name}: {detail}")


def _error_body(error_code: str, message: str, details: dict | None = None) -> dict:
    return {"success": False, "error_code": error_code, "message": message, "details": details}


async def source_not_found_handler(request: Request, exc: SourceNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content=_error_body("SOURCE_NOT_FOUND", str(exc)))


async def job_not_found_handler(request: Request, exc: JobNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content=_error_body("JOB_NOT_FOUND", str(exc)))


async def job_already_running_handler(request: Request, exc: JobAlreadyRunningError) -> JSONResponse:
    return JSONResponse(status_code=409, content=_error_body("JOB_ALREADY_RUNNING", str(exc)))


async def database_unavailable_handler(request: Request, exc: DatabaseUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=503, content=_error_body("DATABASE_UNAVAILABLE", "Database is not available"))


async def scraper_error_handler(request: Request, exc: ScraperError) -> JSONResponse:
    return JSONResponse(status_code=500, content=_error_body("SCRAPER_FAILED", str(exc)))


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=_error_body("INTERNAL_ERROR", "An unexpected error occurred"),
    )


def register_exception_handlers(app) -> None:  # type: ignore[no-untyped-def]
    app.add_exception_handler(SourceNotFoundError, source_not_found_handler)
    app.add_exception_handler(JobNotFoundError, job_not_found_handler)
    app.add_exception_handler(JobAlreadyRunningError, job_already_running_handler)
    app.add_exception_handler(DatabaseUnavailableError, database_unavailable_handler)
    app.add_exception_handler(ScraperError, scraper_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
