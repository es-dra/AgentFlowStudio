from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS

PRODUCTION_RUN_SCHEMA_VERSION = "afs_runtime_production_run.v0.1"
PRODUCTION_CHECKPOINT_SCHEMA_VERSION = "afs_runtime_production_checkpoint.v0.1"
STUDIO_PRODUCTION_BINDING_SCHEMA_VERSION = "afs_studio_production_binding.v0.1"
CREATOR_DECISION_SCHEMA_VERSION = "afs_creator_decision.v0.1"
QUALITY_REVIEW_SCHEMA_VERSION = "afs_production_quality_review.v0.1"
PRODUCTION_EXPORT_SCHEMA_VERSION = "afs_production_export.v0.1"
REPRESENTATIVE_EPISODE_BINDING_SCHEMA_VERSION = "afs_representative_episode_binding.v0.1"

SAFE_IDENTIFIER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$"
SHA256_PATTERN = r"^[a-f0-9]{64}$"
SAFE_ARTIFACT_ROLES = frozenset(
    {
        "candidate_preview",
        "candidate_manifest",
        "script",
        "character_asset",
        "scene_asset",
        "storyboard",
        "shot",
        "selected_revision",
        "production_export",
        "production_evidence",
    }
)


class ProductionContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProductionCheckpoint(ProductionContractModel):
    schema_version: Literal["afs_runtime_production_checkpoint.v0.1"] = PRODUCTION_CHECKPOINT_SCHEMA_VERSION
    version: int = Field(ge=1, strict=True)
    previous_digest: str | None = Field(default=None, pattern=SHA256_PATTERN)
    state_digest: str = Field(pattern=SHA256_PATTERN)
    updated_at: str = Field(min_length=1, max_length=80)

    @field_validator("updated_at")
    @classmethod
    def validate_updated_at(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("checkpoint updated_at must be an ISO-8601 timestamp") from exc
        return value


class SafeArtifactRef(ProductionContractModel):
    artifact_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    artifact_type: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    role: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    media_type: Literal["application/json", "text/markdown", "image/png", "image/jpeg", "image/webp"]

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in SAFE_ARTIFACT_ROLES:
            raise ValueError("unsupported safe artifact role")
        return value


class ProductionCandidate(ProductionContractModel):
    candidate_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    canonical_digest: str = Field(pattern=SHA256_PATTERN)
    parent_job_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    parent_candidate_id: str | None = Field(default=None, pattern=SAFE_IDENTIFIER_PATTERN)
    parent_revision_id: str | None = Field(default=None, pattern=SAFE_IDENTIFIER_PATTERN)
    shot_id: str | None = Field(default=None, pattern=SAFE_IDENTIFIER_PATTERN)
    safe_artifact_refs: list[SafeArtifactRef] = Field(default_factory=list, max_length=16)


class ProductionRunCreateRequest(ProductionContractModel):
    schema_version: Literal["afs_runtime_production_run.v0.1"] = PRODUCTION_RUN_SCHEMA_VERSION
    run_id: str | None = Field(default=None, pattern=SAFE_IDENTIFIER_PATTERN)
    idempotency_key: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    subject_digest: str = Field(pattern=SHA256_PATTERN)
    candidates: list[ProductionCandidate] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def candidate_ids_are_unique(self) -> "ProductionRunCreateRequest":
        candidate_ids = [candidate.candidate_id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate ids must be unique within a production run")
        return self


class CreatorDecisionRequest(ProductionContractModel):
    schema_version: Literal["afs_creator_decision.v0.1"] = CREATOR_DECISION_SCHEMA_VERSION
    decision_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    idempotency_key: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    expected_checkpoint_version: int = Field(ge=1)
    subject_digest: str = Field(pattern=SHA256_PATTERN)
    decision: Literal["select", "revise", "reject"]
    candidate_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    candidate_digest: str = Field(pattern=SHA256_PATTERN)
    parent_revision_id: str | None = Field(default=None, pattern=SAFE_IDENTIFIER_PATTERN)
    revision_intent: str = Field(min_length=1, max_length=800)

    @field_validator("revision_intent")
    @classmethod
    def validate_revision_intent(cls, value: str) -> str:
        return _safe_public_text(value)


class ProductionQualityChecklist(ProductionContractModel):
    story_intent_preserved: bool
    character_continuity_checked: bool
    shot_coverage_checked: bool
    revision_addressed: bool


class ProductionQualityReviewRequest(ProductionContractModel):
    schema_version: Literal["afs_production_quality_review.v0.1"] = QUALITY_REVIEW_SCHEMA_VERSION
    review_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    idempotency_key: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    expected_checkpoint_version: int = Field(ge=1)
    reviewed_subject_digest: str = Field(pattern=SHA256_PATTERN)
    selected_revision_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    selected_revision_digest: str = Field(pattern=SHA256_PATTERN)
    decision: Literal["approve", "reject"]
    checklist: ProductionQualityChecklist
    note: str = Field(default="", max_length=800)

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        return _safe_public_text(value)

    @model_validator(mode="after")
    def approved_review_requires_complete_checklist(self) -> "ProductionQualityReviewRequest":
        if self.decision == "approve" and not all(self.checklist.model_dump().values()):
            raise ValueError("approved quality review requires every checklist item")
        return self


class ProductionExportRequest(ProductionContractModel):
    schema_version: Literal["afs_production_export.v0.1"] = PRODUCTION_EXPORT_SCHEMA_VERSION
    export_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    idempotency_key: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    expected_checkpoint_version: int = Field(ge=1)
    selected_revision_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    selected_revision_digest: str = Field(pattern=SHA256_PATTERN)


class EpisodeEntityVersionRef(ProductionContractModel):
    entity_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    current_approved_version_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)


class EpisodeAssetReadinessRef(ProductionContractModel):
    asset_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    current_revision_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    status: Literal["missing", "ready"]
    provider_needed: bool

    @model_validator(mode="after")
    def missing_assets_require_a_provider_gate(self) -> "EpisodeAssetReadinessRef":
        if self.status == "missing" and not self.provider_needed:
            raise ValueError("missing episode asset must retain provider_needed gate")
        return self


class EpisodeReconfirmationEvidenceRef(ProductionContractModel):
    task_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    approved_version_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    status: Literal["required_pending", "reconfirmed"]


class RepresentativeEpisodeBindingRequest(ProductionContractModel):
    schema_version: Literal["afs_representative_episode_binding.v0.1"] = (
        REPRESENTATIVE_EPISODE_BINDING_SCHEMA_VERSION
    )
    idempotency_key: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    expected_checkpoint_version: int = Field(ge=1, strict=True)
    expected_package_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    package_sha256: str = Field(pattern=SHA256_PATTERN)
    package_project_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    episode_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    episode_version_id: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    character_refs: list[EpisodeEntityVersionRef] = Field(min_length=3, max_length=3)
    scene_refs: list[EpisodeEntityVersionRef] = Field(min_length=3, max_length=3)
    shot_refs: list[EpisodeEntityVersionRef] = Field(min_length=15, max_length=15)
    asset_refs: list[EpisodeAssetReadinessRef] = Field(min_length=25, max_length=25)
    pending_media_count: int = Field(ge=0, le=25, strict=True)
    creator_decision_ref: str = Field(pattern=SAFE_IDENTIFIER_PATTERN)
    authoritative_affected_task_refs: list[str] = Field(min_length=1, max_length=32)
    downstream_reconfirmations: list[EpisodeReconfirmationEvidenceRef] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def exact_episode_inventory_is_consistent(self) -> "RepresentativeEpisodeBindingRequest":
        _require_unique_refs(self.character_refs, "entity_id", "character")
        _require_unique_refs(self.scene_refs, "entity_id", "scene")
        _require_unique_refs(self.shot_refs, "entity_id", "shot")
        _require_unique_refs(self.asset_refs, "asset_id", "asset")
        _require_unique_strings(self.authoritative_affected_task_refs, "affected task")
        _require_unique_refs(self.downstream_reconfirmations, "task_id", "reconfirmation task")
        missing_count = sum(item.status == "missing" for item in self.asset_refs)
        if self.pending_media_count != missing_count:
            raise ValueError("pending_media_count must equal the missing asset inventory")
        reconfirmation_task_ids = {item.task_id for item in self.downstream_reconfirmations}
        if reconfirmation_task_ids != set(self.authoritative_affected_task_refs):
            raise ValueError("downstream reconfirmation evidence must cover every authoritative affected task")
        if any(item.approved_version_id != self.episode_version_id for item in self.downstream_reconfirmations):
            raise ValueError("downstream reconfirmation evidence must target the exact episode version")
        return self


def canonical_json_digest(payload: Any) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def checkpoint_digest(payload: dict[str, Any]) -> str:
    checkpoint = payload.get("checkpoint") if isinstance(payload.get("checkpoint"), dict) else {}
    unsigned = {
        **{key: value for key, value in payload.items() if key != "checkpoint"},
        "checkpoint": {key: value for key, value in checkpoint.items() if key != "state_digest"},
    }
    return canonical_json_digest(unsigned)


def is_sha256(value: str) -> bool:
    return bool(re.fullmatch(SHA256_PATTERN, str(value or "")))


def _safe_public_text(value: str) -> str:
    lowered = str(value or "").lower()
    if any(fragment.lower() in lowered for fragment in AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS):
        raise ValueError("production contract text contains a private path, media ref, or secret-like fragment")
    return str(value)


def _require_unique_refs(records: list[Any], field: str, label: str) -> None:
    values = [str(getattr(item, field, "") or "") for item in records]
    if len(values) != len(set(values)):
        raise ValueError(f"{label} refs must be unique")


def _require_unique_strings(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} refs must be unique")
    if any(not re.fullmatch(SAFE_IDENTIFIER_PATTERN, str(value or "")) for value in values):
        raise ValueError(f"{label} refs must use safe identifiers")


__all__ = (
    "CREATOR_DECISION_SCHEMA_VERSION",
    "PRODUCTION_CHECKPOINT_SCHEMA_VERSION",
    "PRODUCTION_EXPORT_SCHEMA_VERSION",
    "PRODUCTION_RUN_SCHEMA_VERSION",
    "QUALITY_REVIEW_SCHEMA_VERSION",
    "REPRESENTATIVE_EPISODE_BINDING_SCHEMA_VERSION",
    "STUDIO_PRODUCTION_BINDING_SCHEMA_VERSION",
    "CreatorDecisionRequest",
    "ProductionCandidate",
    "ProductionCheckpoint",
    "ProductionExportRequest",
    "ProductionQualityChecklist",
    "ProductionQualityReviewRequest",
    "ProductionRunCreateRequest",
    "EpisodeAssetReadinessRef",
    "EpisodeEntityVersionRef",
    "EpisodeReconfirmationEvidenceRef",
    "RepresentativeEpisodeBindingRequest",
    "SafeArtifactRef",
    "canonical_json_digest",
    "checkpoint_digest",
    "is_sha256",
)
