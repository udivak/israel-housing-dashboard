from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class StandardResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    message: str = ""


class ErrorResponse(BaseModel):
    success: bool = False
    error_code: str
    message: str
    details: Optional[dict[str, Any]] = None


class PaginationParams(BaseModel):
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class JobAcceptedResponse(BaseModel):
    job_id: str
    message: str = "Job accepted"
