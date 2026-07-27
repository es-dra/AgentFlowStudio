from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from agentflow.harness.json_io import exclusive_file_lock, write_json
from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id


SCRIPT_TRUTH_SCHEMA_VERSION = "afs.script_core_truth.v0.1"
SCRIPT_REVISION_SCHEMA_VERSION = "afs.script_revision.v0.1"
ANALYSIS_CANDIDATE_SCHEMA_VERSION = "afs.structured_analysis_candidate.v0.1"
CORE_ASSET_COMMAND_SCHEMA_VERSION = "afs.core_asset_command.v0.1"
AUTO_CONFIRM_CONFIDENCE = 0.82
ACTIVE_STATUSES = {"confirmed", "pending_confirmation", "analysis_required", "low_confidence_pending"}


class EvidenceSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str = Field(min_length=1, max_length=1200)

    @model_validator(mode="after")
    def validate_span_order(self) -> "EvidenceSpan":
        if self.end <= self.start:
            raise ValueError("evidence span end must be greater than start")
        return self


class CandidateCharacter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=120)
    aliases: list[str] = Field(default_factory=list, max_length=20)
    pronoun_links: list[str] = Field(default_factory=list, max_length=20)
    evidence_spans: list[EvidenceSpan] = Field(min_length=1, max_length=12)
    confidence: float = Field(ge=0.0, le=1.0)
    status: Literal["candidate", "confirmed", "pending_confirmation"] = "candidate"


class CandidateMainScene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    evidence_spans: list[EvidenceSpan] = Field(min_length=1, max_length=12)
    confidence: float = Field(ge=0.0, le=1.0)
    status: Literal["candidate", "confirmed", "pending_confirmation"] = "candidate"


class ScriptRevisionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_kind: Literal["idea", "script", "uploaded_text"] = "script"
    source_text: str = Field(min_length=1, max_length=200_000)
    parent_revision_id: str | None = Field(default=None, max_length=120)
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = Field(default=None, max_length=80)


class StructuredAnalysisCandidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=128)
    revision_id: str = Field(min_length=1, max_length=120)
    source_digest: str = Field(min_length=64, max_length=64)
    schema_version: str = Field(min_length=1, max_length=80)
    named_characters: list[CandidateCharacter] = Field(default_factory=list, max_length=80)
    main_scenes: list[CandidateMainScene] = Field(default_factory=list, max_length=80)
    style: str | None = Field(default=None, max_length=600)
    genre: str | None = Field(default=None, max_length=240)
    tone: str | None = Field(default=None, max_length=240)
    actions: list[str] = Field(default_factory=list, max_length=120)
    events: list[str] = Field(default_factory=list, max_length=120)
    beats: list[dict[str, Any]] = Field(default_factory=list, max_length=120)
    generated_at: str | None = Field(default=None, max_length=80)
    provider_dispatch_count: int = Field(default=0, ge=0, le=0)
    remote_dispatch_count: int = Field(default=0, ge=0, le=0)


class CoreAssetCommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=128)
    revision_id: str = Field(min_length=1, max_length=120)
    source_digest: str = Field(min_length=64, max_length=64)
    schema_version: str = Field(min_length=1, max_length=80)
    command_type: Literal[
        "edit_asset",
        "retire_asset",
        "restore_asset",
        "merge_alias",
        "create_manual_prop",
        "retire_manual_prop",
    ]
    target_asset_id: str | None = Field(default=None, max_length=140)
    patch: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = Field(default=None, max_length=400)
    generated_at: str | None = Field(default=None, max_length=80)
    provider_dispatch_count: int = Field(default=0, ge=0, le=0)
    remote_dispatch_count: int = Field(default=0, ge=0, le=0)


class CoreAssetUndoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=128)
    receipt_id: str = Field(min_length=1, max_length=160)
    revision_id: str = Field(min_length=1, max_length=120)
    source_digest: str = Field(min_length=64, max_length=64)
    schema_version: str = Field(min_length=1, max_length=80)


def register_runtime_script_core_truth_routes(app: FastAPI, store: RuntimeStore, auth: RuntimeAuthStore) -> None:
    @app.post("/projects/{project_id}/script-revisions")
    def create_script_revision(
        project_id: str,
        body: ScriptRevisionCreateRequest,
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        store.ensure_project_manifest(project_id)
        with exclusive_file_lock(_lock_path(store, project_id)):
            state = _load_state(store, project_id)
            parent_revision_id = _clean_token(body.parent_revision_id or "")
            if parent_revision_id and parent_revision_id not in state["revisions"]:
                raise _contract_error(
                    "parent_revision_not_found",
                    "Parent revision does not exist in this project truth store.",
                    project_id=project_id,
                    stage="script_revision_create",
                    status_code=409,
                )
            revision = _new_revision(project_id, body, parent_revision_id)
            state["revisions"][revision["revision_id"]] = revision
            state["current_revision_id"] = revision["revision_id"]
            _append_audit(
                state,
                {
                    "event_type": "script_revision_created",
                    "revision_id": revision["revision_id"],
                    "parent_revision_id": parent_revision_id,
                    "source_digest": revision["source_digest"],
                },
            )
            _write_state(store, project_id, state)
        artifact = store.register_artifact(_state_path(store, project_id), role="script_core_truth")
        projection = public_projection(state)
        return {
            "project_id": project_id,
            "revision": public_revision(revision, include_source=True),
            "analysis_state": projection["analysis_state"],
            "projection": projection,
            "artifact": artifact,
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.post("/projects/{project_id}/script-revisions/{revision_id}/select")
    def select_script_revision(project_id: str, revision_id: str, request: Request) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        with exclusive_file_lock(_lock_path(store, project_id)):
            state = _load_state(store, project_id)
            if revision_id not in state["revisions"]:
                raise _contract_error(
                    "script_revision_not_found",
                    "Script revision does not exist in this project truth store.",
                    project_id=project_id,
                    stage="script_revision_select",
                    status_code=404,
                )
            state["current_revision_id"] = revision_id
            _append_audit(state, {"event_type": "script_revision_selected", "revision_id": revision_id})
            _write_state(store, project_id, state)
        return {
            "project_id": project_id,
            "current_revision_id": revision_id,
            "projection": public_projection(state),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @get_script_truth_route(app)
    def get_script_truth(project_id: str, request: Request) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        store.ensure_project_manifest(project_id)
        state = _load_state(store, project_id)
        return {
            "project_id": project_id,
            "projection": public_projection(state),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.post("/projects/{project_id}/script-revisions/{revision_id}/analysis-candidates")
    def submit_structured_analysis_candidate(
        project_id: str,
        revision_id: str,
        body: StructuredAnalysisCandidateRequest,
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        with exclusive_file_lock(_lock_path(store, project_id)):
            state = _load_state(store, project_id)
            revision = _require_revision_contract(
                state,
                project_id=project_id,
                revision_id=revision_id,
                body_project_id=body.project_id,
                source_digest=body.source_digest,
                schema_version=body.schema_version,
                stage="analysis_candidate_submit",
                expected_schema=ANALYSIS_CANDIDATE_SCHEMA_VERSION,
            )
            _validate_evidence_spans(body, revision)
            candidate = _analysis_candidate_record(project_id, revision, body)
            previous_assets = dict(state.get("assets") or {})
            assets, affected, preserved = _assets_from_candidate(project_id, revision, candidate, previous_assets)
            for asset in assets:
                state["assets"][asset["asset_id"]] = asset
            state.setdefault("analysis_candidates", {})[candidate["candidate_id"]] = candidate
            revision["analysis_state"] = _analysis_state_for_assets(assets)
            revision["analysis_candidate_id"] = candidate["candidate_id"]
            state["current_revision_id"] = revision_id
            _append_audit(
                state,
                {
                    "event_type": "structured_analysis_candidate_submitted",
                    "revision_id": revision_id,
                    "candidate_id": candidate["candidate_id"],
                    "affected_asset_ids": affected,
                    "preserved_asset_ids": preserved,
                },
            )
            _write_state(store, project_id, state)
        return {
            "project_id": project_id,
            "candidate": public_candidate(candidate),
            "analysis_state": revision["analysis_state"],
            "projection": public_projection(state),
            "affected_asset_ids": affected,
            "preserved_asset_ids": preserved,
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.post("/projects/{project_id}/core-assets/commands/preview")
    def preview_core_asset_command(
        project_id: str,
        body: CoreAssetCommandRequest,
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        state = _load_state(store, project_id)
        preview = _preview_core_asset_command(state, project_id, body)
        return {
            "project_id": project_id,
            "command": preview,
            "projection": public_projection(state),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.post("/projects/{project_id}/core-assets/commands/confirm")
    def confirm_core_asset_command(
        project_id: str,
        body: CoreAssetCommandRequest,
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        with exclusive_file_lock(_lock_path(store, project_id)):
            state = _load_state(store, project_id)
            preview = _preview_core_asset_command(state, project_id, body)
            receipt = _apply_core_asset_command(state, project_id, body, preview)
            _append_audit(
                state,
                {
                    "event_type": "core_asset_command_confirmed",
                    "revision_id": body.revision_id,
                    "command_type": body.command_type,
                    "receipt_id": receipt["receipt_id"],
                    "affected_asset_ids": receipt["affected_asset_ids"],
                },
            )
            _write_state(store, project_id, state)
        return {
            "project_id": project_id,
            "receipt": public_receipt(receipt),
            "projection": public_projection(state),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.post("/projects/{project_id}/core-assets/commands/undo")
    def undo_core_asset_command(
        project_id: str,
        body: CoreAssetUndoRequest,
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        with exclusive_file_lock(_lock_path(store, project_id)):
            state = _load_state(store, project_id)
            _require_revision_contract(
                state,
                project_id=project_id,
                revision_id=body.revision_id,
                body_project_id=body.project_id,
                source_digest=body.source_digest,
                schema_version=body.schema_version,
                stage="core_asset_command_undo",
                expected_schema=CORE_ASSET_COMMAND_SCHEMA_VERSION,
            )
            receipt = dict(state.get("receipts", {}).get(body.receipt_id) or {})
            if not receipt or receipt.get("undone"):
                raise _contract_error(
                    "core_asset_receipt_not_undoable",
                    "Receipt is missing or has already been undone.",
                    project_id=project_id,
                    stage="core_asset_command_undo",
                    status_code=409,
                )
            undo_receipt = _apply_undo(state, receipt)
            _append_audit(
                state,
                {
                    "event_type": "core_asset_command_undone",
                    "revision_id": body.revision_id,
                    "receipt_id": body.receipt_id,
                    "undo_receipt_id": undo_receipt["receipt_id"],
                },
            )
            _write_state(store, project_id, state)
        return {
            "project_id": project_id,
            "receipt": public_receipt(undo_receipt),
            "projection": public_projection(state),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }


def get_script_truth_route(app: FastAPI):
    return app.get("/projects/{project_id}/script-truth")


def public_projection(state: dict[str, Any]) -> dict[str, Any]:
    revision = _current_revision(state)
    revision_id = str(revision.get("revision_id") or "")
    assets = [
        public_asset(asset)
        for asset in sorted((state.get("assets") or {}).values(), key=lambda item: str(item.get("created_at") or ""))
        if _asset_belongs_to_revision(asset, revision_id)
    ]
    candidate = _current_candidate(state, revision)
    counts = {
        "characters": sum(1 for item in assets if item["asset_type"] == "character" and item["status"] != "retired"),
        "main_scenes": sum(1 for item in assets if item["asset_type"] == "main_scene" and item["status"] != "retired"),
        "manual_props": sum(1 for item in assets if item["asset_type"] == "prop" and item["source_mode"] == "manual" and item["status"] != "retired"),
        "auto_props": 0,
        "style_assets": 0,
        "action_event_assets": 0,
    }
    return {
        "artifact_type": "afs_script_core_truth_projection",
        "schema_version": SCRIPT_TRUTH_SCHEMA_VERSION,
        "project_id": state["project_id"],
        "current_revision_id": revision_id,
        # The authenticated Studio needs the current source to render and resume
        # the creator's text workflow after a refresh. Historical revisions stay
        # metadata-only to keep the projection bounded.
        "current_revision": public_revision(revision, include_source=True) if revision else None,
        "revision_history": [
            public_revision(item, include_source=False)
            for item in sorted((state.get("revisions") or {}).values(), key=lambda value: str(value.get("created_at") or ""))
        ],
        "assets": assets,
        "asset_counts": counts,
        "analysis_state": str(revision.get("analysis_state") or "analysis_required") if revision else "analysis_required",
        "analysis_candidate": public_candidate(candidate) if candidate else None,
        "narrative_fields": {
            "style": str(candidate.get("style") or "") if candidate else "",
            "genre": str(candidate.get("genre") or "") if candidate else "",
            "tone": str(candidate.get("tone") or "") if candidate else "",
            "actions_count": len(candidate.get("actions") or []) if candidate else 0,
            "events_count": len(candidate.get("events") or []) if candidate else 0,
            "beats_count": len(candidate.get("beats") or []) if candidate else 0,
            "promoted_to_assets": False,
        },
        "future_contracts": {
            "dynamic_beats": "reserved_not_implemented",
            "dynamic_shots": "reserved_not_implemented",
            "t2v_i2v_chunks": "reserved_not_implemented",
            "continuity_anchors": "reserved_not_implemented",
            "recovery_final_concat": "reserved_not_implemented",
        },
        "storyboard_mode": "read_only_consumer",
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def script_core_truth_projection_for_project(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    store.ensure_project_manifest(project_id)
    return public_projection(_load_state(store, project_id))


def public_revision(revision: dict[str, Any], *, include_source: bool) -> dict[str, Any]:
    if not revision:
        return {}
    payload = {
        "artifact_type": "afs_script_revision",
        "schema_version": revision.get("schema_version") or SCRIPT_REVISION_SCHEMA_VERSION,
        "project_id": str(revision.get("project_id") or ""),
        "revision_id": str(revision.get("revision_id") or ""),
        "parent_revision_id": str(revision.get("parent_revision_id") or ""),
        "source_kind": str(revision.get("source_kind") or ""),
        "source_digest": str(revision.get("source_digest") or ""),
        "source_length": int(revision.get("source_length") or 0),
        "created_at": str(revision.get("created_at") or ""),
        "provenance": _safe_public_dict(revision.get("provenance") or {}),
        "analysis_state": str(revision.get("analysis_state") or "analysis_required"),
        "analysis_candidate_id": str(revision.get("analysis_candidate_id") or ""),
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    if include_source:
        payload["source_text"] = str(revision.get("source_text") or "")
    return payload


def public_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    if not candidate:
        return {}
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "schema_version": str(candidate.get("schema_version") or ""),
        "project_id": str(candidate.get("project_id") or ""),
        "revision_id": str(candidate.get("revision_id") or ""),
        "source_digest": str(candidate.get("source_digest") or ""),
        "named_character_count": len(candidate.get("named_characters") or []),
        "main_scene_count": len(candidate.get("main_scenes") or []),
        "style": str(candidate.get("style") or ""),
        "genre": str(candidate.get("genre") or ""),
        "tone": str(candidate.get("tone") or ""),
        "actions": [str(item)[:240] for item in candidate.get("actions", [])[:20]],
        "events": [str(item)[:240] for item in candidate.get("events", [])[:20]],
        "beats_count": len(candidate.get("beats") or []),
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def public_asset(asset: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "asset_id": str(asset.get("asset_id") or ""),
        "asset_type": str(asset.get("asset_type") or ""),
        "source_mode": str(asset.get("source_mode") or ""),
        "status": str(asset.get("status") or ""),
        "project_id": str(asset.get("project_id") or ""),
        "revision_id": str(asset.get("revision_id") or ""),
        "source_digest": str(asset.get("source_digest") or ""),
        "display_name": str(asset.get("display_name") or asset.get("name") or ""),
        "name": str(asset.get("name") or asset.get("display_name") or ""),
        "aliases": list(asset.get("aliases") or []),
        "pronoun_links": list(asset.get("pronoun_links") or []),
        "evidence_spans": list(asset.get("evidence_spans") or []),
        "confidence": float(asset.get("confidence") or 0.0),
        "lineage": dict(asset.get("lineage") or {}),
        "created_at": str(asset.get("created_at") or ""),
        "updated_at": str(asset.get("updated_at") or ""),
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    return payload


def public_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "receipt_id": str(receipt.get("receipt_id") or ""),
        "command_id": str(receipt.get("command_id") or ""),
        "command_type": str(receipt.get("command_type") or ""),
        "status": str(receipt.get("status") or ""),
        "summary": str(receipt.get("summary") or ""),
        "executed_at": str(receipt.get("executed_at") or ""),
        "revision_id": str(receipt.get("revision_id") or ""),
        "source_digest": str(receipt.get("source_digest") or ""),
        "affected_asset_ids": list(receipt.get("affected_asset_ids") or []),
        "undo_available": bool(receipt.get("undo_available")),
        "storyboard_write": False,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _new_revision(project_id: str, body: ScriptRevisionCreateRequest, parent_revision_id: str) -> dict[str, Any]:
    created_at = _safe_time(body.created_at)
    source_text = _clean_source_text(body.source_text)
    source_digest = _source_digest(source_text)
    revision = {
        "artifact_type": "afs_script_revision",
        "schema_version": SCRIPT_REVISION_SCHEMA_VERSION,
        "project_id": project_id,
        "revision_id": f"scrrev_{uuid4().hex[:16]}",
        "parent_revision_id": parent_revision_id,
        "source_kind": body.source_kind,
        "source_text": source_text,
        "source_digest": source_digest,
        "source_length": len(source_text),
        "created_at": created_at,
        "provenance": _safe_public_dict(body.provenance),
        "analysis_state": "analysis_required",
        "analysis_candidate_id": "",
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    reject_unsafe_payload(revision)
    return revision


def _analysis_candidate_record(
    project_id: str,
    revision: dict[str, Any],
    body: StructuredAnalysisCandidateRequest,
) -> dict[str, Any]:
    payload = body.model_dump(mode="json")
    payload["artifact_type"] = "afs_structured_analysis_candidate"
    payload["candidate_id"] = f"candidate_{_sha256_json(payload)[:16]}"
    payload["created_at"] = _safe_time(body.generated_at)
    payload["project_id"] = project_id
    payload["revision_id"] = revision["revision_id"]
    payload["source_digest"] = revision["source_digest"]
    reject_unsafe_payload(payload)
    return payload


def _assets_from_candidate(
    project_id: str,
    revision: dict[str, Any],
    candidate: dict[str, Any],
    previous_assets: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    revision_id = revision["revision_id"]
    source_digest = revision["source_digest"]
    now = _server_now()
    previous_by_lineage = {
        _asset_preservation_key(asset): asset
        for asset in previous_assets.values()
        if asset.get("status") not in {"retired", "undone"} and asset.get("source_mode") == "analysis_candidate"
    }
    assets: list[dict[str, Any]] = []
    affected: list[str] = []
    preserved: list[str] = []
    for item in candidate.get("named_characters") or []:
        asset = _candidate_asset(
            project_id=project_id,
            revision_id=revision_id,
            source_digest=source_digest,
            source_mode="analysis_candidate",
            asset_type="character",
            label=str(item["display_name"]),
            aliases=[str(value) for value in item.get("aliases", [])],
            pronoun_links=[str(value) for value in item.get("pronoun_links", [])],
            evidence_spans=item.get("evidence_spans") or [],
            confidence=float(item.get("confidence") or 0.0),
            requested_status=str(item.get("status") or "candidate"),
            created_at=now,
        )
        asset = _preserve_asset_identity(asset, previous_by_lineage, affected, preserved)
        assets.append(asset)
    for item in candidate.get("main_scenes") or []:
        asset = _candidate_asset(
            project_id=project_id,
            revision_id=revision_id,
            source_digest=source_digest,
            source_mode="analysis_candidate",
            asset_type="main_scene",
            label=str(item["name"]),
            aliases=[],
            pronoun_links=[],
            evidence_spans=item.get("evidence_spans") or [],
            confidence=float(item.get("confidence") or 0.0),
            requested_status=str(item.get("status") or "candidate"),
            created_at=now,
        )
        asset = _preserve_asset_identity(asset, previous_by_lineage, affected, preserved)
        assets.append(asset)
    active_lineage = {_asset_preservation_key(asset) for asset in assets}
    for asset in previous_assets.values():
        if not _asset_belongs_to_revision(asset, revision_id) or asset.get("source_mode") != "analysis_candidate":
            continue
        if _asset_preservation_key(asset) in active_lineage:
            continue
        retired = dict(asset)
        retired["status"] = "retired"
        retired["updated_at"] = now
        assets.append(retired)
        affected.append(str(retired["asset_id"]))
    return assets, _unique(affected), _unique(preserved)


def _candidate_asset(
    *,
    project_id: str,
    revision_id: str,
    source_digest: str,
    source_mode: str,
    asset_type: str,
    label: str,
    aliases: list[str],
    pronoun_links: list[str],
    evidence_spans: list[dict[str, Any]],
    confidence: float,
    requested_status: str,
    created_at: str,
) -> dict[str, Any]:
    status = "confirmed" if confidence >= AUTO_CONFIRM_CONFIDENCE and requested_status != "pending_confirmation" else "pending_confirmation"
    quote_digest = _sha256_json([span.get("quote", "") for span in evidence_spans])
    key = _normal_key(f"{asset_type}:{label}:{quote_digest}")
    asset_id = f"{'char' if asset_type == 'character' else 'scene'}_{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}"
    asset = {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "source_mode": source_mode,
        "status": status,
        "project_id": project_id,
        "revision_id": revision_id,
        "source_digest": source_digest,
        "display_name": _clean_label(label),
        "name": _clean_label(label),
        "aliases": _clean_text_list(aliases),
        "pronoun_links": _clean_text_list(pronoun_links),
        "evidence_spans": evidence_spans,
        "confidence": confidence,
        "lineage": {
            "source_revision_id": revision_id,
            "source_digest": source_digest,
            "candidate_quote_digest": quote_digest,
            "preservation_key": key,
            "auto_asset_scope": "character_or_main_scene_only",
        },
        "created_at": created_at,
        "updated_at": created_at,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    reject_unsafe_payload(asset)
    return asset


def _preserve_asset_identity(
    asset: dict[str, Any],
    previous_by_lineage: dict[str, Any],
    affected: list[str],
    preserved: list[str],
) -> dict[str, Any]:
    previous = previous_by_lineage.get(_asset_preservation_key(asset))
    if not previous:
        affected.append(str(asset["asset_id"]))
        return asset
    merged = {**asset, "asset_id": previous["asset_id"], "created_at": previous.get("created_at") or asset["created_at"]}
    if previous.get("status") in {"confirmed", "pending_confirmation"} and asset.get("status") == previous.get("status"):
        preserved.append(str(previous["asset_id"]))
    else:
        affected.append(str(previous["asset_id"]))
    return merged


def _preview_core_asset_command(state: dict[str, Any], project_id: str, body: CoreAssetCommandRequest) -> dict[str, Any]:
    revision = _require_revision_contract(
        state,
        project_id=project_id,
        revision_id=body.revision_id,
        body_project_id=body.project_id,
        source_digest=body.source_digest,
        schema_version=body.schema_version,
        stage="core_asset_command_preview",
        expected_schema=CORE_ASSET_COMMAND_SCHEMA_VERSION,
    )
    assets = state.setdefault("assets", {})
    now = _safe_time(body.generated_at)
    before: dict[str, Any] | None = None
    after: dict[str, Any]
    target_id = _clean_token(body.target_asset_id or "")
    if body.command_type == "create_manual_prop":
        name = _clean_label(body.patch.get("display_name") or body.patch.get("name"))
        if not name:
            raise _contract_error(
                "manual_prop_name_required",
                "Manual prop command requires a display_name or name patch.",
                project_id=project_id,
                stage="core_asset_command_preview",
            )
        asset_id = f"prop_{hashlib.sha256(f'{project_id}:{body.revision_id}:{name}:{now}'.encode('utf-8')).hexdigest()[:16]}"
        after = {
            "asset_id": asset_id,
            "asset_type": "prop",
            "source_mode": "manual",
            "status": "confirmed",
            "project_id": project_id,
            "revision_id": body.revision_id,
            "source_digest": body.source_digest,
            "display_name": name,
            "name": name,
            "aliases": [],
            "pronoun_links": [],
            "evidence_spans": [],
            "confidence": 1.0,
            "lineage": {
                "source_revision_id": body.revision_id,
                "source_digest": body.source_digest,
                "manual_command": "create_manual_prop",
            },
            "created_at": now,
            "updated_at": now,
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }
    else:
        before = _require_asset_for_command(assets, project_id, body.revision_id, target_id, body.command_type)
        after = _mutated_asset_snapshot(before, body, now)
    affected = [str(after["asset_id"])]
    return {
        "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
        "command_id": f"cmd_{_sha256_json(body.model_dump(mode='json'))[:16]}",
        "command_type": body.command_type,
        "status": "preview",
        "project_id": project_id,
        "revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "title": _command_title(body.command_type),
        "summary": _command_summary(body.command_type, after),
        "before": public_asset(before) if before else None,
        "after": public_asset(after),
        "affected_asset_ids": affected,
        "requires_confirmation": True,
        "storyboard_write": False,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _apply_core_asset_command(
    state: dict[str, Any],
    project_id: str,
    body: CoreAssetCommandRequest,
    preview: dict[str, Any],
) -> dict[str, Any]:
    after = dict(preview["after"])
    assets = state.setdefault("assets", {})
    assets[after["asset_id"]] = {
        **assets.get(after["asset_id"], {}),
        **after,
        "project_id": project_id,
        "revision_id": body.revision_id,
        "source_digest": body.source_digest,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    receipt = {
        "receipt_id": f"receipt_{uuid4().hex[:16]}",
        "command_id": preview["command_id"],
        "command_type": body.command_type,
        "status": "executed",
        "summary": f"{preview['title']} executed against canonical core asset truth.",
        "executed_at": _server_now(),
        "project_id": project_id,
        "revision_id": body.revision_id,
        "source_digest": body.source_digest,
        "before": preview.get("before"),
        "after": preview.get("after"),
        "affected_asset_ids": preview["affected_asset_ids"],
        "undo_available": True,
        "undone": False,
        "storyboard_write": False,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    state.setdefault("receipts", {})[receipt["receipt_id"]] = receipt
    return receipt


def _apply_undo(state: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    asset_id = str((receipt.get("after") or {}).get("asset_id") or "")
    before = receipt.get("before")
    assets = state.setdefault("assets", {})
    if before:
        assets[asset_id] = dict(before)
    elif asset_id:
        after = dict(receipt.get("after") or {})
        after["status"] = "undone"
        after["updated_at"] = _server_now()
        assets[asset_id] = after
    receipt["undone"] = True
    receipt["undo_available"] = False
    undo_receipt = {
        "receipt_id": f"receipt_{uuid4().hex[:16]}",
        "command_id": receipt.get("command_id", ""),
        "command_type": f"{receipt.get('command_type', '')}.undo",
        "status": "undone",
        "summary": "Canonical core asset command was undone.",
        "executed_at": _server_now(),
        "project_id": receipt.get("project_id", ""),
        "revision_id": receipt.get("revision_id", ""),
        "source_digest": receipt.get("source_digest", ""),
        "before": receipt.get("after"),
        "after": before,
        "affected_asset_ids": [asset_id] if asset_id else [],
        "undo_available": False,
        "undone": True,
        "storyboard_write": False,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    state.setdefault("receipts", {})[undo_receipt["receipt_id"]] = undo_receipt
    return undo_receipt


def _mutated_asset_snapshot(before: dict[str, Any], body: CoreAssetCommandRequest, now: str) -> dict[str, Any]:
    after = dict(before)
    after["updated_at"] = now
    if body.command_type == "edit_asset":
        label = _clean_label(body.patch.get("display_name") or body.patch.get("name") or after.get("display_name"))
        if not label:
            raise ValueError("edited asset label cannot be empty")
        after["display_name"] = label
        after["name"] = label
        if "aliases" in body.patch:
            after["aliases"] = _clean_text_list(list(body.patch.get("aliases") or []))
    elif body.command_type == "retire_asset" or body.command_type == "retire_manual_prop":
        after["status"] = "retired"
        after["retired_at"] = now
    elif body.command_type == "restore_asset":
        after["status"] = str(before.get("last_active_status") or "confirmed")
        after.pop("retired_at", None)
    elif body.command_type == "merge_alias":
        if after.get("asset_type") != "character":
            raise _contract_error(
                "merge_alias_requires_character",
                "Alias merge is only available for character assets.",
                project_id=str(body.project_id),
                stage="core_asset_command_preview",
                status_code=409,
            )
        alias = _clean_label(body.patch.get("alias") or body.patch.get("display_name"))
        aliases = _clean_text_list([*(after.get("aliases") or []), alias])
        if not alias or alias not in aliases:
            raise _contract_error(
                "alias_required",
                "Alias merge command requires an alias patch.",
                project_id=str(body.project_id),
                stage="core_asset_command_preview",
            )
        after["aliases"] = aliases
    else:
        raise ValueError("unsupported command type")
    after["provider_dispatch_count"] = 0
    after["remote_dispatch_count"] = 0
    if before.get("status") in ACTIVE_STATUSES:
        after["last_active_status"] = before.get("status")
    reject_unsafe_payload(after)
    return after


def _require_asset_for_command(
    assets: dict[str, Any],
    project_id: str,
    revision_id: str,
    target_id: str,
    command_type: str,
) -> dict[str, Any]:
    if not target_id:
        raise _contract_error(
            "core_asset_target_required",
            "Core asset command requires a target asset id.",
            project_id=project_id,
            stage="core_asset_command_preview",
        )
    asset = dict(assets.get(target_id) or {})
    if not asset or asset.get("project_id") != project_id or asset.get("revision_id") != revision_id:
        raise _contract_error(
            "core_asset_target_not_found",
            "Target asset does not belong to this project revision.",
            project_id=project_id,
            stage="core_asset_command_preview",
            status_code=404,
        )
    if command_type == "restore_asset" and asset.get("status") != "retired":
        raise _contract_error(
            "core_asset_not_retired",
            "Restore command requires a retired asset.",
            project_id=project_id,
            stage="core_asset_command_preview",
            status_code=409,
        )
    if command_type != "restore_asset" and asset.get("status") == "retired":
        raise _contract_error(
            "core_asset_already_retired",
            "Retired assets must be restored before other edits.",
            project_id=project_id,
            stage="core_asset_command_preview",
            status_code=409,
        )
    if command_type == "retire_manual_prop" and not (asset.get("asset_type") == "prop" and asset.get("source_mode") == "manual"):
        raise _contract_error(
            "manual_prop_target_required",
            "Manual prop retirement requires a manual prop target.",
            project_id=project_id,
            stage="core_asset_command_preview",
            status_code=409,
        )
    return asset


def _require_revision_contract(
    state: dict[str, Any],
    *,
    project_id: str,
    revision_id: str,
    body_project_id: str,
    source_digest: str,
    schema_version: str,
    stage: str,
    expected_schema: str,
) -> dict[str, Any]:
    if body_project_id != project_id:
        raise _contract_error(
            "project_identity_mismatch",
            "Request project id does not match the URL project scope.",
            project_id=project_id,
            stage=stage,
            status_code=409,
        )
    if schema_version != expected_schema:
        raise _contract_error(
            "schema_version_mismatch",
            "Request schema version is not accepted by this contract.",
            project_id=project_id,
            stage=stage,
            status_code=409,
        )
    revision = dict((state.get("revisions") or {}).get(revision_id) or {})
    if not revision:
        raise _contract_error(
            "script_revision_not_found",
            "Script revision does not exist in this project truth store.",
            project_id=project_id,
            stage=stage,
            status_code=404,
        )
    if str(revision.get("source_digest") or "") != source_digest:
        raise _contract_error(
            "source_digest_mismatch",
            "Request source digest does not match the script revision.",
            project_id=project_id,
            stage=stage,
            status_code=409,
        )
    if str(state.get("current_revision_id") or "") != revision_id:
        raise _contract_error(
            "current_revision_mismatch",
            "Request revision is not the selected current script revision.",
            project_id=project_id,
            stage=stage,
            status_code=409,
        )
    return state["revisions"][revision_id]


def _validate_evidence_spans(body: StructuredAnalysisCandidateRequest, revision: dict[str, Any]) -> None:
    source_text = str(revision.get("source_text") or "")
    for item in [*body.named_characters, *body.main_scenes]:
        for span in item.evidence_spans:
            expected = source_text[span.start : span.end]
            if expected != span.quote:
                raise _contract_error(
                    "evidence_span_mismatch",
                    "Evidence span quote must exactly match the bound source revision text.",
                    project_id=str(body.project_id),
                    stage="analysis_candidate_submit",
                    status_code=409,
                    details={"revision_id": body.revision_id},
                )


def _analysis_state_for_assets(assets: list[dict[str, Any]]) -> str:
    active = [item for item in assets if item.get("status") != "retired"]
    if not active:
        return "low_confidence_pending"
    if any(item.get("status") == "pending_confirmation" for item in active):
        return "pending_confirmation"
    return "confirmed"


def _current_revision(state: dict[str, Any]) -> dict[str, Any]:
    revision_id = str(state.get("current_revision_id") or "")
    return dict((state.get("revisions") or {}).get(revision_id) or {})


def _current_candidate(state: dict[str, Any], revision: dict[str, Any]) -> dict[str, Any]:
    candidate_id = str(revision.get("analysis_candidate_id") or "")
    return dict((state.get("analysis_candidates") or {}).get(candidate_id) or {})


def _asset_belongs_to_revision(asset: dict[str, Any], revision_id: str) -> bool:
    return str(asset.get("revision_id") or "") == revision_id and str(asset.get("status") or "") != "undone"


def _asset_preservation_key(asset: dict[str, Any]) -> str:
    lineage = asset.get("lineage") if isinstance(asset.get("lineage"), dict) else {}
    key = str(lineage.get("preservation_key") or "")
    if key:
        return key
    return _normal_key(f"{asset.get('asset_type')}:{asset.get('display_name') or asset.get('name')}:{asset.get('source_digest')}")


def _load_state(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    path = _state_path(store, project_id)
    if path.is_file():
        state = read_json(path)
        reject_unsafe_payload(state)
        if state.get("project_id") != project_id:
            raise ValueError("script truth project id mismatch")
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
        "artifact_type": "afs_script_core_asset_truth",
        "schema_version": SCRIPT_TRUTH_SCHEMA_VERSION,
        "project_id": project_id,
        "current_revision_id": "",
        "revisions": {},
        "analysis_candidates": {},
        "assets": {},
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
    for key in ("revisions", "analysis_candidates", "assets", "receipts"):
        if not isinstance(payload.get(key), dict):
            payload[key] = {}
    if not isinstance(payload.get("audit_history"), list):
        payload["audit_history"] = []
    payload["provider_dispatch_count"] = 0
    payload["remote_dispatch_count"] = 0
    return payload


def _append_audit(state: dict[str, Any], event: dict[str, Any]) -> None:
    safe_event = {
        "event_id": f"audit_{uuid4().hex[:12]}",
        "recorded_at": _server_now(),
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
        **event,
    }
    state["audit_history"] = [*state.get("audit_history", []), safe_event][-120:]


def _contract_error(
    error: str,
    message: str,
    *,
    project_id: str,
    stage: str,
    status_code: int = 422,
    details: dict[str, Any] | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=safe_error_detail(
            error,
            message=message,
            user_action="Refresh script truth and retry with the exact project, revision, schema, and source digest.",
            project_id=project_id,
            action=stage,
            stage=stage,
            details=details or {},
        ),
    )


def _enforce_project_access(auth: RuntimeAuthStore, request: Request, project_id: str) -> None:
    if not auth.enabled():
        return
    user = auth.require_user(request)
    if not project_id or not auth.user_can_access_project(str(user["user_id"]), project_id):
        raise HTTPException(status_code=403, detail="project access denied")


def _safe_time(value: str | None = None) -> str:
    text = str(value or "").strip()
    return text[:80] if text else _server_now()


def _server_now() -> str:
    return datetime.now(UTC).isoformat()


def _source_digest(source_text: str) -> str:
    return hashlib.sha256(source_text.encode("utf-8")).hexdigest()


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _clean_source_text(value: str) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def _clean_label(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:120]


def _clean_text_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for value in values:
        text = _clean_label(value)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            cleaned.append(text)
    return cleaned[:20]


def _clean_token(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]+", "", str(value or ""))[:160]


def _safe_public_dict(value: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, item in (value or {}).items():
        safe_key = _clean_token(key)
        if not safe_key:
            continue
        if isinstance(item, (str, int, float, bool)) or item is None:
            payload[safe_key] = item
        elif isinstance(item, list):
            payload[safe_key] = [entry for entry in item[:20] if isinstance(entry, (str, int, float, bool)) or entry is None]
        elif isinstance(item, dict):
            payload[safe_key] = _safe_public_dict(item)
    return payload


def _normal_key(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().casefold())


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _command_title(command_type: str) -> str:
    return {
        "edit_asset": "Edit core asset",
        "retire_asset": "Retire core asset",
        "restore_asset": "Restore core asset",
        "merge_alias": "Merge character alias",
        "create_manual_prop": "Create manual prop",
        "retire_manual_prop": "Retire manual prop",
    }.get(command_type, "Core asset command")


def _command_summary(command_type: str, asset: dict[str, Any]) -> str:
    return f"{_command_title(command_type)}: {asset.get('display_name') or asset.get('name') or asset.get('asset_id')}"


def _truth_dir(store: RuntimeStore, project_id: str) -> Path:
    return store.projects_dir / safe_id(project_id) / "script_core_truth"


def _state_path(store: RuntimeStore, project_id: str) -> Path:
    return _truth_dir(store, project_id) / "truth_state.json"


def _lock_path(store: RuntimeStore, project_id: str) -> Path:
    return _truth_dir(store, project_id) / "truth_state.lock"


__all__ = (
    "ANALYSIS_CANDIDATE_SCHEMA_VERSION",
    "CORE_ASSET_COMMAND_SCHEMA_VERSION",
    "SCRIPT_REVISION_SCHEMA_VERSION",
    "SCRIPT_TRUTH_SCHEMA_VERSION",
    "public_projection",
    "register_runtime_script_core_truth_routes",
    "script_core_truth_projection_for_project",
)
