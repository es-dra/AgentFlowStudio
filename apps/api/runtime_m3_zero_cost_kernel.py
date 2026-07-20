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
from apps.api.runtime_dynamic_production_plan import production_plan_projection_for_project
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_script_core_truth import script_core_truth_projection_for_project
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id


M3_ZERO_COST_SCHEMA_VERSION = "afs.m3_zero_cost_kernel.v0.1"
KNOWLEDGE_PACK_SCHEMA_VERSION = "afs.knowledge_pack.v0.1"
KNOWLEDGE_ENTRY_SCHEMA_VERSION = "afs.knowledge_entry.v0.1"
CONTEXT_PACK_SCHEMA_VERSION = "afs.context_pack_manifest.v0.1"
FEEDBACK_CANDIDATE_SCHEMA_VERSION = "afs.feedback_candidate.v0.1"
PROMOTION_DECISION_SCHEMA_VERSION = "afs.promotion_decision.v0.1"
QUALITY_RUBRIC_SCHEMA_VERSION = "afs.quality_rubric.v0.1"
EVALUATION_REPORT_SCHEMA_VERSION = "afs.evaluation_report.v0.1"
M3_CONTEXT_COMMAND_SCHEMA_VERSION = "afs.m3_context_command.v0.1"
ZERO_PROVIDER_GATES = {"llm", "image", "video", "audio", "asr", "vision", "external_download"}
EVALUATOR_ROLES = {
    "story_editor",
    "director_cinematographer_editor",
    "asset_production_continuity",
    "agent_context_safety_product",
}


class ContextPackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=128)
    script_revision_id: str = Field(min_length=1, max_length=160)
    source_digest: str = Field(min_length=64, max_length=64)
    schema_version: str = Field(min_length=1, max_length=80)
    instruction: str = Field(min_length=1, max_length=1200)
    selected_node_id: str | None = Field(default=None, max_length=160)
    selected_node_type: str | None = Field(default=None, max_length=80)
    plan_id: str | None = Field(default=None, max_length=160)
    plan_digest: str | None = Field(default=None, min_length=64, max_length=64)
    requested_domains: list[str] = Field(default_factory=list, max_length=16)
    constraints: dict[str, Any] = Field(default_factory=dict)
    preferences: dict[str, Any] = Field(default_factory=dict)
    upstream_refs: list[str] = Field(default_factory=list, max_length=40)
    downstream_refs: list[str] = Field(default_factory=list, max_length=40)
    exclusions: list[str] = Field(default_factory=list, max_length=40)
    token_budget: int = Field(default=1600, ge=300, le=12000)
    provider_gates: dict[str, bool] = Field(default_factory=dict)
    tool_gates: dict[str, bool] = Field(default_factory=dict)
    trace_id: str | None = Field(default=None, max_length=160)
    provider_dispatch_count: int = Field(default=0, ge=0, le=0)
    remote_dispatch_count: int = Field(default=0, ge=0, le=0)

    @model_validator(mode="after")
    def validate_zero_provider_scope(self) -> "ContextPackRequest":
        if self.schema_version != M3_CONTEXT_COMMAND_SCHEMA_VERSION:
            raise ValueError("unsupported context command schema")
        if any(bool(self.provider_gates.get(name)) for name in ZERO_PROVIDER_GATES):
            raise ValueError("M3.0 context pack must keep provider gates closed")
        if bool(self.tool_gates.get("external_download")) or bool(self.tool_gates.get("model_call")):
            raise ValueError("M3.0 context pack cannot authorize external download or model calls")
        return self


class ContextPackUndoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=128)
    context_pack_id: str = Field(min_length=1, max_length=180)
    receipt_id: str = Field(min_length=1, max_length=180)
    script_revision_id: str = Field(min_length=1, max_length=160)
    source_digest: str = Field(min_length=64, max_length=64)
    schema_version: str = Field(min_length=1, max_length=80)


class FeedbackCandidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=128)
    schema_version: str = Field(min_length=1, max_length=80)
    source_kind: Literal["user_accept", "user_reject", "user_edit", "rating", "failure_review"]
    output_ref: str = Field(min_length=1, max_length=180)
    output_digest: str = Field(min_length=64, max_length=64)
    bound_scope: Literal["project", "user", "team", "domain", "global"] = "project"
    reason: str = Field(min_length=1, max_length=1000)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list, max_length=40)
    privacy_scope: Literal["private_project", "private_user", "team", "domain", "global_candidate"] = "private_project"
    rights: dict[str, Any] = Field(default_factory=dict)
    memory_write_requested: bool = False
    provider_dispatch_count: int = Field(default=0, ge=0, le=0)
    remote_dispatch_count: int = Field(default=0, ge=0, le=0)

    @model_validator(mode="after")
    def validate_feedback_not_memory(self) -> "FeedbackCandidateRequest":
        if self.schema_version != FEEDBACK_CANDIDATE_SCHEMA_VERSION:
            raise ValueError("unsupported feedback candidate schema")
        if self.memory_write_requested:
            raise ValueError("feedback candidate is not memory")
        return self


class PromotionDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=128)
    schema_version: str = Field(min_length=1, max_length=80)
    feedback_candidate_id: str = Field(min_length=1, max_length=180)
    target_scope: Literal["project", "user", "team", "domain", "global"]
    decision: Literal["pending", "promoted", "rejected", "revoked"]
    reviewer: str = Field(min_length=1, max_length=160)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list, max_length=40)
    conflict_review: dict[str, Any] = Field(default_factory=dict)
    privacy_review: dict[str, Any] = Field(default_factory=dict)
    rights_review: dict[str, Any] = Field(default_factory=dict)
    rollback: dict[str, Any] = Field(default_factory=dict)
    provider_dispatch_count: int = Field(default=0, ge=0, le=0)
    remote_dispatch_count: int = Field(default=0, ge=0, le=0)

    @model_validator(mode="after")
    def validate_promotion_gate(self) -> "PromotionDecisionRequest":
        if self.schema_version != PROMOTION_DECISION_SCHEMA_VERSION:
            raise ValueError("unsupported promotion decision schema")
        if self.target_scope == "global" and self.decision == "promoted":
            if not self.privacy_review.get("allowed_cross_user_reuse"):
                raise ValueError("global promotion requires explicit cross-user privacy approval")
            if not self.rights_review.get("allow_global_reuse"):
                raise ValueError("global promotion requires explicit rights approval")
            if self.conflict_review.get("status") != "clear":
                raise ValueError("global promotion requires clear conflict review")
        return self


class EvaluationReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=128)
    schema_version: str = Field(min_length=1, max_length=80)
    role: Literal["story_editor", "director_cinematographer_editor", "asset_production_continuity", "agent_context_safety_product"]
    target_ref: str = Field(min_length=1, max_length=180)
    target_digest: str = Field(min_length=64, max_length=64)
    independence: dict[str, Any] = Field(default_factory=dict)
    rubric_refs: list[str] = Field(min_length=1, max_length=20)
    dimensions: list[dict[str, Any]] = Field(min_length=1, max_length=40)
    critical_failures: list[dict[str, Any]] = Field(default_factory=list, max_length=40)
    issue_refs: list[str] = Field(default_factory=list, max_length=80)
    provider_dispatch_count: int = Field(default=0, ge=0, le=0)
    remote_dispatch_count: int = Field(default=0, ge=0, le=0)

    @model_validator(mode="after")
    def validate_report_schema(self) -> "EvaluationReportRequest":
        if self.schema_version != EVALUATION_REPORT_SCHEMA_VERSION:
            raise ValueError("unsupported evaluation report schema")
        if not self.independence.get("separate_pass"):
            raise ValueError("evaluation report must declare independent review pass")
        return self


def register_runtime_m3_zero_cost_kernel_routes(app: FastAPI, store: RuntimeStore, auth: RuntimeAuthStore) -> None:
    @app.get("/projects/{project_id}/m3-zero-cost/audit-truth")
    def get_m3_zero_cost_truth(project_id: str, request: Request) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        store.ensure_project_manifest(project_id)
        state = _load_state(store, project_id)
        return _truth_response(project_id, state)

    @app.get("/projects/{project_id}/m3-zero-cost/knowledge-pack")
    def get_m3_knowledge_pack(project_id: str, request: Request) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        store.ensure_project_manifest(project_id)
        return {
            "project_id": project_id,
            "knowledge_pack": initial_professional_knowledge_pack(),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.post("/projects/{project_id}/m3-zero-cost/context-packs/preview")
    def preview_context_pack(project_id: str, body: ContextPackRequest, request: Request) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        manifest = build_context_pack_manifest(store, project_id, body)
        return {
            "project_id": project_id,
            "command": _context_command(manifest, "preview"),
            "context_pack": manifest,
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.post("/projects/{project_id}/m3-zero-cost/context-packs/confirm")
    def confirm_context_pack(project_id: str, body: ContextPackRequest, request: Request) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        with exclusive_file_lock(_lock_path(store, project_id)):
            state = _load_state(store, project_id)
            manifest = build_context_pack_manifest(store, project_id, body)
            state.setdefault("context_packs", {})[manifest["context_pack_id"]] = manifest
            state["current_context_pack_id"] = manifest["context_pack_id"]
            receipt = _receipt(
                "build_context_pack",
                project_id,
                f"Context Pack locked to ScriptRevision {manifest['script_revision_id']} with {len(manifest['relevant_knowledge_refs'])} scoped knowledge refs.",
                context_pack_id=manifest["context_pack_id"],
                undo_available=True,
            )
            state.setdefault("receipts", {})[receipt["receipt_id"]] = receipt
            _append_audit(state, {"event_type": "context_pack_confirmed", "context_pack_id": manifest["context_pack_id"]})
            _write_state(store, project_id, state)
        return {
            "project_id": project_id,
            "receipt": receipt,
            "context_pack": manifest,
            "projection": public_projection(state),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.post("/projects/{project_id}/m3-zero-cost/context-packs/undo")
    def undo_context_pack(project_id: str, body: ContextPackUndoRequest, request: Request) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        if body.project_id != project_id or body.schema_version != M3_CONTEXT_COMMAND_SCHEMA_VERSION:
            raise _contract_error("context_undo_contract_mismatch", "Undo must bind to exact M3 context command schema and project.", project_id=project_id, stage="context_pack_undo", status_code=409)
        with exclusive_file_lock(_lock_path(store, project_id)):
            state = _load_state(store, project_id)
            pack = dict(state.get("context_packs", {}).get(body.context_pack_id) or {})
            receipt = dict(state.get("receipts", {}).get(body.receipt_id) or {})
            if not pack or not receipt or receipt.get("undone") or not receipt.get("undo_available"):
                raise _contract_error("context_pack_receipt_not_undoable", "Context Pack receipt is missing or already undone.", project_id=project_id, stage="context_pack_undo", status_code=409)
            if pack.get("script_revision_id") != body.script_revision_id or pack.get("source_digest") != body.source_digest:
                raise _contract_error("context_pack_revision_mismatch", "Context Pack undo must bind to the original revision digest.", project_id=project_id, stage="context_pack_undo", status_code=409)
            pack["status"] = "undone"
            pack["undone_at"] = _server_now()
            state["context_packs"][body.context_pack_id] = pack
            if state.get("current_context_pack_id") == body.context_pack_id:
                state["current_context_pack_id"] = ""
            receipt["undo_available"] = False
            receipt["undone"] = True
            state["receipts"][body.receipt_id] = receipt
            undo_receipt = _receipt("build_context_pack.undo", project_id, "Context Pack selection was undone; canonical Script/Plan truth was not changed.", context_pack_id=body.context_pack_id, undo_available=False)
            undo_receipt["status"] = "undone"
            undo_receipt["undone"] = True
            state["receipts"][undo_receipt["receipt_id"]] = undo_receipt
            _append_audit(state, {"event_type": "context_pack_undone", "context_pack_id": body.context_pack_id})
            _write_state(store, project_id, state)
        return {
            "project_id": project_id,
            "receipt": undo_receipt,
            "projection": public_projection(state),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.post("/projects/{project_id}/m3-zero-cost/feedback-candidates")
    def create_feedback_candidate(project_id: str, body: FeedbackCandidateRequest, request: Request) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        if body.project_id != project_id:
            raise _contract_error("project_identity_mismatch", "Feedback candidate project does not match URL project.", project_id=project_id, stage="feedback_candidate_create", status_code=409)
        with exclusive_file_lock(_lock_path(store, project_id)):
            state = _load_state(store, project_id)
            candidate = _feedback_candidate(body)
            state.setdefault("feedback_candidates", {})[candidate["feedback_candidate_id"]] = candidate
            _append_audit(state, {"event_type": "feedback_candidate_recorded", "feedback_candidate_id": candidate["feedback_candidate_id"]})
            _write_state(store, project_id, state)
        return {
            "project_id": project_id,
            "feedback_candidate": candidate,
            "projection": public_projection(state),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.post("/projects/{project_id}/m3-zero-cost/promotion-decisions")
    def create_promotion_decision(project_id: str, body: PromotionDecisionRequest, request: Request) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        if body.project_id != project_id:
            raise _contract_error("project_identity_mismatch", "Promotion decision project does not match URL project.", project_id=project_id, stage="promotion_decision_create", status_code=409)
        with exclusive_file_lock(_lock_path(store, project_id)):
            state = _load_state(store, project_id)
            if body.feedback_candidate_id not in state.get("feedback_candidates", {}):
                raise _contract_error("feedback_candidate_not_found", "Promotion must reference an existing FeedbackCandidate.", project_id=project_id, stage="promotion_decision_create", status_code=404)
            decision = _promotion_decision(body)
            state.setdefault("promotion_decisions", {})[decision["promotion_decision_id"]] = decision
            _append_audit(state, {"event_type": "promotion_decision_recorded", "promotion_decision_id": decision["promotion_decision_id"]})
            _write_state(store, project_id, state)
        return {
            "project_id": project_id,
            "promotion_decision": decision,
            "projection": public_projection(state),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }

    @app.post("/projects/{project_id}/m3-zero-cost/evaluation-reports")
    def create_evaluation_report(project_id: str, body: EvaluationReportRequest, request: Request) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        if body.project_id != project_id:
            raise _contract_error("project_identity_mismatch", "Evaluation report project does not match URL project.", project_id=project_id, stage="evaluation_report_create", status_code=409)
        with exclusive_file_lock(_lock_path(store, project_id)):
            state = _load_state(store, project_id)
            report = _evaluation_report(body)
            state.setdefault("evaluation_reports", {})[report["evaluation_report_id"]] = report
            _append_audit(state, {"event_type": "evaluation_report_recorded", "evaluation_report_id": report["evaluation_report_id"], "role": report["role"]})
            _write_state(store, project_id, state)
        return {
            "project_id": project_id,
            "evaluation_report": report,
            "projection": public_projection(state),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }


def initial_professional_knowledge_pack() -> dict[str, Any]:
    entries = [_knowledge_entry(**item) for item in _INITIAL_KNOWLEDGE_ENTRIES]
    pack = {
        "artifact_type": "afs_knowledge_pack",
        "schema_version": KNOWLEDGE_PACK_SCHEMA_VERSION,
        "pack_id": "afs_m3_initial_professional_pack",
        "version": "2026.07.18.zero_cost.v1",
        "locale": "zh-CN",
        "provenance": {
            "authoring_mode": "server_codex_original",
            "created_for_gate": "M3_0_CODEX_ZERO_COST_KNOWLEDGE_CONTEXT_CREATIVE_CHAIN_AUDIT_AND_CONTRACT",
            "copyright_source_text_copied": False,
        },
        "rights": {
            "owner": "AFS product",
            "license": "internal_original_test_and_product_contract",
            "third_party_copyright_text": False,
            "rollback_supported": True,
        },
        "entries": entries,
        "entry_count": len(entries),
        "pack_hash": _sha256_json(entries),
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    reject_unsafe_payload(pack)
    return pack


def build_context_pack_manifest(store: RuntimeStore, project_id: str, body: ContextPackRequest) -> dict[str, Any]:
    if body.project_id != project_id:
        raise _contract_error("project_identity_mismatch", "Context Pack project does not match URL project.", project_id=project_id, stage="context_pack_build", status_code=409)
    script_truth = script_core_truth_projection_for_project(store, project_id)
    current_revision = script_truth.get("current_revision") or {}
    if not current_revision:
        raise _contract_error("script_revision_required", "Context Pack requires current ScriptRevision truth.", project_id=project_id, stage="context_pack_build", status_code=409)
    if script_truth.get("current_revision_id") != body.script_revision_id or current_revision.get("source_digest") != body.source_digest:
        raise _contract_error("script_revision_contract_mismatch", "Context Pack must bind to current ScriptRevision and source digest.", project_id=project_id, stage="context_pack_build", status_code=409)
    plan_projection = production_plan_projection_for_project(store, project_id)
    current_plan = plan_projection.get("current_plan") or {}
    if body.plan_id or body.plan_digest:
        if not current_plan or current_plan.get("plan_id") != body.plan_id or current_plan.get("plan_digest") != body.plan_digest:
            raise _contract_error("production_plan_contract_mismatch", "Context Pack plan fields must bind to the current ProductionPlan digest.", project_id=project_id, stage="context_pack_build", status_code=409)
    knowledge_pack = initial_professional_knowledge_pack()
    refs, exclusions = retrieve_relevant_knowledge_refs(
        knowledge_pack,
        requested_domains=body.requested_domains,
        exclusions=body.exclusions,
        token_budget=body.token_budget,
    )
    truth_digest = _canonical_truth_digest(script_truth, plan_projection, body)
    manifest = {
        "artifact_type": "afs_context_pack_manifest",
        "schema_version": CONTEXT_PACK_SCHEMA_VERSION,
        "context_pack_id": f"ctx_{_sha256_json([project_id, body.model_dump(mode='json'), truth_digest, refs])[:16]}",
        "status": "preview",
        "project_id": project_id,
        "script_revision_id": body.script_revision_id,
        "source_digest": body.source_digest,
        "plan_id": str(current_plan.get("plan_id") or body.plan_id or ""),
        "plan_digest": str(current_plan.get("plan_digest") or body.plan_digest or ""),
        "canonical_truth_digest": truth_digest,
        "selected_node": {
            "node_id": _clean_token(body.selected_node_id or ""),
            "node_type": _clean_token(body.selected_node_type or ""),
        },
        "instruction": _clean_text(body.instruction, 1200),
        "constraints": _safe_public_dict(body.constraints),
        "preferences": _safe_public_dict(body.preferences),
        "upstream_refs": _clean_list(body.upstream_refs, 40),
        "downstream_refs": _clean_list(body.downstream_refs, 40),
        "relevant_knowledge_refs": refs,
        "knowledge_exclusions": exclusions,
        "provider_gates": {name: False for name in ZERO_PROVIDER_GATES},
        "tool_gates": {
            "model_call": False,
            "external_download": False,
            "media_generation": False,
        },
        "token_budget": body.token_budget,
        "estimated_context_tokens": sum(int(item.get("estimated_tokens") or 0) for item in refs),
        "trace_id": _clean_token(body.trace_id or f"trace_{uuid4().hex[:12]}"),
        "draft_is_not_truth": True,
        "feedback_is_not_memory": True,
        "test_sample_is_not_product_truth": True,
        "provider_disabled": True,
        "created_at": _server_now(),
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    reject_unsafe_payload(manifest)
    return manifest


def retrieve_relevant_knowledge_refs(
    knowledge_pack: dict[str, Any],
    *,
    requested_domains: list[str],
    exclusions: list[str],
    token_budget: int,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    requested = {_normal_key(item) for item in requested_domains if _normal_key(item)}
    excluded = {_normal_key(item) for item in exclusions if _normal_key(item)}
    refs: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    used = 0
    for entry in knowledge_pack.get("entries", []):
        domains = {_normal_key(item) for item in entry.get("domains", [])}
        stages = {_normal_key(item) for item in entry.get("stages", [])}
        overlap = requested & (domains | stages | {_normal_key(entry.get("scope") or "")})
        entry_id = str(entry.get("entry_id") or "")
        if _normal_key(entry_id) in excluded or domains & excluded:
            skipped.append({"entry_id": entry_id, "reason": "explicitly_excluded"})
            continue
        if requested and not overlap:
            skipped.append({"entry_id": entry_id, "reason": "domain_scope_not_requested"})
            continue
        estimate = int(entry.get("estimated_tokens") or 120)
        if used + estimate > token_budget:
            skipped.append({"entry_id": entry_id, "reason": "token_budget"})
            continue
        refs.append(
            {
                "entry_id": entry_id,
                "version": str(entry.get("version") or ""),
                "content_hash": str(entry.get("content_hash") or ""),
                "domains": list(entry.get("domains") or []),
                "scope": str(entry.get("scope") or ""),
                "confidence": float(entry.get("confidence") or 0),
                "estimated_tokens": estimate,
                "selection_reason": "matched declared domain/stage/scope; content was not generated by keyword fallback",
            }
        )
        used += estimate
    return refs, skipped


def public_projection(state: dict[str, Any]) -> dict[str, Any]:
    context_packs = state.get("context_packs") or {}
    feedback = state.get("feedback_candidates") or {}
    promotions = state.get("promotion_decisions") or {}
    reports = state.get("evaluation_reports") or {}
    return {
        "artifact_type": "afs_m3_zero_cost_audit_projection",
        "schema_version": M3_ZERO_COST_SCHEMA_VERSION,
        "project_id": state["project_id"],
        "current_context_pack_id": str(state.get("current_context_pack_id") or ""),
        "context_pack_count": len(context_packs),
        "feedback_candidate_count": len(feedback),
        "promotion_decision_count": len(promotions),
        "evaluation_report_count": len(reports),
        "evaluator_roles_covered": sorted({str(item.get("role") or "") for item in reports.values()} & EVALUATOR_ROLES),
        "pending_feedback_not_memory": all(item.get("memory_status") == "not_memory" for item in feedback.values()),
        "promoted_global_count": sum(1 for item in promotions.values() if item.get("target_scope") == "global" and item.get("decision") == "promoted"),
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def evaluate_zero_cost_creative_chain_case(case: dict[str, Any], knowledge_pack: dict[str, Any] | None = None) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    pack = knowledge_pack or initial_professional_knowledge_pack()
    case_id = str(case.get("case_id") or "unknown")
    required = [
        "idea_brief",
        "professional_script_candidate",
        "script_understanding",
        "story_plan_candidate",
        "asset_bible_candidate",
        "context_pack_manifest",
        "knowledge_pack_manifest",
        "evaluation_reports",
        "issue_ledger",
        "affected_only_replan",
        "agent_chat_lifecycle",
    ]
    for key in required:
        if not case.get(key):
            findings.append(_finding("P0", case_id, key, "required stage artifact is missing"))
    _check_professional_script(case_id, case.get("professional_script_candidate") or {}, findings)
    _check_story_plan(case_id, case.get("story_plan_candidate") or {}, findings)
    _check_asset_bible(case_id, case.get("asset_bible_candidate") or {}, findings)
    _check_context_manifest(case_id, case.get("context_pack_manifest") or {}, pack, findings)
    _check_evaluation_reports(case_id, case.get("evaluation_reports") or [], findings)
    _check_issue_ledger(case_id, case.get("issue_ledger") or [], findings)
    _check_replan(case_id, case.get("affected_only_replan") or {}, findings)
    _check_agent_lifecycle(case_id, case.get("agent_chat_lifecycle") or {}, findings)
    return {
        "case_id": case_id,
        "status": "passed" if not [item for item in findings if item["severity"] in {"P0", "P1"}] else "failed",
        "findings": findings,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def evaluate_zero_cost_creative_chain_corpus(corpus: dict[str, Any]) -> dict[str, Any]:
    pack = initial_professional_knowledge_pack()
    case_reports = [evaluate_zero_cost_creative_chain_case(case, pack) for case in corpus.get("cases", [])]
    findings = [finding for report in case_reports for finding in report["findings"]]
    adversarial = corpus.get("adversarial_variants") or []
    if len(corpus.get("cases", [])) < 5:
        findings.append(_finding("P0", "corpus", "case_count", "at least five original zero-cost cases are required"))
    if len(adversarial) < 10:
        findings.append(_finding("P1", "corpus", "adversarial_variants", "adversarial coverage is too small"))
    if not corpus.get("provenance", {}).get("copyright_source_text_copied") is False:
        findings.append(_finding("P0", "corpus", "rights", "corpus must declare no copied copyrighted source text"))
    p0 = sum(1 for item in findings if item["severity"] == "P0")
    p1 = sum(1 for item in findings if item["severity"] == "P1")
    return {
        "artifact_type": "afs_m3_zero_cost_creative_chain_evaluation",
        "schema_version": M3_ZERO_COST_SCHEMA_VERSION,
        "verdict": "PASS" if p0 == 0 and p1 == 0 else "FAIL",
        "case_count": len(corpus.get("cases", [])),
        "adversarial_variant_count": len(adversarial),
        "case_reports": case_reports,
        "findings": findings,
        "P0": p0,
        "P1": p1,
        "P2": sum(1 for item in findings if item["severity"] == "P2"),
        "P3": sum(1 for item in findings if item["severity"] == "P3"),
        "knowledge_pack_hash": pack["pack_hash"],
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
        "non_claims": [
            "not_provider_story_planning",
            "not_media_generation",
            "not_human_creative_quality_assurance",
            "not_owner_acceptance",
            "not_business_validation",
        ],
    }


def _truth_response(project_id: str, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "projection": public_projection(state),
        "knowledge_pack": initial_professional_knowledge_pack(),
        "context_packs": list((state.get("context_packs") or {}).values()),
        "feedback_candidates": list((state.get("feedback_candidates") or {}).values()),
        "promotion_decisions": list((state.get("promotion_decisions") or {}).values()),
        "evaluation_reports": list((state.get("evaluation_reports") or {}).values()),
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _context_command(manifest: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "schema_version": M3_CONTEXT_COMMAND_SCHEMA_VERSION,
        "command_id": f"cmd_{manifest['context_pack_id']}",
        "command_type": "build_context_pack",
        "status": status,
        "title": "构建精准上下文包",
        "summary": f"将使用 {len(manifest['relevant_knowledge_refs'])} 条相关知识、当前剧本版本和计划摘要；Provider 保持关闭。",
        "project_id": manifest["project_id"],
        "script_revision_id": manifest["script_revision_id"],
        "source_digest": manifest["source_digest"],
        "context_pack_id": manifest["context_pack_id"],
        "canonical_truth_digest": manifest["canonical_truth_digest"],
        "requires_confirmation": True,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _feedback_candidate(body: FeedbackCandidateRequest) -> dict[str, Any]:
    payload = body.model_dump(mode="json")
    payload.update(
        {
            "artifact_type": "afs_feedback_candidate",
            "feedback_candidate_id": f"fb_{_sha256_json(payload)[:16]}",
            "status": "pending_promotion_review",
            "memory_status": "not_memory",
            "created_at": _server_now(),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }
    )
    reject_unsafe_payload(payload)
    return payload


def _promotion_decision(body: PromotionDecisionRequest) -> dict[str, Any]:
    payload = body.model_dump(mode="json")
    payload.update(
        {
            "artifact_type": "afs_promotion_decision",
            "promotion_decision_id": f"promo_{_sha256_json(payload)[:16]}",
            "created_at": _server_now(),
            "rollback_supported": bool(payload.get("rollback")),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }
    )
    reject_unsafe_payload(payload)
    return payload


def _evaluation_report(body: EvaluationReportRequest) -> dict[str, Any]:
    payload = body.model_dump(mode="json")
    payload.update(
        {
            "artifact_type": "afs_evaluation_report",
            "evaluation_report_id": f"eval_{_sha256_json(payload)[:16]}",
            "created_at": _server_now(),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }
    )
    reject_unsafe_payload(payload)
    return payload


def _receipt(command_type: str, project_id: str, summary: str, *, context_pack_id: str = "", undo_available: bool) -> dict[str, Any]:
    return {
        "receipt_id": f"receipt_{uuid4().hex[:16]}",
        "command_id": f"cmd_{uuid4().hex[:12]}",
        "command_type": command_type,
        "status": "executed",
        "summary": summary,
        "executed_at": _server_now(),
        "project_id": project_id,
        "context_pack_id": context_pack_id,
        "undo_available": undo_available,
        "undone": False,
        "draft_is_not_truth": True,
        "storyboard_write": False,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _knowledge_entry(
    *,
    entry_id: str,
    domains: list[str],
    stages: list[str],
    scope: str,
    title: str,
    content: str,
    confidence: float = 0.86,
    estimated_tokens: int = 120,
) -> dict[str, Any]:
    content = _clean_text(content, 1800)
    return {
        "artifact_type": "afs_knowledge_entry",
        "schema_version": KNOWLEDGE_ENTRY_SCHEMA_VERSION,
        "entry_id": entry_id,
        "source": "server_codex_original_m3_0",
        "provenance": "Original AFS professional practice note authored for this zero-cost gate; no copyrighted source text copied.",
        "rights": {
            "owner": "AFS product",
            "reuse_scope": "project_and_product_contract_review",
            "third_party_copyright_text": False,
        },
        "version": "2026.07.18.v1",
        "locale": "zh-CN",
        "domains": domains,
        "stages": stages,
        "scope": scope,
        "confidence": confidence,
        "status": "active",
        "title": title,
        "content": content,
        "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "evaluator": {
            "rubric_ref": "m3_zero_cost_professional_kernel_rubric",
            "last_result": "accepted_for_zero_cost_contract_testing",
        },
        "rollback": {
            "supported": True,
            "strategy": "pin prior pack_hash or revoke entry status",
        },
        "estimated_tokens": estimated_tokens,
    }


def _canonical_truth_digest(script_truth: dict[str, Any], plan_projection: dict[str, Any], body: ContextPackRequest) -> str:
    safe_script = {
        "current_revision_id": script_truth.get("current_revision_id"),
        "current_revision": script_truth.get("current_revision"),
        "asset_counts": script_truth.get("asset_counts"),
        "asset_ids": [item.get("asset_id") for item in script_truth.get("assets", [])],
        "analysis_state": script_truth.get("analysis_state"),
    }
    safe_plan = {
        "current_plan": plan_projection.get("current_plan"),
        "planning_state": plan_projection.get("planning_state"),
        "shot_ids": [item.get("shot_id") for item in plan_projection.get("shots", [])],
        "chunk_ids": [item.get("chunk_id") for item in plan_projection.get("chunks", [])],
    }
    return _sha256_json({"script": safe_script, "plan": safe_plan, "selected_node": body.selected_node_id})


def _check_professional_script(case_id: str, script: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    for key in ("title", "synopsis", "theme", "genre", "target_duration_seconds", "characters", "scene_blocks", "beats"):
        if not script.get(key):
            findings.append(_finding("P0", case_id, f"professional_script_candidate.{key}", "professional script candidate is incomplete"))
    if len(script.get("scene_blocks") or []) < 1:
        findings.append(_finding("P1", case_id, "scene_blocks", "at least one scene block is required"))
    if any(not block.get("action") for block in script.get("scene_blocks") or []):
        findings.append(_finding("P1", case_id, "scene_blocks.action", "scene block action must be explicit"))


def _check_story_plan(case_id: str, plan: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    shots = plan.get("shots") or []
    if not shots:
        findings.append(_finding("P0", case_id, "story_plan_candidate.shots", "story plan requires dynamic shots"))
        return
    durations = [float(shot.get("duration_seconds") or 0) for shot in shots]
    if len(shots) == 4 and all(abs(value - 15.0) < 0.001 for value in durations):
        findings.append(_finding("P0", case_id, "story_plan_candidate.equal_count_duration_template", "equal four-shot fifteen-second plan is forbidden"))
    if len(set(durations)) <= 1 and len(shots) > 2:
        findings.append(_finding("P1", case_id, "story_plan_candidate.dynamic_duration", "shot durations should reflect story structure, not a fixed template"))
    for shot in shots:
        for key in ("narrative_purpose", "lineage", "scene_ref", "asset_refs", "shot_size", "camera", "motion", "transition", "continuity", "media_strategy", "quality_gate"):
            if not shot.get(key):
                findings.append(_finding("P1", case_id, f"shot.{shot.get('shot_id')}.{key}", "shot is missing professional planning field"))
        strategy = (shot.get("media_strategy") or {}).get("strategy")
        if strategy not in {"t2v", "i2v"} or not (shot.get("media_strategy") or {}).get("strategy_reason"):
            findings.append(_finding("P0", case_id, f"shot.{shot.get('shot_id')}.media_strategy", "shot must choose T2V/I2V with reason"))


def _check_asset_bible(case_id: str, bible: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    required_groups = ("characters", "main_scenes", "props", "style", "closeups", "reference_sets")
    for group in required_groups:
        if group not in bible:
            findings.append(_finding("P1", case_id, f"asset_bible_candidate.{group}", "asset bible group missing"))
    for group in ("characters", "main_scenes", "props", "closeups"):
        for asset in bible.get(group, []) or []:
            if not asset.get("stable_id") or not asset.get("lineage") or asset.get("truth_status") == "truth":
                findings.append(_finding("P0", case_id, f"asset_bible_candidate.{group}", "draft asset must have stable id/lineage and must not become truth"))


def _check_context_manifest(case_id: str, manifest: dict[str, Any], pack: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    refs = manifest.get("relevant_knowledge_refs") or []
    if not refs:
        findings.append(_finding("P0", case_id, "context_pack_manifest.knowledge_refs", "context pack must include scoped knowledge refs"))
    if len(refs) >= int(pack.get("entry_count") or 0):
        findings.append(_finding("P1", case_id, "context_pack_manifest.knowledge_scope", "context pack must not inject the entire knowledge pack"))
    if any(manifest.get("provider_gates", {}).get(name) for name in ZERO_PROVIDER_GATES):
        findings.append(_finding("P0", case_id, "context_pack_manifest.provider_gates", "provider gates must remain closed"))
    if not manifest.get("canonical_truth_digest") or not manifest.get("trace_id"):
        findings.append(_finding("P0", case_id, "context_pack_manifest.lineage", "context pack must bind canonical truth digest and trace id"))


def _check_evaluation_reports(case_id: str, reports: list[dict[str, Any]], findings: list[dict[str, Any]]) -> None:
    roles = {str(item.get("role") or "") for item in reports}
    missing = EVALUATOR_ROLES - roles
    for role in sorted(missing):
        findings.append(_finding("P0", case_id, f"evaluation_reports.{role}", "required evaluator role missing"))
    for report in reports:
        if not report.get("evidence") or not report.get("rubric_refs") or not report.get("independent"):
            findings.append(_finding("P1", case_id, f"evaluation_reports.{report.get('role')}", "evaluation report lacks evidence/rubric/independence"))
        for failure in report.get("critical_failures") or []:
            severity = str(failure.get("severity") or "P1")
            if severity in {"P0", "P1"} and failure.get("status") != "fixed_verified":
                findings.append(_finding(severity, case_id, f"critical_failure.{report.get('role')}", "critical failure is not fixed and verified"))


def _check_issue_ledger(case_id: str, issues: list[dict[str, Any]], findings: list[dict[str, Any]]) -> None:
    for issue in issues:
        severity = str(issue.get("severity") or "")
        if severity in {"P0", "P1"} and issue.get("status") != "fixed_verified":
            findings.append(_finding(severity, case_id, f"issue_ledger.{issue.get('issue_id')}", "P0/P1 issue must be fixed_verified"))


def _check_replan(case_id: str, replan: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    affected = set(replan.get("affected_ids") or [])
    preserved = set(replan.get("preserved_ids") or [])
    if not affected or not preserved:
        findings.append(_finding("P1", case_id, "affected_only_replan", "affected-only replan must prove both changed and preserved items"))
    if affected & preserved:
        findings.append(_finding("P0", case_id, "affected_only_replan", "affected and preserved sets must not overlap"))


def _check_agent_lifecycle(case_id: str, lifecycle: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    states = lifecycle.get("states") or []
    for required in ("preview", "confirmed", "receipt", "undo"):
        if required not in states:
            findings.append(_finding("P0", case_id, "agent_chat_lifecycle", f"missing {required} state"))
    if lifecycle.get("storyboard_write") or lifecycle.get("provider_dispatch_count") or lifecycle.get("raw_command_visible_default"):
        findings.append(_finding("P0", case_id, "agent_chat_lifecycle", "lifecycle leaked raw command, wrote storyboard, or dispatched provider"))


def _finding(severity: str, case_id: str, scope: str, issue: str) -> dict[str, Any]:
    return {"severity": severity, "case_id": case_id, "scope": scope, "issue": issue}


def _load_state(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    path = _state_path(store, project_id)
    if path.is_file():
        state = read_json(path)
        reject_unsafe_payload(state)
        if state.get("project_id") != project_id:
            raise ValueError("M3 zero-cost project id mismatch")
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
        "artifact_type": "afs_m3_zero_cost_audit_truth",
        "schema_version": M3_ZERO_COST_SCHEMA_VERSION,
        "project_id": project_id,
        "current_context_pack_id": "",
        "context_packs": {},
        "feedback_candidates": {},
        "promotion_decisions": {},
        "evaluation_reports": {},
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
    for key in ("context_packs", "feedback_candidates", "promotion_decisions", "evaluation_reports", "receipts"):
        if not isinstance(payload.get(key), dict):
            payload[key] = {}
    if not isinstance(payload.get("audit_history"), list):
        payload["audit_history"] = []
    payload["provider_dispatch_count"] = 0
    payload["remote_dispatch_count"] = 0
    return payload


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
            user_action="Refresh M3 Context Pack inputs and retry with exact project, revision, digest, plan, and schema.",
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


def _clean_list(values: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = _clean_text(value, 180)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _clean_text(value: Any, limit: int) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _clean_token(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]+", "", str(value or ""))[:180]


def _normal_key(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().casefold())


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _server_now() -> str:
    return datetime.now(UTC).isoformat()


def _truth_dir(store: RuntimeStore, project_id: str) -> Path:
    return store.projects_dir / safe_id(project_id) / "m3_zero_cost_audit"


def _state_path(store: RuntimeStore, project_id: str) -> Path:
    return _truth_dir(store, project_id) / "truth_state.json"


def _lock_path(store: RuntimeStore, project_id: str) -> Path:
    return _truth_dir(store, project_id) / "truth_state.lock"


_INITIAL_KNOWLEDGE_ENTRIES = [
    {
        "entry_id": "kp_story_causal_theme_v1",
        "domains": ["script", "story", "narrative"],
        "stages": ["professional_script", "script_understanding"],
        "scope": "domain",
        "title": "因果主题检查",
        "content": "每次优化先确认主角想要什么、阻力来自哪里、选择造成什么后果；主题必须通过行动改变显现，而不是旁白解释。",
        "estimated_tokens": 110,
    },
    {
        "entry_id": "kp_character_dialogue_arc_v1",
        "domains": ["script", "character", "dialogue"],
        "stages": ["professional_script", "asset_bible"],
        "scope": "domain",
        "title": "人物动机与对白",
        "content": "命名人物需要动机、关系压力和可观察弧光；对白应携带目的、掩饰或转折，避免只解释设定。",
        "estimated_tokens": 120,
    },
    {
        "entry_id": "kp_director_shot_purpose_v1",
        "domains": ["director", "cinematography", "shot_plan"],
        "stages": ["story_plan", "production_plan"],
        "scope": "domain",
        "title": "镜头目的优先",
        "content": "每个镜头必须说明叙事目的、景别、机位、运动、动作和出入连续性；没有新信息或情绪推进的镜头应合并或删减。",
        "estimated_tokens": 135,
    },
    {
        "entry_id": "kp_editing_rhythm_continuity_v1",
        "domains": ["editing", "rhythm", "continuity"],
        "stages": ["story_plan", "replan"],
        "scope": "domain",
        "title": "节奏与连续性",
        "content": "动态时长由信息密度、动作复杂度、对白长度和转场需求决定；局部重规划只能影响依赖链，未受影响镜头保持ID和顺序稳定。",
        "estimated_tokens": 145,
    },
    {
        "entry_id": "kp_asset_bible_reference_set_v1",
        "domains": ["asset_bible", "reference_set", "continuity"],
        "stages": ["asset_bible", "reference_set"],
        "scope": "domain",
        "title": "资产 Bible 与引用集",
        "content": "人物、主场景、道具、服装、时间天气光线和特写都要有稳定ID、别名、证据、版本和 lineage；草案不得自动成为truth。",
        "estimated_tokens": 155,
    },
    {
        "entry_id": "kp_media_strategy_limits_v1",
        "domains": ["media_strategy", "provider_capability", "continuity"],
        "stages": ["story_plan", "chunk_plan"],
        "scope": "domain",
        "title": "媒体策略与能力限制",
        "content": "T2V/I2V选择必须来自显式参考、锁定关键帧、用户约束和能力合同；缺少I2V引用时标记pending_input，不得伪造参考。",
        "estimated_tokens": 145,
    },
    {
        "entry_id": "kp_context_privacy_injection_v1",
        "domains": ["context", "safety", "privacy"],
        "stages": ["context_pack", "promotion"],
        "scope": "global_policy",
        "title": "上下文与隐私边界",
        "content": "Context Pack只取与任务、选中节点和依赖链相关的条目；私有用户数据、聊天全量历史和prompt injection必须被排除并记录原因。",
        "estimated_tokens": 150,
    },
    {
        "entry_id": "kp_quality_rubric_failure_modes_v1",
        "domains": ["evaluation", "rubric", "anti_pattern"],
        "stages": ["evaluation", "audit"],
        "scope": "domain",
        "title": "质量 Rubric 与反模式",
        "content": "P0包括Provider越权、truth分叉、固定模板冒充动态、证据缺失、私有数据全局晋升；P1包括镜头无目的、资产不稳定、上下文过宽。",
        "estimated_tokens": 160,
    },
]


__all__ = (
    "CONTEXT_PACK_SCHEMA_VERSION",
    "EVALUATION_REPORT_SCHEMA_VERSION",
    "FEEDBACK_CANDIDATE_SCHEMA_VERSION",
    "KNOWLEDGE_ENTRY_SCHEMA_VERSION",
    "KNOWLEDGE_PACK_SCHEMA_VERSION",
    "M3_CONTEXT_COMMAND_SCHEMA_VERSION",
    "M3_ZERO_COST_SCHEMA_VERSION",
    "PROMOTION_DECISION_SCHEMA_VERSION",
    "QUALITY_RUBRIC_SCHEMA_VERSION",
    "build_context_pack_manifest",
    "evaluate_zero_cost_creative_chain_case",
    "evaluate_zero_cost_creative_chain_corpus",
    "initial_professional_knowledge_pack",
    "register_runtime_m3_zero_cost_kernel_routes",
    "retrieve_relevant_knowledge_refs",
)
