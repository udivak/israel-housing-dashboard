from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.jobs import PyObjectId


class RetrievalMethod(StrEnum):
    HTTP_GET = "http_get"
    HTTP_POST = "http_post"
    ZIP_DOWNLOAD = "zip_download"
    FTP = "ftp"
    MOCK = "mock"
    BROWSER = "browser"


class ParsingStatus(StrEnum):
    RAW = "raw"
    PARSED = "parsed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RawRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[PyObjectId] = Field(None, alias="_id")
    source_name: str
    source_url: str
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    retrieval_method: RetrievalMethod
    raw_payload: dict[str, Any]
    parsing_status: ParsingStatus = ParsingStatus.RAW
    content_hash: str
    schema_version: str = "v1"
    tags: list[str] = Field(default_factory=list)
    job_id: Optional[str] = None


class IngestionLog(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[PyObjectId] = Field(None, alias="_id")
    job_id: str
    level: str
    message: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: Optional[dict[str, Any]] = None
