from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from agentflow_studio.schemas.base import Metadata, SchemaBase, utc_now


ProjectType = Literal["ai_drama", "short_drama", "novel", "comic", "mixed"]


class Project(SchemaBase):
    project_id: str
    project_name: str
    project_type: ProjectType
    partner_name: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Metadata
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime | None = None
