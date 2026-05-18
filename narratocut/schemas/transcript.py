from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from narratocut.schemas.base import Metadata, SchemaBase


class TranscriptSegment(SchemaBase):
    segment_id: str
    start_time: float = Field(ge=0.0)
    end_time: float = Field(ge=0.0)
    text: str = Field(min_length=1)
    speaker: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Metadata

    @property
    def duration_sec(self) -> float:
        return self.end_time - self.start_time

    @model_validator(mode="after")
    def validate_time_range(self) -> "TranscriptSegment":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be greater than start_time")
        return self


class Transcript(SchemaBase):
    transcript_id: str
    source_video: str | None = None
    language: str | None = None
    segments: list[TranscriptSegment] = Field(min_length=1)
    duration: float | None = Field(default=None, ge=0.0)
    metadata: dict[str, Any] = Metadata

    @model_validator(mode="after")
    def validate_duration(self) -> "Transcript":
        if self.duration is None:
            return self
        last_end_time = max(segment.end_time for segment in self.segments)
        if last_end_time > self.duration:
            raise ValueError("transcript segment end_time exceeds declared duration")
        return self
