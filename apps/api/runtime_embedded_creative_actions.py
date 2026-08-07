from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from agentflow.harness.json_io import exclusive_file_lock, write_json
from agentflow_studio.model_gateway.company_secrets import SERVER_CODEX_SERVICE_ID
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import (
    ProviderDispatchRequest,
    load_provider_registry,
    structured_output_schema_digest,
)
from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_llm_enhancement import llm_provider_gate
from apps.api.runtime_logging import client_request_id_from_request
from apps.api.runtime_film_production_graph import _sequence_workspace_projection
from apps.api.runtime_script_core_truth import current_script_revision_binding
from apps.api.runtime_production_graph import (
    GraphIdempotencyConflict,
    GraphVersionConflict,
    ProductionGraphError,
    ProductionGraphStore,
    canonical_digest,
)
from apps.api.runtime_store import RuntimeStore, public_job, read_json, reject_unsafe_payload, safe_id
from apps.api.runtime_tracing import artifact_refs, write_run_trace


from apps.api.runtime_embedded_screenplay_safety import (
    MAX_STORYBOARD_DURATION_SECONDS,
    _contains_unsafe_fragment,
    _production_brief_for_request,
    _safe_number,
    _safe_production_brief,
    _safe_text,
    _safe_token,
    _safe_validation_reason,
    _screenplay_candidate_schema,
    _shot_plan_duration_assessment,
    _validate_preview_payload,
)

EMBEDDED_CREATIVE_CONTRACT_ID = "afs.runtime.embedded_creative_action.v0.2"
EMBEDDED_CREATIVE_NON_CLAIMS = [
    "not_canvas_mutation_until_user_apply",
    "not_paid_image_video_generation",
    "not_human_acceptance",
    "not_business_validation",
]


class EmbeddedProductionBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_duration_seconds: float = Field(ge=5, le=MAX_STORYBOARD_DURATION_SECONDS)
    duration_source: Literal["script_explicit", "creator_default", "creator_selected"]
    tolerance_seconds: float = Field(ge=0, le=MAX_STORYBOARD_DURATION_SECONDS)
    source_revision_id: str = Field(min_length=1, max_length=140)
    source_digest: str = Field(min_length=64, max_length=64)
    requires_creator_confirmation: bool = True
    source_duration_conflict: bool = False

    @model_validator(mode="after")
    def validate_tolerance(self) -> "EmbeddedProductionBrief":
        if self.tolerance_seconds > self.target_duration_seconds:
            raise ValueError("duration tolerance cannot exceed target duration")
        if self.source_digest and not re.fullmatch(r"[a-f0-9]{64}", self.source_digest):
            raise ValueError("source digest is invalid")
        return self


class EmbeddedCreativeActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: Literal["script_revision", "shot_breakdown"] = "script_revision"
    node_id: str = Field(min_length=1, max_length=160)
    node_type: str = Field(min_length=1, max_length=80)
    source_text: str = Field(min_length=1, max_length=18000)
    mode: Literal[
        "concise_polish",
        "professional_expansion",
        "structure_pace",
        "character_relationship",
        "dialogue_action",
        "visual_production",
        "dynamic_shot_breakdown",
    ] = "professional_expansion"
    context_summary: dict[str, Any] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list, max_length=8)
    production_brief: EmbeddedProductionBrief | None
    source_revision_id: str = Field(max_length=140)
    source_digest: str = Field(max_length=64)
    provider_service_id: str = SERVER_CODEX_SERVICE_ID
    generated_at: str = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def validate_source_binding(self) -> "EmbeddedCreativeActionRequest":
        actual_digest = _text_digest(self.source_text)
        if self.action_type == "shot_breakdown":
            if not self.source_revision_id or not self.source_digest:
                raise ValueError("shot breakdown requires the current script revision binding")
            if self.production_brief is None:
                raise ValueError("shot breakdown requires a confirmed production brief")
        if self.source_digest and self.source_digest != actual_digest:
            raise ValueError("source digest does not match source text")
        if self.source_revision_id and not self.source_digest:
            raise ValueError("source revision requires source digest")
        if self.production_brief:
            if self.production_brief.source_digest and self.production_brief.source_digest != actual_digest:
                raise ValueError("production brief source digest does not match source text")
            if (
                self.source_revision_id
                and self.production_brief.source_revision_id
                and self.production_brief.source_revision_id != self.source_revision_id
            ):
                raise ValueError("production brief source revision does not match request")
            if self.action_type == "shot_breakdown" and (
                self.production_brief.source_revision_id != self.source_revision_id
                or self.production_brief.source_digest != self.source_digest
            ):
                raise ValueError("production brief must bind the current script revision")
        return self


class EmbeddedCreativeActionApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_graph_version: int = Field(ge=0)
    expected_request_digest: str = Field(min_length=64, max_length=64)
    expected_production_brief: EmbeddedProductionBrief

    @model_validator(mode="after")
    def validate_script_binding(self) -> "EmbeddedCreativeActionApplyRequest":
        if (
            not self.expected_production_brief.source_revision_id
            or not self.expected_production_brief.source_digest
        ):
            raise ValueError("shot plan apply requires the current script revision binding")
        return self


def register_runtime_embedded_creative_action_routes(
    app: FastAPI,
    store: RuntimeStore,
    auth: RuntimeAuthStore,
) -> None:
    graph_store = ProductionGraphStore(store)

    def require_access(request: Request, project_id: str) -> None:
        if auth.enabled():
            user = auth.require_user(request)
            if not auth.user_can_access_project(str(user["user_id"]), project_id):
                raise HTTPException(status_code=403, detail="project access denied")

    @app.post("/projects/{project_id}/embedded-creative-actions/preview")
    def embedded_creative_action_preview(
        project_id: str,
        body: EmbeddedCreativeActionRequest,
        request: Request,
    ) -> dict[str, Any]:
        require_access(request, project_id)
        store.ensure_project_manifest(project_id)
        if body.action_type == "shot_breakdown":
            _require_current_script_binding(
                store,
                project_id,
                revision_id=body.source_revision_id,
                source_digest=body.source_digest,
                stage="preview",
            )
        client_request_id = client_request_id_from_request(request)
        job_id = store.new_job_id("embedded_creative_action", project_id)
        if client_request_id:
            normalized = _safe_client_request_id(client_request_id)
            if normalized != client_request_id:
                raise HTTPException(status_code=422, detail="invalid client request id")
            claim = _claim_embedded_creative_request(
                store,
                project_id,
                normalized,
                request_digest=_embedded_request_digest(body),
                job_id=job_id,
            )
            if claim["state"] == "replay":
                recovered = _recover_embedded_creative_action_for_job(
                    store,
                    project_id,
                    normalized,
                    str(claim["record"].get("job_id") or ""),
                )
                if recovered is not None:
                    recovered["idempotent_replay"] = True
                    reject_unsafe_payload(recovered)
                    return recovered
                raise HTTPException(
                    status_code=409,
                    detail=_embedded_idempotency_detail(
                        project_id,
                        normalized,
                        code="embedded_preview_recovery_incomplete",
                        message="同一文本预览已完成，但恢复资料尚不可用。",
                        user_action="请刷新页面恢复同一文本预览；不要重复提交。",
                    ),
                )
            if claim["state"] in {"conflict", "running"}:
                conflict = claim["state"] == "conflict"
                raise HTTPException(
                    status_code=409,
                    detail=_embedded_idempotency_detail(
                        project_id,
                        normalized,
                        code="embedded_preview_idempotency_conflict" if conflict else "embedded_preview_in_progress",
                        message="同一请求标识对应了不同的文本预览。" if conflict else "同一文本预览仍在处理中。",
                        user_action="请使用新的操作重新预览。" if conflict else "请恢复同一文本预览；不会再次提交。",
                        retryable=not conflict,
                    ),
                )
        output_dir = store.run_dir(project_id, job_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        graph_before = graph_store.ensure(project_id)
        started = time.perf_counter()
        result = _preview_creative_action(project_id, body, output_dir, graph_before)
        result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        graph_after = graph_store.ensure(project_id)
        result["graph_mutation"] = _graph_mutation_summary(graph_before, graph_after)
        if client_request_id:
            result["safe_manifest"]["client_request_id"] = client_request_id
            result["safe_manifest"]["request_digest"] = _embedded_request_digest(body)
        result["safe_manifest"]["source_digest"] = _text_digest(body.source_text)
        artifacts = _write_embedded_action_artifacts(
            store,
            output_dir,
            safe_manifest=result["safe_manifest"],
            preview_payload={
                "project_id": project_id,
                "mode": result["mode"],
                "action_type": body.action_type,
                "target": result["target"],
                "creative_task": result.get("creative_task") or {},
                "preview": result.get("preview") or {},
                "provider_lineage": result.get("provider_lineage") or {},
                "graph_mutation": result["graph_mutation"],
                "client_request_id": client_request_id,
                "source_digest": _text_digest(body.source_text),
                "latency_ms": result["latency_ms"],
            },
        )
        trace_path = write_run_trace(
            output_dir,
            project_id=project_id,
            job_id=job_id,
            action="embedded_creative_action_preview",
            status="succeeded" if result["mode"] == "llm" else "blocked",
            input_refs=[
                {"role": "node_id", "ref": body.node_id},
                {"role": "action_type", "ref": body.action_type},
                {"role": "provider_service_id", "ref": body.provider_service_id},
            ],
            generated_artifact_refs=artifact_refs(artifacts),
            tester_feedback={"status": result["mode"]},
            tool_gate_state={"remote_llm": result["provider_gate"]["status"]},
        )
        artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
        job = runtime_job(job_id, project_id, "embedded_creative_action", "succeeded", artifacts=artifacts)
        public_job_payload = store.write_job(job)
        response = {
            "project_id": project_id,
            "job": public_job_payload,
            "mode": result["mode"],
            "action_type": body.action_type,
            "target": result["target"],
            "creative_task": result.get("creative_task") or {},
            "preview": result.get("preview") or {},
            "provider_gate": result["provider_gate"],
            "provider_calls_started": result["provider_calls_started"],
            "provider_lineage": result.get("provider_lineage") or {},
            "safe_manifest": result["safe_manifest"],
            "graph_mutation": result["graph_mutation"],
            "latency_ms": result["latency_ms"],
            "cost_usd": 0,
            "artifacts": artifacts,
            "non_claims": EMBEDDED_CREATIVE_NON_CLAIMS,
        }
        reject_unsafe_payload(response)
        if client_request_id:
            _complete_embedded_creative_request(
                store,
                project_id,
                client_request_id,
                request_digest=_embedded_request_digest(body),
                job_id=job_id,
                provider_calls_started=result["provider_calls_started"] is True,
            )
        return response

    @app.get("/projects/{project_id}/embedded-creative-actions/by-client/{client_request_id}")
    def recover_embedded_creative_action(
        project_id: str,
        client_request_id: str,
        request: Request,
    ) -> dict[str, Any]:
        require_access(request, project_id)
        normalized = _safe_client_request_id(client_request_id)
        if normalized != client_request_id:
            raise HTTPException(status_code=422, detail="invalid client request id")
        claim = _read_embedded_creative_request(store, project_id, normalized)
        if claim:
            if str(claim.get("status") or "") != "completed":
                raise HTTPException(status_code=404, detail="text preview is still processing")
            recovered = _recover_embedded_creative_action_for_job(
                store,
                project_id,
                normalized,
                str(claim.get("job_id") or ""),
            )
            if recovered is None:
                raise HTTPException(status_code=404, detail="text preview recovery is incomplete")
            reject_unsafe_payload(recovered)
            return recovered
        recovered = _recover_embedded_creative_action(store, project_id, normalized)
        if recovered is None:
            raise HTTPException(status_code=404, detail="text preview is still processing")
        reject_unsafe_payload(recovered)
        return recovered

    @app.post("/projects/{project_id}/embedded-creative-actions/by-client/{client_request_id}/apply-shot-plan")
    def apply_embedded_shot_plan(
        project_id: str,
        client_request_id: str,
        body: EmbeddedCreativeActionApplyRequest,
        request: Request,
    ) -> dict[str, Any]:
        require_access(request, project_id)
        normalized = _safe_client_request_id(client_request_id)
        if normalized != client_request_id:
            raise HTTPException(status_code=422, detail="invalid client request id")
        _require_current_script_binding(
            store,
            project_id,
            revision_id=body.expected_production_brief.source_revision_id,
            source_digest=body.expected_production_brief.source_digest,
            stage="apply",
        )
        claim = _read_embedded_creative_request(store, project_id, normalized)
        if not claim or str(claim.get("status") or "") != "completed":
            raise HTTPException(
                status_code=409,
                detail=_embedded_apply_error(
                    project_id,
                    "embedded_preview_not_ready",
                    "分镜预览尚未完成，当前项目未改变。",
                    "请恢复同一分镜预览后再应用。",
                ),
            )
        if str(claim.get("request_digest") or "") != body.expected_request_digest:
            raise HTTPException(
                status_code=409,
                detail=_embedded_apply_error(
                    project_id,
                    "embedded_preview_changed",
                    "当前分镜预览与待应用版本不一致。",
                    "请刷新并审看最新分镜预览。",
                ),
            )
        recovered = _recover_embedded_creative_action_for_job(
            store,
            project_id,
            normalized,
            str(claim.get("job_id") or ""),
        )
        preview = dict(recovered.get("preview") or {}) if recovered else {}
        if (
            not recovered
            or recovered.get("mode") != "llm"
            or recovered.get("action_type") != "shot_breakdown"
            or not isinstance(preview.get("shot_plan"), dict)
        ):
            raise HTTPException(
                status_code=409,
                detail=_embedded_apply_error(
                    project_id,
                    "embedded_shot_plan_invalid",
                    "分镜预览未通过应用检查，当前项目未改变。",
                    "请重新生成并审看文本分镜预览。",
                ),
            )
        expected_brief = _safe_production_brief(body.expected_production_brief)
        recovered_manifest = dict(recovered.get("safe_manifest") or {})
        stored_brief = recovered_manifest.get("production_brief")
        if isinstance(stored_brief, dict) and _safe_production_brief(stored_brief) != expected_brief:
            raise HTTPException(
                status_code=409,
                detail=_embedded_apply_error(
                    project_id,
                    "embedded_production_brief_changed",
                    "当前时长目标与生成分镜时不一致，分镜未应用。",
                    "请按当前目标时长重新规划。",
                ),
            )
        source_digest = str(recovered_manifest.get("source_digest") or "")
        if expected_brief.get("source_digest") and expected_brief["source_digest"] != source_digest:
            raise HTTPException(
                status_code=409,
                detail=_embedded_apply_error(
                    project_id,
                    "embedded_source_revision_changed",
                    "当前剧本版本与分镜预览来源不一致，分镜未应用。",
                    "请从当前剧本重新规划分镜。",
                ),
            )
        duration_assessment = _shot_plan_duration_assessment(preview["shot_plan"], expected_brief)
        if not duration_assessment["apply_allowed"]:
            raise HTTPException(
                status_code=409,
                detail=_embedded_apply_error(
                    project_id,
                    "embedded_shot_plan_duration_out_of_range",
                    "候选总时长超出当前目标，分镜未应用。",
                    "请调整时长并重新规划；当前候选会保留。",
                ),
            )
        graph = graph_store.ensure(project_id)
        idempotency_key = f"apply-embedded-shot-plan-{normalized}"
        if graph.get("nodes") and idempotency_key not in graph.get("idempotency", {}):
            raise HTTPException(
                status_code=409,
                detail=_embedded_apply_error(
                    project_id,
                    "production_graph_already_planned",
                    "当前项目已有制作方案，不能用旧分镜预览覆盖。",
                    "请从当前制作版本重新预览影响。",
                ),
            )
        semantic_digest = canonical_digest(
            {
                "request_digest": body.expected_request_digest,
                "source_digest": source_digest,
                "shot_plan": preview["shot_plan"],
                "production_brief": expected_brief,
            },
        )
        try:
            updated = graph_store.append(
                project_id,
                expected_version=body.expected_graph_version,
                idempotency_key=idempotency_key,
                semantic_digest=semantic_digest,
                events=_compile_embedded_shot_plan_events(
                    normalized,
                    body.expected_request_digest,
                    source_digest,
                    preview["shot_plan"],
                    expected_brief,
                ),
            )
        except (GraphIdempotencyConflict, GraphVersionConflict, ProductionGraphError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=409,
                detail=_embedded_apply_error(
                    project_id,
                    "embedded_shot_plan_apply_conflict",
                    "当前制作版本已变化，分镜未应用。",
                    "请刷新并按当前版本重新预览。",
                ),
            ) from exc
        workspace = _sequence_workspace_projection(updated, project_id=project_id, store=store)
        response = {
            "project_id": project_id,
            "status": "applied",
            "graph_version": int(updated.get("version") or 0),
            "graph_digest": str(updated.get("graph_digest") or ""),
            "idempotent_replay": updated.get("idempotent_replay") is True,
            "workspace": workspace,
            "provider_dispatch_count": 0,
            "image_dispatch_count": 0,
            "video_dispatch_count": 0,
            "cost_usd": 0,
        }
        reject_unsafe_payload(response)
        return response


def _preview_creative_action(
    project_id: str,
    request: EmbeddedCreativeActionRequest,
    output_dir: Path,
    graph_before: dict[str, Any],
) -> dict[str, Any]:
    gate = llm_provider_gate()
    task_id = _creative_task_id(project_id, request)
    target = {
        "node_id": _safe_token(request.node_id, 160),
        "node_type": _safe_token(request.node_type, 80),
        "action_type": request.action_type,
        "mode": request.mode,
        "scope": "selected_node_only" if request.action_type == "script_revision" else "selected_node_shot_plan",
    }
    if request.provider_service_id != SERVER_CODEX_SERVICE_ID:
        return _unavailable_preview(project_id, request, gate, target, task_id=task_id, reason="unsupported_provider_service")
    if gate.get("status") != "ready_not_run":
        return _unavailable_preview(project_id, request, gate, target, task_id=task_id, reason="remote_llm_gate_closed")
    if _contains_unsafe_fragment(request.source_text):
        return _unavailable_preview(project_id, request, gate, target, task_id=task_id, reason="unsafe_source_text")
    schema = _creative_action_output_schema(request.action_type)
    schema_digest = structured_output_schema_digest(schema)
    try:
        registry = load_provider_registry()
        provider_result = _dispatch_creative_action_preview(
            registry,
            project_id,
            request,
            output_dir,
            graph_before,
            schema,
            schema_digest,
            repair_reason="",
        )
        preview, dispatch_count, repair_attempted = _validate_or_repair_preview(
            registry,
            project_id,
            request,
            output_dir,
            graph_before,
            schema,
            schema_digest,
            provider_result,
        )
    except (ModelConfigError, ModelGatewayError):
        return _unavailable_preview(project_id, request, gate, target, task_id=task_id, reason="llm_not_ready")
    except ValueError as exc:
        validation_error_category = _safe_validation_reason(str(exc))
        return _unavailable_preview(
            project_id,
            request,
            gate,
            target,
            task_id=task_id,
            reason="unsafe_or_invalid_llm_preview",
            provider_calls_started=True,
            provider_dispatch_count=2,
            repair_attempted=True,
            completed_phases=["queued", "context", "dispatching", "validating"],
            error_owner="provider_output_validation",
            validation_error_category=validation_error_category,
        )
    lineage = {
        "service_id": SERVER_CODEX_SERVICE_ID,
        "provider": "codex_local",
        "model_surface": "server-codex-login",
        "request_id": f"embedded_action_{project_id}_{int(time.time() * 1000)}",
        "structured_output_contract_id": EMBEDDED_CREATIVE_CONTRACT_ID,
        "structured_output_schema_digest": schema_digest,
        "provider_calls_started": True,
        "provider_dispatch_count": dispatch_count,
        "repair_attempted": repair_attempted,
        "provider_raw_response_stored": False,
        "external_paid_cost_usd": 0,
    }
    return {
        "mode": "llm",
        "target": target,
        "preview": preview,
        "creative_task": _creative_task(
            task_id,
            project_id,
            request,
            state="preview_ready",
            phase="preview_ready",
            completed_phases=["queued", "context", "dispatching", "validating", "preview_ready"],
        ),
        "provider_gate": gate,
        "provider_calls_started": True,
        "provider_lineage": lineage,
        "safe_manifest": _safe_manifest(project_id, request, gate, target, mode="llm", lineage=lineage),
    }


def _dispatch_creative_action_preview(
    registry: Any,
    project_id: str,
    request: EmbeddedCreativeActionRequest,
    output_dir: Path,
    graph_before: dict[str, Any],
    schema: dict[str, Any],
    schema_digest: str,
    *,
    repair_reason: str,
) -> dict[str, Any]:
    prompt = (
        _creative_action_repair_prompt(project_id, request, graph_before, schema_digest, repair_reason)
        if repair_reason
        else _creative_action_prompt(project_id, request, graph_before, schema_digest)
    )
    result = registry.dispatch(
        "llm",
        SERVER_CODEX_SERVICE_ID,
        ProviderDispatchRequest(
            prompt=prompt,
            output_dir=output_dir,
            task_type=f"embedded_{request.action_type}{'_repair' if repair_reason else ''}",
            structured_output_contract_id=EMBEDDED_CREATIVE_CONTRACT_ID,
            structured_output_schema=schema,
            structured_output_schema_digest=schema_digest,
            timeout_sec=300.0,
        ),
    )
    return result if isinstance(result, dict) else {}


def _validate_or_repair_preview(
    registry: Any,
    project_id: str,
    request: EmbeddedCreativeActionRequest,
    output_dir: Path,
    graph_before: dict[str, Any],
    schema: dict[str, Any],
    schema_digest: str,
    provider_result: dict[str, Any],
) -> tuple[dict[str, Any], int, bool]:
    structured = provider_result.get("structured_output") if isinstance(provider_result, dict) else None
    try:
        return _validate_preview_payload(request, structured or {}), 1, False
    except ValueError as validation_error:
        repair_result = _dispatch_creative_action_preview(
            registry,
            project_id,
            request,
            output_dir,
            graph_before,
            schema,
            schema_digest,
            repair_reason=str(validation_error),
        )
        repair_structured = repair_result.get("structured_output") if isinstance(repair_result, dict) else None
        return _validate_preview_payload(request, repair_structured or {}), 2, True


def _creative_action_output_schema(action_type: str) -> dict[str, Any]:
    base_required = [
        "action_type",
        "mode",
        "revised_text",
        "change_summary",
        "rationale",
        "unresolved_decisions",
        "quality_flags",
    ]
    properties: dict[str, Any] = {
        "action_type": {"type": "string", "enum": [action_type]},
        "mode": {"type": "string"},
        "revised_text": {"type": "string", "minLength": 80},
        "change_summary": {"type": "array", "minItems": 2, "maxItems": 8, "items": {"type": "string"}},
        "rationale": {"type": "string", "minLength": 20},
        "unresolved_decisions": {"type": "array", "maxItems": 6, "items": {"type": "string"}},
        "quality_flags": {"type": "array", "maxItems": 6, "items": {"type": "string"}},
    }
    if action_type == "script_revision":
        base_required.append("screenplay_candidate")
        properties["screenplay_candidate"] = _screenplay_candidate_schema()
    if action_type == "shot_breakdown":
        base_required.append("shot_plan")
        properties["shot_plan"] = {
            "type": "object",
            "additionalProperties": False,
            "required": ["scenes", "total_shots", "estimated_duration_sec"],
            "properties": {
                "total_shots": {"type": "integer", "minimum": 1},
                "estimated_duration_sec": {"type": "number", "minimum": 1},
                "scenes": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 8,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["title", "purpose", "shots"],
                        "properties": {
                            "title": {"type": "string", "minLength": 2},
                            "purpose": {"type": "string", "minLength": 6},
                            "shots": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 12,
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": [
                                        "title",
                                        "duration_sec",
                                        "shot_size",
                                        "camera_angle",
                                        "movement",
                                        "blocking",
                                        "sound",
                                        "transition",
                                        "narrative_purpose",
                                    ],
                                    "properties": {
                                        "title": {"type": "string", "minLength": 2},
                                        "duration_sec": {
                                            "type": "number",
                                            "minimum": 1,
                                            "maximum": MAX_STORYBOARD_DURATION_SECONDS,
                                        },
                                        "shot_size": {"type": "string", "minLength": 2},
                                        "camera_angle": {"type": "string", "minLength": 2},
                                        "movement": {"type": "string", "minLength": 2},
                                        "blocking": {"type": "string", "minLength": 2},
                                        "sound": {"type": "string", "minLength": 2},
                                        "transition": {"type": "string", "minLength": 2},
                                        "narrative_purpose": {"type": "string", "minLength": 4},
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": base_required,
        "properties": properties,
    }




def _creative_action_prompt(
    project_id: str,
    request: EmbeddedCreativeActionRequest,
    graph_before: dict[str, Any],
    schema_digest: str,
) -> str:
    mode_label = {
        "concise_polish": "简洁润色：保持结构，提升措辞、画面性和可读性。",
        "professional_expansion": "专业扩写：显著补足角色目标、冲突、动作、对白、节奏与视觉表达。",
        "structure_pace": "结构与节奏：强化开端、转折、推进、悬念与段落时长。",
        "character_relationship": "人物关系：加深目标、关系、变化与冲突动机。",
        "dialogue_action": "对白动作：把人物意图转成可拍动作、对白和反应。",
        "visual_production": "视觉制作：补足空间、光线、镜头可执行线索和连续性约束。",
        "dynamic_shot_breakdown": "动态拆分分镜：根据内容决定场景、镜头数量和时长，不使用固定模板。",
    }.get(request.mode, request.mode)
    graph_summary = {
        "version": int(graph_before.get("version") or 0),
        "nodes": len(graph_before.get("nodes") or {}),
        "relations": len(graph_before.get("relations") or []),
    }
    context_summary = _safe_context_summary(request.context_summary)
    constraints = [_safe_text(item, 160) for item in request.constraints if _safe_text(item, 160)]
    production_brief = _production_brief_for_request(request)
    duration_instruction = ""
    if request.action_type == "shot_breakdown":
        duration_instruction = (
            f"本次成片目标总时长为 {production_brief['target_duration_seconds']:.2f} 秒，"
            f"允许偏差 {production_brief['tolerance_seconds']:.2f} 秒。"
            "逐镜头 duration_sec 合计必须落在该范围；不得让候选自行改写目标时长。"
        )
    return "\n".join(
        [
            "你是 AFS Studio 的节点内 AI 创作动作引擎，服务专业影视创作者。",
            "这次只生成预览，不修改画布、不创建节点、不写入 ProductionGraph、不生成图片或视频。",
            "必须使用用户给定原文和安全上下文，不允许关键词模板、固定大纲、固定4x15/10x6或空泛标题。",
            "如果是普通优化/改写，输出应保留同一节点身份；只有用户明确要求分支才可建议分支。",
            "中文输出，内容必须可拍、可审、可继续拆分。",
            "如果动作是 script_revision，必须输出 screenplay_candidate：片名/版本/logline、角色目标冲突变化、按场排序的场景标题、地点、时间、动作、人物名、对白、转场；不要只写散文故事。",
            "screenplay_candidate.scenes[].space_type 必须是 内景、外景、INT. 或 EXT.；heading 必须以 内景 -、外景 -、INT. 或 EXT. 开头，禁止“内景/外景待定”、数字标题或散文小标题。",
            "每个场景标题必须包含空间类型、地点、时间三段，例如“内景 - 旧摄影棚 - 夜”；人物名提示后必须在同一场景内接对白，可夹一个括号提示，禁止悬空人物名。",
            "blocks 必须使用专业剧本块流：action 可独立；character 必须立刻接 dialogue；parenthetical 只能夹在 character 与 dialogue 中间；不要把“人物：对白”合写成单个散文段。",
            "如果原文已有对白，请保留并扩写为明确的 character/dialogue 块，不能省略人物说话关系。",
            "revised_text 只是 screenplay_candidate 的可读投影；镜头和摄影语言只在 shot_breakdown 里使用，不要混进文学剧本文本。",
            "如果动作是 shot_breakdown，只输出可审查分镜候选，不创建图片、不生成关键帧。",
            duration_instruction,
            "不要输出内部路径、端口、provider raw、密钥、请求头、schema 名称或调度细节。",
            f"项目：{project_id}",
            f"节点：{request.node_id} / {request.node_type}",
            f"动作：{request.action_type}",
            f"模式：{mode_label}",
            f"安全上下文：{context_summary}",
            f"制作图摘要：{graph_summary}",
            f"约束：{constraints}",
            f"Closed schema digest: {schema_digest}",
            "原文如下：",
            request.source_text,
        ]
    )


def _creative_action_repair_prompt(
    project_id: str,
    request: EmbeddedCreativeActionRequest,
    graph_before: dict[str, Any],
    schema_digest: str,
    repair_reason: str,
) -> str:
    return "\n".join(
        [
            _creative_action_prompt(project_id, request, graph_before, schema_digest),
            "",
            "上一轮真实模型输出未通过 AFS 结构验证，本轮是一次有界的 provider-backed 修复重试。",
            f"验证失败类别：{_safe_text(repair_reason, 220)}",
            "不要复述错误；请基于同一原文重新生成完整、可审查、符合 closed JSON schema 的结果。",
            "尤其检查 screenplay_candidate.scenes[].blocks：每个 character 后必须紧跟 dialogue；如果需要括号提示，顺序只能是 character、parenthetical、dialogue。",
            "每个 dialogue 必须有清楚说话人；不要只写“林澈：……”这种合写行，除非结构里同时提供独立 character 与 dialogue 块。",
            "仍然禁止本地模板、固定镜头数、散文冒充专业剧本、图片/视频生成和画布写入。",
        ]
    )




def _unavailable_preview(
    project_id: str,
    request: EmbeddedCreativeActionRequest,
    gate: dict[str, str],
    target: dict[str, Any],
    *,
    task_id: str,
    reason: str,
    provider_calls_started: bool = False,
    provider_dispatch_count: int = 0,
    repair_attempted: bool = False,
    completed_phases: list[str] | None = None,
    error_owner: str = "llm_provider",
    validation_error_category: str = "",
) -> dict[str, Any]:
    rationale = {
        "unsafe_or_invalid_llm_preview": "真实文本模型已返回，但结果没有通过专业剧本/分镜结构校验；当前节点保持不变。",
        "llm_not_ready": "AI 模型当前不可用；不会使用本地模板冒充专业改写。",
        "remote_llm_gate_closed": "文本模型开关未打开；不会使用本地模板冒充专业改写。",
        "unsafe_source_text": "当前节点包含不安全的内部路径或凭据样式文本；请移除后重试。",
    }.get(reason, "AI 模型当前不可用；不会使用本地模板冒充专业改写。")
    preview = {
        "preview_id": f"blocked_{int(time.time() * 1000)}",
        "action_type": request.action_type,
        "mode": request.mode,
        "revised_text": "",
        "change_summary": [],
        "rationale": rationale,
        "unresolved_decisions": ["稍后重试，或先手工编辑当前节点。"],
        "quality_flags": [
            "fail_closed_no_canvas_mutation",
            *([f"validation_{validation_error_category}"] if validation_error_category else []),
        ],
    }
    lineage = {
        "service_id": SERVER_CODEX_SERVICE_ID if provider_calls_started else "",
        "provider": "codex_local" if provider_calls_started else "",
        "model_surface": "server-codex-login" if provider_calls_started else "",
        "request_id": f"embedded_action_{project_id}_{int(time.time() * 1000)}" if provider_calls_started else "",
        "structured_output_contract_id": EMBEDDED_CREATIVE_CONTRACT_ID,
        "provider_calls_started": provider_calls_started,
        "provider_dispatch_count": int(provider_dispatch_count or (1 if provider_calls_started else 0)),
        "repair_attempted": bool(repair_attempted),
        "provider_raw_response_stored": False,
        "external_paid_cost_usd": 0,
    }
    if validation_error_category:
        lineage["validation_error_category"] = validation_error_category
    return {
        "mode": "unavailable",
        "target": target,
        "preview": preview,
        "creative_task": _creative_task(
            task_id,
            project_id,
            request,
            state="failed",
            phase="failed",
            completed_phases=completed_phases or ["queued", "context"],
            error_owner=error_owner,
            error_category=reason,
            error_detail=validation_error_category,
        ),
        "provider_gate": gate,
        "provider_calls_started": provider_calls_started,
        "provider_lineage": lineage,
        "safe_manifest": _safe_manifest(
            project_id,
            request,
            gate,
            target,
            mode="unavailable",
            fallback_reason=reason,
            lineage=lineage,
            provider_calls_started=provider_calls_started,
            validation_error_category=validation_error_category,
        ),
    }


def _creative_task_id(project_id: str, request: EmbeddedCreativeActionRequest) -> str:
    return "_".join([
        "creative_task",
        _safe_token(project_id, 80) or "project",
        _safe_token(request.node_id, 80) or "node",
        _safe_token(request.action_type, 40) or "action",
        str(int(time.time() * 1000)),
    ])


def _creative_task(
    task_id: str,
    project_id: str,
    request: EmbeddedCreativeActionRequest,
    *,
    state: str,
    phase: str,
    completed_phases: list[str],
    error_owner: str = "",
    error_category: str = "",
    error_detail: str = "",
) -> dict[str, Any]:
    task = {
        "schema_version": "afs.creative_task.v0.1",
        "task_id": task_id,
        "project_id": project_id,
        "node_id": request.node_id,
        "node_type": request.node_type,
        "action_type": request.action_type,
        "mode": request.mode,
        "state": state,
        "phase": phase,
        "completed_phases": completed_phases,
        "cancel_requested": False,
        "idempotency_key": f"{project_id}:{request.node_id}:{request.action_type}:{request.generated_at}",
        "result_scope": "same_node_revision" if request.action_type == "script_revision" else "candidate_storyboard_subgraph",
        "error_owner": error_owner,
        "error_category": error_category,
        "error_detail": _safe_token(error_detail, 120),
    }
    reject_unsafe_payload(task)
    return task


def _safe_manifest(
    project_id: str,
    request: EmbeddedCreativeActionRequest,
    gate: dict[str, str],
    target: dict[str, Any],
    *,
    mode: str,
    fallback_reason: str = "",
    lineage: dict[str, Any] | None = None,
    provider_calls_started: bool | None = None,
    validation_error_category: str = "",
) -> dict[str, Any]:
    started = mode == "llm" if provider_calls_started is None else bool(provider_calls_started)
    manifest = {
        "schema_version": "afs_embedded_creative_action_safe_manifest.v0.2",
        "project_id": project_id,
        "mode": mode,
        "target": target,
        "provider_service_id": request.provider_service_id,
        "provider_gate": gate,
        "fallback_reason": fallback_reason,
        "provider_calls_started": started,
        "provider_lineage": lineage or {},
        "provider_dispatch_count": int((lineage or {}).get("provider_dispatch_count") or (1 if started else 0)),
        "repair_attempted": bool((lineage or {}).get("repair_attempted")),
        "validation_error_category": _safe_token(validation_error_category, 120),
        "provider_raw_response_stored": False,
        "credentialed_urls_returned_by_api": False,
        "local_paths_returned_by_api": False,
        "media_bytes_returned_by_api": False,
        "canvas_mutation_enabled": False,
        "image_video_generation_enabled": False,
        "source_revision_id": _safe_token(request.source_revision_id, 140),
        "source_digest": request.source_digest if re.fullmatch(r"[a-f0-9]{64}", request.source_digest or "") else "",
        "production_brief": _production_brief_for_request(request) if request.action_type == "shot_breakdown" else None,
    }
    reject_unsafe_payload(manifest)
    return manifest


def _write_embedded_action_artifacts(
    store: RuntimeStore,
    output_dir: Path,
    *,
    safe_manifest: dict[str, Any],
    preview_payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    reject_unsafe_payload(safe_manifest)
    reject_unsafe_payload(preview_payload)
    write_json(output_dir / "embedded_creative_action_safe_manifest.json", safe_manifest)
    write_json(output_dir / "embedded_creative_action_preview.json", preview_payload)
    return {
        "embedded_creative_action_safe_manifest": store.register_artifact(
            output_dir / "embedded_creative_action_safe_manifest.json",
            role="embedded_creative_action_safe_manifest",
        ),
        "embedded_creative_action_preview": store.register_artifact(
            output_dir / "embedded_creative_action_preview.json",
            role="embedded_creative_action_preview",
        ),
    }


def _safe_client_request_id(value: str) -> str:
    normalized = safe_id(str(value or "").strip())
    return normalized[:120] if normalized.startswith("cli_") else ""


def _embedded_request_digest(request: EmbeddedCreativeActionRequest) -> str:
    payload = request.model_dump(mode="json")
    payload.pop("generated_at", None)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _text_digest(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _embedded_request_record_path(store: RuntimeStore, project_id: str, client_request_id: str) -> Path:
    return (
        store.projects_dir
        / safe_id(project_id)
        / "embedded_creative_action_requests"
        / f"{safe_id(client_request_id)}.json"
    )


def _claim_embedded_creative_request(
    store: RuntimeStore,
    project_id: str,
    client_request_id: str,
    *,
    request_digest: str,
    job_id: str,
) -> dict[str, Any]:
    path = _embedded_request_record_path(store, project_id, client_request_id)
    with exclusive_file_lock(path.with_suffix(".transaction.lock")):
        if path.is_file():
            record = read_json(path)
            if (
                str(record.get("project_id") or "") != project_id
                or str(record.get("client_request_id") or "") != client_request_id
            ):
                return {"state": "conflict", "record": record}
            if str(record.get("request_digest") or "") != request_digest:
                return {"state": "conflict", "record": record}
            if str(record.get("status") or "") == "completed":
                return {"state": "replay", "record": record}
            return {"state": "running", "record": record}
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "schema_version": "afs.embedded_creative_action_request.v0.1",
            "project_id": project_id,
            "client_request_id": client_request_id,
            "request_digest": request_digest,
            "status": "running",
            "job_id": job_id,
            "provider_calls_started": False,
            "created_at": now,
            "updated_at": now,
            "contains_request_payload": False,
            "contains_provider_output": False,
            "contains_secret": False,
        }
        write_json(path, record)
        return {"state": "claimed", "record": record}


def _complete_embedded_creative_request(
    store: RuntimeStore,
    project_id: str,
    client_request_id: str,
    *,
    request_digest: str,
    job_id: str,
    provider_calls_started: bool,
) -> None:
    path = _embedded_request_record_path(store, project_id, client_request_id)
    with exclusive_file_lock(path.with_suffix(".transaction.lock")):
        if not path.is_file():
            raise RuntimeError("embedded creative request claim is missing")
        record = read_json(path)
        if (
            str(record.get("project_id") or "") != project_id
            or str(record.get("client_request_id") or "") != client_request_id
            or str(record.get("request_digest") or "") != request_digest
            or str(record.get("job_id") or "") != job_id
            or str(record.get("status") or "") != "running"
        ):
            raise RuntimeError("embedded creative request claim changed before completion")
        write_json(
            path,
            {
                **record,
                "status": "completed",
                "provider_calls_started": bool(provider_calls_started),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )


def _read_embedded_creative_request(
    store: RuntimeStore,
    project_id: str,
    client_request_id: str,
) -> dict[str, Any] | None:
    path = _embedded_request_record_path(store, project_id, client_request_id)
    if not path.is_file():
        return None
    record = read_json(path)
    if (
        str(record.get("project_id") or "") != project_id
        or str(record.get("client_request_id") or "") != client_request_id
    ):
        return None
    return record


def _embedded_idempotency_detail(
    project_id: str,
    client_request_id: str,
    *,
    code: str,
    message: str,
    user_action: str,
    retryable: bool = False,
) -> dict[str, Any]:
    detail = safe_error_detail(
        code,
        detail_code=code,
        message=message,
        user_action=user_action,
        client_request_id=client_request_id,
        project_id=project_id,
        action="embedded_creative_action_preview",
        stage="idempotency",
        status="blocked",
        retryable=retryable,
        details={"provider_calls_started": False},
    )
    detail["provider_calls_started"] = False
    return detail


def _embedded_apply_error(
    project_id: str,
    code: str,
    message: str,
    user_action: str,
) -> dict[str, Any]:
    return safe_error_detail(
        code,
        detail_code=code,
        message=message,
        user_action=user_action,
        project_id=project_id,
        action="apply_embedded_shot_plan",
        stage="confirm",
        status="blocked",
        retryable=True,
        details={
            "provider_calls_started": False,
            "image_dispatch_count": 0,
            "video_dispatch_count": 0,
        },
    )


def _require_current_script_binding(
    store: RuntimeStore,
    project_id: str,
    *,
    revision_id: str,
    source_digest: str,
    stage: str,
) -> None:
    if not revision_id or not source_digest:
        raise HTTPException(
            status_code=409,
            detail=safe_error_detail(
                "embedded_source_revision_required",
                detail_code="embedded_source_revision_required",
                message="当前剧本版本尚未可靠绑定，分镜操作已停止。",
                user_action="请刷新项目并从当前已应用剧本重新规划分镜。",
                project_id=project_id,
                action="embedded_creative_action_preview" if stage == "preview" else "apply_embedded_shot_plan",
                stage=stage,
                status="blocked",
                retryable=False,
                details={
                    "provider_calls_started": False,
                    "image_dispatch_count": 0,
                    "video_dispatch_count": 0,
                },
            ),
        )
    current = current_script_revision_binding(store, project_id)
    if (
        str(current.get("revision_id") or "") == revision_id
        and str(current.get("source_digest") or "") == source_digest
    ):
        return
    raise HTTPException(
        status_code=409,
        detail=safe_error_detail(
            "embedded_source_revision_changed",
            detail_code="embedded_source_revision_changed",
            message="当前剧本版本已变化，旧分镜操作已停止。",
            user_action="请从当前已应用剧本重新规划分镜。",
            project_id=project_id,
            action="embedded_creative_action_preview" if stage == "preview" else "apply_embedded_shot_plan",
            stage=stage,
            status="blocked",
            retryable=False,
            details={
                "provider_calls_started": False,
                "image_dispatch_count": 0,
                "video_dispatch_count": 0,
            },
        ),
    )


def _compile_embedded_shot_plan_events(
    client_request_id: str,
    request_digest: str,
    source_digest: str,
    shot_plan: dict[str, Any],
    production_brief: dict[str, Any],
) -> list[dict[str, Any]]:
    prefix = request_digest[:16]
    revision_id = f"revision-embedded-{prefix}"
    sequence_id = f"sequence-embedded-{prefix}"
    events: list[dict[str, Any]] = [
        {
            "type": "node_upserted",
            "node": {
                "node_id": revision_id,
                "category": "revision",
                "metadata": {
                    "title": "已确认剧本",
                    "source_digest": source_digest,
                    "source_kind": "embedded_text_preview",
                    "client_request_ref": client_request_id,
                },
            },
        },
        {
            "type": "node_upserted",
            "node": {
                "node_id": sequence_id,
                "category": "collection",
                "metadata": {
                    "name": "制作序列",
                    "target_duration_seconds": float(production_brief.get("target_duration_seconds") or 0),
                    "duration_tolerance_seconds": float(production_brief.get("tolerance_seconds") or 0),
                    "duration_source": _safe_token(production_brief.get("duration_source"), 40),
                    "candidate_duration_seconds": float(shot_plan.get("estimated_duration_sec") or 0),
                },
            },
        },
        {
            "type": "relation_upserted",
            "from_id": revision_id,
            "to_id": sequence_id,
            "relation_type": "derived_from",
        },
    ]
    total_shots = 0
    for scene_index, scene in enumerate(shot_plan.get("scenes") or [], start=1):
        if not isinstance(scene, dict):
            continue
        scene_id = f"scene-embedded-{prefix}-{scene_index:02d}"
        events.extend(
            [
                {
                    "type": "node_upserted",
                    "node": {
                        "node_id": scene_id,
                        "category": "location",
                        "metadata": {
                            "name": _safe_text(scene.get("title"), 120),
                            "purpose": _safe_text(scene.get("purpose"), 180),
                            "order": scene_index,
                            "source_digest": source_digest,
                        },
                    },
                },
                {
                    "type": "relation_upserted",
                    "from_id": sequence_id,
                    "to_id": scene_id,
                    "relation_type": "contains",
                },
            ],
        )
        for shot_index, shot in enumerate(scene.get("shots") or [], start=1):
            if not isinstance(shot, dict):
                continue
            total_shots += 1
            shot_id = f"shot-embedded-{prefix}-{scene_index:02d}-{shot_index:02d}"
            metadata = {
                "title": _safe_text(shot.get("title"), 120),
                "intent": _safe_text(shot.get("narrative_purpose"), 180),
                "duration_seconds": float(shot.get("duration_sec") or 0),
                "order": total_shots,
                "scene_order": scene_index,
                "shot_order": shot_index,
                "shot_size": _safe_text(shot.get("shot_size"), 80),
                "camera_angle": _safe_text(shot.get("camera_angle"), 80),
                "movement": _safe_text(shot.get("movement"), 120),
                "blocking": _safe_text(shot.get("blocking"), 180),
                "sound": _safe_text(shot.get("sound"), 120),
                "transition": _safe_text(shot.get("transition"), 80),
                "source_digest": source_digest,
            }
            events.extend(
                [
                    {
                        "type": "node_upserted",
                        "node": {
                            "node_id": shot_id,
                            "category": "unit",
                            "metadata": metadata,
                        },
                    },
                    {
                        "type": "relation_upserted",
                        "from_id": scene_id,
                        "to_id": shot_id,
                        "relation_type": "contains",
                    },
                    {
                        "type": "work_created",
                        "work_id": f"work-{shot_id}",
                        "semantic_digest": canonical_digest(metadata),
                        "depends_on": [shot_id, scene_id],
                    },
                ],
            )
    if total_shots < 1:
        raise ValueError("shot plan has no shots")
    return events


def _recover_embedded_creative_action_for_job(
    store: RuntimeStore,
    project_id: str,
    client_request_id: str,
    job_id: str,
) -> dict[str, Any] | None:
    if not job_id:
        return None
    run_dir = store.run_dir(project_id, job_id)
    recovered = _recover_embedded_creative_action_from_run(
        store,
        project_id,
        client_request_id,
        run_dir,
    )
    if recovered is None:
        return None
    try:
        job = store.load_job(job_id)
    except KeyError:
        return None
    if str(job.get("project_id") or "") != project_id or str(job.get("job_id") or "") != job_id:
        return None
    recovered["job"] = public_job(job)
    recovered["artifacts"] = dict(job.get("artifacts") or {})
    return recovered


def _recover_embedded_creative_action(
    store: RuntimeStore,
    project_id: str,
    client_request_id: str,
) -> dict[str, Any] | None:
    project_runs = store.runs_dir / safe_id(project_id)
    if not project_runs.is_dir():
        return None
    run_dirs = sorted(
        (path for path in project_runs.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for run_dir in run_dirs:
        recovered = _recover_embedded_creative_action_from_run(
            store,
            project_id,
            client_request_id,
            run_dir,
        )
        if recovered is not None:
            return recovered
    return None


def _recover_embedded_creative_action_from_run(
    store: RuntimeStore,
    project_id: str,
    client_request_id: str,
    run_dir: Path,
) -> dict[str, Any] | None:
    manifest_path = run_dir / "embedded_creative_action_safe_manifest.json"
    preview_path = run_dir / "embedded_creative_action_preview.json"
    if not manifest_path.is_file() or not preview_path.is_file():
        return None
    manifest = read_json(manifest_path)
    if str(manifest.get("project_id") or "") != project_id:
        return None
    if str(manifest.get("client_request_id") or "") != client_request_id:
        return None
    preview_payload = read_json(preview_path)
    if str(preview_payload.get("project_id") or "") != project_id:
        return None
    response = {
        "project_id": project_id,
        "mode": str(preview_payload.get("mode") or manifest.get("mode") or ""),
        "action_type": str(preview_payload.get("action_type") or ""),
        "target": dict(preview_payload.get("target") or manifest.get("target") or {}),
        "creative_task": dict(preview_payload.get("creative_task") or {}),
        "preview": dict(preview_payload.get("preview") or {}),
        "provider_gate": dict(manifest.get("provider_gate") or {}),
        "provider_calls_started": manifest.get("provider_calls_started") is True,
        "provider_lineage": dict(preview_payload.get("provider_lineage") or manifest.get("provider_lineage") or {}),
        "safe_manifest": manifest,
        "graph_mutation": dict(preview_payload.get("graph_mutation") or {}),
        "latency_ms": float(preview_payload.get("latency_ms") or 0),
        "cost_usd": 0,
        "recovered": True,
        "non_claims": EMBEDDED_CREATIVE_NON_CLAIMS,
    }
    reject_unsafe_payload(response)
    return response


def _graph_mutation_summary(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_digest = str(before.get("graph_digest") or "")
    after_digest = str(after.get("graph_digest") or "")
    before_version = int(before.get("version") or 0)
    after_version = int(after.get("version") or 0)
    return {
        "before_version": before_version,
        "after_version": after_version,
        "before_digest": before_digest,
        "after_digest": after_digest,
        "mutated": before_version != after_version or before_digest != after_digest,
    }


def _safe_context_summary(value: Any) -> dict[str, str | int]:
    if not isinstance(value, dict):
        return {}
    allowed = {
        "project_name",
        "selected_node_title",
        "selected_node_type",
        "selected_node_status",
        "selected_edge_relation_type",
        "counts",
        "section",
    }
    out: dict[str, str | int] = {}
    for key in allowed:
        if key not in value:
            continue
        item = value.get(key)
        if isinstance(item, (int, float)):
            out[key] = int(item)
        elif isinstance(item, dict):
            out[key] = " ".join(f"{_safe_token(k, 40)}={_safe_number(v, 0):.0f}" for k, v in item.items())[:180]
        else:
            out[key] = _safe_text(item, 160)
    return out




__all__ = ("register_runtime_embedded_creative_action_routes",)
