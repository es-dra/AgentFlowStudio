from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ExternalVideoJobRequest(BaseModel):
    node_id: str | None = None
    prompt_text: str = Field(min_length=1, max_length=6000)
    title: str = Field(default="AI comic roadshow demo", min_length=1, max_length=120)
    engine: Literal["replay", "libtv"] = "replay"
    style: str = Field(default="animated_comic", min_length=1, max_length=120)
    aspect_ratio: str = Field(default="9:16", min_length=3, max_length=12)
    duration_sec: int = Field(default=6, ge=1, le=180)
    scene_count: int = Field(default=3, ge=1, le=12)
    replay_profile: Literal["ai_comic_demo"] = "ai_comic_demo"
    generated_at: str = Field(min_length=1, max_length=80)


__all__ = ("ExternalVideoJobRequest",)
