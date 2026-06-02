from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from agentflow_studio.schemas.base import Metadata, SchemaBase, utc_now


HighlightSourceType = Literal["script", "transcript"]
HighlightType = Literal[
    "hook",
    "conflict",
    "reversal",
    "climax",
    "quote",
    "insight",
    "summary",
    "cta",
    "call_to_action",
    "other",
]
HighlightInputMode = Literal["script_only", "timestamped_transcript"]


class HighlightSegment(SchemaBase):
    highlight_id: str
    source_type: HighlightSourceType
    highlight_type: HighlightType
    title: str
    text: str = Field(min_length=1)
    reason: str
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    roi_tags: list[str] = Field(default_factory=list)
    source_segment_ids: list[str] = Field(default_factory=list)
    start_time: float | None = Field(default=None, ge=0.0)
    end_time: float | None = Field(default=None, ge=0.0)
    suggested_duration: float | None = Field(default=None, gt=0.0)
    metadata: dict[str, Any] = Metadata

    @model_validator(mode="after")
    def validate_time_range(self) -> "HighlightSegment":
        has_start = self.start_time is not None
        has_end = self.end_time is not None
        if has_start != has_end:
            raise ValueError("start_time and end_time must be provided together")
        if self.start_time is not None and self.end_time is not None and self.end_time <= self.start_time:
            raise ValueError("end_time must be greater than start_time")
        return self


class HighlightPlan(SchemaBase):
    plan_id: str
    input_mode: HighlightInputMode
    source_id: str | None = None
    roi_profile: dict[str, Any] | None = None
    highlights: list[HighlightSegment] = Field(min_length=1)
    summary: str | None = None
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Metadata
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_input_mode_timestamps(self) -> "HighlightPlan":
        timed_highlights = [
            highlight
            for highlight in self.highlights
            if highlight.start_time is not None or highlight.end_time is not None
        ]
        if self.input_mode == "script_only" and timed_highlights:
            raise ValueError("script_only HighlightPlan must not include highlight timestamps")
        if self.input_mode == "timestamped_transcript" and len(timed_highlights) != len(self.highlights):
            raise ValueError("timestamped_transcript HighlightPlan requires timestamps for every highlight")
        return self
