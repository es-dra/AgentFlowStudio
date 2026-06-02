from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from agentflow_studio.schemas.base import SchemaBase, utc_now


class SubtitleCue(SchemaBase):
    index: int = Field(ge=1)
    segment_id: str
    start_time: float = Field(ge=0.0)
    end_time: float = Field(ge=0.0)
    start_timestamp: str
    end_timestamp: str
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_time_range(self) -> "SubtitleCue":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be greater than start_time")
        return self


class SubtitleManifest(SchemaBase):
    status: Literal["succeeded", "failed"]
    format: Literal["srt"] = "srt"
    timeline: Literal["source_video", "final_video"] = "source_video"
    subtitle_path: str
    source_transcript_id: str | None = None
    source_video: str | None = None
    language: str | None = None
    segment_count: int = Field(ge=0)
    duration_sec: float | None = Field(default=None, ge=0.0)
    cues: list[SubtitleCue] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    manifest_path: str = "subtitle_manifest.json"
    created_at: datetime = Field(default_factory=utc_now)
