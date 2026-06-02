from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from agentflow_studio.schemas.base import Metadata, SchemaBase, utc_now


ScriptSegmentType = Literal["opening", "body", "climax", "cta", "other"]


class ScriptSegment(SchemaBase):
    segment_type: ScriptSegmentType
    text: str
    duration_sec: float | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Metadata


class ShortVideoScript(SchemaBase):
    script_id: str
    project_id: str
    hook_id: str
    platform: str = "douyin"
    target_duration_sec: int = Field(default=60, gt=0)
    style: str = "suspense_hook"
    title: str
    cover_text: str
    opening_3s: str
    segments: list[ScriptSegment] = Field(default_factory=list)
    cta: str
    risk_tags: list[str] = Field(default_factory=list)
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Metadata
    created_at: datetime = Field(default_factory=utc_now)
