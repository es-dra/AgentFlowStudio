from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from narratocut.schemas.base import Metadata, SchemaBase, utc_now


ProbeStatus = Literal["succeeded", "failed", "missing"]


class VideoMetadata(SchemaBase):
    file_path: str
    duration_sec: float | None = Field(default=None, ge=0)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    codec: str | None = None
    fps: float | None = Field(default=None, ge=0)
    bitrate: int | None = Field(default=None, ge=0)
    probe_status: ProbeStatus
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Metadata
    created_at: datetime = Field(default_factory=utc_now)


class GeneratedVideo(SchemaBase):
    video_id: str
    project_id: str
    file_path: str
    duration_sec: float = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    hook_id: str | None = None
    script_id: str | None = None
    clip_plan_id: str | None = None
    title: str | None = None
    publish_text: str | None = None
    cover_path: str | None = None
    cost: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Metadata
    created_at: datetime = Field(default_factory=utc_now)


class ExportPackage(SchemaBase):
    package_id: str
    run_id: str
    project_id: str
    output_dir: str
    videos: list[GeneratedVideo] = Field(default_factory=list)
    metadata_path: str
    publish_texts_path: str | None = None
    metadata: dict[str, Any] = Metadata
    created_at: datetime = Field(default_factory=utc_now)
