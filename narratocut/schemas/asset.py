from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from narratocut.schemas.base import Metadata, SchemaBase, utc_now


AssetType = Literal["video", "audio", "image", "text", "subtitle", "script", "json", "other"]


class Asset(SchemaBase):
    asset_id: str
    project_id: str
    asset_type: AssetType
    path: str
    file_name: str | None = None
    duration_sec: float | None = Field(default=None, ge=0)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    metadata: dict[str, Any] = Metadata
    created_at: datetime = Field(default_factory=utc_now)
