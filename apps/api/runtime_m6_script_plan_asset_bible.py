from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from typing import Any, Literal, Mapping

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_film_production_graph import compile_film_candidate, film_graph_projection
from apps.api.runtime_logging import client_request_id_from_request
from apps.api.runtime_m6_preview_runs import (
    M6PreviewRunError,
    M6PreviewRunStore,
    preview_run_uses_remote_llm,
    preview_source_digest,
    submit_m6_preview_run,
)
from apps.api.runtime_production_graph import (
    GraphPlanningRequired,
    GraphVersionConflict,
    ProductionGraphError,
    ProductionGraphStore,
    canonical_digest,
    graph_path,
)
from apps.api.runtime_script_core_truth import current_script_revision_binding
from apps.api.runtime_store import RuntimeStore


M6_SCHEMA_VERSION = "afs.m6.script_plan_asset_bible.v0.1"
FILM_SCHEMA_VERSION = "afs.film_domain_pack.v0.1"
M6_SCOPE_REVIEW_SCHEMA_VERSION = "afs.m6.canonical_scope_review.v0.1"
REVIEW_ROLES = (
    "screenwriter",
    "director_storyboard",
    "cinematographer",
    "asset_continuity",
    "production_feasibility",
    "engineering_lineage_knowledge_safety",
)
KNOWLEDGE_LAYERS = {"fact", "user_preference", "project_decision", "draft", "long_term_experience"}
KNOWLEDGE_SCOPES = {"project", "user", "team"}
CANONICAL_ASSET_KINDS = {"prop"}
PRODUCTION_AID_KINDS = {"closeup", "reference_set", "style"}


class M6ScriptPlanPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_kind: Literal["idea", "script", "uploaded_text"] = "idea"
    source_text: str = Field(min_length=1, max_length=200_000)
    source_revision_id: str = Field(min_length=1, max_length=140)
    source_revision_digest: str = Field(min_length=64, max_length=64)
    revision_instruction: str | None = Field(default=None, max_length=2000)
    parent_candidate_digest: str | None = Field(default=None, max_length=64)
    requested_language: str = Field(default="zh-CN", max_length=24)
    provider_dispatch_count: int = Field(default=0, ge=0, le=0)
    cost_usd: int = Field(default=0, ge=0, le=0)

    @field_validator("source_text")
    @classmethod
    def source_text_must_contain_creator_input(cls, value: str) -> str:
        if not _clean_source_text(value):
            raise ValueError("creator input is required")
        return value

    @model_validator(mode="after")
    def validate_applied_script_binding(self) -> "M6ScriptPlanPreviewRequest":
        if self.source_kind != "script":
            raise ValueError("production planning requires the current applied script")
        digest = hashlib.sha256(_clean_source_text(self.source_text).encode("utf-8")).hexdigest()
        if self.source_revision_digest != digest:
            raise ValueError("source revision digest does not match source text")
        return self


class M6ScriptPlanConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1, max_length=120)
    candidate_digest: str = Field(min_length=64, max_length=64)
    expected_graph_version: int = Field(ge=0)
    provider_dispatch_count: int = Field(default=0, ge=0, le=0)
    cost_usd: int = Field(default=0, ge=0, le=0)


def register_runtime_m6_script_plan_asset_bible_routes(app: FastAPI, store: RuntimeStore, auth: RuntimeAuthStore) -> None:
    graph_store = ProductionGraphStore(store)
    preview_runs = M6PreviewRunStore(store)

    def require_access(request: Request, project_id: str) -> str:
        if auth.enabled():
            user = auth.require_user(request)
            if not auth.user_can_access_project(str(user["user_id"]), project_id):
                raise HTTPException(status_code=403, detail="project access denied")
            return str(user["user_id"])
        return "local-runtime-owner"

    @app.post("/projects/{project_id}/m6/script-plan-asset-bible/preview")
    def preview_script_plan_asset_bible(project_id: str, body: M6ScriptPlanPreviewRequest, request: Request) -> dict[str, Any]:
        owner_id = require_access(request, project_id)
        store.ensure_project_manifest(project_id)
        _require_current_m6_script_binding(store, project_id, body)
        client_request_id = client_request_id_from_request(request)
        if not client_request_id:
            raise _contract_error(
                "m6_preview_client_request_required",
                "M6 preview requires a stable client request id.",
                project_id=project_id,
                stage="m6_preview_create",
                status_code=422,
            )
        remote_llm_enabled = _server_codex_m6_enabled()
        graph_version = graph_store.load(project_id)["version"] if graph_path(store, project_id).is_file() else 0
        try:
            run, _ = preview_runs.create_or_load(
                project_id,
                owner_id=owner_id,
                client_request_id=client_request_id,
                source_digest=preview_source_digest(body.model_dump()),
                expected_graph_version=graph_version,
                remote_llm_enabled=remote_llm_enabled,
            )
            committed_remote_llm = preview_run_uses_remote_llm(run)
            if committed_remote_llm and not remote_llm_enabled:
                run = preview_runs.fail(
                    project_id,
                    str(run["run_id"]),
                    owner_id=owner_id,
                    error=M6PreviewRunError(
                        "preview_provider_gate_closed",
                        "committed text provider gate is closed",
                    ),
                )
                return preview_runs.public(run)
            submit_m6_preview_run(
                preview_runs,
                project_id,
                str(run["run_id"]),
                owner_id=owner_id,
                body=body.model_dump(),
                planner_resolver=_preview_planner,
            )
            return preview_runs.public(preview_runs.load(project_id, str(run["run_id"]), owner_id=owner_id))
        except M6PreviewRunError as exc:
            raise _preview_run_http_error(exc, project_id=project_id, stage="m6_preview_create") from exc

    @app.get("/projects/{project_id}/m6/script-plan-asset-bible/preview-runs/latest")
    def latest_script_plan_preview_run(project_id: str, request: Request) -> dict[str, Any]:
        owner_id = require_access(request, project_id)
        try:
            run = preview_runs.latest(project_id, owner_id=owner_id)
            return {"status": "empty", "run": None} if run is None else preview_runs.public(run)
        except M6PreviewRunError as exc:
            raise _preview_run_http_error(exc, project_id=project_id, stage="m6_preview_recover") from exc

    @app.get("/projects/{project_id}/m6/script-plan-asset-bible/preview-runs/by-client/{client_request_id}")
    def recover_script_plan_preview_by_client(project_id: str, client_request_id: str, request: Request) -> dict[str, Any]:
        owner_id = require_access(request, project_id)
        try:
            run = preview_runs.load_by_client_request(
                project_id,
                client_request_id,
                owner_id=owner_id,
            )
            return preview_runs.public(run)
        except M6PreviewRunError as exc:
            raise _preview_run_http_error(exc, project_id=project_id, stage="m6_preview_recover") from exc

    @app.get("/projects/{project_id}/m6/script-plan-asset-bible/preview-runs/{run_id}")
    def load_script_plan_preview_run(project_id: str, run_id: str, request: Request) -> dict[str, Any]:
        owner_id = require_access(request, project_id)
        try:
            return preview_runs.public(preview_runs.recover(project_id, run_id, owner_id=owner_id))
        except M6PreviewRunError as exc:
            raise _preview_run_http_error(exc, project_id=project_id, stage="m6_preview_recover") from exc

    @app.post("/projects/{project_id}/m6/script-plan-asset-bible/preview-runs/{run_id}/cancel")
    def cancel_script_plan_preview_run(project_id: str, run_id: str, request: Request) -> dict[str, Any]:
        owner_id = require_access(request, project_id)
        try:
            return preview_runs.public(preview_runs.cancel(project_id, run_id, owner_id=owner_id))
        except M6PreviewRunError as exc:
            raise _preview_run_http_error(exc, project_id=project_id, stage="m6_preview_cancel") from exc

    @app.post("/projects/{project_id}/m6/script-plan-asset-bible/confirm")
    def confirm_script_plan_asset_bible(project_id: str, body: M6ScriptPlanConfirmRequest, request: Request) -> dict[str, Any]:
        owner_id = require_access(request, project_id)
        try:
            def build_confirmation(run: dict[str, Any], preview: dict[str, Any]) -> dict[str, Any]:
                candidate = preview.get("candidate")
                if not isinstance(candidate, dict):
                    raise M6PreviewRunError("preview_candidate_missing", "stored preview candidate is unavailable")
                _require_current_m6_candidate_binding(store, project_id, candidate)
                validation = validate_m6_candidate(candidate)
                events = compile_film_candidate(project_id, candidate)
                graph = graph_store.append(
                    project_id,
                    expected_version=body.expected_graph_version,
                    idempotency_key=f"confirm-{body.run_id}",
                    semantic_digest=canonical_digest(candidate),
                    events=events,
                )
                return {
                    "status": "confirmed",
                    "run_id": body.run_id,
                    "candidate_digest": body.candidate_digest,
                    "graph": graph,
                    "projection": film_graph_projection(graph, "studio"),
                    "m6_validation": validation,
                    "provider_dispatch_count": int(run.get("dispatch_count") or 0),
                    "cost": dict(run.get("cost") or {}),
                    "cost_usd": (run.get("cost") or {}).get("contract_cost_usd", 0),
                }

            return preview_runs.confirm_once(
                project_id,
                body.run_id,
                owner_id=owner_id,
                candidate_digest=body.candidate_digest,
                expected_graph_version=body.expected_graph_version,
                build_response=build_confirmation,
            )
        except M6PreviewRunError as exc:
            raise _preview_run_http_error(exc, project_id=project_id, stage="m6_confirm") from exc
        except (M6PlanningError, GraphPlanningRequired, GraphVersionConflict, ProductionGraphError, KeyError, TypeError, ValueError) as exc:
            raise _contract_error("m6_candidate_rejected", str(exc), project_id=project_id, stage="m6_confirm", status_code=409) from exc


class M6PlanningError(ValueError):
    def __init__(self, message: str, *, validator_code: str = "") -> None:
        super().__init__(message)
        self.validator_code = validator_code


def _server_codex_m6_enabled() -> bool:
    from apps.api.runtime_m6_server_codex_planner import server_codex_m6_enabled

    return server_codex_m6_enabled()


def _preview_planner(remote_llm_enabled: bool):
    if remote_llm_enabled:
        from apps.api.runtime_m6_server_codex_planner import build_m6_server_codex_script_plan_asset_bible

        return build_m6_server_codex_script_plan_asset_bible
    return build_m6_script_plan_asset_bible


def _require_current_m6_script_binding(
    store: RuntimeStore,
    project_id: str,
    body: M6ScriptPlanPreviewRequest,
) -> None:
    current = current_script_revision_binding(store, project_id)
    if (
        str(current.get("revision_id") or "") == body.source_revision_id
        and str(current.get("source_digest") or "") == body.source_revision_digest
    ):
        return
    raise _contract_error(
        "m6_source_revision_changed",
        "当前已应用剧本版本已变化，请从当前剧本重新准备制作方案。",
        project_id=project_id,
        stage="m6_preview_create",
        status_code=409,
    )


def _require_current_m6_candidate_binding(
    store: RuntimeStore,
    project_id: str,
    candidate: Mapping[str, Any],
) -> None:
    lineage = candidate.get("brief", {}).get("lineage", {})
    current = current_script_revision_binding(store, project_id)
    if (
        isinstance(lineage, Mapping)
        and str(lineage.get("source_revision_id") or "") == str(current.get("revision_id") or "")
        and str(lineage.get("source_revision_digest") or "") == str(current.get("source_digest") or "")
        and str(current.get("revision_id") or "")
    ):
        return
    raise M6PreviewRunError(
        "preview_source_revision_changed",
        "当前已应用剧本版本已变化；旧制作方案不能确认。",
    )


def _preview_run_http_error(exc: M6PreviewRunError, *, project_id: str, stage: str) -> HTTPException:
    status_code = 409
    if exc.code == "preview_run_not_found":
        status_code = 404
    elif exc.code == "preview_run_expired":
        status_code = 410
    elif exc.code == "preview_run_access_denied":
        status_code = 403
    return _contract_error(exc.code, str(exc), project_id=project_id, stage=stage, status_code=status_code)


def build_m6_script_plan_asset_bible(project_id: str, body: Mapping[str, Any]) -> dict[str, Any]:
    source_text = _clean_source_text(body.get("source_text"))
    source_digest = canonical_digest({
        "schema_version": M6_SCHEMA_VERSION,
        "source_kind": body.get("source_kind") or "idea",
        "source_text": source_text,
        "revision_instruction": _clean_text(body.get("revision_instruction")),
        "parent_candidate_digest": body.get("parent_candidate_digest") or "",
    })
    segments = _source_segments(source_text)
    source_scope = m6_source_canonical_scope(source_text)
    cast = source_scope["characters"]
    scenes = source_scope["scenes"]
    props = source_scope["props"]
    closeups = source_scope["closeups"]
    styles = source_scope["styles"]
    if len(cast) < 1:
        raise M6PlanningError("M6 preview requires at least one named character in the idea or script.")
    if len(scenes) < 1:
        raise M6PlanningError("M6 preview requires at least one concrete scene or location.")
    if len(segments) < 2:
        raise M6PlanningError("M6 preview requires at least two story beats for dynamic sequence planning.")
    project_key = _safe_token(project_id)
    candidate_key = source_digest[:12]
    revision_id = f"m6-script-{candidate_key}"
    brief_id = f"m6-brief-{candidate_key}"
    sequence_id = f"m6-sequence-{candidate_key}"
    character_rows = [_character_row(project_key, candidate_key, index, name, source_text) for index, name in enumerate(cast, start=1)]
    scene_rows = [_scene_row(project_key, candidate_key, index, name, source_text, revision_id) for index, name in enumerate(scenes, start=1)]
    asset_rows = _asset_rows(project_key, candidate_key, props, closeups, styles, character_rows, scene_rows, source_digest)
    shot_rows = _shot_rows(project_key, candidate_key, segments, character_rows, scene_rows, asset_rows, revision_id)
    scope_review = build_m6_scope_review(
        source_text=source_text,
        characters=character_rows,
        scenes=scene_rows,
        assets=asset_rows,
        shots=shot_rows,
    )
    candidate = {
        "schema_version": FILM_SCHEMA_VERSION,
        "m6_schema_version": M6_SCHEMA_VERSION,
        "trusted_candidate": True,
        "source_digest": source_digest,
        "provider_dispatch_count": 0,
        "cost_usd": 0,
        "brief": {
            "brief_id": brief_id,
            "source_kind": body.get("source_kind") or "idea",
            "title": _title_from_source(source_text),
            "logline": _logline(segments),
            "professional_contract": {
                "requires_named_characters": True,
                "requires_conflict_relationship_change": True,
                "requires_scene_time_place_action_dialogue": True,
                "requires_rhythm_emotion_visual_expression": True,
            },
            "lineage": {
                "source_digest": source_digest,
                "source_revision_id": _safe_token(body.get("source_revision_id")),
                "source_revision_digest": str(body.get("source_revision_digest") or ""),
                "parent_candidate_digest": body.get("parent_candidate_digest") or "",
                "revision_instruction": _clean_text(body.get("revision_instruction")),
            },
        },
        "script_revision": {
            "revision_id": revision_id,
            "revision_number": 1 if not body.get("parent_candidate_digest") else 2,
            "source_digest": source_digest,
            "draft_text": _expanded_script_text(segments, character_rows, scene_rows),
            "revision_instruction": _clean_text(body.get("revision_instruction")),
            "structure": _script_structure(segments),
            "script_contract": {
                "named_character_count": len(character_rows),
                "scene_count": len(scene_rows),
                "has_dialogue_or_sound_design": _has_dialogue_or_sound(source_text),
                "lineage_state": "candidate_pending_confirmation",
            },
        },
        "sequence": {
            "sequence_id": sequence_id,
            "name": f"{_title_from_source(source_text)} · 制作序列",
            "target_duration_seconds": round(sum(float(shot["duration_seconds"]) for shot in shot_rows), 2),
            "dynamic_policy": {
                "source_segment_count": len(segments),
                "shot_count_decided_by_content": True,
                "fixed_profile_forbidden": ["4x15", "4×15", "10x6", "10×6", "fixed_shot_count"],
            },
        },
        "characters": character_rows,
        "scenes": scene_rows,
        "assets": asset_rows,
        "shots": shot_rows,
        "asset_bible": {
            "status": "pending_confirmation",
            "character_refs": [row["character_id"] for row in character_rows],
            "scene_refs": [row["scene_id"] for row in scene_rows],
            "prop_refs": [row["asset_id"] for row in asset_rows if row["kind"] == "prop"],
            "closeup_refs": [row["asset_id"] for row in asset_rows if row["kind"] == "closeup"],
            "reference_set_refs": [row["asset_id"] for row in asset_rows if row["kind"] == "reference_set"],
            "style_refs": [row["asset_id"] for row in asset_rows if row["kind"] == "style"],
            "production_aid_refs": [row["asset_id"] for row in asset_rows if row["kind"] in PRODUCTION_AID_KINDS],
            "continuity_policy": "creator_confirmed_before_provider_dispatch",
        },
        "m6_scope_review": scope_review,
        "knowledge_context": _knowledge_context(source_digest),
        "review_requirements": _review_requirements(),
        "issue_ledger": {
            "schema_version": "afs.m6.issue_ledger.v0.1",
            "status": "open_zero_p0_p1",
            "findings": [],
            "residual_risk": ["deterministic_zero_cost_planner_is_not_provider_creative_quality"],
        },
        "delivery_id": f"m6-delivery-{candidate_key}",
        "timeline_refs": [f"timeline:m6:{sequence_id}"],
        "rights_refs": ["rights:project-original-or-user-supplied-pending-confirmation"],
    }
    validation = validate_m6_candidate(candidate)
    return {
        "artifact_type": "afs_m6_script_plan_asset_bible_preview",
        "schema_version": M6_SCHEMA_VERSION,
        "project_id": project_id,
        "candidate": candidate,
        "candidate_digest": canonical_digest(candidate),
        "validation": validation,
        "provider_dispatch_count": 0,
        "cost_usd": 0,
        "non_claims": [
            "not_provider_smoke",
            "not_generated_media_qa",
            "not_creative_qa",
            "not_owner_acceptance",
            "not_business_validation",
        ],
    }


def validate_m6_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    if candidate.get("schema_version") != FILM_SCHEMA_VERSION or candidate.get("m6_schema_version") != M6_SCHEMA_VERSION:
        findings.append(_finding("P0", "schema", "candidate must carry both film and M6 schema versions"))
    if candidate.get("trusted_candidate") is not True:
        findings.append(_finding("P0", "trusted_candidate", "candidate must be explicitly trusted after preview validation"))
    provider_dispatch_count = int(candidate.get("provider_dispatch_count") or 0)
    cost_usd = float(candidate.get("cost_usd") or 0)
    if provider_dispatch_count < 0 or cost_usd != 0:
        findings.append(_finding("P0", "provider", "M6 text planning candidate cannot carry negative dispatch or nonzero cost"))
    characters = _rows(candidate, "characters")
    scenes = _rows(candidate, "scenes")
    assets = _rows(candidate, "assets")
    shots = _rows(candidate, "shots")
    if not characters or not scenes or len(shots) < 2:
        findings.append(_finding("P0", "structure", "candidate requires named characters, scenes, and at least two shots"))
    _check_required(characters, ("display_name", "goal", "conflict", "relationship_arc", "change_vector", "appearance", "wardrobe", "age_range", "proportion", "signature_features", "do_not_change"), findings, "character")
    _check_required(scenes, ("name", "space", "time_of_day", "lighting", "season", "continuity", "action", "rhythm", "emotion", "visual_expression", "do_not_change"), findings, "scene")
    _check_required(assets, ("name", "kind", "classification", "rights_boundary", "source", "version", "applicable_scope", "confidence", "do_not_change"), findings, "asset")
    _check_required(shots, ("duration_seconds", "intent", "shot_size", "camera_angle", "camera_movement", "blocking", "sound", "transition", "narrative_purpose", "content_driven_duration_reason"), findings, "shot")
    character_ids = {row.get("character_id") for row in characters}
    scene_ids = {row.get("scene_id") for row in scenes}
    asset_ids = {row.get("asset_id") for row in assets}
    for shot in shots:
        if shot.get("scene_id") not in scene_ids:
            findings.append(_finding("P0", "shot_scene_ref", f"shot {shot.get('shot_id')} references an unknown scene"))
        if not set(shot.get("character_refs") or []) <= character_ids:
            findings.append(_finding("P0", "shot_character_ref", f"shot {shot.get('shot_id')} has unresolved character refs"))
        if not set(shot.get("asset_refs") or []) <= asset_ids:
            findings.append(_finding("P0", "shot_asset_ref", f"shot {shot.get('shot_id')} has unresolved asset refs"))
    durations = [round(float(shot.get("duration_seconds") or 0), 2) for shot in shots]
    if len(durations) == 4 and set(durations) == {15.0}:
        findings.append(_finding("P0", "fixed_profile", "4x15 profile is forbidden for M6 planning"))
    if len(durations) == 10 and set(durations) == {6.0}:
        findings.append(_finding("P0", "fixed_profile", "10x6 profile is forbidden for M6 planning"))
    if len(durations) > 1 and len(set(durations)) == 1 and _has_repeated_shot_timing_semantics(shots):
        findings.append(_finding(
            "P0",
            "dynamic_duration",
            "equal-duration shots require distinct intent, narrative purpose, and duration rationale",
        ))
    sequence = candidate.get("sequence") if isinstance(candidate.get("sequence"), Mapping) else {}
    total = round(sum(durations), 2)
    if round(float(sequence.get("target_duration_seconds") or 0), 2) != total:
        findings.append(_finding("P1", "duration_sum", "sequence target duration must equal the sum of shot durations"))
    bible = candidate.get("asset_bible") if isinstance(candidate.get("asset_bible"), Mapping) else {}
    if bible.get("status") not in {"pending_confirmation", "confirmed"}:
        findings.append(_finding("P0", "asset_bible", "asset Bible must be explicit and confirmation-gated"))
    for required_ref_key in ("character_refs", "scene_refs"):
        if not bible.get(required_ref_key):
            findings.append(_finding("P1", "asset_bible_refs", f"asset Bible missing {required_ref_key}"))
    _validate_m6_asset_scope(assets, bible, findings)
    _validate_m6_scope_review(candidate, characters, scenes, assets, shots, findings)
    knowledge_items = _rows(candidate.get("knowledge_context") or {}, "items")
    for item in knowledge_items:
        missing = [key for key in ("source", "version", "applicable_scope", "confidence", "rights_boundary", "layer", "scope", "promotion_state", "rollback_ref") if not item.get(key)]
        if missing:
            findings.append(_finding("P1", "knowledge_item", f"knowledge item missing {', '.join(missing)}"))
        if item.get("layer") not in KNOWLEDGE_LAYERS or item.get("scope") not in KNOWLEDGE_SCOPES:
            findings.append(_finding("P1", "knowledge_layer_scope", "knowledge item uses unsupported layer or scope"))
        if item.get("promotion_state") == "promoted":
            findings.append(_finding("P1", "knowledge_promotion", "candidate experience cannot be promoted during M6 preview"))
    roles = {row.get("role") for row in _rows(candidate, "review_requirements")}
    if roles != set(REVIEW_ROLES):
        findings.append(_finding("P0", "review_roles", "M6 candidate must carry all six review roles"))
    p0 = sum(item["severity"] == "P0" for item in findings)
    p1 = sum(item["severity"] == "P1" for item in findings)
    if findings:
        raise M6PlanningError(
            "; ".join(f"{item['severity']}:{item['surface']}:{item['issue']}" for item in findings[:6]),
            validator_code=f"candidate_{findings[0]['surface']}",
        )
    scope_review = candidate.get("m6_scope_review") if isinstance(candidate.get("m6_scope_review"), Mapping) else {}
    return {
        "verdict": "PASS",
        "P0": p0,
        "P1": p1,
        "review_roles": sorted(roles),
        "provider_dispatch_count": provider_dispatch_count,
        "cost_usd": cost_usd,
        "canonical_scope": {
            "status": "PASS",
            "characters": len((scope_review.get("canonical") or {}).get("characters") or []),
            "scenes": len((scope_review.get("canonical") or {}).get("scenes") or []),
            "props": len((scope_review.get("canonical") or {}).get("props") or []),
            "production_aids": len(scope_review.get("production_aids") or []),
        },
    }


def _has_repeated_shot_timing_semantics(shots: list[Mapping[str, Any]]) -> bool:
    for key in ("intent", "narrative_purpose", "content_driven_duration_reason"):
        values = [_normalized_semantic_text(shot.get(key)) for shot in shots]
        if any(not value for value in values) or len(set(values)) != len(shots):
            return True
        if any(
            SequenceMatcher(None, left, right, autojunk=False).ratio() >= 0.8
            for index, left in enumerate(values)
            for right in values[index + 1:]
        ):
            return True
    return False


def _normalized_semantic_text(value: Any) -> str:
    text = str(value or "").casefold()
    text = re.sub(r"(?:第|镜头)\s*[0-9一二三四五六七八九十]+\s*(?:个|号|段|镜头|阶段|步|幕|场)?", "", text)
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE)


def _character_row(project_key: str, candidate_key: str, index: int, name: str, source_text: str) -> dict[str, Any]:
    return {
        "character_id": f"{project_key}-m6-character-{index}-{candidate_key}",
        "display_name": name,
        "aliases": [],
        "goal": _field_from_source(source_text, ("目标", "goal"), f"{name}必须把场景中的核心选择落到可见行动。"),
        "conflict": _field_from_source(source_text, ("冲突", "conflict"), f"{name}面对关系压力与制作限制的双重阻力。"),
        "relationship_arc": _field_from_source(source_text, ("关系", "relationship"), f"{name}与其他角色的信任从试探转向共同决定。"),
        "change_vector": _field_from_source(source_text, ("变化", "change"), f"{name}从犹豫进入明确行动。"),
        "appearance": _field_from_source(source_text, ("外观", "appearance"), f"{name}的外观由用户文本确认，进入资产Bible待审。"),
        "wardrobe": _field_from_source(source_text, ("服装", "wardrobe"), "服装保持场景职业身份与季节连续性。"),
        "age_range": _field_from_source(source_text, ("年龄", "age"), "成人，具体年龄段待创作者确认。"),
        "proportion": _field_from_source(source_text, ("比例", "proportion"), "真人影视比例，镜头间不改变体态。"),
        "signature_features": [_field_from_source(source_text, ("标志", "signature"), f"{name}的可识别轮廓和动作习惯")],
        "do_not_change": ["身份", "年龄段", "发型轮廓", "服装主色", "关系位置"],
        "source_evidence_refs": [_evidence(source_text, name)],
    }


def _scene_row(project_key: str, candidate_key: str, index: int, name: str, source_text: str, revision_id: str) -> dict[str, Any]:
    return {
        "scene_id": f"{project_key}-m6-scene-{index}-{candidate_key}",
        "name": name,
        "lineage": [revision_id],
        "space": _field_from_source(source_text, ("空间", "space"), name),
        "time_of_day": _field_from_source(source_text, ("时间", "time"), "时间由剧本文本确认，缺口进入评审"),
        "lighting": _field_from_source(source_text, ("光线", "lighting"), "自然光与实用光保持连续"),
        "season": _field_from_source(source_text, ("季节", "season"), "季节连续性待确认"),
        "continuity": _field_from_source(source_text, ("连续性", "continuity"), "角色位置、道具状态和光线方向必须跨镜保持"),
        "action": _field_from_source(source_text, ("动作", "action"), "围绕角色目标组织可拍行动"),
        "dialogue_refs": _dialogue_refs(source_text),
        "rhythm": _field_from_source(source_text, ("节奏", "rhythm"), "由动作密度和对白停顿决定"),
        "emotion": _field_from_source(source_text, ("情绪", "emotion"), "从压抑到明确"),
        "visual_expression": _field_from_source(source_text, ("视觉", "visual"), "通过空间层次、视线方向和道具特写表达"),
        "do_not_change": ["空间朝向", "时间段", "光线方向", "关键道具位置"],
        "source_evidence_refs": [_evidence(source_text, name)],
    }


def _asset_rows(
    project_key: str,
    candidate_key: str,
    props: list[str],
    closeups: list[str],
    styles: list[str],
    characters: list[Mapping[str, Any]],
    scenes: list[Mapping[str, Any]],
    source_digest: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for kind, values in (("prop", props), ("closeup", closeups), ("style", styles)):
        for value in values:
            rows.append(_asset_row(project_key, candidate_key, kind, value, source_digest, len(rows) + 1))
    if not any(row["kind"] == "reference_set" for row in rows):
        ref_name = f"{characters[0]['display_name']}与{scenes[0]['name']}连续性参考集"
        rows.append(_asset_row(project_key, candidate_key, "reference_set", ref_name, source_digest, len(rows) + 1))
    return rows


def _asset_row(project_key: str, candidate_key: str, kind: str, name: str, source_digest: str, index: int) -> dict[str, Any]:
    return {
        "asset_id": f"{project_key}-m6-{kind}-{index}-{candidate_key}",
        "name": name,
        "kind": kind,
        **m6_asset_scope_fields(kind),
        "source": "user_supplied_text_or_zero_cost_deterministic_preview",
        "version": "candidate.v1",
        "applicable_scope": "project",
        "confidence": 0.74,
        "rights_boundary": "user_supplied_or_project_original_pending_confirmation",
        "style": name if kind == "style" else "",
        "do_not_change": ["名称", "用途", "相对尺寸", "镜头间连续状态"],
        "source_digest": source_digest,
    }


def m6_asset_scope_fields(kind: str) -> dict[str, str]:
    normalized = str(kind or "").strip()
    if normalized in CANONICAL_ASSET_KINDS:
        return {
            "classification": "canonical_prop",
            "canonical_asset_type": "prop",
            "production_aid_type": "",
            "scope_authority": "user_supplied_canonical_scope",
        }
    if normalized in PRODUCTION_AID_KINDS:
        return {
            "classification": "production_aid",
            "canonical_asset_type": "",
            "production_aid_type": normalized,
            "scope_authority": "production_aid_not_canonical_asset",
        }
    return {
        "classification": "unknown",
        "canonical_asset_type": "",
        "production_aid_type": "",
        "scope_authority": "unclassified",
    }


def _shot_rows(
    project_key: str,
    candidate_key: str,
    segments: list[str],
    characters: list[Mapping[str, Any]],
    scenes: list[Mapping[str, Any]],
    assets: list[Mapping[str, Any]],
    revision_id: str,
) -> list[dict[str, Any]]:
    rows = []
    for index, segment in enumerate(segments, start=1):
        scene = scenes[(index - 1) % len(scenes)]
        character = characters[(index - 1) % len(characters)]
        duration = _duration_for_segment(segment, index)
        asset_refs = [assets[(index - 1) % len(assets)]["asset_id"]] if assets else []
        rows.append({
            "shot_id": f"{project_key}-m6-shot-{index}-{candidate_key}",
            "scene_id": scene["scene_id"],
            "duration_seconds": duration,
            "intent": segment[:300],
            "character_refs": [character["character_id"]],
            "asset_refs": asset_refs,
            "shot_size": _shot_size(segment, index),
            "camera_angle": "平视为主，按角色权力变化微调机位",
            "camera_movement": _camera_movement(segment),
            "blocking": f"{character['display_name']}在{scene['name']}内完成可见调度，动作终点为下一镜连续性锚点。",
            "sound": _sound_design(segment),
            "transition": "动作或视线匹配转场" if index < len(segments) else "情绪收束后切出",
            "narrative_purpose": _narrative_purpose(index, len(segments)),
            "content_driven_duration_reason": f"由该段 {len(segment)} 字、对白/动作密度和叙事位置计算；不是固定镜头模板。",
            "source_evidence_refs": [{"source_kind": "script_revision", "source_id": revision_id, "quote": segment[:240]}],
        })
    return rows


def m6_source_canonical_scope(source_text: str) -> dict[str, list[str]]:
    text = _clean_source_text(source_text)
    return {
        "characters": _extract_named_characters(text),
        "scenes": _extract_scenes(text),
        "props": _dedupe(
            _extract_list_after_labels(text, ("道具", "props", "prop"))
            + _extract_declared_names(text, ("道具名称", "道具名", "prop name", "prop names"))
        )[:12],
        "closeups": _extract_list_after_labels(text, ("特写", "closeups", "closeup")),
        "styles": _extract_list_after_labels(text, ("风格", "视觉风格", "style")),
    }


def build_m6_scope_review(
    *,
    source_text: str,
    characters: list[Mapping[str, Any]],
    scenes: list[Mapping[str, Any]],
    assets: list[Mapping[str, Any]],
    shots: list[Mapping[str, Any]],
) -> dict[str, Any]:
    source_scope = m6_source_canonical_scope(source_text)
    canonical = {
        "characters": list(source_scope["characters"]),
        "scenes": list(source_scope["scenes"]),
        "props": list(source_scope["props"]),
    }
    candidate_canonical = {
        "characters": [_clean_label(str(row.get("display_name") or "")) for row in characters if _clean_label(str(row.get("display_name") or ""))],
        "scenes": [_clean_label(str(row.get("name") or "")) for row in scenes if _clean_label(str(row.get("name") or ""))],
        "props": [_clean_label(str(row.get("name") or "")) for row in assets if row.get("kind") == "prop" and _clean_label(str(row.get("name") or ""))],
    }
    drift = _canonical_scope_drift(canonical, candidate_canonical)
    additions = _scope_additions(characters, scenes, assets, shots)
    production_aids = [
        {
            "asset_id": str(row.get("asset_id") or ""),
            "name": str(row.get("name") or ""),
            "kind": str(row.get("kind") or ""),
            "classification": "production_aid",
            "production_aid_type": str(row.get("production_aid_type") or row.get("kind") or ""),
        }
        for row in assets
        if str(row.get("kind") or "") in PRODUCTION_AID_KINDS
    ]
    return {
        "schema_version": M6_SCOPE_REVIEW_SCHEMA_VERSION,
        "source_authority": "user_supplied_canonical_scope",
        "canonical": canonical,
        "candidate_canonical": candidate_canonical,
        "production_aids": production_aids,
        "proposed_additions": additions,
        "proposed_renames": drift["renamed_canonical_entities"],
        "proposed_expansions": _scope_expansions(characters, scenes, assets, shots),
        "proposed_classifications": _scope_classifications(characters, scenes, assets),
        "affected_associations": _scope_associations(characters, scenes, assets, shots),
        "fail_closed": {
            "status": "pass" if not drift["reasons"] else "blocked",
            "reasons": drift["reasons"],
            "extra_canonical_entities": drift["extra_canonical_entities"],
            "missing_canonical_entities": drift["missing_canonical_entities"],
            "renamed_canonical_entities": drift["renamed_canonical_entities"],
        },
    }


def _scope_additions(
    characters: list[Mapping[str, Any]],
    scenes: list[Mapping[str, Any]],
    assets: list[Mapping[str, Any]],
    shots: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    additions: list[dict[str, Any]] = []
    for row in characters:
        additions.append({
            "item_type": "character",
            "id": str(row.get("character_id") or ""),
            "name": str(row.get("display_name") or ""),
            "classification": "canonical_character",
            "authority": "user_supplied_canonical_scope",
        })
    for row in scenes:
        additions.append({
            "item_type": "scene",
            "id": str(row.get("scene_id") or ""),
            "name": str(row.get("name") or ""),
            "classification": "canonical_scene",
            "authority": "user_supplied_canonical_scope",
        })
    for row in assets:
        kind = str(row.get("kind") or "")
        additions.append({
            "item_type": "asset",
            "id": str(row.get("asset_id") or ""),
            "name": str(row.get("name") or ""),
            "kind": kind,
            "classification": str(row.get("classification") or ""),
            "authority": "user_supplied_canonical_scope" if kind == "prop" else "production_aid_pending_confirmation",
        })
    for index, row in enumerate(shots, start=1):
        additions.append({
            "item_type": "shot",
            "id": str(row.get("shot_id") or ""),
            "name": f"镜头{index}",
            "classification": "production_shot",
            "duration_seconds": float(row.get("duration_seconds") or 0),
        })
    return additions


def _scope_expansions(
    characters: list[Mapping[str, Any]],
    scenes: list[Mapping[str, Any]],
    assets: list[Mapping[str, Any]],
    shots: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    expansions: list[dict[str, Any]] = []
    for row in characters:
        expansions.append({
            "item_type": "character",
            "name": str(row.get("display_name") or ""),
            "fields": ["goal", "conflict", "relationship_arc", "change_vector", "appearance", "continuity_locks"],
        })
    for row in scenes:
        expansions.append({
            "item_type": "scene",
            "name": str(row.get("name") or ""),
            "fields": ["space", "time_of_day", "lighting", "season", "continuity", "action", "rhythm", "emotion", "visual_expression"],
        })
    for row in assets:
        expansions.append({
            "item_type": "asset",
            "name": str(row.get("name") or ""),
            "fields": ["source", "rights_boundary", "version", "applicable_scope", "do_not_change"],
        })
    for index, row in enumerate(shots, start=1):
        expansions.append({
            "item_type": "shot",
            "name": f"镜头{index}",
            "fields": ["intent", "duration_seconds", "shot_size", "camera_angle", "camera_movement", "blocking", "sound", "transition"],
        })
    return expansions


def _scope_classifications(
    characters: list[Mapping[str, Any]],
    scenes: list[Mapping[str, Any]],
    assets: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(
        {
            "item_type": "character",
            "id": str(row.get("character_id") or ""),
            "name": str(row.get("display_name") or ""),
            "classification": "canonical_character",
        }
        for row in characters
    )
    rows.extend(
        {
            "item_type": "scene",
            "id": str(row.get("scene_id") or ""),
            "name": str(row.get("name") or ""),
            "classification": "canonical_scene",
        }
        for row in scenes
    )
    rows.extend(
        {
            "item_type": "asset",
            "id": str(row.get("asset_id") or ""),
            "name": str(row.get("name") or ""),
            "kind": str(row.get("kind") or ""),
            "classification": str(row.get("classification") or ""),
            "canonical_asset_type": str(row.get("canonical_asset_type") or ""),
            "production_aid_type": str(row.get("production_aid_type") or ""),
        }
        for row in assets
    )
    return rows


def _scope_associations(
    characters: list[Mapping[str, Any]],
    scenes: list[Mapping[str, Any]],
    assets: list[Mapping[str, Any]],
    shots: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    character_names = {str(row.get("character_id") or ""): str(row.get("display_name") or "") for row in characters}
    scene_names = {str(row.get("scene_id") or ""): str(row.get("name") or "") for row in scenes}
    asset_by_id = {str(row.get("asset_id") or ""): row for row in assets}
    prop_assets = [row for row in assets if row.get("kind") == "prop"]
    aid_assets = [row for row in assets if str(row.get("kind") or "") in PRODUCTION_AID_KINDS]
    associations: list[dict[str, Any]] = [
        {
            "association_type": "asset_bible.character_refs",
            "names": [str(row.get("display_name") or "") for row in characters],
            "classification": "canonical_character_refs",
        },
        {
            "association_type": "asset_bible.scene_refs",
            "names": [str(row.get("name") or "") for row in scenes],
            "classification": "canonical_scene_refs",
        },
        {
            "association_type": "asset_bible.prop_refs",
            "names": [str(row.get("name") or "") for row in prop_assets],
            "classification": "canonical_prop_refs_only",
        },
        {
            "association_type": "asset_bible.production_aid_refs",
            "names": [str(row.get("name") or "") for row in aid_assets],
            "classification": "production_aid_refs_not_canonical_props",
        },
    ]
    for index, shot in enumerate(shots, start=1):
        referenced_assets = [asset_by_id.get(str(asset_id or "")) for asset_id in shot.get("asset_refs") or []]
        referenced_assets = [row for row in referenced_assets if row]
        associations.append({
            "association_type": "shot.references",
            "name": f"镜头{index}",
            "scene": scene_names.get(str(shot.get("scene_id") or ""), ""),
            "characters": [character_names.get(str(character_id or ""), "") for character_id in shot.get("character_refs") or []],
            "canonical_props": [str(row.get("name") or "") for row in referenced_assets if row.get("kind") == "prop"],
            "production_aids": [str(row.get("name") or "") for row in referenced_assets if str(row.get("kind") or "") in PRODUCTION_AID_KINDS],
            "duration_seconds": float(shot.get("duration_seconds") or 0),
        })
    return associations


def _canonical_scope_drift(canonical: Mapping[str, list[str]], candidate_canonical: Mapping[str, list[str]]) -> dict[str, Any]:
    extra: list[dict[str, str]] = []
    missing: list[dict[str, str]] = []
    renamed: list[dict[str, str]] = []
    reasons: list[str] = []
    for entity_type in ("characters", "scenes", "props"):
        expected = list(canonical.get(entity_type) or [])
        actual = list(candidate_canonical.get(entity_type) or [])
        missing.extend({"entity_type": entity_type, "name": name} for name in expected if name not in actual)
        extra.extend({"entity_type": entity_type, "name": name} for name in actual if name not in expected)
        if len(expected) == len(actual):
            renamed.extend(
                {
                    "entity_type": entity_type,
                    "before": before,
                    "after": after,
                    "classification": f"canonical_{entity_type[:-1]}_rename",
                }
                for before, after in zip(expected, actual)
                if before != after
            )
    if extra:
        reasons.append("extra_canonical_entities")
    if missing:
        reasons.append("missing_canonical_entities")
    if renamed:
        reasons.append("renamed_canonical_entities")
    return {
        "reasons": reasons,
        "extra_canonical_entities": extra,
        "missing_canonical_entities": missing,
        "renamed_canonical_entities": renamed,
    }


def _validate_m6_asset_scope(
    assets: list[Mapping[str, Any]],
    bible: Mapping[str, Any],
    findings: list[dict[str, str]],
) -> None:
    prop_ids = {row.get("asset_id") for row in assets if row.get("kind") == "prop"}
    closeup_ids = {row.get("asset_id") for row in assets if row.get("kind") == "closeup"}
    reference_set_ids = {row.get("asset_id") for row in assets if row.get("kind") == "reference_set"}
    style_ids = {row.get("asset_id") for row in assets if row.get("kind") == "style"}
    production_aid_ids = closeup_ids | reference_set_ids | style_ids
    for row in assets:
        kind = str(row.get("kind") or "")
        expected = m6_asset_scope_fields(kind)
        if expected["classification"] == "unknown":
            findings.append(_finding("P0", "asset_scope", f"asset {row.get('asset_id')} uses unsupported kind {kind}"))
            continue
        if row.get("classification") != expected["classification"]:
            findings.append(_finding("P0", "asset_scope", f"asset {row.get('asset_id')} classification must be {expected['classification']}"))
        if str(row.get("canonical_asset_type") or "") != expected["canonical_asset_type"]:
            findings.append(_finding("P0", "asset_scope", f"asset {row.get('asset_id')} canonical type drifted"))
        if str(row.get("production_aid_type") or "") != expected["production_aid_type"]:
            findings.append(_finding("P0", "asset_scope", f"asset {row.get('asset_id')} production aid type drifted"))

    prop_refs = set(bible.get("prop_refs") or [])
    if prop_refs != prop_ids:
        findings.append(_finding("P0", "asset_bible_refs", "asset Bible prop_refs must contain only canonical prop assets"))
    if prop_refs & production_aid_ids:
        findings.append(_finding("P0", "asset_bible_refs", "production aids cannot appear in prop_refs"))
    if set(bible.get("closeup_refs") or []) != closeup_ids:
        findings.append(_finding("P0", "asset_bible_refs", "closeup_refs must contain only closeup production aids"))
    if set(bible.get("reference_set_refs") or []) != reference_set_ids:
        findings.append(_finding("P0", "asset_bible_refs", "reference_set_refs must contain only reference set production aids"))
    if set(bible.get("style_refs") or []) != style_ids:
        findings.append(_finding("P0", "asset_bible_refs", "style_refs must contain only style production aids"))
    if set(bible.get("production_aid_refs") or []) != production_aid_ids:
        findings.append(_finding("P0", "asset_bible_refs", "production_aid_refs must enumerate every closeup/reference/style aid"))


def _validate_m6_scope_review(
    candidate: Mapping[str, Any],
    characters: list[Mapping[str, Any]],
    scenes: list[Mapping[str, Any]],
    assets: list[Mapping[str, Any]],
    shots: list[Mapping[str, Any]],
    findings: list[dict[str, str]],
) -> None:
    review = candidate.get("m6_scope_review") if isinstance(candidate.get("m6_scope_review"), Mapping) else None
    if not review:
        findings.append(_finding("P0", "m6_scope_review", "candidate must carry canonical scope review"))
        return
    if review.get("schema_version") != M6_SCOPE_REVIEW_SCHEMA_VERSION:
        findings.append(_finding("P0", "m6_scope_review", "canonical scope review schema mismatch"))
    fail_closed = review.get("fail_closed") if isinstance(review.get("fail_closed"), Mapping) else {}
    if fail_closed.get("status") != "pass":
        findings.append(_finding("P0", "m6_scope_review", f"canonical scope review failed closed: {', '.join(fail_closed.get('reasons') or [])}"))
    for key in ("extra_canonical_entities", "missing_canonical_entities", "renamed_canonical_entities"):
        if fail_closed.get(key):
            findings.append(_finding("P0", "m6_scope_review", f"canonical scope review contains {key}"))

    canonical = review.get("canonical") if isinstance(review.get("canonical"), Mapping) else {}
    expected = {
        "characters": list(canonical.get("characters") or []),
        "scenes": list(canonical.get("scenes") or []),
        "props": list(canonical.get("props") or []),
    }
    actual = {
        "characters": [str(row.get("display_name") or "") for row in characters],
        "scenes": [str(row.get("name") or "") for row in scenes],
        "props": [str(row.get("name") or "") for row in assets if row.get("kind") == "prop"],
    }
    for entity_type, expected_names in expected.items():
        if actual[entity_type] != expected_names:
            findings.append(_finding("P0", "m6_scope_review", f"{entity_type} must exactly match user canonical scope"))
    if not review.get("proposed_additions") or not review.get("proposed_expansions"):
        findings.append(_finding("P0", "m6_scope_review", "confirmation scope review must enumerate additions and expansions"))
    if len(review.get("proposed_classifications") or []) < len(characters) + len(scenes) + len(assets):
        findings.append(_finding("P0", "m6_scope_review", "confirmation scope review must enumerate classifications"))
    association_types = {item.get("association_type") for item in review.get("affected_associations") or [] if isinstance(item, Mapping)}
    required_associations = {"asset_bible.character_refs", "asset_bible.scene_refs", "asset_bible.prop_refs", "asset_bible.production_aid_refs", "shot.references"}
    if not required_associations <= association_types:
        findings.append(_finding("P0", "m6_scope_review", "confirmation scope review must enumerate affected associations"))


def _knowledge_context(source_digest: str) -> dict[str, Any]:
    return {
        "schema_version": "afs.m6.knowledge_context.v0.1",
        "rollback_supported": True,
        "items": [
            {
                "knowledge_id": "m6-film-writing-contract",
                "layer": "fact",
                "scope": "team",
                "source": "AFS internal film-domain contract",
                "version": "v0.1",
                "applicable_scope": "professional script and scene breakdown planning",
                "confidence": 0.78,
                "rights_boundary": "internal_contract_no_external_training_claim",
                "promotion_state": "evaluated_contract",
                "rollback_ref": "knowledge:m6-film-writing-contract:v0.1",
            },
            {
                "knowledge_id": f"m6-project-decision-{source_digest[:10]}",
                "layer": "project_decision",
                "scope": "project",
                "source": "current project source text",
                "version": "candidate.v1",
                "applicable_scope": "this project only until creator confirmation",
                "confidence": 0.68,
                "rights_boundary": "user_supplied_project_private",
                "promotion_state": "candidate_not_promoted",
                "rollback_ref": f"candidate:{source_digest[:16]}",
            },
            {
                "knowledge_id": "m6-feedback-candidate-rule",
                "layer": "long_term_experience",
                "scope": "user",
                "source": "candidate experience policy",
                "version": "v0.1",
                "applicable_scope": "future feedback must be evaluated before promotion",
                "confidence": 0.72,
                "rights_boundary": "feedback_is_evidence_not_training_consent",
                "promotion_state": "candidate_not_promoted",
                "rollback_ref": "policy:m6-feedback-candidate-rule:v0.1",
            },
        ],
    }


def _review_requirements() -> list[dict[str, Any]]:
    return [
        {"role": role, "required": True, "status": "pending", "must_record": ["finding", "severity", "evidence_ref", "retest_state"]}
        for role in REVIEW_ROLES
    ]


def _source_segments(text: str) -> list[str]:
    explicit = [part.strip(" \t-—") for part in re.split(r"\n+|(?:^|[；;。！？!?])\s*", text) if part.strip(" \t-—")]
    segments = [segment for segment in explicit if not re.match(r"^(角色|人物|场景|地点|道具|特写|风格|目标|冲突|关系|变化|时间|光线|季节|连续性)\s*[:：]", segment, re.I)]
    if len(segments) < 2:
        segments = [part.strip() for part in re.split(r"[，,]\s*", text) if len(part.strip()) >= 8][:6]
    return segments[:9]


def _extract_named_characters(text: str) -> list[str]:
    values = _dedupe(
        _extract_list_after_labels(text, ("角色", "人物", "characters", "cast"))
        + _extract_declared_names(
            text,
            ("角色名称", "角色名", "人物名称", "人物名", "character name", "character names"),
        )
    )
    if values:
        return values[:12]
    matches = re.findall(r"([\u4e00-\u9fff]{2,4})(?:说|问|看|走|跑|递|打开|发现|决定|进入|握住|停下)", text)
    values.extend(matches)
    values.extend(re.findall(r"\b([A-Z][a-z]{2,18})\b", text))
    return _dedupe(values)[:12]


def _extract_scenes(text: str) -> list[str]:
    values = _dedupe(
        _extract_list_after_labels(text, ("场景", "地点", "locations", "scenes"))
        + _extract_declared_names(
            text,
            ("场景名称", "场景名", "地点名称", "地点名", "scene name", "scene names", "location name", "location names"),
        )
    )
    if values:
        return values[:12]
    values.extend(re.findall(r"(?:在|进入|回到)([\u4e00-\u9fffA-Za-z0-9·\- ]{2,24})(?:里|内|上|下|前|后|，|。|；|;|,)", text))
    return _dedupe(values)[:12]


def _extract_list_after_labels(text: str, labels: tuple[str, ...]) -> list[str]:
    rows: list[str] = []
    label_pattern = "|".join(re.escape(label) for label in labels)
    for match in re.finditer(rf"(?:{label_pattern})\s*[:：]\s*([^\n。；;]+)", text, re.I):
        raw = match.group(1)
        raw = re.sub(r"[（(][^）)]*[）)]", "", raw)
        rows.extend(
            part.strip(" 、,，/")
            for part in re.split(r"[、,，/]|(?:\s+(?:and|和|与)\s+)", raw, flags=re.I)
            if part.strip(" 、,，/")
        )
    return _dedupe([_clean_label(item) for item in rows if _clean_label(item)])


def _extract_declared_names(text: str, labels: tuple[str, ...]) -> list[str]:
    rows: list[str] = []
    label_pattern = "|".join(re.escape(label) for label in sorted(labels, key=len, reverse=True))
    declaration = re.compile(rf"(?:{label_pattern})\s*(?:是|为|[:：])?\s*", re.I)
    separator = re.compile(r"\s*(?:[、,，/]|和|与|\band\b)\s*", re.I)
    for match in declaration.finditer(text):
        prefix = text[max(0, match.start() - 24):match.start()]
        if re.search(r"(?:不要|不得|禁止|避免).{0,8}(?:新增|添加|使用|采用)", prefix):
            continue
        if re.search(r"(?:do not|don't|must not).{0,24}(?:add|use)", prefix, re.I):
            continue
        cursor = match.end()
        while len(rows) < 12:
            quoted = _quoted_value_at(text, cursor)
            if quoted is None:
                break
            value, cursor = quoted
            cleaned = _clean_label(value)
            if cleaned:
                rows.append(cleaned)
            joined = separator.match(text, cursor)
            if joined is None:
                break
            cursor = joined.end()
    return _dedupe(rows)


def _quoted_value_at(text: str, start: int) -> tuple[str, int] | None:
    cursor = start
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    pairs = {"“": "”", '"': '"', "「": "」", "『": "』", "'": "'"}
    closing = pairs.get(text[cursor:cursor + 1])
    if closing is None:
        return None
    end = text.find(closing, cursor + 1)
    if end < 0:
        return None
    return text[cursor + 1:end], end + 1


def _field_from_source(text: str, labels: tuple[str, ...], default_text: str) -> str:
    values = _extract_list_after_labels(text, labels)
    return values[0] if values else default_text


def _dialogue_refs(text: str) -> list[str]:
    refs = [item.strip() for item in re.findall(r"[“\"']([^”\"']{1,120})[”\"']", text)]
    return refs[:8] or ["对白或声音设计待创作者确认"]


def _has_dialogue_or_sound(text: str) -> bool:
    return bool(re.search(r"[“\"']|说|问|声音|音效|沉默|旁白", text))


def _expanded_script_text(segments: list[str], characters: list[Mapping[str, Any]], scenes: list[Mapping[str, Any]]) -> str:
    lead = characters[0]["display_name"]
    lines = []
    for index, segment in enumerate(segments, start=1):
        scene = scenes[(index - 1) % len(scenes)]["name"]
        lines.append(f"第{index}段｜{scene}：{segment} {lead}的目标、冲突和关系变化必须通过动作、对白或沉默被看见。")
    return "\n".join(lines)


def _script_structure(segments: list[str]) -> dict[str, Any]:
    midpoint = max(1, len(segments) // 2)
    return {
        "sequence_count": 1,
        "beat_count": len(segments),
        "turning_points": [
            {"beat_order": 1, "function": "setup_goal_conflict"},
            {"beat_order": midpoint, "function": "pressure_or_reveal"},
            {"beat_order": len(segments), "function": "changed_state"},
        ],
    }


def _duration_for_segment(segment: str, index: int) -> float:
    dialogue_bonus = 1.25 if _has_dialogue_or_sound(segment) else 0.0
    action_bonus = min(2.5, len(re.findall(r"走|跑|递|拿|打开|关闭|转身|追|停|看|发现|举起|放下", segment)) * 0.55)
    density = min(4.0, len(segment) / 32)
    digest_offset = (int(canonical_digest({"segment": segment, "index": index})[:2], 16) % 7) / 10
    return round(2.75 + density + dialogue_bonus + action_bonus + digest_offset, 2)


def _shot_size(segment: str, index: int) -> str:
    if re.search(r"特写|眼|手|道具|照片|屏幕|镜头", segment):
        return "特写"
    if re.search(r"进入|场景|空间|屋顶|街|室|棚|房间|大厅", segment):
        return "大全景"
    if _has_dialogue_or_sound(segment):
        return "中近景"
    return "中景" if index % 2 else "近景"


def _camera_movement(segment: str) -> str:
    if re.search(r"追|跑|冲|移动|穿过", segment):
        return "跟拍或横移，保持动作连续"
    if re.search(r"发现|意识|看见|望", segment):
        return "缓慢推进到反应"
    return "稳定构图内轻微调整"


def _sound_design(segment: str) -> str:
    if _has_dialogue_or_sound(segment):
        return "保留对白、呼吸和关键环境声，音乐不遮挡信息"
    return "环境声建立空间，必要时用沉默承接情绪"


def _narrative_purpose(index: int, total: int) -> str:
    if index == 1:
        return "建立目标、空间和第一层冲突"
    if index == total:
        return "呈现选择后的新状态并留下连续性锚点"
    return "推进压力、关系和可见行动"


def _title_from_source(text: str) -> str:
    first = _source_segments(text)[0] if _source_segments(text) else text
    return re.sub(r"\s+", "", first)[:32] or "未命名制作方案"


def _logline(segments: list[str]) -> str:
    return " / ".join(segment[:80] for segment in segments[:2])


def _evidence(text: str, quote: str) -> dict[str, Any]:
    start = max(0, text.find(quote))
    return {"source_kind": "source_text", "source_id": "m6_input", "start": start, "end": start + len(quote), "quote": quote}


def _rows(value: Mapping[str, Any], name: str) -> list[dict[str, Any]]:
    row = value.get(name) if isinstance(value, Mapping) else None
    return [dict(item) for item in row] if isinstance(row, list) else []


def _check_required(rows: list[Mapping[str, Any]], keys: tuple[str, ...], findings: list[dict[str, str]], surface: str) -> None:
    for index, row in enumerate(rows, start=1):
        missing = [key for key in keys if row.get(key) in (None, "", [])]
        if missing:
            findings.append(_finding("P1", surface, f"{surface} {index} missing {', '.join(missing)}"))


def _finding(severity: str, surface: str, issue: str) -> dict[str, str]:
    return {"severity": severity, "surface": surface, "issue": issue}


def _safe_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "").strip()).strip("-").lower()
    return token[:40] or "project"


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _clean_source_text(value: Any) -> str:
    normalized = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.strip() for line in normalized.split("\n")).strip()


def _clean_label(value: str) -> str:
    return str(value or "").strip()


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.lower()
        if key and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _contract_error(error: str, message: str, *, project_id: str, stage: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=safe_error_detail(
            error,
            "contract_rejected",
            message=message,
            project_id=project_id,
            stage=stage,
            details={"provider_dispatch_count": 0, "cost_usd": 0},
        ),
    )


__all__ = (
    "M6_SCHEMA_VERSION",
    "REVIEW_ROLES",
    "build_m6_script_plan_asset_bible",
    "register_runtime_m6_script_plan_asset_bible_routes",
    "validate_m6_candidate",
)
