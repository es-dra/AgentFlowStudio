from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from agentflow.harness.json_io import exclusive_file_lock, write_json
from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_script_core_truth import script_core_truth_projection_for_project
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id


PRODUCTION_PLAN_SCHEMA_VERSION = "afs.dynamic_production_plan.v0.1"
STORY_PLAN_CANDIDATE_SCHEMA_VERSION = "afs.story_plan_candidate.v0.1"
PROVIDER_CAPABILITY_SCHEMA_VERSION = "afs.provider_capability_contract.v0.1"
PRODUCTION_PLAN_COMMAND_SCHEMA_VERSION = "afs.production_plan_command.v0.1"
PLAN_TASK_STATES = {"planned", "ready", "running", "succeeded", "failed", "cancelled", "blocked"}


class SourceEvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_kind: Literal["script_revision", "core_asset", "analysis_candidate"]
    source_id: str = Field(min_length=1, max_length=160)
    quote: str | None = Field(default=None, max_length=600)
    note: str | None = Field(default=None, max_length=240)


class MediaReferenceLineage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=128)
    script_revision_id: str = Field(min_length=1, max_length=160)
    source_digest: str = Field(min_length=64, max_length=64)
    asset_id: str | None = Field(default=None, max_length=160)
    artifact_id: str | None = Field(default=None, max_length=160)
    locked_keyframe_id: str | None = Field(default=None, max_length=160)


class MediaReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref_id: str = Field(min_length=1, max_length=160)
    source_kind: Literal["locked_keyframe", "reference_artifact", "visual_asset", "core_asset_lineage"]
    asset_id: str | None = Field(default=None, max_length=160)
    artifact_id: str | None = Field(default=None, max_length=160)
    lineage: MediaReferenceLineage


class MediaStrategyCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: Literal["t2v", "i2v"]
    strategy_reason: str = Field(min_length=1, max_length=600)
    input_requirements: list[str] = Field(default_factory=list, max_length=20)
    reference_asset_refs: list[MediaReference] = Field(default_factory=list, max_length=20)
    user_constraints: dict[str, Any] = Field(default_factory=dict)


class ProviderCapabilityContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(min_length=1, max_length=80)
    provider_profile_id: str = Field(min_length=1, max_length=120)
    supports_t2v: bool = True
    supports_i2v: bool = True
    supported_clip_durations: list[float] = Field(min_length=1, max_length=40)
    max_duration_seconds: float = Field(gt=0)
    supports_start_frame: bool = False
    supports_end_frame: bool = False
    aspect_ratios: list[str] = Field(default_factory=list, max_length=20)
    fps_values: list[int] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_capability(self) -> "ProviderCapabilityContract":
        if self.schema_version != PROVIDER_CAPABILITY_SCHEMA_VERSION:
            raise ValueError("unsupported provider capability schema")
        durations = [_duration_units(value) for value in self.supported_clip_durations]
        if any(value <= 0 for value in durations):
            raise ValueError("clip durations must be positive")
        if _duration_units(self.max_duration_seconds) < max(durations):
            raise ValueError("max_duration_seconds must cover every supported clip duration")
        return self


class StoryBeatCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    beat_id: str = Field(min_length=1, max_length=120)
    order: int = Field(ge=1)
    summary: str = Field(min_length=1, max_length=800)
    source_evidence_refs: list[SourceEvidenceRef] = Field(min_length=1, max_length=20)
    narrative_purpose: str = Field(min_length=1, max_length=600)


class StoryShotCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shot_id: str = Field(min_length=1, max_length=120)
    beat_id: str = Field(min_length=1, max_length=120)
    order: int = Field(ge=1)
    intent: str = Field(min_length=1, max_length=900)
    duration_seconds: float = Field(gt=0)
    character_refs: list[str] = Field(default_factory=list, max_length=40)
    scene_refs: list[str] = Field(default_factory=list, max_length=20)
    continuity_in: str = Field(default="", max_length=600)
    continuity_out: str = Field(default="", max_length=600)
    source_evidence_refs: list[SourceEvidenceRef] = Field(min_length=1, max_length=20)
    media_strategy: MediaStrategyCandidate


class StoryPlanCandidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=128)
    script_revision_id: str = Field(min_length=1, max_length=160)
    source_digest: str = Field(min_length=64, max_length=64)
    schema_version: str = Field(min_length=1, max_length=80)
    candidate_digest: str = Field(min_length=64, max_length=64)
    beats: list[StoryBeatCandidate] = Field(min_length=1, max_length=160)
    shots: list[StoryShotCandidate] = Field(min_length=1, max_length=400)
    capability_contract: ProviderCapabilityContract
    generated_at: str | None = Field(default=None, max_length=80)
    provider_dispatch_count: int = Field(default=0, ge=0, le=0)
    remote_dispatch_count: int = Field(default=0, ge=0, le=0)


class StoryPlanConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=128)
    script_revision_id: str = Field(min_length=1, max_length=160)
    source_digest: str = Field(min_length=64, max_length=64)
    candidate_digest: str = Field(min_length=64, max_length=64)
    schema_version: str = Field(min_length=1, max_length=80)


class ProductionPlanCommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=128)
    script_revision_id: str = Field(min_length=1, max_length=160)
    source_digest: str = Field(min_length=64, max_length=64)
    plan_id: str = Field(min_length=1, max_length=160)
    plan_digest: str = Field(min_length=64, max_length=64)
    schema_version: str = Field(min_length=1, max_length=80)
    command_type: Literal[
        "edit_shot_duration",
        "edit_shot_intent",
        "set_shot_strategy",
        "split_shot",
        "merge_shot_next",
        "replan_affected",
        "mark_failed",
        "retry_failed",
    ]
    target_shot_id: str | None = Field(default=None, max_length=160)
    target_chunk_id: str | None = Field(default=None, max_length=180)
    patch: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = Field(default=None, max_length=400)
    generated_at: str | None = Field(default=None, max_length=80)
    provider_dispatch_count: int = Field(default=0, ge=0, le=0)
    remote_dispatch_count: int = Field(default=0, ge=0, le=0)


class ProductionPlanUndoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=128)
    receipt_id: str = Field(min_length=1, max_length=160)
    script_revision_id: str = Field(min_length=1, max_length=160)
    source_digest: str = Field(min_length=64, max_length=64)
    plan_digest: str = Field(min_length=64, max_length=64)
    schema_version: str = Field(min_length=1, max_length=80)


def register_runtime_dynamic_production_plan_routes(app: FastAPI, store: RuntimeStore, auth: RuntimeAuthStore) -> None:
    @app.get("/projects/{project_id}/production-plan-truth")
    def get_production_plan_truth(project_id: str, request: Request) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        store.ensure_project_manifest(project_id)
        state = _load_state(store, project_id)
        return {
            "project_id": project_id,
            "projection": public_projection(state),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.post("/projects/{project_id}/story-plan-candidates")
    def submit_story_plan_candidate(
        project_id: str,
        body: StoryPlanCandidateRequest,
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        store.ensure_project_manifest(project_id)
        with exclusive_file_lock(_lock_path(store, project_id)):
            state = _load_state(store, project_id)
            script_truth = _validated_script_truth(store, project_id, body.project_id, body.script_revision_id, body.source_digest, "story_plan_candidate_submit")
            _validate_candidate_contract(body, script_truth, project_id)
            candidate = _candidate_record(body)
            state.setdefault("candidates", {})[candidate["candidate_digest"]] = candidate
            _append_audit(state, {"event_type": "story_plan_candidate_submitted", "candidate_digest": candidate["candidate_digest"]})
            _write_state(store, project_id, state)
        return {
            "project_id": project_id,
            "candidate": public_candidate(candidate),
            "projection": public_projection(state),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.post("/projects/{project_id}/story-plan-candidates/{candidate_digest}/confirm")
    def confirm_story_plan_candidate(
        project_id: str,
        candidate_digest: str,
        body: StoryPlanConfirmRequest,
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        with exclusive_file_lock(_lock_path(store, project_id)):
            state = _load_state(store, project_id)
            _validated_script_truth(store, project_id, body.project_id, body.script_revision_id, body.source_digest, "story_plan_candidate_confirm")
            if body.schema_version != STORY_PLAN_CANDIDATE_SCHEMA_VERSION:
                raise _contract_error("schema_version_mismatch", "Story plan confirm schema is not accepted.", project_id=project_id, stage="story_plan_candidate_confirm", status_code=409)
            if body.candidate_digest != candidate_digest:
                raise _contract_error("candidate_digest_mismatch", "Candidate digest in URL and request body must match.", project_id=project_id, stage="story_plan_candidate_confirm", status_code=409)
            candidate = dict(state.get("candidates", {}).get(candidate_digest) or {})
            if not candidate:
                raise _contract_error("story_plan_candidate_not_found", "Story plan candidate has not been submitted.", project_id=project_id, stage="story_plan_candidate_confirm", status_code=404)
            if candidate.get("script_revision_id") != body.script_revision_id or candidate.get("source_digest") != body.source_digest:
                raise _contract_error("candidate_revision_mismatch", "Candidate does not match the requested script revision.", project_id=project_id, stage="story_plan_candidate_confirm", status_code=409)
            plan, affected, preserved = _plan_from_candidate(project_id, candidate, parent_plan=None)
            state.setdefault("plan_versions", {})[plan["plan_id"]] = plan
            state["current_plan_id"] = plan["plan_id"]
            receipt = _receipt(
                command_type="confirm_story_plan_candidate",
                project_id=project_id,
                script_revision_id=plan["script_revision_id"],
                source_digest=plan["source_digest"],
                before_plan_id="",
                after_plan_id=plan["plan_id"],
                before_plan_digest="",
                after_plan_digest=plan["plan_digest"],
                affected=affected,
                preserved=preserved,
                summary="Dynamic production plan candidate confirmed into canonical truth.",
                undo_available=True,
            )
            state.setdefault("receipts", {})[receipt["receipt_id"]] = receipt
            _append_audit(state, {"event_type": "story_plan_candidate_confirmed", "candidate_digest": candidate_digest, "plan_id": plan["plan_id"]})
            _write_state(store, project_id, state)
        return {
            "project_id": project_id,
            "receipt": public_receipt(receipt),
            "projection": public_projection(state),
            "affected_ids": affected,
            "preserved_ids": preserved,
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.post("/projects/{project_id}/production-plan-commands/preview")
    def preview_production_plan_command(
        project_id: str,
        body: ProductionPlanCommandRequest,
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        state = _load_state(store, project_id)
        plan = _require_plan_contract(state, project_id, body)
        preview = _preview_command(plan, body)
        return {
            "project_id": project_id,
            "command": preview,
            "projection": public_projection(state),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.post("/projects/{project_id}/production-plan-commands/confirm")
    def confirm_production_plan_command(
        project_id: str,
        body: ProductionPlanCommandRequest,
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        with exclusive_file_lock(_lock_path(store, project_id)):
            state = _load_state(store, project_id)
            plan = _require_plan_contract(state, project_id, body)
            preview = _preview_command(plan, body)
            next_plan = preview["_next_plan"]
            state.setdefault("plan_versions", {})[next_plan["plan_id"]] = next_plan
            state["current_plan_id"] = next_plan["plan_id"]
            receipt = _receipt(
                command_type=body.command_type,
                project_id=project_id,
                script_revision_id=next_plan["script_revision_id"],
                source_digest=next_plan["source_digest"],
                before_plan_id=plan["plan_id"],
                after_plan_id=next_plan["plan_id"],
                before_plan_digest=plan["plan_digest"],
                after_plan_digest=next_plan["plan_digest"],
                affected=preview["affected_ids"],
                preserved=preview["preserved_ids"],
                summary=f"{_command_title(body.command_type)} applied to canonical production plan.",
                undo_available=True,
            )
            state.setdefault("receipts", {})[receipt["receipt_id"]] = receipt
            _append_audit(state, {"event_type": "production_plan_command_confirmed", "command_type": body.command_type, "receipt_id": receipt["receipt_id"]})
            _write_state(store, project_id, state)
        return {
            "project_id": project_id,
            "receipt": public_receipt(receipt),
            "projection": public_projection(state),
            "affected_ids": preview["affected_ids"],
            "preserved_ids": preview["preserved_ids"],
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.post("/projects/{project_id}/production-plan-commands/undo")
    def undo_production_plan_command(
        project_id: str,
        body: ProductionPlanUndoRequest,
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        with exclusive_file_lock(_lock_path(store, project_id)):
            state = _load_state(store, project_id)
            if body.schema_version != PRODUCTION_PLAN_COMMAND_SCHEMA_VERSION:
                raise _contract_error("schema_version_mismatch", "Production plan undo schema is not accepted.", project_id=project_id, stage="production_plan_command_undo", status_code=409)
            current = _current_plan(state)
            if not current or current.get("plan_digest") != body.plan_digest:
                raise _contract_error("plan_digest_mismatch", "Undo must bind to the current plan digest.", project_id=project_id, stage="production_plan_command_undo", status_code=409)
            receipt = dict(state.get("receipts", {}).get(body.receipt_id) or {})
            if not receipt or receipt.get("undone") or not receipt.get("undo_available"):
                raise _contract_error("production_plan_receipt_not_undoable", "Receipt is missing or already undone.", project_id=project_id, stage="production_plan_command_undo", status_code=409)
            before_plan_id = str(receipt.get("before_plan_id") or "")
            if before_plan_id and before_plan_id not in state.get("plan_versions", {}):
                raise _contract_error("undo_plan_version_missing", "The prior immutable plan version is unavailable.", project_id=project_id, stage="production_plan_command_undo", status_code=409)
            state["current_plan_id"] = before_plan_id
            receipt["undo_available"] = False
            receipt["undone"] = True
            undo_receipt = _receipt(
                command_type=f"{receipt.get('command_type', '')}.undo",
                project_id=project_id,
                script_revision_id=body.script_revision_id,
                source_digest=body.source_digest,
                before_plan_id=str(receipt.get("after_plan_id") or ""),
                after_plan_id=before_plan_id,
                before_plan_digest=body.plan_digest,
                after_plan_digest=str(receipt.get("before_plan_digest") or ""),
                affected=list(receipt.get("affected_ids") or []),
                preserved=list(receipt.get("preserved_ids") or []),
                summary="Production plan command was undone by selecting the prior immutable plan version.",
                undo_available=False,
            )
            undo_receipt["undone"] = True
            state.setdefault("receipts", {})[body.receipt_id] = receipt
            state.setdefault("receipts", {})[undo_receipt["receipt_id"]] = undo_receipt
            _append_audit(state, {"event_type": "production_plan_command_undone", "receipt_id": body.receipt_id, "undo_receipt_id": undo_receipt["receipt_id"]})
            _write_state(store, project_id, state)
        return {
            "project_id": project_id,
            "receipt": public_receipt(undo_receipt),
            "projection": public_projection(state),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }


def public_projection(state: dict[str, Any]) -> dict[str, Any]:
    plan = _current_plan(state)
    if not plan:
        return {
            "artifact_type": "afs_dynamic_production_plan_projection",
            "schema_version": PRODUCTION_PLAN_SCHEMA_VERSION,
            "project_id": state["project_id"],
            "planning_state": "planning_required",
            "current_plan": None,
            "beats": [],
            "shots": [],
            "chunks": [],
            "concat_plan": None,
            "plan_history": [],
            "storyboard_mode": "read_only_consumer",
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }
    beats = sorted(plan.get("beats", {}).values(), key=lambda item: int(item.get("order") or 0))
    shots = sorted(plan.get("shots", {}).values(), key=lambda item: int(item.get("order") or 0))
    chunks = sorted(plan.get("chunks", {}).values(), key=lambda item: (int(item.get("shot_order") or 0), int(item.get("sequence") or 0)))
    return {
        "artifact_type": "afs_dynamic_production_plan_projection",
        "schema_version": PRODUCTION_PLAN_SCHEMA_VERSION,
        "project_id": state["project_id"],
        "planning_state": plan.get("planning_state") or "planned",
        "current_plan": {
            "plan_id": plan["plan_id"],
            "plan_digest": plan["plan_digest"],
            "parent_plan_id": plan.get("parent_plan_id", ""),
            "plan_version": plan.get("plan_version", 1),
            "script_revision_id": plan["script_revision_id"],
            "source_digest": plan["source_digest"],
            "candidate_digest": plan.get("candidate_digest", ""),
            "created_at": plan.get("created_at", ""),
            "updated_at": plan.get("updated_at", ""),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        },
        "beats": [public_beat(item) for item in beats],
        "shots": [public_shot(item) for item in shots],
        "chunks": [public_chunk(item) for item in chunks],
        "concat_plan": copy.deepcopy(plan.get("concat_plan") or {}),
        "plan_history": [
            {
                "plan_id": item.get("plan_id", ""),
                "plan_digest": item.get("plan_digest", ""),
                "parent_plan_id": item.get("parent_plan_id", ""),
                "plan_version": item.get("plan_version", 1),
                "planning_state": item.get("planning_state", ""),
            }
            for item in sorted((state.get("plan_versions") or {}).values(), key=lambda value: int(value.get("plan_version") or 0))
        ],
        "storyboard_mode": "read_only_consumer",
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def production_plan_projection_for_project(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    store.ensure_project_manifest(project_id)
    return public_projection(_load_state(store, project_id))


def public_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_digest": str(candidate.get("candidate_digest") or ""),
        "schema_version": str(candidate.get("schema_version") or ""),
        "project_id": str(candidate.get("project_id") or ""),
        "script_revision_id": str(candidate.get("script_revision_id") or ""),
        "source_digest": str(candidate.get("source_digest") or ""),
        "beat_count": len(candidate.get("beats") or []),
        "shot_count": len(candidate.get("shots") or []),
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def public_beat(beat: dict[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(beat.get(key)) for key in ("beat_id", "order", "summary", "source_evidence_refs", "narrative_purpose")}


def public_shot(shot: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(shot.get(key))
        for key in (
            "shot_id",
            "beat_id",
            "order",
            "intent",
            "duration_seconds",
            "character_refs",
            "scene_refs",
            "continuity_in",
            "continuity_out",
            "source_evidence_refs",
            "media_strategy",
            "media_input_state",
            "status",
            "chunk_ids",
            "attempt_history",
        )
    }


def public_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(chunk.get(key))
        for key in (
            "chunk_id",
            "shot_id",
            "shot_order",
            "sequence",
            "target_duration_seconds",
            "continuity_anchor_in",
            "continuity_anchor_out",
            "depends_on",
            "state",
            "remainder_strategy",
            "attempt_history",
            "selected_artifact_version_ref",
        )
    }


def public_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "receipt_id": str(receipt.get("receipt_id") or ""),
        "command_id": str(receipt.get("command_id") or ""),
        "command_type": str(receipt.get("command_type") or ""),
        "status": str(receipt.get("status") or ""),
        "summary": str(receipt.get("summary") or ""),
        "executed_at": str(receipt.get("executed_at") or ""),
        "script_revision_id": str(receipt.get("script_revision_id") or ""),
        "source_digest": str(receipt.get("source_digest") or ""),
        "before_plan_id": str(receipt.get("before_plan_id") or ""),
        "after_plan_id": str(receipt.get("after_plan_id") or ""),
        "before_plan_digest": str(receipt.get("before_plan_digest") or ""),
        "after_plan_digest": str(receipt.get("after_plan_digest") or ""),
        "affected_ids": list(receipt.get("affected_ids") or []),
        "preserved_ids": list(receipt.get("preserved_ids") or []),
        "undo_available": bool(receipt.get("undo_available")),
        "storyboard_write": False,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def story_plan_candidate_digest(payload: dict[str, Any]) -> str:
    seed = copy.deepcopy(payload)
    seed["candidate_digest"] = str(seed.get("candidate_digest") or "0" * 64)
    try:
        body = StoryPlanCandidateRequest(**seed).model_dump(mode="json")
    except Exception:
        body = seed
        body.setdefault("generated_at", None)
        body.setdefault("provider_dispatch_count", 0)
        body.setdefault("remote_dispatch_count", 0)
    body.pop("candidate_digest", None)
    return _sha256_json(body)


def _validate_candidate_contract(body: StoryPlanCandidateRequest, script_truth: dict[str, Any], project_id: str) -> None:
    if body.project_id != project_id:
        raise _contract_error("project_identity_mismatch", "Candidate project does not match URL project.", project_id=project_id, stage="story_plan_candidate_submit", status_code=409)
    if body.schema_version != STORY_PLAN_CANDIDATE_SCHEMA_VERSION:
        raise _contract_error("schema_version_mismatch", "Story plan candidate schema is not accepted.", project_id=project_id, stage="story_plan_candidate_submit", status_code=409)
    expected_digest = story_plan_candidate_digest(body.model_dump(mode="json"))
    if body.candidate_digest != expected_digest:
        raise _contract_error("candidate_digest_mismatch", "Candidate digest does not match the submitted structured plan.", project_id=project_id, stage="story_plan_candidate_submit", status_code=409)
    beat_ids = [item.beat_id for item in body.beats]
    shot_ids = [item.shot_id for item in body.shots]
    if len(set(beat_ids)) != len(beat_ids) or len(set(shot_ids)) != len(shot_ids):
        raise _contract_error("duplicate_plan_ids", "Beat and shot ids must be unique.", project_id=project_id, stage="story_plan_candidate_submit")
    asset_index = _asset_index(script_truth)
    for beat in body.beats:
        _validate_evidence_refs(beat.source_evidence_refs, body.script_revision_id, asset_index, project_id, "story_plan_candidate_submit")
    for shot in body.shots:
        if shot.beat_id not in beat_ids:
            raise _contract_error("beat_reference_mismatch", "Shot beat_id must reference a submitted beat.", project_id=project_id, stage="story_plan_candidate_submit", status_code=409)
        for asset_id in shot.character_refs:
            if asset_index.get(asset_id, {}).get("asset_type") != "character":
                raise _contract_error("character_reference_mismatch", "Shot character_refs must reference current Character truth.", project_id=project_id, stage="story_plan_candidate_submit", status_code=409)
        for asset_id in shot.scene_refs:
            if asset_index.get(asset_id, {}).get("asset_type") != "main_scene":
                raise _contract_error("scene_reference_mismatch", "Shot scene_refs must reference current Main Scene truth.", project_id=project_id, stage="story_plan_candidate_submit", status_code=409)
        _validate_evidence_refs(shot.source_evidence_refs, body.script_revision_id, asset_index, project_id, "story_plan_candidate_submit")
        _validate_media_strategy(shot.media_strategy, body, project_id)


def _validate_media_strategy(strategy: MediaStrategyCandidate, body: StoryPlanCandidateRequest, project_id: str) -> None:
    capability = body.capability_contract
    if strategy.strategy == "t2v" and not capability.supports_t2v:
        raise _contract_error("t2v_not_supported", "Capability contract does not support T2V.", project_id=project_id, stage="story_plan_candidate_submit", status_code=409)
    if strategy.strategy == "i2v" and not capability.supports_i2v:
        raise _contract_error("i2v_not_supported", "Capability contract does not support I2V.", project_id=project_id, stage="story_plan_candidate_submit", status_code=409)
    for ref in strategy.reference_asset_refs:
        lineage = ref.lineage
        if lineage.project_id != body.project_id or lineage.script_revision_id != body.script_revision_id or lineage.source_digest != body.source_digest:
            raise _contract_error("media_reference_lineage_mismatch", "Media reference lineage must bind to the current project revision.", project_id=project_id, stage="story_plan_candidate_submit", status_code=409)
        if ref.source_kind in {"locked_keyframe", "reference_artifact"} and not (ref.artifact_id or lineage.artifact_id or lineage.locked_keyframe_id):
            raise _contract_error("media_reference_artifact_required", "I2V reference lineage requires an artifact or locked keyframe id.", project_id=project_id, stage="story_plan_candidate_submit")
        if ref.source_kind == "visual_asset" and not (ref.asset_id or lineage.asset_id):
            raise _contract_error("media_reference_asset_required", "Visual asset reference lineage requires an asset id.", project_id=project_id, stage="story_plan_candidate_submit")


def _validate_evidence_refs(refs: list[SourceEvidenceRef], script_revision_id: str, asset_index: dict[str, dict[str, Any]], project_id: str, stage: str) -> None:
    for ref in refs:
        if ref.source_kind == "script_revision" and ref.source_id != script_revision_id:
            raise _contract_error("source_evidence_revision_mismatch", "Source evidence revision id does not match the bound script revision.", project_id=project_id, stage=stage, status_code=409)
        if ref.source_kind == "core_asset" and ref.source_id not in asset_index:
            raise _contract_error("source_evidence_asset_mismatch", "Source evidence asset id is not in current core asset truth.", project_id=project_id, stage=stage, status_code=409)


def _candidate_record(body: StoryPlanCandidateRequest) -> dict[str, Any]:
    payload = body.model_dump(mode="json")
    payload["artifact_type"] = "afs_story_plan_candidate"
    payload["created_at"] = _safe_time(body.generated_at)
    payload["provider_dispatch_count"] = 0
    payload["remote_dispatch_count"] = 0
    reject_unsafe_payload(payload)
    return payload


def _plan_from_candidate(project_id: str, candidate: dict[str, Any], parent_plan: dict[str, Any] | None) -> tuple[dict[str, Any], list[str], list[str]]:
    now = _server_now()
    parent = parent_plan or {}
    beats = {
        beat["beat_id"]: {
            **copy.deepcopy(beat),
            "status": "planned",
        }
        for beat in candidate.get("beats", [])
    }
    shots = {
        shot["shot_id"]: _shot_from_candidate(project_id, candidate, shot)
        for shot in sorted(candidate.get("shots", []), key=lambda item: int(item.get("order") or 0))
    }
    chunks: dict[str, dict[str, Any]] = {}
    for shot in shots.values():
        shot_chunks = _chunks_for_shot(shot, candidate["capability_contract"])
        shot["chunk_ids"] = [chunk["chunk_id"] for chunk in shot_chunks]
        chunks.update({chunk["chunk_id"]: chunk for chunk in shot_chunks})
    plan = {
        "artifact_type": "afs_dynamic_production_plan",
        "schema_version": PRODUCTION_PLAN_SCHEMA_VERSION,
        "project_id": project_id,
        "script_revision_id": candidate["script_revision_id"],
        "source_digest": candidate["source_digest"],
        "candidate_digest": candidate["candidate_digest"],
        "parent_plan_id": parent.get("plan_id", ""),
        "plan_version": int(parent.get("plan_version") or 0) + 1,
        "beats": beats,
        "shots": _renumber_shots(shots),
        "chunks": chunks,
        "capability_contract": copy.deepcopy(candidate["capability_contract"]),
        "created_at": parent.get("created_at") or now,
        "updated_at": now,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    _rebuild_chunks(plan, list(plan["shots"]))
    _refresh_plan_identity(plan)
    affected = [*plan["beats"], *plan["shots"], *plan["chunks"], "concat_plan"]
    preserved: list[str] = []
    return plan, affected, preserved


def _shot_from_candidate(project_id: str, candidate: dict[str, Any], shot: dict[str, Any]) -> dict[str, Any]:
    media = copy.deepcopy(shot["media_strategy"])
    media_input_state = _media_input_state(media)
    status = "blocked" if media_input_state == "pending_input" else "planned"
    return {
        "shot_id": shot["shot_id"],
        "beat_id": shot["beat_id"],
        "order": int(shot["order"]),
        "intent": _clean_text(shot["intent"], 900),
        "duration_seconds": _duration_float(shot["duration_seconds"]),
        "character_refs": list(shot.get("character_refs") or []),
        "scene_refs": list(shot.get("scene_refs") or []),
        "continuity_in": _clean_text(shot.get("continuity_in") or "", 600),
        "continuity_out": _clean_text(shot.get("continuity_out") or "", 600),
        "source_evidence_refs": copy.deepcopy(shot.get("source_evidence_refs") or []),
        "media_strategy": media,
        "media_input_state": media_input_state,
        "status": status,
        "attempt_history": [],
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
        "lineage": {
            "project_id": project_id,
            "script_revision_id": candidate["script_revision_id"],
            "source_digest": candidate["source_digest"],
            "candidate_digest": candidate["candidate_digest"],
        },
    }


def _chunks_for_shot(shot: dict[str, Any], capability: dict[str, Any]) -> list[dict[str, Any]]:
    duration = _duration_units(shot["duration_seconds"])
    allowed = sorted({_duration_units(value) for value in capability.get("supported_clip_durations", []) if _duration_units(value) > 0}, reverse=True)
    max_duration = _duration_units(capability.get("max_duration_seconds") or 0)
    if not allowed or max_duration <= 0:
        return [_chunk(shot, 1, duration, "", "blocked", "pending_capability")]
    usable = [value for value in allowed if value <= max_duration]
    chunks: list[dict[str, Any]] = []
    remaining = duration
    sequence = 1
    depends_on = ""
    while remaining > 0 and usable:
        pick = next((value for value in usable if value <= remaining), 0)
        if pick <= 0:
            break
        state = _chunk_ready_state(shot)
        chunk = _chunk(shot, sequence, pick, depends_on, state, "")
        chunks.append(chunk)
        depends_on = chunk["chunk_id"]
        remaining -= pick
        sequence += 1
    if remaining > 0:
        chunks.append(_chunk(shot, sequence, remaining, depends_on, "blocked", "pending_capability"))
    return _link_chunk_anchors(chunks, shot)


def _chunk(shot: dict[str, Any], sequence: int, duration_units: int, depends_on: str, state: str, remainder_strategy: str) -> dict[str, Any]:
    chunk_id = f"chunk_{shot['shot_id']}_{sequence}"
    return {
        "chunk_id": chunk_id,
        "shot_id": shot["shot_id"],
        "shot_order": int(shot.get("order") or 0),
        "sequence": sequence,
        "target_duration_seconds": _units_float(duration_units),
        "continuity_anchor_in": "",
        "continuity_anchor_out": "",
        "depends_on": depends_on,
        "state": state,
        "remainder_strategy": remainder_strategy,
        "attempt_history": [],
        "selected_artifact_version_ref": "",
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _link_chunk_anchors(chunks: list[dict[str, Any]], shot: dict[str, Any]) -> list[dict[str, Any]]:
    previous_out = _clean_text(shot.get("continuity_in") or "", 600)
    for chunk in chunks:
        chunk["continuity_anchor_in"] = previous_out
        chunk["continuity_anchor_out"] = f"placeholder_last_frame:{shot['shot_id']}:{chunk['sequence']}"
        previous_out = chunk["continuity_anchor_out"]
    if chunks and shot.get("continuity_out"):
        chunks[-1]["continuity_anchor_out"] = _clean_text(shot.get("continuity_out") or "", 600)
    return chunks


def _chunk_ready_state(shot: dict[str, Any]) -> str:
    return "blocked" if shot.get("media_input_state") == "pending_input" else "ready"


def _media_input_state(media: dict[str, Any]) -> str:
    if media.get("strategy") != "i2v":
        return "ready"
    return "ready" if media.get("reference_asset_refs") else "pending_input"


def _preview_command(plan: dict[str, Any], body: ProductionPlanCommandRequest) -> dict[str, Any]:
    next_plan, affected, preserved = _apply_command_to_copy(plan, body)
    return {
        "schema_version": PRODUCTION_PLAN_COMMAND_SCHEMA_VERSION,
        "command_id": f"cmd_{_sha256_json(body.model_dump(mode='json'))[:16]}",
        "command_type": body.command_type,
        "status": "preview",
        "title": _command_title(body.command_type),
        "summary": f"{_command_title(body.command_type)} will update {len(affected)} plan item(s).",
        "project_id": body.project_id,
        "script_revision_id": body.script_revision_id,
        "source_digest": body.source_digest,
        "before_plan_id": plan["plan_id"],
        "before_plan_digest": plan["plan_digest"],
        "after_plan_id": next_plan["plan_id"],
        "after_plan_digest": next_plan["plan_digest"],
        "affected_ids": affected,
        "preserved_ids": preserved,
        "requires_confirmation": True,
        "storyboard_write": False,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
        "_next_plan": next_plan,
    }


def _apply_command_to_copy(plan: dict[str, Any], body: ProductionPlanCommandRequest) -> tuple[dict[str, Any], list[str], list[str]]:
    next_plan = copy.deepcopy(plan)
    affected: set[str] = set()
    target_shot_id = _clean_token(body.target_shot_id or "")
    target_chunk_id = _clean_token(body.target_chunk_id or "")
    if body.command_type in {"edit_shot_duration", "edit_shot_intent", "set_shot_strategy", "split_shot", "merge_shot_next", "mark_failed"} and not (target_shot_id or target_chunk_id):
        raise _contract_error("production_plan_target_required", "Command requires a selected shot or chunk target.", project_id=body.project_id, stage="production_plan_command_preview")

    if body.command_type == "edit_shot_duration":
        shot = _require_shot(next_plan, target_shot_id, body)
        shot["duration_seconds"] = _patch_duration(body.patch.get("duration_seconds"), body, "shot_duration_invalid")
        affected.update(_rebuild_chunks(next_plan, [shot["shot_id"]]))
        affected.add(shot["shot_id"])
    elif body.command_type == "edit_shot_intent":
        shot = _require_shot(next_plan, target_shot_id, body)
        intent = _clean_text(body.patch.get("intent"), 900)
        if not intent:
            raise _contract_error("shot_intent_required", "Shot intent edit requires an intent patch.", project_id=body.project_id, stage="production_plan_command_preview")
        shot["intent"] = intent
        affected.add(shot["shot_id"])
    elif body.command_type == "set_shot_strategy":
        shot = _require_shot(next_plan, target_shot_id, body)
        strategy = _strategy_patch(shot, body)
        shot["media_strategy"] = strategy
        shot["media_input_state"] = _media_input_state(strategy)
        shot["status"] = "blocked" if shot["media_input_state"] == "pending_input" else "planned"
        affected.update(_rebuild_chunks(next_plan, [shot["shot_id"]]))
        affected.add(shot["shot_id"])
    elif body.command_type == "split_shot":
        affected.update(_split_shot(next_plan, target_shot_id, body))
    elif body.command_type == "merge_shot_next":
        affected.update(_merge_shot_next(next_plan, target_shot_id, body))
    elif body.command_type == "replan_affected":
        shot_ids = [_clean_token(value) for value in body.patch.get("affected_shot_ids", []) if _clean_token(value)]
        if target_shot_id:
            shot_ids.append(target_shot_id)
        if not shot_ids:
            shot_ids = [shot_id for shot_id, shot in next_plan.get("shots", {}).items() if shot.get("status") in {"blocked", "failed"}]
        for shot_id in _unique(shot_ids):
            _require_shot(next_plan, shot_id, body)
        affected.update(_rebuild_chunks(next_plan, _unique(shot_ids)))
        affected.update(_unique(shot_ids))
    elif body.command_type == "mark_failed":
        affected.update(_mark_failed(next_plan, target_shot_id, target_chunk_id, body))
    elif body.command_type == "retry_failed":
        affected.update(_retry_failed(next_plan))
    else:
        raise _contract_error("unsupported_production_plan_command", "Unsupported production plan command.", project_id=body.project_id, stage="production_plan_command_preview")

    _renumber_shots_in_place(next_plan)
    next_plan["parent_plan_id"] = plan["plan_id"]
    next_plan["plan_version"] = int(plan.get("plan_version") or 1) + 1
    next_plan["updated_at"] = _server_now()
    _refresh_plan_identity(next_plan)
    preserved = _preserved_ids(plan, next_plan, affected)
    return next_plan, sorted(affected), preserved


def _strategy_patch(shot: dict[str, Any], body: ProductionPlanCommandRequest) -> dict[str, Any]:
    current = copy.deepcopy(shot.get("media_strategy") or {})
    strategy = _clean_token(body.patch.get("strategy") or current.get("strategy"))
    if strategy not in {"t2v", "i2v"}:
        raise _contract_error("shot_strategy_invalid", "Shot strategy must be t2v or i2v.", project_id=body.project_id, stage="production_plan_command_preview")
    reason = _clean_text(body.patch.get("strategy_reason") or body.patch.get("reason") or current.get("strategy_reason"), 600)
    if not reason:
        raise _contract_error("strategy_reason_required", "Strategy edits require a verifiable strategy_reason.", project_id=body.project_id, stage="production_plan_command_preview")
    current["strategy"] = strategy
    current["strategy_reason"] = reason
    if "input_requirements" in body.patch:
        current["input_requirements"] = [_clean_text(value, 160) for value in body.patch.get("input_requirements", []) if _clean_text(value, 160)]
    if "reference_asset_refs" in body.patch:
        current["reference_asset_refs"] = copy.deepcopy(body.patch.get("reference_asset_refs") or [])
    current["user_constraints"] = copy.deepcopy(body.patch.get("user_constraints") or current.get("user_constraints") or {})
    return current


def _split_shot(plan: dict[str, Any], shot_id: str, body: ProductionPlanCommandRequest) -> set[str]:
    shot = _require_shot(plan, shot_id, body)
    durations = [_patch_duration(value, body, "split_duration_invalid") for value in body.patch.get("durations", [])]
    if len(durations) != 2 or abs(sum(durations) - float(shot["duration_seconds"])) > 0.01:
        raise _contract_error("split_duration_mismatch", "Split shot requires two positive durations summing to the original shot duration.", project_id=body.project_id, stage="production_plan_command_preview")
    original_order = int(shot["order"])
    shots = plan["shots"]
    del shots[shot_id]
    first = copy.deepcopy(shot)
    second = copy.deepcopy(shot)
    first["shot_id"] = f"{shot_id}a"
    second["shot_id"] = f"{shot_id}b"
    first["duration_seconds"] = durations[0]
    second["duration_seconds"] = durations[1]
    first["intent"] = _clean_text(body.patch.get("first_intent") or f"{shot['intent']} / part 1", 900)
    second["intent"] = _clean_text(body.patch.get("second_intent") or f"{shot['intent']} / part 2", 900)
    first["order"] = original_order
    second["order"] = original_order + 1
    for item in shots.values():
        if int(item.get("order") or 0) > original_order:
            item["order"] = int(item["order"]) + 1
    shots[first["shot_id"]] = first
    shots[second["shot_id"]] = second
    affected = {shot_id, first["shot_id"], second["shot_id"]}
    affected.update(_rebuild_chunks(plan, [first["shot_id"], second["shot_id"]]))
    return affected


def _merge_shot_next(plan: dict[str, Any], shot_id: str, body: ProductionPlanCommandRequest) -> set[str]:
    shot = _require_shot(plan, shot_id, body)
    ordered = sorted(plan["shots"].values(), key=lambda item: int(item.get("order") or 0))
    index = next((idx for idx, item in enumerate(ordered) if item["shot_id"] == shot_id), -1)
    if index < 0 or index + 1 >= len(ordered):
        raise _contract_error("merge_next_missing", "Selected shot has no following shot to merge.", project_id=body.project_id, stage="production_plan_command_preview", status_code=409)
    next_shot = ordered[index + 1]
    shot["intent"] = _clean_text(body.patch.get("intent") or f"{shot['intent']} / {next_shot['intent']}", 900)
    shot["duration_seconds"] = _duration_float(float(shot["duration_seconds"]) + float(next_shot["duration_seconds"]))
    shot["continuity_out"] = next_shot.get("continuity_out", "")
    shot["character_refs"] = _unique([*shot.get("character_refs", []), *next_shot.get("character_refs", [])])
    shot["scene_refs"] = _unique([*shot.get("scene_refs", []), *next_shot.get("scene_refs", [])])
    removed_id = next_shot["shot_id"]
    del plan["shots"][removed_id]
    affected = {shot_id, removed_id}
    affected.update(_rebuild_chunks(plan, [shot_id]))
    return affected


def _mark_failed(plan: dict[str, Any], shot_id: str, chunk_id: str, body: ProductionPlanCommandRequest) -> set[str]:
    affected: set[str] = set()
    if chunk_id:
        chunk = _require_chunk(plan, chunk_id, body)
        if chunk.get("state") != "succeeded":
            chunk["state"] = "failed"
            chunk.setdefault("attempt_history", []).append({"state": "failed", "recorded_at": _server_now(), "reason": _clean_text(body.reason or body.patch.get("reason") or "agent_marked_failed", 240)})
            affected.add(chunk_id)
            shot_id = chunk["shot_id"]
    if shot_id:
        shot = _require_shot(plan, shot_id, body)
        shot["status"] = "failed"
        affected.add(shot_id)
        if not chunk_id:
            for chunk in plan.get("chunks", {}).values():
                if chunk.get("shot_id") == shot_id and chunk.get("state") != "succeeded":
                    chunk["state"] = "failed"
                    chunk.setdefault("attempt_history", []).append({"state": "failed", "recorded_at": _server_now(), "reason": _clean_text(body.reason or "agent_marked_failed", 240)})
                    affected.add(chunk["chunk_id"])
    return affected


def _retry_failed(plan: dict[str, Any]) -> set[str]:
    affected: set[str] = set()
    for chunk in plan.get("chunks", {}).values():
        if chunk.get("state") != "failed":
            continue
        chunk["state"] = "ready"
        chunk.setdefault("attempt_history", []).append({"state": "planned", "recorded_at": _server_now(), "retry_scope": "failed_chunk_only"})
        affected.add(chunk["chunk_id"])
        shot = plan.get("shots", {}).get(chunk["shot_id"])
        if shot and shot.get("status") == "failed":
            shot["status"] = "planned"
            affected.add(shot["shot_id"])
    return affected


def _patch_duration(value: Any, body: ProductionPlanCommandRequest, error: str) -> float:
    try:
        return _duration_float(value)
    except (ValueError, ArithmeticError):
        raise _contract_error(
            error,
            "Production plan duration edits require a positive numeric duration in seconds.",
            project_id=body.project_id,
            stage="production_plan_command_preview",
        ) from None


def _rebuild_chunks(plan: dict[str, Any], shot_ids: list[str]) -> list[str]:
    capability = plan.get("capability_contract") or {}
    affected: list[str] = []
    for shot_id in shot_ids:
        shot = plan["shots"][shot_id]
        old_chunk_ids = [chunk_id for chunk_id, chunk in plan.get("chunks", {}).items() if chunk.get("shot_id") == shot_id]
        for chunk_id in old_chunk_ids:
            affected.append(chunk_id)
            del plan["chunks"][chunk_id]
        chunks = _chunks_for_shot(shot, capability)
        shot["chunk_ids"] = [chunk["chunk_id"] for chunk in chunks]
        for chunk in chunks:
            plan["chunks"][chunk["chunk_id"]] = chunk
            affected.append(chunk["chunk_id"])
    plan["planning_state"] = _planning_state(plan)
    plan["concat_plan"] = _concat_plan(plan)
    return _unique(affected)


def _refresh_plan_identity(plan: dict[str, Any]) -> None:
    plan["planning_state"] = _planning_state(plan)
    plan["concat_plan"] = _concat_plan(plan)
    digest_body = {
        "schema_version": plan["schema_version"],
        "project_id": plan["project_id"],
        "script_revision_id": plan["script_revision_id"],
        "source_digest": plan["source_digest"],
        "candidate_digest": plan.get("candidate_digest", ""),
        "parent_plan_id": plan.get("parent_plan_id", ""),
        "plan_version": plan.get("plan_version", 1),
        "beats": plan.get("beats", {}),
        "shots": plan.get("shots", {}),
        "chunks": plan.get("chunks", {}),
        "concat_plan": plan.get("concat_plan", {}),
        "capability_contract": plan.get("capability_contract", {}),
    }
    plan["plan_digest"] = _sha256_json(digest_body)
    plan["plan_id"] = f"plan_{plan['plan_digest'][:16]}"
    reject_unsafe_payload(plan)


def _planning_state(plan: dict[str, Any]) -> str:
    chunks = list((plan.get("chunks") or {}).values())
    shots = list((plan.get("shots") or {}).values())
    if any(shot.get("media_input_state") == "pending_input" for shot in shots):
        return "pending_input"
    if any(chunk.get("remainder_strategy") == "pending_capability" for chunk in chunks):
        return "pending_capability"
    if any(chunk.get("state") == "failed" for chunk in chunks) or any(shot.get("status") == "failed" for shot in shots):
        return "blocked"
    return "planned"


def _concat_plan(plan: dict[str, Any]) -> dict[str, Any]:
    shots = sorted(plan.get("shots", {}).values(), key=lambda item: int(item.get("order") or 0))
    return {
        "concat_plan_id": f"concat_{plan.get('script_revision_id', '')}",
        "state": "planned_not_executed",
        "shot_order": [shot["shot_id"] for shot in shots],
        "selected_artifact_version_refs": [
            {
                "shot_id": shot["shot_id"],
                "artifact_version_ref": f"artifact_placeholder:{shot['shot_id']}",
                "state": "planned_placeholder",
            }
            for shot in shots
        ],
        "executes_media": False,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _validated_script_truth(store: RuntimeStore, project_id: str, body_project_id: str, script_revision_id: str, source_digest: str, stage: str) -> dict[str, Any]:
    if body_project_id != project_id:
        raise _contract_error("project_identity_mismatch", "Request project id does not match URL project.", project_id=project_id, stage=stage, status_code=409)
    projection = script_core_truth_projection_for_project(store, project_id)
    current = projection.get("current_revision") or {}
    if projection.get("current_revision_id") != script_revision_id or current.get("source_digest") != source_digest:
        raise _contract_error("script_revision_contract_mismatch", "Story plan must bind to the current ScriptRevision and source digest.", project_id=project_id, stage=stage, status_code=409)
    if not current:
        raise _contract_error("planning_required", "No trusted ScriptRevision is available for planning.", project_id=project_id, stage=stage, status_code=409)
    return projection


def _require_plan_contract(state: dict[str, Any], project_id: str, body: ProductionPlanCommandRequest) -> dict[str, Any]:
    if body.project_id != project_id:
        raise _contract_error("project_identity_mismatch", "Command project does not match URL project.", project_id=project_id, stage="production_plan_command_preview", status_code=409)
    if body.schema_version != PRODUCTION_PLAN_COMMAND_SCHEMA_VERSION:
        raise _contract_error("schema_version_mismatch", "Production plan command schema is not accepted.", project_id=project_id, stage="production_plan_command_preview", status_code=409)
    plan = _current_plan(state)
    if not plan or plan.get("plan_id") != body.plan_id:
        raise _contract_error("production_plan_not_current", "Command must bind to the selected current production plan.", project_id=project_id, stage="production_plan_command_preview", status_code=409)
    if plan.get("plan_digest") != body.plan_digest:
        raise _contract_error("plan_digest_mismatch", "Command plan digest does not match current production plan.", project_id=project_id, stage="production_plan_command_preview", status_code=409)
    if plan.get("script_revision_id") != body.script_revision_id or plan.get("source_digest") != body.source_digest:
        raise _contract_error("script_revision_contract_mismatch", "Command revision contract does not match the current production plan.", project_id=project_id, stage="production_plan_command_preview", status_code=409)
    return plan


def _require_shot(plan: dict[str, Any], shot_id: str, body: ProductionPlanCommandRequest) -> dict[str, Any]:
    shot = plan.get("shots", {}).get(shot_id)
    if not shot:
        raise _contract_error("shot_not_found", "Target shot does not exist in the current production plan.", project_id=body.project_id, stage="production_plan_command_preview", status_code=404)
    return shot


def _require_chunk(plan: dict[str, Any], chunk_id: str, body: ProductionPlanCommandRequest) -> dict[str, Any]:
    chunk = plan.get("chunks", {}).get(chunk_id)
    if not chunk:
        raise _contract_error("chunk_not_found", "Target chunk does not exist in the current production plan.", project_id=body.project_id, stage="production_plan_command_preview", status_code=404)
    return chunk


def _asset_index(script_truth: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["asset_id"]: item
        for item in script_truth.get("assets", [])
        if item.get("status") != "retired" and item.get("asset_type") in {"character", "main_scene", "prop"}
    }


def _load_state(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    path = _state_path(store, project_id)
    if path.is_file():
        state = read_json(path)
        reject_unsafe_payload(state)
        if state.get("project_id") != project_id:
            raise ValueError("production plan project id mismatch")
        return _normalized_state(state, project_id)
    return _empty_state(project_id)


def _write_state(store: RuntimeStore, project_id: str, state: dict[str, Any]) -> None:
    payload = _normalized_state(state, project_id)
    payload["updated_at"] = _server_now()
    reject_unsafe_payload(payload)
    write_json(_state_path(store, project_id), payload)


def _empty_state(project_id: str) -> dict[str, Any]:
    now = _server_now()
    return {
        "artifact_type": "afs_dynamic_production_plan_truth",
        "schema_version": PRODUCTION_PLAN_SCHEMA_VERSION,
        "project_id": project_id,
        "current_plan_id": "",
        "candidates": {},
        "plan_versions": {},
        "receipts": {},
        "audit_history": [],
        "created_at": now,
        "updated_at": now,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _normalized_state(state: dict[str, Any], project_id: str) -> dict[str, Any]:
    payload = {**_empty_state(project_id), **state}
    payload["project_id"] = project_id
    for key in ("candidates", "plan_versions", "receipts"):
        if not isinstance(payload.get(key), dict):
            payload[key] = {}
    if not isinstance(payload.get("audit_history"), list):
        payload["audit_history"] = []
    payload["provider_dispatch_count"] = 0
    payload["remote_dispatch_count"] = 0
    return payload


def _current_plan(state: dict[str, Any]) -> dict[str, Any]:
    plan_id = str(state.get("current_plan_id") or "")
    return copy.deepcopy((state.get("plan_versions") or {}).get(plan_id) or {})


def _receipt(
    *,
    command_type: str,
    project_id: str,
    script_revision_id: str,
    source_digest: str,
    before_plan_id: str,
    after_plan_id: str,
    before_plan_digest: str,
    after_plan_digest: str,
    affected: list[str],
    preserved: list[str],
    summary: str,
    undo_available: bool,
) -> dict[str, Any]:
    return {
        "receipt_id": f"receipt_{uuid4().hex[:16]}",
        "command_id": f"cmd_{uuid4().hex[:12]}",
        "command_type": command_type,
        "status": "executed",
        "summary": summary,
        "executed_at": _server_now(),
        "project_id": project_id,
        "script_revision_id": script_revision_id,
        "source_digest": source_digest,
        "before_plan_id": before_plan_id,
        "after_plan_id": after_plan_id,
        "before_plan_digest": before_plan_digest,
        "after_plan_digest": after_plan_digest,
        "affected_ids": _unique(affected),
        "preserved_ids": _unique(preserved),
        "undo_available": undo_available,
        "undone": False,
        "storyboard_write": False,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _append_audit(state: dict[str, Any], event: dict[str, Any]) -> None:
    state["audit_history"] = [
        *state.get("audit_history", []),
        {
            "event_id": f"audit_{uuid4().hex[:12]}",
            "recorded_at": _server_now(),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
            **event,
        },
    ][-160:]


def _contract_error(error: str, message: str, *, project_id: str, stage: str, status_code: int = 422) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=safe_error_detail(
            error,
            message=message,
            user_action="Refresh Script/Core Asset truth and Production Plan truth, then retry with exact project, revision, digest, plan, and schema.",
            project_id=project_id,
            action=stage,
            stage=stage,
        ),
    )


def _enforce_project_access(auth: RuntimeAuthStore, request: Request, project_id: str) -> None:
    if not auth.enabled():
        return
    user = auth.require_user(request)
    if not project_id or not auth.user_can_access_project(str(user["user_id"]), project_id):
        raise HTTPException(status_code=403, detail="project access denied")


def _renumber_shots(shots: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    ordered = sorted(shots.values(), key=lambda item: (int(item.get("order") or 0), item.get("shot_id", "")))
    return {shot["shot_id"]: {**shot, "order": index + 1} for index, shot in enumerate(ordered)}


def _renumber_shots_in_place(plan: dict[str, Any]) -> None:
    plan["shots"] = _renumber_shots(plan.get("shots", {}))


def _preserved_ids(before: dict[str, Any], after: dict[str, Any], affected: set[str]) -> list[str]:
    ids = set(before.get("beats", {})) | set(before.get("shots", {})) | set(before.get("chunks", {}))
    after_ids = set(after.get("beats", {})) | set(after.get("shots", {})) | set(after.get("chunks", {}))
    return sorted((ids & after_ids) - set(affected))


def _duration_units(value: Any) -> int:
    number = Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(number * 100)


def _duration_float(value: Any) -> float:
    units = _duration_units(value)
    if units <= 0:
        raise ValueError("duration must be positive")
    return _units_float(units)


def _units_float(units: int) -> float:
    return float(Decimal(units) / Decimal(100))


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _safe_time(value: str | None = None) -> str:
    text = str(value or "").strip()
    return text[:80] if text else _server_now()


def _server_now() -> str:
    return datetime.now(UTC).isoformat()


def _clean_token(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]+", "", str(value or ""))[:180]


def _clean_text(value: Any, limit: int) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _command_title(command_type: str) -> str:
    return {
        "edit_shot_duration": "Edit shot duration",
        "edit_shot_intent": "Edit shot intent",
        "set_shot_strategy": "Set shot media strategy",
        "split_shot": "Split shot",
        "merge_shot_next": "Merge shot with next",
        "replan_affected": "Replan affected shots",
        "mark_failed": "Mark failed",
        "retry_failed": "Retry failed only",
    }.get(command_type, "Production plan command")


def _truth_dir(store: RuntimeStore, project_id: str) -> Path:
    return store.projects_dir / safe_id(project_id) / "dynamic_production_plan"


def _state_path(store: RuntimeStore, project_id: str) -> Path:
    return _truth_dir(store, project_id) / "truth_state.json"


def _lock_path(store: RuntimeStore, project_id: str) -> Path:
    return _truth_dir(store, project_id) / "truth_state.lock"


__all__ = (
    "PRODUCTION_PLAN_COMMAND_SCHEMA_VERSION",
    "PRODUCTION_PLAN_SCHEMA_VERSION",
    "PROVIDER_CAPABILITY_SCHEMA_VERSION",
    "STORY_PLAN_CANDIDATE_SCHEMA_VERSION",
    "production_plan_projection_for_project",
    "public_projection",
    "register_runtime_dynamic_production_plan_routes",
    "story_plan_candidate_digest",
)
