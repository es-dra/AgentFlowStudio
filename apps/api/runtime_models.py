from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ProjectStatus = Literal["in_progress", "blocked", "ready_for_next_round"]


class ProjectCreateRequest(BaseModel):
    project_id: str = Field(min_length=1)
    project_type: str = "short_video_campaign"
    goal: str = Field(min_length=1)
    status: ProjectStatus = "in_progress"


class ProjectImportRequest(BaseModel):
    manifest: dict[str, Any]


class SourceAssetRegisterRequest(BaseModel):
    asset_id: str = Field(min_length=1)
    asset_type: str = "reference"
    label: str = Field(min_length=1)
    summary: str = Field(min_length=1)


class ContentCardRegisterRequest(BaseModel):
    card_id: str = Field(min_length=1)
    card_type: str = "scene"
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    target_platform: str = "short_video"


class ReviewDecisionRecordRequest(BaseModel):
    card_id: str = Field(min_length=1)
    candidate_id: str | None = None
    artifact_id: str | None = None
    decision: Literal["keep", "revise", "reject"]
    note: str = Field(min_length=1)
    generated_at: str = Field(min_length=1)


class SceneInspectorUpdateRequest(BaseModel):
    card_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    reference_summary: str = Field(min_length=1)
    style_direction: str = Field(min_length=1)
    retry_intent: str = Field(min_length=1)


class CanvasDraftRequest(BaseModel):
    generated_at: str = Field(min_length=1)


class AssetTestRunRequest(BaseModel):
    project_id: str = Field(min_length=1)
    asset_profile_seed: str = Field(min_length=1)
    loop: str = "examples/agentflow/production_memory_loop.example.json"
    feedback_json: str = "examples/agentflow/production_memory_asset_feedback.example.json"
    consistency_review_json: str = "examples/agentflow/production_memory_asset_consistency_review.example.json"
    project_materials: str | None = None
    character_reference_image: str | None = None
    promotion_decision: str = Field(min_length=1)
    promotion_rationale: str = Field(min_length=1)
    reviewer_role: str = "operator"
    generated_at: str = Field(min_length=1)
    decided_at: str = Field(min_length=1)
    reviewed_at: str = Field(min_length=1)


class TwoRoundValidateRequest(BaseModel):
    project_id: str = Field(min_length=1)
    round_1_job_id: str = Field(min_length=1)
    consistency_review_json: str = "examples/agentflow/production_memory_asset_consistency_review.example.json"
    generated_at: str = Field(min_length=1)
    reviewed_at: str = Field(min_length=1)


class ProviderValidationPlanRequest(BaseModel):
    project_id: str = Field(min_length=1)
    asset_profile_seed: str = Field(min_length=1)
    provider_config: str | None = None
    project_materials: str | None = None
    character_reference_image: str | None = None
    image_service: str = "minimax_image"
    video_service: str = "kling_i2v"
    generated_at: str = Field(min_length=1)


class ProviderScriptDraftPlanRequest(BaseModel):
    project_id: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    target_platform: str = "short_video"
    style: str = "clear_demo"
    review_feedback_artifact_id: str | None = None
    previous_script_artifact_id: str | None = None
    generated_at: str = Field(min_length=1)


class DirectorSetup2D(BaseModel):
    view: str = "top_down_2d"
    activeCameraId: str | None = None
    activeSubjectIds: list[str] = Field(default_factory=list)
    characters: list[dict[str, Any]] = Field(default_factory=list)
    subjects: list[dict[str, Any]] = Field(default_factory=list)
    lights: list[dict[str, Any]] = Field(default_factory=list)
    cameras: list[dict[str, Any]] = Field(default_factory=list)
    modifiers: list[dict[str, Any]] = Field(default_factory=list)
    props: list[dict[str, Any]] = Field(default_factory=list)
    composition: str = ""
    notes: str = ""


class ContextSubgraphNode(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    title: str | None = None
    prompt: str | None = None
    image_asset_refs: list[str] = Field(default_factory=list)
    visual_asset_ids: list[str] = Field(default_factory=list)
    director_setup_summary: str | None = None
    node_parameters: dict[str, Any] | None = None


class ContextSubgraphEdge(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str | None = None
    from_node_id: str = Field(alias="from", min_length=1)
    to_node_id: str = Field(alias="to", min_length=1)
    relation_type: str = "generation"


class ContextSubgraph(BaseModel):
    target_node_id: str = Field(min_length=1)
    nodes: list[ContextSubgraphNode] = Field(default_factory=list)
    edges: list[ContextSubgraphEdge] = Field(default_factory=list)
    runtime_work_mode: str = "context_generate"


class TemporaryLockOverride(BaseModel):
    asset_id: str = Field(min_length=1)
    lock_text: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class PromptOptimizationRequest(BaseModel):
    node_id: str | None = None
    node_type: Literal["text", "image", "video", "audio", "script", "director", "video_merge"] = "text"
    prompt_text: str = Field(min_length=1)
    generation_target: Literal["prompt", "script", "image", "keyframe", "video", "audio"] = "prompt"
    target_platform: str = "short_video"
    style: str = "cinematic"
    asset_refs: list[str] = Field(default_factory=list)
    director_setup: DirectorSetup2D | None = None
    node_parameters: dict[str, Any] | None = None
    context_subgraph: ContextSubgraph | None = None
    generated_at: str = Field(min_length=1)


class KeyframeGenerationRequest(BaseModel):
    node_id: str | None = None
    prompt_text: str = Field(min_length=1)
    optimized_prompt: str | None = None
    target_platform: str = "short_video"
    style: str = "cinematic"
    aspect_ratio: str = "9:16"
    candidate_count: int = Field(default=1, ge=1, le=4)
    seed: int | None = Field(default=None, ge=0)
    provider_service_id: str = "minimax_image"
    asset_refs: list[str] = Field(default_factory=list)
    director_setup: DirectorSetup2D | None = None
    node_parameters: dict[str, Any] | None = None
    context_subgraph: ContextSubgraph | None = None
    temporary_lock_overrides: list[TemporaryLockOverride] = Field(default_factory=list)
    generated_at: str = Field(min_length=1)


class GenerationComparisonRequest(BaseModel):
    node_id: str | None = None
    prompt_text: str = Field(min_length=1)
    optimized_prompt: str | None = None
    target_platform: str = "short_video"
    style: str = "cinematic"
    aspect_ratio: str = "9:16"
    candidate_count: int = Field(default=1, ge=1, le=4)
    seed: int | None = Field(default=None, ge=0)
    provider_service_id: str = "minimax_image"
    context_subgraph: ContextSubgraph | None = None
    manual_scores: dict[str, Any] = Field(default_factory=dict)
    generated_at: str = Field(min_length=1)


class VisualAssetPromoteRequest(BaseModel):
    source_image_asset_refs: list[str] = Field(min_length=1)
    asset_type: Literal["character", "scene"]
    label: str = Field(min_length=1)
    signature: str = Field(min_length=1)
    feature_card: dict[str, Any] = Field(default_factory=dict)
    negative_locks: list[str] = Field(default_factory=list)
    source_node_id: str | None = None
    review_decision: Literal["fixed", "rejected"]
    reviewed_at: str = Field(min_length=1)


class VisualAssetRetireRequest(BaseModel):
    reason: str = Field(min_length=1)
    retired_at: str | None = None


class ImageAssetUploadRequest(BaseModel):
    node_id: str | None = None
    filename: str = Field(min_length=1)
    mime_type: str = Field(min_length=1)
    data_base64: str = Field(min_length=1)
    role: str = "reference_image"
    generated_at: str = Field(min_length=1)


class FeedbackRecordRequest(BaseModel):
    project_id: str = Field(min_length=1)
    feedback: dict[str, Any]
    generated_at: str = Field(min_length=1)


__all__ = (
    "AssetTestRunRequest",
    "CanvasDraftRequest",
    "ContentCardRegisterRequest",
    "ContextSubgraph",
    "ContextSubgraphEdge",
    "ContextSubgraphNode",
    "DirectorSetup2D",
    "FeedbackRecordRequest",
    "GenerationComparisonRequest",
    "ImageAssetUploadRequest",
    "KeyframeGenerationRequest",
    "PromptOptimizationRequest",
    "ProjectCreateRequest",
    "ProjectImportRequest",
    "ProviderScriptDraftPlanRequest",
    "ProviderValidationPlanRequest",
    "ProjectStatus",
    "ReviewDecisionRecordRequest",
    "SceneInspectorUpdateRequest",
    "SourceAssetRegisterRequest",
    "TemporaryLockOverride",
    "TwoRoundValidateRequest",
    "VisualAssetPromoteRequest",
    "VisualAssetRetireRequest",
)
