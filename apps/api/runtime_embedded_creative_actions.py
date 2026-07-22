from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.company_secrets import SERVER_CODEX_SERVICE_ID
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import (
    ProviderDispatchRequest,
    load_provider_registry,
    structured_output_schema_digest,
)
from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_llm_enhancement import llm_provider_gate
from apps.api.runtime_production_graph import ProductionGraphStore
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload
from apps.api.runtime_tracing import artifact_refs, write_run_trace


EMBEDDED_CREATIVE_CONTRACT_ID = "afs.runtime.embedded_creative_action.v0.1"
EMBEDDED_CREATIVE_NON_CLAIMS = [
    "not_canvas_mutation_until_user_apply",
    "not_paid_image_video_generation",
    "not_human_acceptance",
    "not_business_validation",
]
UNSAFE_TEXT_FRAGMENTS = (
    "api key",
    "authorization:",
    "bearer ",
    "cookie:",
    "secret",
    "token",
    "signed url",
    "provider raw",
    "\\users\\",
    "/home/",
    "/opt/",
    "/var/lib/",
)
PROMPT_LEAK_FRAGMENTS = (
    "system prompt",
    "developer message",
    "request_json",
    "output.schema",
    "provider raw",
    "api key",
    "authorization",
    "cookie",
)


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
    provider_service_id: str = SERVER_CODEX_SERVICE_ID
    generated_at: str = Field(min_length=1, max_length=80)


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
        job_id = store.new_job_id("embedded_creative_action", project_id)
        output_dir = store.run_dir(project_id, job_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        graph_before = graph_store.ensure(project_id)
        started = time.perf_counter()
        result = _preview_creative_action(project_id, body, output_dir, graph_before)
        result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        graph_after = graph_store.ensure(project_id)
        result["graph_mutation"] = _graph_mutation_summary(graph_before, graph_after)
        artifacts = _write_embedded_action_artifacts(
            store,
            output_dir,
            safe_manifest=result["safe_manifest"],
            preview_payload={
                "project_id": project_id,
                "mode": result["mode"],
                "action_type": body.action_type,
                "target": result["target"],
                "preview": result.get("preview") or {},
                "provider_lineage": result.get("provider_lineage") or {},
                "graph_mutation": result["graph_mutation"],
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
        response = {
            "project_id": project_id,
            "job": store.write_job(job),
            "mode": result["mode"],
            "action_type": body.action_type,
            "target": result["target"],
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
        return response


def _preview_creative_action(
    project_id: str,
    request: EmbeddedCreativeActionRequest,
    output_dir: Path,
    graph_before: dict[str, Any],
) -> dict[str, Any]:
    gate = llm_provider_gate()
    target = {
        "node_id": _safe_token(request.node_id, 160),
        "node_type": _safe_token(request.node_type, 80),
        "action_type": request.action_type,
        "mode": request.mode,
        "scope": "selected_node_only" if request.action_type == "script_revision" else "selected_node_shot_plan",
    }
    if request.provider_service_id != SERVER_CODEX_SERVICE_ID:
        return _unavailable_preview(project_id, request, gate, target, reason="unsupported_provider_service")
    if gate.get("status") != "ready_not_run":
        return _unavailable_preview(project_id, request, gate, target, reason="remote_llm_gate_closed")
    if _contains_unsafe_fragment(request.source_text):
        return _unavailable_preview(project_id, request, gate, target, reason="unsafe_source_text")
    schema = _creative_action_output_schema(request.action_type)
    schema_digest = structured_output_schema_digest(schema)
    try:
        registry = load_provider_registry()
        provider_result = registry.dispatch(
            "llm",
            SERVER_CODEX_SERVICE_ID,
            ProviderDispatchRequest(
                prompt=_creative_action_prompt(project_id, request, graph_before, schema_digest),
                output_dir=output_dir,
                task_type=f"embedded_{request.action_type}",
                structured_output_contract_id=EMBEDDED_CREATIVE_CONTRACT_ID,
                structured_output_schema=schema,
                structured_output_schema_digest=schema_digest,
                timeout_sec=120.0,
            ),
        )
        structured = provider_result.get("structured_output") if isinstance(provider_result, dict) else None
        preview = _validate_preview_payload(request, structured or {})
    except (ModelConfigError, ModelGatewayError):
        return _unavailable_preview(project_id, request, gate, target, reason="llm_not_ready")
    except ValueError:
        return _unavailable_preview(project_id, request, gate, target, reason="unsafe_or_invalid_llm_preview")
    lineage = {
        "service_id": SERVER_CODEX_SERVICE_ID,
        "provider": "codex_local",
        "model_surface": "server-codex-login",
        "request_id": f"embedded_action_{project_id}_{int(time.time() * 1000)}",
        "structured_output_contract_id": EMBEDDED_CREATIVE_CONTRACT_ID,
        "structured_output_schema_digest": schema_digest,
        "provider_calls_started": True,
        "provider_raw_response_stored": False,
        "external_paid_cost_usd": 0,
    }
    return {
        "mode": "llm",
        "target": target,
        "preview": preview,
        "provider_gate": gate,
        "provider_calls_started": True,
        "provider_lineage": lineage,
        "safe_manifest": _safe_manifest(project_id, request, gate, target, mode="llm", lineage=lineage),
    }


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
                                        "duration_sec": {"type": "number", "minimum": 1},
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
    return "\n".join(
        [
            "你是 AFS Studio 的节点内 AI 创作动作引擎，服务专业影视创作者。",
            "这次只生成预览，不修改画布、不创建节点、不写入 ProductionGraph、不生成图片或视频。",
            "必须使用用户给定原文和安全上下文，不允许关键词模板、固定大纲、固定4x15/10x6或空泛标题。",
            "如果是普通优化/改写，输出应保留同一节点身份；只有用户明确要求分支才可建议分支。",
            "中文输出，内容必须可拍、可审、可继续拆分。",
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


def _validate_preview_payload(request: EmbeddedCreativeActionRequest, value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("structured output is not an object")
    revised_text = _safe_text(value.get("revised_text"), 20000)
    if len(revised_text) < 40 or revised_text.strip() == request.source_text.strip():
        raise ValueError("revised text is empty or unchanged")
    summary = [_safe_text(item, 180) for item in value.get("change_summary") or [] if _safe_text(item, 180)]
    rationale = _safe_text(value.get("rationale"), 420)
    if len(summary) < 2 or len(rationale) < 12:
        raise ValueError("preview is not reviewable")
    preview = {
        "preview_id": f"preview_{int(time.time() * 1000)}",
        "action_type": request.action_type,
        "mode": request.mode,
        "revised_text": revised_text,
        "change_summary": summary[:8],
        "rationale": rationale,
        "unresolved_decisions": [_safe_text(item, 180) for item in value.get("unresolved_decisions") or [] if _safe_text(item, 180)][:6],
        "quality_flags": [_safe_text(item, 180) for item in value.get("quality_flags") or [] if _safe_text(item, 180)][:6],
    }
    if request.action_type == "shot_breakdown":
        plan = value.get("shot_plan")
        if not isinstance(plan, dict):
            raise ValueError("shot plan is missing")
        preview["shot_plan"] = _safe_shot_plan(plan)
    reject_unsafe_payload(preview)
    return preview


def _safe_shot_plan(plan: dict[str, Any]) -> dict[str, Any]:
    scenes = []
    total = 0
    for scene in plan.get("scenes") or []:
        if not isinstance(scene, dict):
            continue
        shots = []
        for shot in scene.get("shots") or []:
            if not isinstance(shot, dict):
                continue
            shots.append({
                "title": _safe_text(shot.get("title"), 120),
                "duration_sec": max(1.0, min(30.0, _safe_number(shot.get("duration_sec"), 4.0))),
                "shot_size": _safe_text(shot.get("shot_size"), 80),
                "camera_angle": _safe_text(shot.get("camera_angle"), 80),
                "movement": _safe_text(shot.get("movement"), 120),
                "blocking": _safe_text(shot.get("blocking"), 180),
                "sound": _safe_text(shot.get("sound"), 120),
                "transition": _safe_text(shot.get("transition"), 80),
                "narrative_purpose": _safe_text(shot.get("narrative_purpose"), 180),
            })
        if not shots:
            continue
        total += len(shots)
        scenes.append({
            "title": _safe_text(scene.get("title"), 120),
            "purpose": _safe_text(scene.get("purpose"), 180),
            "shots": shots[:12],
        })
    if not scenes or total < 1:
        raise ValueError("shot plan has no shots")
    return {
        "scenes": scenes[:8],
        "total_shots": total,
        "estimated_duration_sec": max(1.0, min(600.0, _safe_number(plan.get("estimated_duration_sec"), sum(
            shot["duration_sec"] for scene in scenes for shot in scene["shots"]
        )))),
    }


def _unavailable_preview(
    project_id: str,
    request: EmbeddedCreativeActionRequest,
    gate: dict[str, str],
    target: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    preview = {
        "preview_id": f"blocked_{int(time.time() * 1000)}",
        "action_type": request.action_type,
        "mode": request.mode,
        "revised_text": "",
        "change_summary": [],
        "rationale": "AI 模型当前不可用；不会使用本地模板冒充专业改写。",
        "unresolved_decisions": ["稍后重试，或先手工编辑当前节点。"],
        "quality_flags": ["fail_closed_no_canvas_mutation"],
    }
    return {
        "mode": "unavailable",
        "target": target,
        "preview": preview,
        "provider_gate": gate,
        "provider_calls_started": False,
        "safe_manifest": _safe_manifest(project_id, request, gate, target, mode="unavailable", fallback_reason=reason),
    }


def _safe_manifest(
    project_id: str,
    request: EmbeddedCreativeActionRequest,
    gate: dict[str, str],
    target: dict[str, Any],
    *,
    mode: str,
    fallback_reason: str = "",
    lineage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = {
        "schema_version": "afs_embedded_creative_action_safe_manifest.v0.1",
        "project_id": project_id,
        "mode": mode,
        "target": target,
        "provider_service_id": request.provider_service_id,
        "provider_gate": gate,
        "fallback_reason": fallback_reason,
        "provider_calls_started": mode == "llm",
        "provider_lineage": lineage or {},
        "provider_raw_response_stored": False,
        "credentialed_urls_returned_by_api": False,
        "local_paths_returned_by_api": False,
        "media_bytes_returned_by_api": False,
        "canvas_mutation_enabled": False,
        "image_video_generation_enabled": False,
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


def _safe_number(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_token(value: Any, limit: int) -> str:
    return "".join(ch for ch in str(value or "") if ch.isalnum() or ch in "_-:.").strip()[:limit]


def _safe_text(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    if _contains_unsafe_fragment(text) or _contains_prompt_leak_fragment(text):
        raise ValueError("unsafe text")
    return text[:limit]


def _contains_unsafe_fragment(value: str) -> bool:
    lowered = str(value or "").lower()
    return any(fragment in lowered for fragment in UNSAFE_TEXT_FRAGMENTS)


def _contains_prompt_leak_fragment(value: str) -> bool:
    lowered = str(value or "").lower()
    return any(fragment in lowered for fragment in PROMPT_LEAK_FRAGMENTS)


__all__ = ("register_runtime_embedded_creative_action_routes",)
