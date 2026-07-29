from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


StudioSurface = Literal[
    "overview",
    "canvas",
    "script",
    "storyboard",
    "asset-bible",
    "review",
    "delivery",
]
AuthorityMode = Literal["legacy_file", "graph_v1"]


class StudioModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StudioProjectSummary(StudioModel):
    project_id: str
    project_type: str
    name: str
    status: str


class StudioEntity(StudioModel):
    entity_id: str
    entity_type: str
    label: str
    state: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class StudioRelation(StudioModel):
    from_id: str
    to_id: str
    relation_type: str


class StudioAllowedAction(StudioModel):
    action: str
    enabled: bool
    requires_preview: bool = False
    target_entity_id: str = ""
    reason: str = ""


class StudioSurfaceSummary(StudioModel):
    state: Literal["empty", "ready", "attention", "blocked"]
    headline: str
    entity_count: int = Field(ge=0)
    attention_count: int = Field(ge=0)


class StudioResumeTarget(StudioModel):
    available: bool
    surface: StudioSurface
    entity_id: str = ""
    reason: str


class StudioAgentSummary(StudioModel):
    state: Literal[
        "collapsed",
        "suggestion_available",
        "attention_required",
        "content_updated",
    ]
    based_on_project_version: int = Field(ge=0)
    entity_id: str = ""
    headline: str


class StudioTaskSummary(StudioModel):
    task_id: str
    state: str
    depends_on: list[str] = Field(default_factory=list)
    attempt_count: int = Field(default=0, ge=0)


class StudioReviewItem(StudioModel):
    review_id: str
    target_entity_id: str
    state: str
    evidence_refs: list[str] = Field(default_factory=list)


class StudioArtifactSummary(StudioModel):
    artifact_id: str
    state: str
    version: int = Field(default=1, ge=1)
    selected: bool = False


class StudioCostSummary(StudioModel):
    available: bool = False
    reserved: float = Field(default=0, ge=0)
    committed: float = Field(default=0, ge=0)
    currency: str = ""
    message: str


class StudioRecoverySummary(StudioModel):
    attention_required: bool
    attention_task_count: int = Field(ge=0)
    safe_to_repeat_provider_dispatch: Literal[False] = False
    message: str


class StudioReworkPreview(StudioModel):
    available: bool
    target_entity_id: str = ""
    impact_refs: list[str] = Field(default_factory=list)
    keep_refs: list[str] = Field(default_factory=list)
    cost_available: bool = False
    reason: str


class StudioDeliverySummary(StudioModel):
    state: Literal["empty", "blocked", "review_ready", "ready", "delivered"]
    blocker_count: int = Field(ge=0)
    delivery_version_id: str = ""
    playable: bool = False


class StudioSurfaceEnvelope(StudioModel):
    schema_version: Literal["afs.studio_bff.v0.2"] = "afs.studio_bff.v0.2"
    project_id: str
    project: StudioProjectSummary
    authority_mode: AuthorityMode
    project_version: int = Field(ge=0)
    graph_digest: str
    event_cursor: int = Field(ge=0)
    surface: StudioSurface
    surface_summary: StudioSurfaceSummary
    focused_entity: StudioEntity | None = None
    resume_target: StudioResumeTarget
    agent_summary: StudioAgentSummary
    entities: list[StudioEntity] = Field(default_factory=list)
    relations: list[StudioRelation] = Field(default_factory=list)
    allowed_actions: list[StudioAllowedAction] = Field(default_factory=list)
    task_summaries: list[StudioTaskSummary] = Field(default_factory=list)
    review_queue: list[StudioReviewItem] = Field(default_factory=list)
    artifact_summaries: list[StudioArtifactSummary] = Field(default_factory=list)
    rework_preview: StudioReworkPreview
    delivery_summary: StudioDeliverySummary
    cost_summary: StudioCostSummary
    recovery_summary: StudioRecoverySummary
    provider_dispatch_count: Literal[0] = 0


__all__ = (
    "StudioSurface",
    "StudioSurfaceEnvelope",
)
