import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router, health_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.db.mongo import close_mongo_connection, connect_to_mongo, create_indexes, get_database
from app.db.repositories.jobs import JobsRepository
from app.db.repositories.raw_records import RawRecordsRepository
from app.services.collection_service import CollectionService
from app.services.source_registry import SourceRegistry

configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await logger.ainfo("Starting up lab1 API")
    await connect_to_mongo()
    await create_indexes()

    db = get_database()
    jobs_repo = JobsRepository(db)
    recovered = await jobs_repo.recover_stale_jobs()
    if recovered:
        await logger.awarning("Recovered stale jobs on startup", count=recovered)

    registry = SourceRegistry(db)
    await registry.seed_default_sources()

    app.state.source_registry = registry
    app.state.jobs_repo = jobs_repo
    app.state.raw_records_repo = RawRecordsRepository(db)
    app.state.collection_service = CollectionService(db, registry)

    await logger.ainfo("Startup complete — 2 sources active: odata_il_nadlan, cbs_housing")
    yield

    await logger.ainfo("Shutting down lab1 API")
    await close_mongo_connection()


app = FastAPI(
    title="Lab1 — Israel Housing Scraper",
    description=(
        "Scraping exercise: downloads Israeli housing data from odata.org.il (ZIP/XLSX) "
        "and the CBS price-index API (paginated REST), stores results in local MongoDB."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    request_id = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        service_name=settings.SERVICE_NAME,
    )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


register_exception_handlers(app)
app.include_router(health_router)
app.include_router(api_router)
