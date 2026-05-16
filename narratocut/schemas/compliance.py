from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from narratocut.schemas.base import Metadata, SchemaBase, utc_now


RiskLevel = Literal["low", "medium", "high"]


class ComplianceResult(SchemaBase):
    passed: bool
    risk_level: RiskLevel
    risk_tags: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Metadata
    checked_at: datetime = Field(default_factory=utc_now)
