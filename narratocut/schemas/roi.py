from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

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


ValidationPolicy = Literal["advisory", "strict"]


class ROISettings(SchemaBase):
    target_platform: str
    target_audience: str
    content_goal: str
    min_clip_duration: float | None = Field(default=None, ge=0)
    max_clip_duration: float | None = Field(default=None, gt=0)
    target_clip_count: int | None = Field(default=None, ge=0)
    min_clip_count: int | None = Field(default=None, ge=0)
    max_clip_count: int | None = Field(default=None, ge=0)
    risk_tolerance: str | None = None
    priority: list[str] = Field(default_factory=list)
    validation_policy: ValidationPolicy = "advisory"
    metadata: dict[str, Any] = Metadata
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_ranges(self) -> "ROISettings":
        if (
            self.min_clip_duration is not None
            and self.max_clip_duration is not None
            and self.max_clip_duration < self.min_clip_duration
        ):
            raise ValueError("max_clip_duration must be greater than or equal to min_clip_duration")
        if (
            self.min_clip_count is not None
            and self.max_clip_count is not None
            and self.max_clip_count < self.min_clip_count
        ):
            raise ValueError("max_clip_count must be greater than or equal to min_clip_count")
        if (
            self.target_clip_count is not None
            and self.min_clip_count is not None
            and self.target_clip_count < self.min_clip_count
        ):
            raise ValueError("target_clip_count must be greater than or equal to min_clip_count")
        if (
            self.target_clip_count is not None
            and self.max_clip_count is not None
            and self.target_clip_count > self.max_clip_count
        ):
            raise ValueError("target_clip_count must be less than or equal to max_clip_count")
        return self
