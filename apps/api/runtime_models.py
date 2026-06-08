from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ProjectStatus = Literal["in_progress", "blocked", "ready_for_next_round"]


class ProjectCreateRequest(BaseModel):
    project_id: str = Field(min_length=1)
    project_type: str = "short_video_campaign"
    goal: str = Field(min_length=1)
    status: ProjectStatus = "in_progress"


class ProjectImportRequest(BaseModel):
    manifest: dict[str, Any]


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


class FeedbackRecordRequest(BaseModel):
    project_id: str = Field(min_length=1)
    feedback: dict[str, Any]
    generated_at: str = Field(min_length=1)


__all__ = (
    "AssetTestRunRequest",
    "FeedbackRecordRequest",
    "ProjectCreateRequest",
    "ProjectImportRequest",
    "ProviderValidationPlanRequest",
    "ProjectStatus",
    "TwoRoundValidateRequest",
)
