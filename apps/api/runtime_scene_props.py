"""Production SceneProps schema flattened into Scene-owned candidate facts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from apps.api.runtime_candidate_fact_status import ClaimedText


SCHEMA_VERSION = "afs.script_understanding.scene_props.v0.1"


class ScenePropItem(BaseModel):
    """One explicit prop mention owned by a Scene."""

    model_config = ConfigDict(extra="forbid")

    prop_id: str = Field(min_length=1, max_length=120)
    name: ClaimedText
    importance: ClaimedText | None = Field(
        default=None,
        description="Only populated when the screenplay explicitly labels importance.",
    )


class SceneProps(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    scene_entity_id: str = Field(min_length=1, max_length=120)
    items: list[ScenePropItem] = Field(default_factory=list, max_length=32)


__all__ = ("SCHEMA_VERSION", "ScenePropItem", "SceneProps")
