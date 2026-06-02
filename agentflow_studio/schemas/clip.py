from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from agentflow_studio.schemas.base import Metadata, SchemaBase, utc_now


AspectRatio = Literal["9:16", "16:9", "1:1"]
RenderMode = Literal["blurred_bg", "center_crop", "fit"]


class ClipSegment(SchemaBase):
    segment_id: str | None = None
    source_video: str
    start_sec: float = Field(ge=0)
    end_sec: float = Field(ge=0)
    text: str | None = None
    speed: float = Field(default=1.0, gt=0)
    keep_original_audio: bool = True
    metadata: dict[str, Any] = Metadata

    @model_validator(mode="after")
    def validate_range(self) -> "ClipSegment":
        if self.end_sec <= self.start_sec:
            raise ValueError("end_sec must be greater than start_sec")
        return self


class SubtitleStyle(SchemaBase):
    font: str = "default"
    font_size: int = Field(default=42, gt=0)
    color: str = "#FFFFFF"
    stroke_color: str = "#000000"
    position: Literal["top", "center", "bottom"] = "bottom"


class RenderSpec(SchemaBase):
    aspect_ratio: AspectRatio = "9:16"
    width: int = Field(default=1080, gt=0)
    height: int = Field(default=1920, gt=0)
    fps: int = Field(default=30, gt=0)
    render_mode: RenderMode = "blurred_bg"
    subtitle_style: SubtitleStyle = Field(default_factory=SubtitleStyle)


class ClipPlan(SchemaBase):
    clip_plan_id: str
    project_id: str
    hook_id: str
    script_id: str | None = None
    duration_sec: float | None = Field(default=None, ge=0)
    title: str
    cover_text: str
    segments: list[ClipSegment] = Field(default_factory=list)
    render_spec: RenderSpec = Field(default_factory=RenderSpec)
    bgm_path: str | None = None
    voiceover_text: str | None = None
    cta_text: str | None = None
    output_name: str | None = None
    metadata: dict[str, Any] = Metadata
    created_at: datetime = Field(default_factory=utc_now)
