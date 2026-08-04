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
from apps.api.runtime_production_graph import (
    GraphIdempotencyConflict,
    GraphVersionConflict,
    ProductionGraphError,
    ProductionGraphStore,
    canonical_digest,
)
from apps.api.runtime_script_candidate_extraction import (
    DETERMINISTIC_EXTRACTION_SCHEMA_VERSION,
    build_deterministic_analysis_candidate,
)
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id


SCRIPT_TRUTH_SCHEMA_VERSION = "afs.script_core_truth.v0.1"
SCRIPT_REVISION_SCHEMA_VERSION = "afs.script_revision.v0.1"
ANALYSIS_CANDIDATE_SCHEMA_VERSION = "afs.structured_analysis_candidate.v0.1"
ANALYSIS_REVIEW_SCHEMA_VERSION = "afs.analysis_asset_review.v0.1"
SCENE_OWNERSHIP_SCHEMA_VERSION = "afs.scene_ownership_relationship.v0.1"
SCENE_OWNERSHIP_REVIEW_SCHEMA_VERSION = "afs.scene_ownership_review.v0.1"
CORE_ASSET_COMMAND_SCHEMA_VERSION = "afs.core_asset_command.v0.1"
AUTO_CONFIRM_CONFIDENCE = 0.82
ACTIVE_STATUSES = {"candidate", "modified", "confirmed", "pending_confirmation", "analysis_required", "low_confidence_pending"}


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
    evidence_status: Literal["extracted_from_text", "model_inferred", "conflicting"] = "model_inferred"
    extraction_method: str = Field(default="unspecified_structured_analysis", min_length=1, max_length=120)
    uncertainty_note: str | None = Field(default=None, max_length=600)


class CandidateMainScene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    evidence_spans: list[EvidenceSpan] = Field(min_length=1, max_length=12)
    confidence: float = Field(ge=0.0, le=1.0)
    status: Literal["candidate", "confirmed", "pending_confirmation"] = "candidate"
    evidence_status: Literal["extracted_from_text", "model_inferred", "conflicting"] = "model_inferred"
    extraction_method: str = Field(default="unspecified_structured_analysis", min_length=1, max_length=120)
    uncertainty_note: str | None = Field(default=None, max_length=600)


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
    missing_slots: list[Literal["named_characters", "main_scenes"]] = Field(default_factory=list, max_length=2)
    extraction_notes: list[str] = Field(default_factory=list, max_length=20)
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
    expected_asset_version: int | None = Field(default=None, ge=1)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=160)
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


class AnalysisAssetReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=128)
    revision_id: str = Field(min_length=1, max_length=120)
    source_digest: str = Field(min_length=64, max_length=64)
    candidate_id: str = Field(min_length=1, max_length=160)
    asset_version_id: str = Field(min_length=1, max_length=160)
    expected_asset_version: int = Field(ge=1)
    expected_graph_version: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=160)
    schema_version: str = Field(min_length=1, max_length=80)
    decision: Literal["confirm", "reject"]
    reason: str | None = Field(default=None, max_length=600)
    decided_at: str | None = Field(default=None, max_length=80)


class SceneOwnershipReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=128)
    revision_id: str = Field(min_length=1, max_length=120)
    source_digest: str = Field(min_length=64, max_length=64)
    relationship_version_id: str = Field(min_length=1, max_length=160)
    expected_relationship_version: int = Field(ge=1)
    expected_graph_version: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=160)
    schema_version: str = Field(min_length=1, max_length=80)
    decision: Literal["confirm", "reject"]
    reason: str | None = Field(default=None, max_length=600)
    decided_at: str | None = Field(default=None, max_length=80)


def register_runtime_script_core_truth_routes(app: FastAPI, store: RuntimeStore, auth: RuntimeAuthStore) -> None:
    graph_store = ProductionGraphStore(store)

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
            _remove_confirmed_relationships_from_graph(
                graph_store,
                state,
                project_id=project_id,
                relationships=_confirmed_relationships(state),
                idempotency_key=(
                    f"scene-ownership-revision-expire:{state.get('current_revision_id', '')}:"
                    f"{revision['source_digest']}"
                ),
                stage="script_revision_create",
            )
            _expire_open_analysis(state, superseded_by_revision_id=revision["revision_id"])
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
            current_revision_id = str(state.get("current_revision_id") or "")
            if current_revision_id != revision_id:
                active_relationships = _active_relationships(state)
                _remove_confirmed_relationships_from_graph(
                    graph_store,
                    state,
                    project_id=project_id,
                    relationships=[item for item in active_relationships if item.get("status") == "confirmed"],
                    idempotency_key=f"scene-ownership-revision-select:{current_revision_id}:{revision_id}",
                    stage="script_revision_select",
                )
                _expire_relationships(
                    state,
                    active_relationships,
                    reason="current_revision_selected",
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
            revision, candidate, assets, affected, preserved = _apply_structured_analysis_candidate(
                state,
                project_id=project_id,
                revision_id=revision_id,
                body=body,
            )
            _invalidate_stale_relationships_after_asset_change(
                graph_store,
                state,
                project_id=project_id,
                idempotency_key=f"scene-ownership-candidate-refresh:{candidate['candidate_id']}",
                stage="analysis_candidate_submit",
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

    @app.post("/projects/{project_id}/script-revisions/{revision_id}/analysis-candidates/extract")
    def extract_deterministic_analysis_candidate(
        project_id: str,
        revision_id: str,
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        with exclusive_file_lock(_lock_path(store, project_id)):
            state = _load_state(store, project_id)
            revision = _require_current_revision_for_extraction(
                state,
                project_id=project_id,
                revision_id=revision_id,
            )
            body = StructuredAnalysisCandidateRequest.model_validate(
                build_deterministic_analysis_candidate(
                    project_id=project_id,
                    revision_id=revision_id,
                    source_digest=str(revision["source_digest"]),
                    source_text=str(revision["source_text"]),
                    candidate_schema_version=ANALYSIS_CANDIDATE_SCHEMA_VERSION,
                )
            )
            revision, candidate, assets, affected, preserved = _apply_structured_analysis_candidate(
                state,
                project_id=project_id,
                revision_id=revision_id,
                body=body,
            )
            _invalidate_stale_relationships_after_asset_change(
                graph_store,
                state,
                project_id=project_id,
                idempotency_key=f"scene-ownership-candidate-refresh:{candidate['candidate_id']}",
                stage="analysis_candidate_extract",
            )
            _write_state(store, project_id, state)
        return {
            "project_id": project_id,
            "candidate": public_candidate(candidate),
            "analysis_state": revision["analysis_state"],
            "projection": public_projection(state),
            "affected_asset_ids": affected,
            "preserved_asset_ids": preserved,
            "extraction": {
                "schema_version": DETERMINISTIC_EXTRACTION_SCHEMA_VERSION,
                "missing_slots": list(body.missing_slots),
                "notes": list(body.extraction_notes),
            },
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.post("/projects/{project_id}/script-revisions/{revision_id}/analysis-relationships/extract")
    def extract_scene_ownership_relationships(
        project_id: str,
        revision_id: str,
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        with exclusive_file_lock(_lock_path(store, project_id)):
            state = _load_state(store, project_id)
            revision = _require_current_revision_for_extraction(
                state,
                project_id=project_id,
                revision_id=revision_id,
            )
            relationships, affected, preserved = _extract_scene_ownership(state, revision)
            _append_audit(
                state,
                {
                    "event_type": "scene_ownership_relationships_extracted",
                    "revision_id": revision_id,
                    "affected_relationship_ids": affected,
                    "preserved_relationship_ids": preserved,
                },
            )
            _write_state(store, project_id, state)
        return {
            "project_id": project_id,
            "revision_id": revision_id,
            "source_digest": revision["source_digest"],
            "relationships": [public_relationship(item) for item in relationships],
            "affected_relationship_ids": affected,
            "preserved_relationship_ids": preserved,
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.get("/projects/{project_id}/script-revisions/{revision_id}/analysis-candidates")
    def list_analysis_candidates(project_id: str, revision_id: str, request: Request) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        state = _load_state(store, project_id)
        revision = dict((state.get("revisions") or {}).get(revision_id) or {})
        if not revision:
            raise _contract_error(
                "script_revision_not_found",
                "Script revision does not exist in this project truth store.",
                project_id=project_id,
                stage="analysis_candidate_query",
                status_code=404,
            )
        candidates = [
            public_candidate(item)
            for item in (state.get("analysis_candidates") or {}).values()
            if str(item.get("revision_id") or "") == revision_id
        ]
        assets = [public_asset(item) for item in _analysis_assets_for_revision(state, revision_id)]
        decisions = [
            public_review_decision(item)
            for item in (state.get("review_decisions") or {}).values()
            if str(item.get("revision_id") or "") == revision_id
        ]
        relationships = _relationships_for_revision(state, revision_id)
        relationship_decisions = [
            public_relationship_review_decision(item)
            for item in (state.get("relationship_review_decisions") or {}).values()
            if str(item.get("revision_id") or "") == revision_id
        ]
        return {
            "project_id": project_id,
            "revision": public_revision(revision, include_source=False),
            "candidates": sorted(candidates, key=lambda item: str(item.get("created_at") or "")),
            "assets": assets,
            "review_decisions": sorted(decisions, key=lambda item: str(item.get("decided_at") or "")),
            "relationships": [public_relationship(item) for item in relationships],
            "relationship_review_decisions": sorted(
                relationship_decisions,
                key=lambda item: str(item.get("decided_at") or ""),
            ),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.post(
        "/projects/{project_id}/script-revisions/{revision_id}/analysis-relationships/{relationship_id}/review"
    )
    def review_scene_ownership_relationship(
        project_id: str,
        revision_id: str,
        relationship_id: str,
        body: SceneOwnershipReviewRequest,
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        semantic_digest = _scene_ownership_review_digest(body, revision_id, relationship_id)
        with exclusive_file_lock(_lock_path(store, project_id)):
            state = _load_state(store, project_id)
            existing = _relationship_review_receipt_for_key(state, body.idempotency_key)
            if existing:
                if existing.get("semantic_digest") != semantic_digest:
                    raise _contract_error(
                        "scene_ownership_review_idempotency_conflict",
                        "Idempotency key was already used for a different relationship decision.",
                        project_id=project_id,
                        stage="scene_ownership_review",
                        status_code=409,
                    )
                relationship = _relationship_version_by_id(
                    state,
                    relationship_id,
                    str(existing.get("relationship_version_id") or ""),
                )
                decision = dict(
                    (state.get("relationship_review_decisions") or {}).get(existing.get("review_decision_id")) or {}
                )
                return _scene_ownership_review_response(
                    project_id,
                    relationship,
                    decision,
                    existing,
                    graph_store.ensure(project_id),
                    idempotent_replay=True,
                    graph_idempotent_replay=bool(existing.get("graph_idempotent_replay")),
                )

            revision = _require_revision_contract(
                state,
                project_id=project_id,
                revision_id=revision_id,
                body_project_id=body.project_id,
                source_digest=body.source_digest,
                schema_version=body.schema_version,
                stage="scene_ownership_review",
                expected_schema=SCENE_OWNERSHIP_REVIEW_SCHEMA_VERSION,
            )
            if body.revision_id != revision_id:
                raise _contract_error(
                    "revision_identity_mismatch",
                    "Request revision id does not match the URL revision scope.",
                    project_id=project_id,
                    stage="scene_ownership_review",
                    status_code=409,
                )
            relationship = dict((state.get("relationships") or {}).get(relationship_id) or {})
            scene, member = _require_reviewable_relationship(
                state,
                relationship,
                relationship_id=relationship_id,
                body=body,
                project_id=project_id,
            )
            decided_at = _safe_time(body.decided_at)
            reviewed_relationship = _reviewed_relationship_version(
                relationship,
                body=body,
                semantic_digest=semantic_digest,
                decided_at=decided_at,
            )
            graph = graph_store.ensure(project_id)
            graph_replay = False
            if body.decision == "confirm":
                try:
                    graph = graph_store.append(
                        project_id,
                        expected_version=body.expected_graph_version,
                        idempotency_key=body.idempotency_key,
                        semantic_digest=semantic_digest,
                        events=_scene_ownership_confirmation_events(
                            graph,
                            revision,
                            scene,
                            member,
                            reviewed_relationship,
                            project_id=project_id,
                        ),
                    )
                    graph_replay = bool(graph.get("idempotent_replay"))
                except GraphIdempotencyConflict as exc:
                    raise _contract_error(
                        "scene_ownership_review_idempotency_conflict",
                        "Idempotency key was already used for a different graph mutation.",
                        project_id=project_id,
                        stage="scene_ownership_review",
                        status_code=409,
                    ) from exc
                except GraphVersionConflict as exc:
                    raise _contract_error(
                        "production_graph_version_conflict",
                        "Production Graph changed before this relationship decision was committed.",
                        project_id=project_id,
                        stage="scene_ownership_review",
                        status_code=409,
                    ) from exc
                except ProductionGraphError as exc:
                    raise _contract_error(
                        "production_graph_write_rejected",
                        "Confirmed scene ownership could not be written to Production Graph.",
                        project_id=project_id,
                        stage="scene_ownership_review",
                        status_code=409,
                    ) from exc
            elif graph.get("version") != body.expected_graph_version:
                raise _contract_error(
                    "production_graph_version_conflict",
                    "Production Graph changed before this relationship decision was committed.",
                    project_id=project_id,
                    stage="scene_ownership_review",
                    status_code=409,
                )

            decision, receipt = _apply_scene_ownership_review(
                state,
                project_id=project_id,
                relationship=relationship,
                reviewed_relationship=reviewed_relationship,
                body=body,
                semantic_digest=semantic_digest,
                graph=graph,
                graph_idempotent_replay=graph_replay,
                decided_at=decided_at,
            )
            _append_audit(
                state,
                {
                    "event_type": "scene_ownership_relationship_reviewed",
                    "revision_id": revision_id,
                    "relationship_id": relationship_id,
                    "relationship_version_id": reviewed_relationship["version_id"],
                    "review_decision_id": decision["review_decision_id"],
                    "decision": decision["decision"],
                },
            )
            _write_state(store, project_id, state)
        return _scene_ownership_review_response(
            project_id,
            reviewed_relationship,
            decision,
            receipt,
            graph,
            idempotent_replay=False,
            graph_idempotent_replay=graph_replay,
        )

    @app.post(
        "/projects/{project_id}/script-revisions/{revision_id}/analysis-assets/{asset_id}/review"
    )
    def review_analysis_asset(
        project_id: str,
        revision_id: str,
        asset_id: str,
        body: AnalysisAssetReviewRequest,
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        semantic_digest = _analysis_review_digest(body, revision_id=revision_id, asset_id=asset_id)
        with exclusive_file_lock(_lock_path(store, project_id)):
            state = _load_state(store, project_id)
            existing = _review_receipt_for_key(state, body.idempotency_key)
            if existing:
                if existing.get("semantic_digest") != semantic_digest:
                    raise _contract_error(
                        "analysis_review_idempotency_conflict",
                        "Idempotency key was already used for a different review decision.",
                        project_id=project_id,
                        stage="analysis_asset_review",
                        status_code=409,
                    )
                graph = graph_store.ensure(project_id)
                reviewed_asset = _asset_version_by_id(state, asset_id, str(existing.get("asset_version_id") or ""))
                decision = dict((state.get("review_decisions") or {}).get(existing.get("review_decision_id")) or {})
                return _analysis_review_response(
                    project_id,
                    reviewed_asset,
                    decision,
                    existing,
                    graph,
                    idempotent_replay=True,
                    graph_idempotent_replay=bool(existing.get("graph_idempotent_replay")),
                )

            revision = _require_revision_contract(
                state,
                project_id=project_id,
                revision_id=revision_id,
                body_project_id=body.project_id,
                source_digest=body.source_digest,
                schema_version=body.schema_version,
                stage="analysis_asset_review",
                expected_schema=ANALYSIS_REVIEW_SCHEMA_VERSION,
            )
            if body.revision_id != revision_id:
                raise _contract_error(
                    "revision_identity_mismatch",
                    "Request revision id does not match the URL revision scope.",
                    project_id=project_id,
                    stage="analysis_asset_review",
                    status_code=409,
                )
            candidate = dict((state.get("analysis_candidates") or {}).get(body.candidate_id) or {})
            if (
                not candidate
                or candidate.get("project_id") != project_id
                or candidate.get("revision_id") != revision_id
                or candidate.get("source_digest") != body.source_digest
            ):
                raise _contract_error(
                    "analysis_candidate_not_found",
                    "Review candidate does not belong to this exact script revision.",
                    project_id=project_id,
                    stage="analysis_asset_review",
                    status_code=404,
                )
            asset = dict((state.get("assets") or {}).get(asset_id) or {})
            _require_reviewable_asset(asset, body, project_id=project_id, asset_id=asset_id)
            decided_at = _safe_time(body.decided_at)
            reviewed_asset = _reviewed_asset_version(
                asset,
                body=body,
                semantic_digest=semantic_digest,
                decided_at=decided_at,
            )

            graph = graph_store.ensure(project_id)
            graph_replay = False
            if body.decision == "confirm":
                try:
                    graph = graph_store.append(
                        project_id,
                        expected_version=body.expected_graph_version,
                        idempotency_key=body.idempotency_key,
                        semantic_digest=semantic_digest,
                        events=_analysis_confirmation_events(revision, candidate, reviewed_asset, semantic_digest),
                    )
                    graph_replay = bool(graph.get("idempotent_replay"))
                except GraphIdempotencyConflict as exc:
                    raise _contract_error(
                        "analysis_review_idempotency_conflict",
                        "Idempotency key was already used for a different graph mutation.",
                        project_id=project_id,
                        stage="analysis_asset_review",
                        status_code=409,
                    ) from exc
                except GraphVersionConflict as exc:
                    raise _contract_error(
                        "production_graph_version_conflict",
                        "Production Graph changed before this review decision was committed.",
                        project_id=project_id,
                        stage="analysis_asset_review",
                        status_code=409,
                        details={"expected_graph_version": body.expected_graph_version},
                    ) from exc
                except ProductionGraphError as exc:
                    raise _contract_error(
                        "production_graph_write_rejected",
                        "Confirmed analysis asset could not be written to Production Graph.",
                        project_id=project_id,
                        stage="analysis_asset_review",
                        status_code=409,
                    ) from exc
            elif graph.get("version") != body.expected_graph_version:
                raise _contract_error(
                    "production_graph_version_conflict",
                    "Production Graph changed before this review decision was committed.",
                    project_id=project_id,
                    stage="analysis_asset_review",
                    status_code=409,
                    details={"expected_graph_version": body.expected_graph_version},
                )

            decision, reviewed_asset, receipt = _apply_analysis_review(
                state,
                project_id=project_id,
                revision=revision,
                candidate=candidate,
                asset=asset,
                body=body,
                semantic_digest=semantic_digest,
                graph=graph,
                graph_idempotent_replay=graph_replay,
                reviewed_asset=reviewed_asset,
                decided_at=decided_at,
            )
            _expire_relationships(
                state,
                _active_relationships(state, asset_id=asset_id),
                reason=f"endpoint_asset_{decision['decision']}",
            )
            _append_audit(
                state,
                {
                    "event_type": "analysis_asset_reviewed",
                    "revision_id": revision_id,
                    "candidate_id": candidate["candidate_id"],
                    "asset_id": asset_id,
                    "asset_version_id": reviewed_asset["version_id"],
                    "review_decision_id": decision["review_decision_id"],
                    "decision": decision["decision"],
                    "production_graph_node_id": receipt.get("production_graph_node_id", ""),
                },
            )
            _write_state(store, project_id, state)
        return _analysis_review_response(
            project_id,
            reviewed_asset,
            decision,
            receipt,
            graph,
            idempotent_replay=False,
            graph_idempotent_replay=graph_replay,
        )

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
            existing = _core_command_receipt(state, body)
            if existing:
                return {
                    "project_id": project_id,
                    "receipt": public_receipt(existing),
                    "projection": public_projection(state),
                    "idempotent_replay": True,
                    "provider_dispatch_count": 0,
                    "remote_dispatch_count": 0,
                }
            preview = _preview_core_asset_command(state, project_id, body)
            target_relationships = _active_relationships(
                state,
                asset_id=str((preview.get("after") or {}).get("asset_id") or ""),
            )
            _remove_confirmed_relationships_from_graph(
                graph_store,
                state,
                project_id=project_id,
                relationships=[item for item in target_relationships if item.get("status") == "confirmed"],
                idempotency_key=f"scene-ownership-asset-change:{preview['command_id']}",
                stage="core_asset_command_confirm",
            )
            receipt = _apply_core_asset_command(state, project_id, body, preview)
            _expire_relationships(
                state,
                target_relationships,
                reason="endpoint_asset_changed",
            )
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
            asset_id = str((receipt.get("after") or {}).get("asset_id") or "")
            active_relationships = _active_relationships(state, asset_id=asset_id)
            _remove_confirmed_relationships_from_graph(
                graph_store,
                state,
                project_id=project_id,
                relationships=[item for item in active_relationships if item.get("status") == "confirmed"],
                idempotency_key=f"scene-ownership-asset-undo:{body.receipt_id}",
                stage="core_asset_command_undo",
            )
            undo_receipt = _apply_undo(state, receipt)
            _expire_relationships(
                state,
                active_relationships,
                reason="endpoint_asset_command_undone",
            )
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
    assets = [public_asset(asset) for asset in _analysis_assets_for_revision(state, revision_id)]
    candidate = _current_candidate(state, revision)
    relationships = _relationships_for_revision(state, revision_id)
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
        "scene_ownership_relationships": [public_relationship(item) for item in relationships],
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


def current_script_revision_binding(store: RuntimeStore, project_id: str) -> dict[str, str]:
    revision = _current_revision(_load_state(store, project_id))
    if not revision:
        return {"revision_id": "", "source_digest": ""}
    return {
        "revision_id": str(revision.get("revision_id") or ""),
        "source_digest": str(revision.get("source_digest") or ""),
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
        "status": str(candidate.get("status") or "candidate"),
        "created_at": str(candidate.get("created_at") or ""),
        "expired_at": str(candidate.get("expired_at") or ""),
        "superseded_by_revision_id": str(candidate.get("superseded_by_revision_id") or ""),
        "named_character_count": len(candidate.get("named_characters") or []),
        "main_scene_count": len(candidate.get("main_scenes") or []),
        "style": str(candidate.get("style") or ""),
        "genre": str(candidate.get("genre") or ""),
        "tone": str(candidate.get("tone") or ""),
        "actions": [str(item)[:240] for item in candidate.get("actions", [])[:20]],
        "events": [str(item)[:240] for item in candidate.get("events", [])[:20]],
        "beats_count": len(candidate.get("beats") or []),
        "missing_slots": [str(item) for item in candidate.get("missing_slots", [])[:10]],
        "extraction_notes": [str(item)[:600] for item in candidate.get("extraction_notes", [])[:20]],
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
        "evidence_status": str(asset.get("evidence_status") or "model_inferred"),
        "extraction_method": str(asset.get("extraction_method") or "unspecified_structured_analysis"),
        "uncertainty_note": str(asset.get("uncertainty_note") or ""),
        "lineage": dict(asset.get("lineage") or {}),
        "created_at": str(asset.get("created_at") or ""),
        "updated_at": str(asset.get("updated_at") or ""),
        "candidate_id": str(asset.get("candidate_id") or ""),
        "version": int(asset.get("version") or 1),
        "version_id": str(asset.get("version_id") or ""),
        "parent_version_id": str(asset.get("parent_version_id") or ""),
        "review_decision_id": str(asset.get("review_decision_id") or ""),
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
        "review_decision_id": str(receipt.get("review_decision_id") or ""),
        "asset_version_id": str(receipt.get("asset_version_id") or ""),
        "relationship_version_id": str(receipt.get("relationship_version_id") or ""),
        "production_graph_node_id": str(receipt.get("production_graph_node_id") or ""),
        "production_graph_version": int(receipt.get("production_graph_version") or 0),
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def public_review_decision(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_decision_id": str(decision.get("review_decision_id") or ""),
        "project_id": str(decision.get("project_id") or ""),
        "revision_id": str(decision.get("revision_id") or ""),
        "source_digest": str(decision.get("source_digest") or ""),
        "candidate_id": str(decision.get("candidate_id") or ""),
        "asset_id": str(decision.get("asset_id") or ""),
        "target_asset_version_id": str(decision.get("target_asset_version_id") or ""),
        "result_asset_version_id": str(decision.get("result_asset_version_id") or ""),
        "decision": str(decision.get("decision") or ""),
        "reason": str(decision.get("reason") or ""),
        "decided_at": str(decision.get("decided_at") or ""),
        "production_graph_node_id": str(decision.get("production_graph_node_id") or ""),
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def public_relationship(relationship: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": str(relationship.get("artifact_type") or "afs_scene_ownership_relationship"),
        "schema_version": str(relationship.get("schema_version") or SCENE_OWNERSHIP_SCHEMA_VERSION),
        "relationship_id": str(relationship.get("relationship_id") or ""),
        "relation_type": str(relationship.get("relation_type") or ""),
        "project_id": str(relationship.get("project_id") or ""),
        "revision_id": str(relationship.get("revision_id") or ""),
        "source_digest": str(relationship.get("source_digest") or ""),
        "source_candidate_id": str(relationship.get("source_candidate_id") or ""),
        "scene_asset_id": str(relationship.get("scene_asset_id") or ""),
        "member_asset_id": str(relationship.get("member_asset_id") or ""),
        "scene_asset_version_id": str(relationship.get("scene_asset_version_id") or ""),
        "member_asset_version_id": str(relationship.get("member_asset_version_id") or ""),
        "status": str(relationship.get("status") or "missing"),
        "evidence_status": str(relationship.get("evidence_status") or "missing"),
        "evidence_spans": list(relationship.get("evidence_spans") or []),
        "extraction_method": str(relationship.get("extraction_method") or "exact_scene_block_match"),
        "lineage": dict(relationship.get("lineage") or {}),
        "version": int(relationship.get("version") or 1),
        "version_id": str(relationship.get("version_id") or ""),
        "parent_version_id": str(relationship.get("parent_version_id") or ""),
        "review_decision_id": str(relationship.get("review_decision_id") or ""),
        "created_at": str(relationship.get("created_at") or ""),
        "updated_at": str(relationship.get("updated_at") or ""),
        "expired_at": str(relationship.get("expired_at") or ""),
        "superseded_by_revision_id": str(relationship.get("superseded_by_revision_id") or ""),
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def public_relationship_review_decision(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_decision_id": str(decision.get("review_decision_id") or ""),
        "project_id": str(decision.get("project_id") or ""),
        "revision_id": str(decision.get("revision_id") or ""),
        "source_digest": str(decision.get("source_digest") or ""),
        "relationship_id": str(decision.get("relationship_id") or ""),
        "target_relationship_version_id": str(decision.get("target_relationship_version_id") or ""),
        "result_relationship_version_id": str(decision.get("result_relationship_version_id") or ""),
        "decision": str(decision.get("decision") or ""),
        "reason": str(decision.get("reason") or ""),
        "decided_at": str(decision.get("decided_at") or ""),
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _scene_ownership_review_response(
    project_id: str,
    relationship: dict[str, Any],
    decision: dict[str, Any],
    receipt: dict[str, Any],
    graph: dict[str, Any],
    *,
    idempotent_replay: bool,
    graph_idempotent_replay: bool,
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "relationship": public_relationship(relationship),
        "review_decision": public_relationship_review_decision(decision),
        "receipt": public_receipt(receipt),
        "graph": graph,
        "idempotent_replay": idempotent_replay,
        "graph_idempotent_replay": graph_idempotent_replay,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _analysis_review_response(
    project_id: str,
    asset: dict[str, Any],
    decision: dict[str, Any],
    receipt: dict[str, Any],
    graph: dict[str, Any],
    *,
    idempotent_replay: bool,
    graph_idempotent_replay: bool,
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "asset": public_asset(asset),
        "review_decision": public_review_decision(decision),
        "receipt": public_receipt(receipt),
        "graph": graph,
        "idempotent_replay": idempotent_replay,
        "graph_idempotent_replay": graph_idempotent_replay,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _analysis_review_digest(
    body: AnalysisAssetReviewRequest,
    *,
    revision_id: str,
    asset_id: str,
) -> str:
    payload = body.model_dump(mode="json", exclude={"expected_graph_version"})
    payload["route_revision_id"] = revision_id
    payload["asset_id"] = asset_id
    return canonical_digest(payload)


def _scene_ownership_review_digest(
    body: SceneOwnershipReviewRequest,
    revision_id: str,
    relationship_id: str,
) -> str:
    payload = body.model_dump(mode="json", exclude={"expected_graph_version"})
    payload["route_revision_id"] = revision_id
    payload["relationship_id"] = relationship_id
    return canonical_digest(payload)


def _relationship_review_receipt_for_key(state: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
    for receipt in (state.get("relationship_review_receipts") or {}).values():
        if receipt.get("idempotency_key") == idempotency_key:
            return dict(receipt)
    return {}


def _require_reviewable_relationship(
    state: dict[str, Any],
    relationship: dict[str, Any],
    *,
    relationship_id: str,
    body: SceneOwnershipReviewRequest,
    project_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if (
        not relationship
        or relationship.get("relationship_id") != relationship_id
        or relationship.get("project_id") != project_id
        or relationship.get("revision_id") != body.revision_id
        or relationship.get("source_digest") != body.source_digest
    ):
        raise _contract_error(
            "scene_ownership_relationship_not_found",
            "Relationship does not belong to this exact project and script revision.",
            project_id=project_id,
            stage="scene_ownership_review",
            status_code=404,
        )
    if relationship.get("status") == "missing" or relationship.get("evidence_status") != "extracted_from_text":
        if body.decision == "confirm":
            raise _contract_error(
                "scene_ownership_evidence_missing",
                "A scene relationship cannot be confirmed without exact source-text evidence.",
                project_id=project_id,
                stage="scene_ownership_review",
                status_code=409,
            )
    if relationship.get("status") not in {"candidate", "missing"}:
        raise _contract_error(
            "scene_ownership_relationship_already_reviewed",
            "Relationship has already reached a final or expired review state.",
            project_id=project_id,
            stage="scene_ownership_review",
            status_code=409,
        )
    if (
        int(relationship.get("version") or 1) != body.expected_relationship_version
        or str(relationship.get("version_id") or "") != body.relationship_version_id
    ):
        raise _contract_error(
            "scene_ownership_relationship_version_conflict",
            "Relationship changed before this review decision was committed.",
            project_id=project_id,
            stage="scene_ownership_review",
            status_code=409,
        )
    scene = dict((state.get("assets") or {}).get(relationship.get("scene_asset_id")) or {})
    member = dict((state.get("assets") or {}).get(relationship.get("member_asset_id")) or {})
    for endpoint, expected_type, version_field in (
        (scene, "main_scene", "scene_asset_version_id"),
        (member, None, "member_asset_version_id"),
    ):
        if (
            not endpoint
            or endpoint.get("project_id") != project_id
            or endpoint.get("revision_id") != body.revision_id
            or endpoint.get("source_digest") != body.source_digest
            or endpoint.get("status") != "confirmed"
            or endpoint.get("version_id") != relationship.get(version_field)
            or (expected_type and endpoint.get("asset_type") != expected_type)
        ):
            raise _contract_error(
                "scene_ownership_endpoint_not_authoritative",
                "Both relationship endpoints must be current confirmed assets for the exact revision.",
                project_id=project_id,
                stage="scene_ownership_review",
                status_code=409,
            )
    if member.get("asset_type") not in {"character", "prop"}:
        raise _contract_error(
            "scene_ownership_endpoint_type_invalid",
            "Scene ownership members must be character or prop assets.",
            project_id=project_id,
            stage="scene_ownership_review",
            status_code=409,
        )
    return scene, member


def _graph_node_for_authoritative_asset(asset: dict[str, Any], revision: dict[str, Any]) -> dict[str, Any]:
    asset_type = str(asset.get("asset_type") or "")
    category = "scene" if asset_type == "main_scene" else asset_type
    return {
        "type": "node_upserted",
        "node": {
            "node_id": str(asset["asset_id"]),
            "category": category,
            "metadata": {
                "kind": "script_core_asset",
                "asset_type": asset_type,
                "display_name": asset.get("display_name") or asset.get("name") or "",
                "source_revision_id": revision["revision_id"],
                "source_digest": revision["source_digest"],
                "asset_version_id": asset["version_id"],
                "lineage": dict(asset.get("lineage") or {}),
            },
        },
    }


def _scene_ownership_confirmation_events(
    graph: dict[str, Any],
    revision: dict[str, Any],
    scene: dict[str, Any],
    member: dict[str, Any],
    relationship: dict[str, Any],
    *,
    project_id: str,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for endpoint in (scene, member):
        node_id = str(endpoint["asset_id"])
        node = dict((graph.get("nodes") or {}).get(node_id) or {})
        if not node:
            events.append(_graph_node_for_authoritative_asset(endpoint, revision))
            continue
        metadata = dict(node.get("metadata") or {})
        if node.get("state") != "active" or metadata.get("asset_version_id") != endpoint.get("version_id"):
            raise _contract_error(
                "scene_ownership_endpoint_graph_mismatch",
                "Confirmed relationship endpoint is not the current active Production Graph asset node.",
                project_id=project_id,
                stage="scene_ownership_review",
                status_code=409,
            )
    events.append(
        {
            "type": "relation_upserted",
            "from_id": scene["asset_id"],
            "to_id": member["asset_id"],
            "relation_type": relationship["relation_type"],
        }
    )
    return events


def _reviewed_relationship_version(
    relationship: dict[str, Any],
    *,
    body: SceneOwnershipReviewRequest,
    semantic_digest: str,
    decided_at: str,
) -> dict[str, Any]:
    return _new_relationship_version(
        {
            **relationship,
            "status": "confirmed" if body.decision == "confirm" else "rejected",
            "review_decision_id": f"relreview_{semantic_digest[:20]}",
            "updated_at": decided_at,
        },
        parent=relationship,
    )


def _apply_scene_ownership_review(
    state: dict[str, Any],
    *,
    project_id: str,
    relationship: dict[str, Any],
    reviewed_relationship: dict[str, Any],
    body: SceneOwnershipReviewRequest,
    semantic_digest: str,
    graph: dict[str, Any],
    graph_idempotent_replay: bool,
    decided_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    decision_id = f"relreview_{semantic_digest[:20]}"
    result_status = "confirmed" if body.decision == "confirm" else "rejected"
    decision = {
        "review_decision_id": decision_id,
        "project_id": project_id,
        "revision_id": body.revision_id,
        "source_digest": body.source_digest,
        "relationship_id": relationship["relationship_id"],
        "target_relationship_version_id": relationship["version_id"],
        "result_relationship_version_id": reviewed_relationship["version_id"],
        "decision": result_status,
        "reason": str(body.reason or ""),
        "decided_at": decided_at,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    receipt_id = f"receipt_{_sha256_json({'project_id': project_id, 'key': body.idempotency_key, 'semantic': semantic_digest})[:20]}"
    receipt = {
        "receipt_id": receipt_id,
        "command_id": f"relreviewcmd_{semantic_digest[:20]}",
        "command_type": f"scene_ownership.{body.decision}",
        "status": "executed",
        "summary": f"Scene ownership review recorded as {result_status}.",
        "executed_at": decided_at,
        "project_id": project_id,
        "revision_id": body.revision_id,
        "source_digest": body.source_digest,
        "semantic_digest": semantic_digest,
        "idempotency_key": body.idempotency_key,
        "review_decision_id": decision_id,
        "relationship_version_id": reviewed_relationship["version_id"],
        "affected_asset_ids": [relationship["scene_asset_id"], relationship["member_asset_id"]],
        "production_graph_node_id": relationship["scene_asset_id"] if body.decision == "confirm" else "",
        "production_graph_version": int(graph.get("version") or 0),
        "production_graph_digest": str(graph.get("graph_digest") or ""),
        "graph_idempotent_replay": graph_idempotent_replay,
        "undo_available": False,
        "storyboard_write": False,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    state.setdefault("relationships", {})[relationship["relationship_id"]] = reviewed_relationship
    _record_relationship_version(state, reviewed_relationship)
    state.setdefault("relationship_review_decisions", {})[decision_id] = decision
    state.setdefault("relationship_review_receipts", {})[receipt_id] = receipt
    reject_unsafe_payload(decision)
    reject_unsafe_payload(receipt)
    return decision, receipt


def _review_receipt_for_key(state: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
    for receipt in (state.get("review_receipts") or {}).values():
        if receipt.get("idempotency_key") == idempotency_key:
            return dict(receipt)
    return {}


def _require_reviewable_asset(
    asset: dict[str, Any],
    body: AnalysisAssetReviewRequest,
    *,
    project_id: str,
    asset_id: str,
) -> None:
    if (
        not asset
        or asset.get("asset_id") != asset_id
        or asset.get("project_id") != project_id
        or asset.get("revision_id") != body.revision_id
        or asset.get("source_digest") != body.source_digest
        or asset.get("candidate_id") != body.candidate_id
        or asset.get("source_mode") != "analysis_candidate"
    ):
        raise _contract_error(
            "analysis_asset_not_found",
            "Analysis asset does not belong to this exact candidate and script revision.",
            project_id=project_id,
            stage="analysis_asset_review",
            status_code=404,
        )
    if asset.get("status") == "expired":
        raise _contract_error(
            "analysis_asset_expired",
            "Expired analysis assets cannot be reviewed.",
            project_id=project_id,
            stage="analysis_asset_review",
            status_code=409,
        )
    if asset.get("status") not in {"candidate", "modified"}:
        raise _contract_error(
            "analysis_asset_already_reviewed",
            "Analysis asset has already reached a final review state.",
            project_id=project_id,
            stage="analysis_asset_review",
            status_code=409,
        )
    if (
        int(asset.get("version") or 1) != body.expected_asset_version
        or str(asset.get("version_id") or "") != body.asset_version_id
    ):
        raise _contract_error(
            "analysis_asset_version_conflict",
            "Analysis asset changed before this review decision was committed.",
            project_id=project_id,
            stage="analysis_asset_review",
            status_code=409,
            details={"expected_asset_version": body.expected_asset_version},
        )


def _analysis_confirmation_events(
    revision: dict[str, Any],
    candidate: dict[str, Any],
    asset: dict[str, Any],
    semantic_digest: str,
) -> list[dict[str, Any]]:
    revision_node_id = f"script-revision:{revision['revision_id']}"
    asset_node_id = str(asset["asset_id"])
    return [
        {
            "type": "node_upserted",
            "node": {
                "node_id": revision_node_id,
                "category": "script_revision",
                "metadata": {
                    "source_kind": revision["source_kind"],
                    "source_digest": revision["source_digest"],
                    "source_length": revision["source_length"],
                    "revision_id": revision["revision_id"],
                },
            },
        },
        {
            "type": "node_upserted",
            "node": {
                "node_id": asset_node_id,
                "category": "character" if asset.get("asset_type") == "character" else "scene",
                "metadata": {
                    "kind": "script_core_asset",
                    "asset_type": asset["asset_type"],
                    "display_name": asset.get("display_name") or asset.get("name") or "",
                    "source_revision_id": revision["revision_id"],
                    "source_digest": revision["source_digest"],
                    "candidate_id": candidate["candidate_id"],
                    "asset_version_id": asset["version_id"],
                    "evidence_span_count": len(asset.get("evidence_spans") or []),
                    "review_semantic_digest": semantic_digest,
                    "lineage": dict(asset.get("lineage") or {}),
                },
            },
        },
        {
            "type": "relation_upserted",
            "from_id": revision_node_id,
            "to_id": asset_node_id,
            "relation_type": "analysis_confirmed",
        },
    ]


def _apply_analysis_review(
    state: dict[str, Any],
    *,
    project_id: str,
    revision: dict[str, Any],
    candidate: dict[str, Any],
    asset: dict[str, Any],
    body: AnalysisAssetReviewRequest,
    semantic_digest: str,
    graph: dict[str, Any],
    graph_idempotent_replay: bool,
    reviewed_asset: dict[str, Any],
    decided_at: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    decision_id = f"review_{semantic_digest[:20]}"
    result_status = "confirmed" if body.decision == "confirm" else "rejected"
    production_graph_node_id = str(asset["asset_id"]) if body.decision == "confirm" else ""
    decision = {
        "review_decision_id": decision_id,
        "project_id": project_id,
        "revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "candidate_id": candidate["candidate_id"],
        "asset_id": asset["asset_id"],
        "target_asset_version_id": asset["version_id"],
        "result_asset_version_id": reviewed_asset["version_id"],
        "decision": result_status,
        "reason": str(body.reason or ""),
        "decided_at": decided_at,
        "production_graph_node_id": production_graph_node_id,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    receipt_id = f"receipt_{_sha256_json({'project_id': project_id, 'key': body.idempotency_key, 'semantic': semantic_digest})[:20]}"
    receipt = {
        "receipt_id": receipt_id,
        "command_id": f"reviewcmd_{semantic_digest[:20]}",
        "command_type": f"analysis_asset.{body.decision}",
        "status": "executed",
        "summary": f"Analysis asset review recorded as {result_status}.",
        "executed_at": decided_at,
        "project_id": project_id,
        "revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "semantic_digest": semantic_digest,
        "idempotency_key": body.idempotency_key,
        "review_decision_id": decision_id,
        "asset_version_id": reviewed_asset["version_id"],
        "affected_asset_ids": [asset["asset_id"]],
        "production_graph_node_id": production_graph_node_id,
        "production_graph_version": int(graph.get("version") or 0),
        "production_graph_digest": str(graph.get("graph_digest") or ""),
        "graph_idempotent_replay": graph_idempotent_replay,
        "undo_available": False,
        "storyboard_write": False,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    state.setdefault("assets", {})[asset["asset_id"]] = reviewed_asset
    _record_asset_version(state, reviewed_asset)
    state.setdefault("review_decisions", {})[decision_id] = decision
    state.setdefault("review_receipts", {})[receipt_id] = receipt
    candidate_state = _candidate_review_state(state, candidate["candidate_id"])
    state["analysis_candidates"][candidate["candidate_id"]]["status"] = candidate_state
    revision_assets = _analysis_assets_for_revision(state, revision["revision_id"])
    state["revisions"][revision["revision_id"]]["analysis_state"] = _analysis_state_for_assets(revision_assets)
    reject_unsafe_payload(decision)
    reject_unsafe_payload(receipt)
    return decision, reviewed_asset, receipt


def _reviewed_asset_version(
    asset: dict[str, Any],
    *,
    body: AnalysisAssetReviewRequest,
    semantic_digest: str,
    decided_at: str,
) -> dict[str, Any]:
    result_status = "confirmed" if body.decision == "confirm" else "rejected"
    return _new_asset_version(
        {
            **asset,
            "status": result_status,
            "review_decision_id": f"review_{semantic_digest[:20]}",
            "updated_at": decided_at,
        },
        parent=asset,
    )


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
    payload["status"] = "candidate"
    payload["project_id"] = project_id
    payload["revision_id"] = revision["revision_id"]
    payload["source_digest"] = revision["source_digest"]
    reject_unsafe_payload(payload)
    return payload


def _apply_structured_analysis_candidate(
    state: dict[str, Any],
    *,
    project_id: str,
    revision_id: str,
    body: StructuredAnalysisCandidateRequest,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[str], list[str]]:
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
    existing_candidate = dict(
        (state.get("analysis_candidates") or {}).get(candidate["candidate_id"]) or {}
    )
    if (
        existing_candidate
        and str(revision.get("analysis_candidate_id") or "") == candidate["candidate_id"]
    ):
        existing_assets = _analysis_assets_for_revision(state, revision_id)
        return (
            revision,
            existing_candidate,
            existing_assets,
            [],
            [str(asset["asset_id"]) for asset in existing_assets],
        )
    previous_assets = dict(state.get("assets") or {})
    assets, affected, preserved = _assets_from_candidate(project_id, revision, candidate, previous_assets)
    for asset in assets:
        state["assets"][asset["asset_id"]] = asset
        _record_asset_version(state, asset)
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
            "missing_slots": list(body.missing_slots),
        },
    )
    return revision, candidate, assets, affected, preserved


def _require_current_revision_for_extraction(
    state: dict[str, Any],
    *,
    project_id: str,
    revision_id: str,
) -> dict[str, Any]:
    revision = dict((state.get("revisions") or {}).get(revision_id) or {})
    if not revision:
        raise _contract_error(
            "script_revision_not_found",
            "Script revision does not exist in this project truth store.",
            project_id=project_id,
            stage="analysis_candidate_extract",
            status_code=404,
        )
    if str(state.get("current_revision_id") or "") != revision_id:
        raise _contract_error(
            "current_revision_mismatch",
            "Only the selected current script revision can be extracted.",
            project_id=project_id,
            stage="analysis_candidate_extract",
            status_code=409,
        )
    return revision


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
            candidate_id=str(candidate["candidate_id"]),
            asset_type="character",
            label=str(item["display_name"]),
            aliases=[str(value) for value in item.get("aliases", [])],
            pronoun_links=[str(value) for value in item.get("pronoun_links", [])],
            evidence_spans=item.get("evidence_spans") or [],
            confidence=float(item.get("confidence") or 0.0),
            requested_status=str(item.get("status") or "candidate"),
            evidence_status=str(item.get("evidence_status") or "model_inferred"),
            extraction_method=str(item.get("extraction_method") or "unspecified_structured_analysis"),
            uncertainty_note=str(item.get("uncertainty_note") or ""),
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
            candidate_id=str(candidate["candidate_id"]),
            asset_type="main_scene",
            label=str(item["name"]),
            aliases=[],
            pronoun_links=[],
            evidence_spans=item.get("evidence_spans") or [],
            confidence=float(item.get("confidence") or 0.0),
            requested_status=str(item.get("status") or "candidate"),
            evidence_status=str(item.get("evidence_status") or "model_inferred"),
            extraction_method=str(item.get("extraction_method") or "unspecified_structured_analysis"),
            uncertainty_note=str(item.get("uncertainty_note") or ""),
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
    candidate_id: str,
    asset_type: str,
    label: str,
    aliases: list[str],
    pronoun_links: list[str],
    evidence_spans: list[dict[str, Any]],
    confidence: float,
    requested_status: str,
    evidence_status: str,
    extraction_method: str,
    uncertainty_note: str,
    created_at: str,
) -> dict[str, Any]:
    status = "candidate"
    quote_digest = _sha256_json([span.get("quote", "") for span in evidence_spans])
    key = _normal_key(f"{asset_type}:{label}:{quote_digest}")
    asset_id = f"{'char' if asset_type == 'character' else 'scene'}_{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}"
    asset = {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "source_mode": source_mode,
        "status": status,
        "candidate_id": candidate_id,
        "project_id": project_id,
        "revision_id": revision_id,
        "source_digest": source_digest,
        "display_name": _clean_label(label),
        "name": _clean_label(label),
        "aliases": _clean_text_list(aliases),
        "pronoun_links": _clean_text_list(pronoun_links),
        "evidence_spans": evidence_spans,
        "confidence": confidence,
        "evidence_status": evidence_status,
        "extraction_method": extraction_method,
        "uncertainty_note": uncertainty_note,
        "lineage": {
            "source_revision_id": revision_id,
            "source_digest": source_digest,
            "candidate_quote_digest": quote_digest,
            "preservation_key": key,
            "auto_asset_scope": "character_or_main_scene_only",
            "evidence_status": evidence_status,
            "extraction_method": extraction_method,
        },
        "created_at": created_at,
        "updated_at": created_at,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    asset = _new_asset_version(asset)
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
    if (
        previous.get("revision_id") == asset.get("revision_id")
        and previous.get("candidate_id") == asset.get("candidate_id")
        and _asset_review_content(previous) == _asset_review_content(asset)
    ):
        preserved.append(str(previous["asset_id"]))
        return dict(previous)
    merged = _new_asset_version(
        {
            **asset,
            "asset_id": previous["asset_id"],
            "created_at": previous.get("created_at") or asset["created_at"],
        },
        parent=previous,
    )
    if previous.get("status") == asset.get("status") and previous.get("revision_id") == asset.get("revision_id"):
        preserved.append(str(previous["asset_id"]))
    else:
        affected.append(str(previous["asset_id"]))
    return merged


def _extract_scene_ownership(
    state: dict[str, Any],
    revision: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    revision_id = str(revision["revision_id"])
    source_text = str(revision.get("source_text") or "")
    assets = [
        item
        for item in _analysis_assets_for_revision(state, revision_id)
        if item.get("status") in {"candidate", "modified", "confirmed", "pending_confirmation"}
    ]
    scenes = sorted(
        (item for item in assets if item.get("asset_type") == "main_scene"),
        key=_scene_start,
    )
    members = [item for item in assets if item.get("asset_type") in {"character", "prop"}]
    existing = dict(state.get("relationships") or {})
    relationships: list[dict[str, Any]] = []
    affected: list[str] = []
    preserved: list[str] = []
    now = _server_now()
    for index, scene in enumerate(scenes):
        scene_start = _scene_start(scene)
        end = _scene_start(scenes[index + 1]) if index + 1 < len(scenes) else len(source_text)
        start = _scene_content_start(source_text, scene, end)
        if scene_start < 0 or end <= start:
            continue
        for member in members:
            evidence_spans = _member_spans_in_scene_block(source_text, start, end, member)
            relation_type = "scene_cast" if member.get("asset_type") == "character" else "scene_core_prop"
            identity = {
                "project_id": revision["project_id"],
                "revision_id": revision_id,
                "relation_type": relation_type,
                "scene_asset_id": scene["asset_id"],
                "member_asset_id": member["asset_id"],
            }
            relationship_id = f"rel_{_sha256_json(identity)[:20]}"
            status = "candidate" if evidence_spans else "missing"
            relationship = {
                "artifact_type": "afs_scene_ownership_relationship",
                "schema_version": SCENE_OWNERSHIP_SCHEMA_VERSION,
                "relationship_id": relationship_id,
                "relation_type": relation_type,
                "project_id": revision["project_id"],
                "revision_id": revision_id,
                "source_digest": revision["source_digest"],
                "source_candidate_id": str(revision.get("analysis_candidate_id") or ""),
                "scene_asset_id": scene["asset_id"],
                "member_asset_id": member["asset_id"],
                "scene_asset_version_id": scene["version_id"],
                "member_asset_version_id": member["version_id"],
                "status": status,
                "evidence_status": "extracted_from_text" if evidence_spans else "missing",
                "evidence_spans": evidence_spans,
                "extraction_method": "exact_scene_block_match",
                "lineage": {
                    "source_revision_id": revision_id,
                    "source_digest": revision["source_digest"],
                    "source_candidate_id": str(revision.get("analysis_candidate_id") or ""),
                    "scene_asset_id": scene["asset_id"],
                    "scene_asset_version_id": scene["version_id"],
                    "member_asset_id": member["asset_id"],
                    "member_asset_version_id": member["version_id"],
                    "evidence_policy": "exact_member_label_or_alias_within_confirmed_scene_span",
                    "extraction_method": "exact_scene_block_match",
                },
                "created_at": now,
                "updated_at": now,
                "provider_dispatch_count": 0,
                "remote_dispatch_count": 0,
            }
            prior = dict(existing.get(relationship_id) or {})
            if prior and _relationship_extraction_content(prior) == _relationship_extraction_content(relationship):
                relationship = prior
                preserved.append(relationship_id)
            else:
                relationship = _new_relationship_version(relationship, parent=prior or None)
                affected.append(relationship_id)
            state.setdefault("relationships", {})[relationship_id] = relationship
            _record_relationship_version(state, relationship)
            relationships.append(relationship)
    return relationships, _unique(affected), _unique(preserved)


def _scene_start(scene: dict[str, Any]) -> int:
    starts = [
        int(span.get("start"))
        for span in (scene.get("evidence_spans") or [])
        if isinstance(span, dict) and isinstance(span.get("start"), int)
    ]
    return min(starts) if starts else -1


def _scene_content_start(source_text: str, scene: dict[str, Any], scene_end: int) -> int:
    evidence_ends = [
        int(span.get("end"))
        for span in (scene.get("evidence_spans") or [])
        if isinstance(span, dict) and isinstance(span.get("end"), int)
    ]
    if not evidence_ends:
        return scene_end
    heading_evidence_end = max(evidence_ends)
    line_end = source_text.find("\n", heading_evidence_end, scene_end)
    return scene_end if line_end < 0 else line_end + 1


def _member_spans_in_scene_block(
    source_text: str,
    start: int,
    end: int,
    member: dict[str, Any],
) -> list[dict[str, Any]]:
    labels = _clean_text_list(
        [
            str(member.get("display_name") or member.get("name") or ""),
            *[str(item) for item in (member.get("aliases") or [])],
        ]
    )
    spans: list[dict[str, Any]] = []
    block = source_text[start:end]
    seen: set[tuple[int, int]] = set()
    for label in labels:
        pattern = re.compile(rf"(?<!\w){re.escape(label)}(?!\w)", re.IGNORECASE)
        for match in pattern.finditer(block):
            absolute_start = start + match.start()
            absolute_end = start + match.end()
            identity = (absolute_start, absolute_end)
            if identity in seen:
                continue
            seen.add(identity)
            spans.append(
                {
                    "start": absolute_start,
                    "end": absolute_end,
                    "quote": source_text[absolute_start:absolute_end],
                }
            )
    return sorted(spans, key=lambda item: (item["start"], item["end"]))[:12]


def _relationship_extraction_content(relationship: dict[str, Any]) -> dict[str, Any]:
    return {
        "relation_type": relationship.get("relation_type"),
        "project_id": relationship.get("project_id"),
        "revision_id": relationship.get("revision_id"),
        "source_digest": relationship.get("source_digest"),
        "source_candidate_id": relationship.get("source_candidate_id"),
        "scene_asset_id": relationship.get("scene_asset_id"),
        "member_asset_id": relationship.get("member_asset_id"),
        "scene_asset_version_id": relationship.get("scene_asset_version_id"),
        "member_asset_version_id": relationship.get("member_asset_version_id"),
        "evidence_status": relationship.get("evidence_status"),
        "evidence_spans": list(relationship.get("evidence_spans") or []),
        "extraction_method": relationship.get("extraction_method"),
    }


def _new_relationship_version(
    relationship: dict[str, Any],
    *,
    parent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(relationship)
    payload.pop("version", None)
    payload.pop("version_id", None)
    payload.pop("parent_version_id", None)
    version = int((parent or {}).get("version") or 0) + 1
    parent_version_id = str((parent or {}).get("version_id") or "")
    identity = {
        "relationship_id": payload.get("relationship_id"),
        "version": version,
        "parent_version_id": parent_version_id,
        "content": {
            **_relationship_extraction_content(payload),
            "status": payload.get("status"),
            "review_decision_id": payload.get("review_decision_id", ""),
        },
    }
    payload["version"] = version
    payload["parent_version_id"] = parent_version_id
    payload["version_id"] = f"relver_{_sha256_json(identity)[:20]}"
    reject_unsafe_payload(payload)
    return payload


def _record_relationship_version(state: dict[str, Any], relationship: dict[str, Any]) -> None:
    relationship_id = str(relationship.get("relationship_id") or "")
    version_id = str(relationship.get("version_id") or "")
    if not relationship_id or not version_id:
        return
    history = state.setdefault("relationship_versions", {}).setdefault(relationship_id, [])
    if not any(str(item.get("version_id") or "") == version_id for item in history):
        history.append(dict(relationship))


def _relationship_version_by_id(
    state: dict[str, Any],
    relationship_id: str,
    version_id: str,
) -> dict[str, Any]:
    for item in (state.get("relationship_versions") or {}).get(relationship_id, []):
        if str(item.get("version_id") or "") == version_id:
            return dict(item)
    current = dict((state.get("relationships") or {}).get(relationship_id) or {})
    return current if str(current.get("version_id") or "") == version_id else {}


def _relationships_for_revision(state: dict[str, Any], revision_id: str) -> list[dict[str, Any]]:
    return sorted(
        (
            dict(item)
            for item in (state.get("relationships") or {}).values()
            if str(item.get("revision_id") or "") == revision_id
        ),
        key=lambda item: (str(item.get("created_at") or ""), str(item.get("relationship_id") or "")),
    )


def _core_command_digest(body: CoreAssetCommandRequest) -> str:
    return _sha256_json(body.model_dump(mode="json"))


def _core_command_id(body: CoreAssetCommandRequest) -> str:
    return f"cmd_{_core_command_digest(body)[:16]}"


def _core_command_receipt(state: dict[str, Any], body: CoreAssetCommandRequest) -> dict[str, Any]:
    semantic_digest = _core_command_digest(body)
    command_id = _core_command_id(body)
    for raw in (state.get("receipts") or {}).values():
        receipt = dict(raw or {})
        if body.idempotency_key and receipt.get("idempotency_key") == body.idempotency_key:
            if receipt.get("semantic_digest") != semantic_digest:
                raise _contract_error(
                    "core_asset_idempotency_conflict",
                    "Idempotency key was already used for a different core asset command.",
                    project_id=str(body.project_id),
                    stage="core_asset_command_confirm",
                    status_code=409,
                )
            return receipt
        if receipt.get("command_id") == command_id:
            return receipt
    return {}


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
            "candidate_id": "",
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
        after = _new_asset_version(after)
    else:
        before = _require_asset_for_command(assets, project_id, body.revision_id, target_id, body.command_type)
        if body.expected_asset_version is not None and int(before.get("version") or 1) != body.expected_asset_version:
            raise _contract_error(
                "core_asset_version_conflict",
                "Core asset changed before this command was committed.",
                project_id=project_id,
                stage="core_asset_command_preview",
                status_code=409,
                details={"expected_asset_version": body.expected_asset_version},
            )
        after = _mutated_asset_snapshot(before, body, now)
    affected = [str(after["asset_id"])]
    return {
        "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
        "command_id": _core_command_id(body),
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
    _record_asset_version(state, assets[after["asset_id"]])
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
        "semantic_digest": _core_command_digest(body),
        "idempotency_key": str(body.idempotency_key or ""),
        "before": preview.get("before"),
        "after": preview.get("after"),
        "affected_asset_ids": preview["affected_asset_ids"],
        "asset_version_id": str(after.get("version_id") or ""),
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
    current = dict(assets.get(asset_id) or receipt.get("after") or {})
    if before:
        restored = _new_asset_version(
            {
                **dict(before),
                "asset_id": asset_id,
                "updated_at": _server_now(),
            },
            parent=current,
        )
        assets[asset_id] = restored
    elif asset_id:
        after = dict(receipt.get("after") or {})
        after["status"] = "undone"
        after["updated_at"] = _server_now()
        assets[asset_id] = _new_asset_version(after, parent=current)
    if asset_id:
        _record_asset_version(state, assets[asset_id])
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
        "after": public_asset(assets[asset_id]) if asset_id else before,
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
        previous_label = _clean_label(before.get("display_name") or before.get("name"))
        label = _clean_label(body.patch.get("display_name") or body.patch.get("name") or after.get("display_name"))
        if not label:
            raise ValueError("edited asset label cannot be empty")
        after["display_name"] = label
        after["name"] = label
        evidence_quotes = {
            _clean_label(span.get("quote"))
            for span in (before.get("evidence_spans") or [])
            if isinstance(span, dict) and _clean_label(span.get("quote"))
        }
        if label != previous_label and label not in evidence_quotes:
            after["evidence_status"] = "human_edited"
            after["extraction_method"] = "human_edit"
            after["uncertainty_note"] = (
                "Human-edited label is not an exact source quote; retained spans are contextual evidence."
            )
            lineage = dict(after.get("lineage") or {})
            lineage["evidence_status"] = "human_edited"
            lineage["extraction_method"] = "human_edit"
            after["lineage"] = lineage
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
    if body.command_type == "edit_asset" and before.get("source_mode") == "analysis_candidate":
        after["status"] = "modified"
        after.pop("review_decision_id", None)
    after["provider_dispatch_count"] = 0
    after["remote_dispatch_count"] = 0
    if before.get("status") in ACTIVE_STATUSES:
        after["last_active_status"] = before.get("status")
    after = _new_asset_version(after, parent=before)
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
    if any(item.get("status") in {"candidate", "modified", "pending_confirmation"} for item in active):
        return "pending_confirmation"
    if all(item.get("status") == "rejected" for item in active):
        return "rejected"
    if all(item.get("status") in {"confirmed", "rejected"} for item in active):
        return "confirmed"
    if all(item.get("status") == "expired" for item in active):
        return "expired"
    return "pending_confirmation"


def _candidate_review_state(state: dict[str, Any], candidate_id: str) -> str:
    assets = [
        item
        for item in (state.get("assets") or {}).values()
        if item.get("candidate_id") == candidate_id and item.get("status") != "undone"
    ]
    if not assets:
        return "candidate"
    statuses = {str(item.get("status") or "") for item in assets}
    if statuses == {"expired"}:
        return "expired"
    if statuses <= {"confirmed", "rejected"}:
        return "reviewed"
    if statuses & {"confirmed", "rejected"}:
        return "partially_reviewed"
    return "candidate"


def _current_revision(state: dict[str, Any]) -> dict[str, Any]:
    revision_id = str(state.get("current_revision_id") or "")
    return dict((state.get("revisions") or {}).get(revision_id) or {})


def _current_candidate(state: dict[str, Any], revision: dict[str, Any]) -> dict[str, Any]:
    candidate_id = str(revision.get("analysis_candidate_id") or "")
    return dict((state.get("analysis_candidates") or {}).get(candidate_id) or {})


def _asset_belongs_to_revision(asset: dict[str, Any], revision_id: str) -> bool:
    return str(asset.get("revision_id") or "") == revision_id and str(asset.get("status") or "") != "undone"


def _analysis_assets_for_revision(state: dict[str, Any], revision_id: str) -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for history in (state.get("asset_versions") or {}).values():
        if not isinstance(history, list):
            continue
        for raw in history:
            item = dict(raw or {})
            if not _asset_belongs_to_revision(item, revision_id):
                continue
            asset_id = str(item.get("asset_id") or "")
            current = selected.get(asset_id)
            if asset_id and (not current or int(item.get("version") or 1) > int(current.get("version") or 1)):
                selected[asset_id] = item
    for raw in (state.get("assets") or {}).values():
        item = dict(raw or {})
        if not _asset_belongs_to_revision(item, revision_id):
            continue
        asset_id = str(item.get("asset_id") or "")
        current = selected.get(asset_id)
        if asset_id and (not current or int(item.get("version") or 1) >= int(current.get("version") or 1)):
            selected[asset_id] = item
    return sorted(selected.values(), key=lambda item: (str(item.get("created_at") or ""), str(item.get("asset_id") or "")))


def _asset_version_by_id(state: dict[str, Any], asset_id: str, version_id: str) -> dict[str, Any]:
    for item in (state.get("asset_versions") or {}).get(asset_id, []):
        if str(item.get("version_id") or "") == version_id:
            return dict(item)
    current = dict((state.get("assets") or {}).get(asset_id) or {})
    return current if str(current.get("version_id") or "") == version_id else {}


def _record_asset_version(state: dict[str, Any], asset: dict[str, Any]) -> None:
    asset_id = str(asset.get("asset_id") or "")
    version_id = str(asset.get("version_id") or "")
    if not asset_id or not version_id:
        return
    history = state.setdefault("asset_versions", {}).setdefault(asset_id, [])
    if not any(str(item.get("version_id") or "") == version_id for item in history):
        history.append(dict(asset))


def _new_asset_version(asset: dict[str, Any], *, parent: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(asset)
    payload.pop("version", None)
    payload.pop("version_id", None)
    payload.pop("parent_version_id", None)
    version = int((parent or {}).get("version") or 0) + 1
    parent_version_id = str((parent or {}).get("version_id") or "")
    identity = {
        "asset_id": payload.get("asset_id"),
        "revision_id": payload.get("revision_id"),
        "source_digest": payload.get("source_digest"),
        "candidate_id": payload.get("candidate_id"),
        "version": version,
        "parent_version_id": parent_version_id,
        "content": _asset_review_content(payload),
    }
    payload["version"] = version
    payload["parent_version_id"] = parent_version_id
    payload["version_id"] = f"assetver_{_sha256_json(identity)[:20]}"
    return payload


def _asset_review_content(asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset_type": str(asset.get("asset_type") or ""),
        "display_name": str(asset.get("display_name") or asset.get("name") or ""),
        "aliases": list(asset.get("aliases") or []),
        "pronoun_links": list(asset.get("pronoun_links") or []),
        "evidence_spans": list(asset.get("evidence_spans") or []),
        "confidence": float(asset.get("confidence") or 0.0),
        "evidence_status": str(asset.get("evidence_status") or "model_inferred"),
        "extraction_method": str(asset.get("extraction_method") or "unspecified_structured_analysis"),
        "uncertainty_note": str(asset.get("uncertainty_note") or ""),
        "status": str(asset.get("status") or ""),
    }


def _expire_open_analysis(state: dict[str, Any], *, superseded_by_revision_id: str) -> None:
    now = _server_now()
    for candidate in (state.get("analysis_candidates") or {}).values():
        if candidate.get("status") != "expired":
            candidate["status"] = "expired"
            candidate["expired_at"] = now
            candidate["superseded_by_revision_id"] = superseded_by_revision_id
    for asset_id, raw in list((state.get("assets") or {}).items()):
        asset = dict(raw or {})
        if asset.get("source_mode") != "analysis_candidate" or asset.get("status") not in {
            "candidate",
            "modified",
            "pending_confirmation",
        }:
            continue
        expired = _new_asset_version(
            {
                **asset,
                "status": "expired",
                "expired_at": now,
                "superseded_by_revision_id": superseded_by_revision_id,
                "updated_at": now,
            },
            parent=asset,
        )
        state["assets"][asset_id] = expired
        _record_asset_version(state, expired)
        revision_id = str(asset.get("revision_id") or "")
        if revision_id in (state.get("revisions") or {}):
            state["revisions"][revision_id]["analysis_state"] = "expired"
    for relationship_id, raw in list((state.get("relationships") or {}).items()):
        relationship = dict(raw or {})
        if relationship.get("status") == "expired":
            continue
        expired = _new_relationship_version(
            {
                **relationship,
                "status": "expired",
                "expired_at": now,
                "superseded_by_revision_id": superseded_by_revision_id,
                "updated_at": now,
            },
            parent=relationship,
        )
        state["relationships"][relationship_id] = expired
        _record_relationship_version(state, expired)


def _confirmed_relationships(
    state: dict[str, Any],
    *,
    asset_id: str = "",
) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in (state.get("relationships") or {}).values()
        if item.get("status") == "confirmed"
        and (
            not asset_id
            or asset_id in {str(item.get("scene_asset_id") or ""), str(item.get("member_asset_id") or "")}
        )
    ]


def _active_relationships(
    state: dict[str, Any],
    *,
    asset_id: str = "",
) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in (state.get("relationships") or {}).values()
        if item.get("status") != "expired"
        and (
            not asset_id
            or asset_id in {str(item.get("scene_asset_id") or ""), str(item.get("member_asset_id") or "")}
        )
    ]


def _remove_confirmed_relationships_from_graph(
    graph_store: ProductionGraphStore,
    state: dict[str, Any],
    *,
    project_id: str,
    relationships: list[dict[str, Any]],
    idempotency_key: str,
    stage: str,
) -> None:
    if not relationships:
        return
    ordered = sorted(relationships, key=lambda item: str(item.get("relationship_id") or ""))
    events = [
        {
            "type": "relation_removed",
            "from_id": item["scene_asset_id"],
            "to_id": item["member_asset_id"],
            "relation_type": item["relation_type"],
        }
        for item in ordered
    ]
    semantic_digest = canonical_digest(
        {
            "operation": "expire_scene_ownership",
            "relationships": [
                {
                    "relationship_id": item["relationship_id"],
                    "version_id": item["version_id"],
                    "relation_type": item["relation_type"],
                    "scene_asset_id": item["scene_asset_id"],
                    "member_asset_id": item["member_asset_id"],
                }
                for item in ordered
            ],
        }
    )
    graph = graph_store.ensure(project_id)
    try:
        graph_store.append(
            project_id,
            expected_version=int(graph.get("version") or 0),
            idempotency_key=idempotency_key,
            semantic_digest=semantic_digest,
            events=events,
        )
    except GraphIdempotencyConflict as exc:
        raise _contract_error(
            "scene_ownership_invalidation_idempotency_conflict",
            "Relationship invalidation key was already used for different endpoints.",
            project_id=project_id,
            stage=stage,
            status_code=409,
        ) from exc
    except GraphVersionConflict as exc:
        raise _contract_error(
            "production_graph_version_conflict",
            "Production Graph changed before relationship invalidation committed.",
            project_id=project_id,
            stage=stage,
            status_code=409,
        ) from exc
    except ProductionGraphError as exc:
        raise _contract_error(
            "production_graph_write_rejected",
            "Stale scene ownership could not be removed from Production Graph.",
            project_id=project_id,
            stage=stage,
            status_code=409,
        ) from exc


def _expire_relationships(
    state: dict[str, Any],
    relationships: list[dict[str, Any]],
    *,
    reason: str,
) -> None:
    now = _server_now()
    for relationship in relationships:
        relationship_id = str(relationship.get("relationship_id") or "")
        current = dict((state.get("relationships") or {}).get(relationship_id) or {})
        if not current or current.get("status") == "expired":
            continue
        expired = _new_relationship_version(
            {
                **current,
                "status": "expired",
                "expired_at": now,
                "expiration_reason": reason,
                "updated_at": now,
            },
            parent=current,
        )
        state["relationships"][relationship_id] = expired
        _record_relationship_version(state, expired)


def _invalidate_stale_relationships_after_asset_change(
    graph_store: ProductionGraphStore,
    state: dict[str, Any],
    *,
    project_id: str,
    idempotency_key: str,
    stage: str,
) -> None:
    stale: list[dict[str, Any]] = []
    for relationship in _active_relationships(state):
        scene = dict((state.get("assets") or {}).get(relationship.get("scene_asset_id")) or {})
        member = dict((state.get("assets") or {}).get(relationship.get("member_asset_id")) or {})
        if (
            scene.get("status") != "confirmed"
            or member.get("status") != "confirmed"
            or scene.get("version_id") != relationship.get("scene_asset_version_id")
            or member.get("version_id") != relationship.get("member_asset_version_id")
        ):
            stale.append(relationship)
    _remove_confirmed_relationships_from_graph(
        graph_store,
        state,
        project_id=project_id,
        relationships=[item for item in stale if item.get("status") == "confirmed"],
        idempotency_key=idempotency_key,
        stage=stage,
    )
    _expire_relationships(state, stale, reason="endpoint_asset_reextracted")


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
        "asset_versions": {},
        "review_decisions": {},
        "review_receipts": {},
        "relationships": {},
        "relationship_versions": {},
        "relationship_review_decisions": {},
        "relationship_review_receipts": {},
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
    for key in (
        "revisions",
        "analysis_candidates",
        "assets",
        "asset_versions",
        "review_decisions",
        "review_receipts",
        "relationships",
        "relationship_versions",
        "relationship_review_decisions",
        "relationship_review_receipts",
        "receipts",
    ):
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
    "ANALYSIS_REVIEW_SCHEMA_VERSION",
    "CORE_ASSET_COMMAND_SCHEMA_VERSION",
    "SCENE_OWNERSHIP_REVIEW_SCHEMA_VERSION",
    "SCENE_OWNERSHIP_SCHEMA_VERSION",
    "SCRIPT_REVISION_SCHEMA_VERSION",
    "SCRIPT_TRUTH_SCHEMA_VERSION",
    "public_projection",
    "register_runtime_script_core_truth_routes",
    "script_core_truth_projection_for_project",
)
