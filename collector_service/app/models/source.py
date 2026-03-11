from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.jobs import PyObjectId


class SourceStatus(StrEnum):
    ACTIVE = "active"
    PLANNED = "planned"
    DISABLED = "disabled"


class SourceDefinition(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[PyObjectId] = Field(None, alias="_id")
    name: str
    display_name: str
    description: str = ""
    status: SourceStatus = SourceStatus.ACTIVE
    source_url: str = ""
    tags: list[str] = Field(default_factory=list)


class SourceListResponse(BaseModel):
    sources: list[SourceDefinition]
    total: int
    limit: int
    offset: int
