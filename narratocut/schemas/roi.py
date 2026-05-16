from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from narratocut.schemas.base import Metadata, SchemaBase, utc_now


class TimeRange(SchemaBase):
    start_sec: float = Field(ge=0)
    end_sec: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> "TimeRange":
        if self.end_sec <= self.start_sec:
            raise ValueError("end_sec must be greater than start_sec")
        return self


class Hook(SchemaBase):
    hook_id: str
    project_id: str
    episode_id: str | None = None
    time_range: TimeRange | None = None
    hook_type: str
    emotion_tags: list[str] = Field(default_factory=list)
    plot_summary: str
    core_conflict: str
    user_trigger: str
    recommended_opening: str
    recommended_ending: str
    title_candidates: list[str] = Field(default_factory=list)
    risk_tags: list[str] = Field(default_factory=list)
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Metadata
    created_at: datetime = Field(default_factory=utc_now)
