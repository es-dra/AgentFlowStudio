from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class SchemaBase(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


def metadata_field() -> dict[str, Any]:
    return {}


Metadata = Field(default_factory=metadata_field)
