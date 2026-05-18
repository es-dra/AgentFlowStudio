from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from narratocut.schemas.base import SchemaBase, utc_now


PackageAssetRole = Literal[
    "final_video",
    "subtitled_video",
    "bgm_video",
    "cover_image",
    "review_report",
]


class FinishedPackageAsset(SchemaBase):
    role: PackageAssetRole
    path: str
    required: bool = False
    exists: bool = False
    size_bytes: int | None = Field(default=None, ge=0)


class FinishedPackageManifest(SchemaBase):
    schema_version: str = "0.1"
    status: Literal["succeeded", "failed"]
    package_id: str
    primary_video: FinishedPackageAsset
    assets: list[FinishedPackageAsset] = Field(default_factory=list)
    evidence: dict[str, str] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    manifest_path: str = "finished_package_manifest.json"
    created_at: datetime = Field(default_factory=utc_now)
