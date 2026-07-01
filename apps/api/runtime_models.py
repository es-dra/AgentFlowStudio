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


class AssetExclusion(BaseModel):
    asset_id: str = Field(min_length=1)
    reason: str | None = None


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


class StoryboardBreakdownRequest(BaseModel):
    node_id: str | None = None
    script_text: str = Field(min_length=1)
    target_platform: str = "short_video"
    style: str = "cinematic"
    shot_count_hint: int | None = Field(default=None, ge=1, le=80)
    node_parameters: dict[str, Any] | None = None
    generated_at: str = Field(min_length=1)


class ShotAssetPlanRequest(BaseModel):
    node_id: str | None = None
    shot: dict[str, Any] = Field(default_factory=dict)
    script_text: str | None = None
    existing_assets: list[dict[str, Any]] = Field(default_factory=list)
    target_platform: str = "short_video"
    style: str = "cinematic"
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
    provider_service_id: str = "image_relay"
    asset_refs: list[str] = Field(default_factory=list)
    director_setup: DirectorSetup2D | None = None
    node_parameters: dict[str, Any] | None = None
    context_subgraph: ContextSubgraph | None = None
    temporary_lock_overrides: list[TemporaryLockOverride] = Field(default_factory=list)
    temporary_asset_exclusions: list[AssetExclusion] = Field(default_factory=list)
    preflight_token: str | None = None
    generated_at: str = Field(min_length=1)


class VideoInputSource(BaseModel):
    source_mode: Literal[
        "uploaded_image",
        "upstream_uploaded_image",
        "upstream_generated_image",
        "visual_asset_reference",
        "explicit_first_frame_selection",
    ]
    source_asset_id: str = Field(min_length=1)
    source_node_id: str | None = None
    source_job_id: str | None = None
    visual_asset_id: str | None = None
    role: Literal["first_frame", "last_frame", "reference_image"] = "first_frame"


class VideoGenerationRequest(BaseModel):
    node_id: str | None = None
    prompt_text: str = Field(min_length=1)
    optimized_prompt: str | None = None
    provider_service_id: str = "seedance_i2v"
    first_frame_image_asset_id: str = Field(min_length=1)
    last_frame_image_asset_id: str | None = None
    input_source: VideoInputSource | None = None
    duration_sec: int = Field(default=5, ge=1, le=15)
    resolution: str = "720p"
    aspect_ratio: str = "9:16"
    motion: str = ""
    candidate_count: int = Field(default=1, ge=1, le=1)
    context_subgraph: ContextSubgraph | None = None
    temporary_lock_overrides: list[TemporaryLockOverride] = Field(default_factory=list)
    temporary_asset_exclusions: list[AssetExclusion] = Field(default_factory=list)
    preflight_token: str | None = None
    quota_override_confirmed: bool = False
    generated_at: str = Field(min_length=1)


class VideoRevisionRequest(BaseModel):
    node_id: str | None = None
    base_video_job_id: str = Field(min_length=1)
    base_video_artifact_id: str | None = None
    base_lineage_root_job_id: str | None = None
    parent_revision_job_id: str | None = None
    revision_intent: str = Field(min_length=1)
    editable_targets: list[str] = Field(default_factory=list)
    locked_aspects: list[str] = Field(default_factory=list)
    temporal_scope: dict[str, Any] = Field(default_factory=dict)
    preserve_policy: str = "best_effort"
    provider_capability_mode: Literal["i2v_revision_attempt", "v2v_edit", "masked_edit", "unsupported"] = (
        "i2v_revision_attempt"
    )
    provider_service_id: str = "seedance_i2v"
    first_frame_image_asset_id: str = Field(min_length=1)
    last_frame_image_asset_id: str | None = None
    input_source: VideoInputSource | None = None
    duration_sec: int = Field(default=5, ge=1, le=15)
    resolution: str = "720p"
    aspect_ratio: str = "9:16"
    motion: str = ""
    candidate_count: int = Field(default=1, ge=1, le=1)
    context_subgraph: ContextSubgraph | None = None
    temporary_lock_overrides: list[TemporaryLockOverride] = Field(default_factory=list)
    temporary_asset_exclusions: list[AssetExclusion] = Field(default_factory=list)
    preflight_token: str | None = None
    quota_override_confirmed: bool = False
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
    provider_service_id: str = "image_relay"
    context_subgraph: ContextSubgraph | None = None
    manual_scores: dict[str, Any] = Field(default_factory=dict)
    generated_at: str = Field(min_length=1)


class VisualAssetPromoteRequest(BaseModel):
    source_image_asset_refs: list[str] = Field(min_length=1)
    asset_type: Literal["character", "scene", "prop"]
    label: str = Field(min_length=1)
    signature: str = Field(min_length=1)
    feature_card: dict[str, Any] = Field(default_factory=dict)
    negative_locks: list[str] = Field(default_factory=list)
    source_node_id: str | None = None
    supersedes_asset_id: str | None = None
    source_human_gate_id: str | None = None
    source_asset_card_candidate_id: str | None = None
    review_decision: Literal["fixed", "rejected"]
    reviewed_at: str = Field(min_length=1)


class AssetCardDraftRequest(BaseModel):
    asset_type: Literal["character", "scene", "prop", "video"]
    source_image_asset_refs: list[str] = Field(default_factory=list)
    source_video_artifact_id: str | None = None
    sampled_image_asset_refs: list[str] = Field(default_factory=list)
    node_id: str | None = None
    prompt_text: str = Field(min_length=1)
    provider_service_id: str = "vision_image"
    generated_at: str = Field(min_length=1)


class VideoAssetPromoteRequest(BaseModel):
    source_video_artifact_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    segments: list[dict[str, Any]] = Field(default_factory=list)
    feature_card: dict[str, Any] = Field(default_factory=dict)
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


class FeedbackCandidatePromotionRequest(BaseModel):
    feedback_artifact_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    decision: Literal["promote_to_context_overlay", "reject", "needs_more_evidence"]
    rationale: str = Field(min_length=1)
    reviewed_at: str = Field(min_length=1)


class FeedbackCandidateContextOverlayRequest(BaseModel):
    promotion_decision_artifact_id: str = Field(min_length=1)
    overlay_intent: str = Field(min_length=1)
    generated_at: str = Field(min_length=1)


class HumanGateDecisionRequest(BaseModel):
    target_type: Literal["asset_card_candidate", "keyframe_generation_bridge"]
    target_id: str = Field(min_length=1)
    decision: Literal["accepted_for_next_step", "needs_revision", "rejected"]
    artifact_id: str | None = None
    node_id: str | None = None
    scope: str | None = None
    note: str = ""
    reviewed_at: str = Field(min_length=1)


class StudioClientEventRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=80)
    severity: Literal["info", "warning", "error"] = "info"
    message: str = Field(default="", max_length=240)
    project_id: str = Field(default="", max_length=160)
    action: str = Field(default="", max_length=120)
    details: dict[str, Any] = Field(default_factory=dict)
    generated_at: str = Field(min_length=1)


class SpriteChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1200)
    node_id: str | None = None
    canvas_summary: dict[str, Any] = Field(default_factory=dict)
    provider_service_id: str = "prompt_optimizer"
    generated_at: str = Field(min_length=1)


__all__ = (
    "AssetCardDraftRequest",
    "CanvasDraftRequest",
    "AssetExclusion",
    "ContentCardRegisterRequest",
    "ContextSubgraph",
    "ContextSubgraphEdge",
    "ContextSubgraphNode",
    "DirectorSetup2D",
    "FeedbackCandidateContextOverlayRequest",
    "FeedbackCandidatePromotionRequest",
    "FeedbackRecordRequest",
    "GenerationComparisonRequest",
    "HumanGateDecisionRequest",
    "ImageAssetUploadRequest",
    "KeyframeGenerationRequest",
    "PromptOptimizationRequest",
    "ProjectCreateRequest",
    "ProjectImportRequest",
    "ProviderScriptDraftPlanRequest",
    "ProjectStatus",
    "ReviewDecisionRecordRequest",
    "SceneInspectorUpdateRequest",
    "ShotAssetPlanRequest",
    "SourceAssetRegisterRequest",
    "StoryboardBreakdownRequest",
    "StudioClientEventRequest",
    "SpriteChatRequest",
    "TemporaryLockOverride",
    "VisualAssetPromoteRequest",
    "VisualAssetRetireRequest",
    "VideoAssetPromoteRequest",
    "VideoGenerationRequest",
    "VideoInputSource",
    "VideoRevisionRequest",
)
