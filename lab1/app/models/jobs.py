from datetime import datetime
from enum import StrEnum
from typing import Any, Optional

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field


class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):  # type: ignore[override]
        yield cls.validate

    @classmethod
    def validate(cls, v: Any, _info: Any = None) -> str:
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str) and ObjectId.is_valid(v):
            return v
        raise ValueError(f"Invalid ObjectId: {v}")

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> Any:
        from pydantic_core import core_schema

        return core_schema.no_info_plain_validator_function(
            cls.validate,
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: Any, handler: Any) -> Any:
        return {"type": "string"}


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ScrapeJob(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[PyObjectId] = Field(None, alias="_id")
    source_name: str
    status: JobStatus = JobStatus.PENDING
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    records_inserted: int = 0
    records_skipped: int = 0
    error_message: Optional[str] = None
    sub_job_ids: list[str] = Field(default_factory=list)


class JobSummary(BaseModel):
    job_id: str
    source_name: str
    status: JobStatus
    created_at: datetime
    records_inserted: int = 0
