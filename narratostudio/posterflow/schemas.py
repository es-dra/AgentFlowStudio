from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import Field, field_validator

from narratocut.schemas.base import Metadata, SchemaBase


SCHEMA_VERSION = "0.1.0"
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


class PosterArtifact(SchemaBase):
    schema_version: str = SCHEMA_VERSION
    artifact_type: str
    metadata: dict[str, Any] = Metadata

    @field_validator("schema_version")
    @classmethod
    def schema_version_must_match(cls, value: str) -> str:
        if not SEMVER_RE.match(value):
            raise ValueError("schema_version must use semver, for example 0.1.0")
        if value != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
        return value


class PosterBrief(PosterArtifact):
    artifact_type: Literal["poster_brief"] = "poster_brief"
    project_id: str
    task_id: str
    task_type: Literal["poster_generation"] = "poster_generation"
    use_case: str
    platform: str
    target_audience: str
    theme: str
    business_goal: str
    content_goal: str
    visual_requirements: dict[str, Any] = Field(default_factory=dict)
    text_requirements: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    memory_policy: dict[str, bool] = Field(default_factory=dict)
    raw_user_request: str


class PosterPlan(PosterArtifact):
    artifact_type: Literal["poster_plan"] = "poster_plan"
    project_id: str
    run_id: str
    design_intent: str
    layout_plan: dict[str, Any]
    visual_plan: dict[str, Any]
    color_plan: dict[str, Any]
    text_plan: dict[str, Any]
    negative_rules: list[str] = Field(default_factory=list)
    memory_refs: list[str] = Field(default_factory=list)
    planner_notes: str = ""


class PosterPromptPack(PosterArtifact):
    artifact_type: Literal["poster_prompt_pack"] = "poster_prompt_pack"
    project_id: str
    run_id: str
    prompt_id: str
    target_model_family: str
    prompt_language: str = "en"
    positive_prompt: str
    negative_prompt: str = ""
    prompt_sections: dict[str, str] = Field(default_factory=dict)
    model_params: dict[str, Any] = Field(default_factory=dict)
    context_usage: dict[str, Any] = Field(default_factory=dict)
    source_refs: dict[str, str] = Field(default_factory=dict)


class PosterCandidate(SchemaBase):
    candidate_id: str
    image_path: str
    prompt_id: str
    status: Literal["generated", "failed"] = "generated"
    provider: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class PosterCandidatesManifest(PosterArtifact):
    artifact_type: Literal["poster_candidates_manifest"] = "poster_candidates_manifest"
    project_id: str
    run_id: str
    prompt_id: str
    provider_mode: Literal["remote", "mock"] = "remote"
    candidates: list[PosterCandidate] = Field(min_length=1)
    source_refs: dict[str, str] = Field(default_factory=dict)


class PosterModelInvocation(SchemaBase):
    invocation_id: str
    provider: str
    model: str
    provider_mode: Literal["remote", "mock"] = "remote"
    prompt_id: str
    input_hash: str
    params: dict[str, Any] = Field(default_factory=dict)
    output_files: list[str] = Field(default_factory=list)
    latency_ms: int = Field(default=0, ge=0)
    estimated_cost: float = Field(default=0, ge=0)
    status: Literal["succeeded", "failed"] = "succeeded"
    error: str | None = None


class PosterModelInvocations(PosterArtifact):
    artifact_type: Literal["poster_model_invocations"] = "poster_model_invocations"
    project_id: str
    run_id: str
    invocations: list[PosterModelInvocation] = Field(default_factory=list)


class PosterFeedbackSignal(SchemaBase):
    feedback_id: str
    candidate_id: str
    decision: Literal["preferred", "accepted", "rejected", "pending", "note"]
    reason_tags: list[str] = Field(default_factory=list)
    user_note: str = ""
    source: Literal["human", "demo_fixture"] = "demo_fixture"


class PosterRawFeedbackEvent(SchemaBase):
    schema_version: str = SCHEMA_VERSION
    feedback_id: str
    project_id: str
    run_id: str
    source: Literal["human", "agent", "external", "demo_fixture"] = "demo_fixture"
    target_type: Literal["poster_candidate"] = "poster_candidate"
    target_id: str
    decision: Literal["accepted", "rejected", "needs_revision", "note", "published", "preferred", "pending"]
    reason_tags: list[str] = Field(default_factory=list)
    user_note: str = ""
    created_at: str

    @field_validator("schema_version")
    @classmethod
    def schema_version_must_match(cls, value: str) -> str:
        if not SEMVER_RE.match(value):
            raise ValueError("schema_version must use semver, for example 0.1.0")
        if value != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
        return value


class PosterFeedbackSignalLog(PosterArtifact):
    artifact_type: Literal["poster_feedback_signal_log"] = "poster_feedback_signal_log"
    project_id: str
    run_id: str
    source_of_truth: str = "poster_feedback.jsonl"
    is_primary_feedback_store: Literal[False] = False
    signals: list[PosterFeedbackSignal] = Field(default_factory=list)


class PosterMemoryCandidate(SchemaBase):
    memory_candidate_id: str
    promotion_status: Literal["candidate"] = "candidate"
    memory_type: str
    scope: Literal["run", "project"] = "project"
    claim: str
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    requires_human_review: bool = True
    recommended_action: str = "promote_to_project_profile"
    status: Literal["pending_review"] = "pending_review"


class PosterMemoryReviewEvent(SchemaBase):
    schema_version: str = SCHEMA_VERSION
    review_id: str
    project_id: str
    run_id: str
    memory_candidate_id: str
    decision: Literal["accepted", "rejected", "merged", "expired"]
    review_mode: Literal["demo_human_review_gate"] = "demo_human_review_gate"
    reviewer: Literal["demo_human_review_gate"] = "demo_human_review_gate"
    source_artifact: Literal["poster_memory_candidates.jsonl"] = "poster_memory_candidates.jsonl"
    writes_long_term_memory: Literal[False] = False
    reason: str

    @field_validator("schema_version")
    @classmethod
    def schema_version_must_match(cls, value: str) -> str:
        if not SEMVER_RE.match(value):
            raise ValueError("schema_version must use semver, for example 0.1.0")
        if value != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
        return value


class PosterMemoryCandidates(PosterArtifact):
    artifact_type: Literal["poster_memory_candidates"] = "poster_memory_candidates"
    project_id: str
    run_id: str
    candidates: list[PosterMemoryCandidate] = Field(default_factory=list)


class PosterMemoryDecision(SchemaBase):
    decision_id: str
    memory_candidate_id: str
    decision: Literal["accepted", "rejected"]
    decided_by: Literal["demo_human_review_gate"] = "demo_human_review_gate"
    writes_long_term_memory: Literal[False] = False
    reason: str


class PosterMemoryDecisions(PosterArtifact):
    artifact_type: Literal["poster_memory_decisions"] = "poster_memory_decisions"
    project_id: str
    run_id: str
    decisions: list[PosterMemoryDecision] = Field(default_factory=list)


class PosterPreferenceProfile(PosterArtifact):
    artifact_type: Literal["poster_preference_profile"] = "poster_preference_profile"
    project_id: str
    profile_version: int = Field(default=1, ge=1)
    visual_preferences: list[str] = Field(default_factory=list)
    negative_visual_preferences: list[str] = Field(default_factory=list)
    layout_preferences: list[str] = Field(default_factory=list)
    text_preferences: list[str] = Field(default_factory=list)
    prompt_rules: list[str] = Field(default_factory=list)
    source_memory_candidates: list[str] = Field(default_factory=list)
    scope: Literal["project"] = "project"
    status: Literal["demo_only"] = "demo_only"
    writes_long_term_memory: Literal[False] = False


class ContextBundle(PosterArtifact):
    artifact_type: Literal["context_bundle"] = "context_bundle"
    project_id: str
    run_id: str
    bundle_id: str
    target_artifact: Literal["next_round_prompt"] = "next_round_prompt"
    project_prefix_path: str
    preference_profile_path: str
    source_artifacts: dict[str, str] = Field(default_factory=dict)
    context_layers: dict[str, Any] = Field(default_factory=dict)
    quality_rules: list[str] = Field(default_factory=list)
    cache_plan: dict[str, Any] = Field(default_factory=dict)
    retrieval_status: Literal["not_configured"] = "not_configured"
    writes_long_term_memory: Literal[False] = False


class ContextAssemblyTrace(PosterArtifact):
    artifact_type: Literal["context_assembly_trace"] = "context_assembly_trace"
    project_id: str
    run_id: str
    bundle_id: str
    selection_decisions: list[dict[str, Any]] = Field(default_factory=list)
    budget: dict[str, Any] = Field(default_factory=dict)
    rejected_context: list[dict[str, Any]] = Field(default_factory=list)
    cache_key: str
    writes_long_term_memory: Literal[False] = False


class NextRoundPrompt(PosterArtifact):
    artifact_type: Literal["next_round_prompt"] = "next_round_prompt"
    project_id: str
    new_run_id: str
    based_on_profile_version: int
    memory_context: dict[str, Any]
    task_delta: dict[str, Any]
    composed_positive_prompt: str
    composed_negative_prompt: str
    diff_from_previous_prompt: dict[str, list[str]]
