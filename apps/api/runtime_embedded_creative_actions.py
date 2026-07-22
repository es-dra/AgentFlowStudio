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


EMBEDDED_CREATIVE_CONTRACT_ID = "afs.runtime.embedded_creative_action.v0.2"
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
                "creative_task": result.get("creative_task") or {},
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
        return _unavailable_preview(project_id, request, gate, target, task_id=task_id, reason="llm_not_ready")
    except ValueError:
        return _unavailable_preview(project_id, request, gate, target, task_id=task_id, reason="unsafe_or_invalid_llm_preview")
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


def _screenplay_candidate_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["title", "version_label", "logline", "characters", "scenes"],
        "properties": {
            "title": {"type": "string", "minLength": 2},
            "version_label": {"type": "string", "minLength": 1},
            "logline": {"type": "string", "minLength": 12},
            "characters": {
                "type": "array",
                "minItems": 1,
                "maxItems": 12,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name", "goal", "conflict", "change"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "goal": {"type": "string", "minLength": 4},
                        "conflict": {"type": "string", "minLength": 4},
                        "change": {"type": "string", "minLength": 4},
                    },
                },
            },
            "scenes": {
                "type": "array",
                "minItems": 1,
                "maxItems": 12,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
            "required": ["heading", "space_type", "location", "time_of_day", "purpose", "blocks"],
            "properties": {
                "heading": {"type": "string", "minLength": 4},
                "space_type": {"type": "string", "enum": ["内景", "外景", "INT.", "EXT."]},
                "location": {"type": "string", "minLength": 2},
                "time_of_day": {"type": "string", "minLength": 1},
                "purpose": {"type": "string", "minLength": 6},
                        "blocks": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 36,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["type", "text"],
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["action", "character", "dialogue", "parenthetical", "transition"],
                                    },
                                    "text": {"type": "string", "minLength": 1},
                                },
                            },
                        },
                    },
                },
            },
        },
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
            "如果动作是 script_revision，必须输出 screenplay_candidate：片名/版本/logline、角色目标冲突变化、按场排序的场景标题、地点、时间、动作、人物名、对白、转场；不要只写散文故事。",
            "screenplay_candidate.scenes[].space_type 必须是 内景、外景、INT. 或 EXT.；heading 必须以 内景 -、外景 -、INT. 或 EXT. 开头，禁止“内景/外景待定”、数字标题或散文小标题。",
            "每个场景标题必须包含空间类型、地点、时间三段，例如“内景 - 旧摄影棚 - 夜”；人物名提示后必须在同一场景内接对白，可夹一个括号提示，禁止悬空人物名。",
            "revised_text 只是 screenplay_candidate 的可读投影；镜头和摄影语言只在 shot_breakdown 里使用，不要混进文学剧本文本。",
            "如果动作是 shot_breakdown，只输出可审查分镜候选，不创建图片、不生成关键帧。",
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
    if request.action_type == "script_revision":
        candidate = value.get("screenplay_candidate")
        if not isinstance(candidate, dict):
            raise ValueError("screenplay candidate is missing")
        safe_candidate = _safe_screenplay_candidate(candidate)
        preview["screenplay_candidate"] = safe_candidate
        preview["revised_text"] = _screenplay_text_projection(safe_candidate)
    reject_unsafe_payload(preview)
    return preview


def _safe_screenplay_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    # A long prose story must fail this gate unless it is backed by typed screenplay scenes.
    characters = []
    for item in candidate.get("characters") or []:
        if not isinstance(item, dict):
            continue
        character = {
            "name": _safe_text(item.get("name"), 80),
            "goal": _safe_text(item.get("goal"), 180),
            "conflict": _safe_text(item.get("conflict"), 180),
            "change": _safe_text(item.get("change"), 180),
        }
        if all(character.values()):
            characters.append(character)
    scenes = []
    has_dialogue = False
    has_action = False
    for scene in candidate.get("scenes") or []:
        if not isinstance(scene, dict):
            continue
        blocks = []
        for block in scene.get("blocks") or []:
            if not isinstance(block, dict):
                continue
            block_type = _safe_token(block.get("type"), 32)
            text = _safe_text(block.get("text"), 600)
            if block_type not in {"action", "character", "dialogue", "parenthetical", "transition"} or not text:
                continue
            if block_type == "dialogue":
                has_dialogue = True
            if block_type == "action":
                has_action = True
            blocks.append({"type": block_type, "text": text})
        if not _valid_screenplay_block_flow(blocks):
            continue
        location = _safe_text(scene.get("location"), 120)
        time_of_day = _safe_text(scene.get("time_of_day"), 80)
        space_type = _safe_space_type(scene.get("space_type"))
        safe_scene = {
            "heading": _safe_scene_heading(scene.get("heading"), space_type=space_type, location=location, time_of_day=time_of_day),
            "space_type": space_type,
            "location": location,
            "time_of_day": time_of_day,
            "purpose": _safe_text(scene.get("purpose"), 220),
            "blocks": blocks[:36],
        }
        if safe_scene["heading"] and safe_scene["space_type"] and safe_scene["location"] and safe_scene["time_of_day"] and safe_scene["purpose"] and len(safe_scene["blocks"]) >= 2:
            scenes.append(safe_scene)
    if not characters or not scenes or not has_action:
        raise ValueError("screenplay candidate lacks professional scene/action structure")
    if not has_dialogue and len(characters) > 1:
        raise ValueError("screenplay candidate lacks dialogue for multi-character material")
    return {
        "schema_version": "afs.screenplay_candidate.v0.1",
        "title": _safe_text(candidate.get("title"), 120) or "未命名剧本",
        "version_label": _safe_text(candidate.get("version_label"), 80) or "v1",
        "logline": _safe_text(candidate.get("logline"), 360),
        "characters": characters[:12],
        "scenes": scenes[:12],
    }


def _safe_space_type(value: Any) -> str:
    text = _safe_text(value, 16).upper()
    if text in {"INT.", "INT"}:
        return "INT."
    if text in {"EXT.", "EXT"}:
        return "EXT."
    if str(value or "").strip() in {"内景", "外景"}:
        return str(value).strip()
    return ""


def _safe_scene_heading(value: Any, *, space_type: str, location: str, time_of_day: str) -> str:
    text = _safe_text(value, 160)
    if space_type and location and time_of_day:
        fallback = f"{space_type} - {location} - {time_of_day}"
    else:
        fallback = ""
    if not text:
        return fallback
    upper = text.upper()
    if "内景/外景待定" in text or upper.startswith(("1.", "2.", "3.", "4.", "5.", "6.")):
        return fallback
    normalized = text.replace("—", "-").replace("－", "-")
    parts = [part.strip() for part in normalized.split("-") if part.strip()]
    if parts and parts[0] in {"内景", "外景"}:
        if len(parts) >= 3:
            return f"{parts[0]} - {parts[1]} - {parts[2]}"
        return fallback
    if upper.startswith(("INT.", "EXT.")):
        if len(parts) >= 2 and parts[-1]:
            return text
        return fallback
    return ""


def _valid_screenplay_block_flow(blocks: list[dict[str, str]]) -> bool:
    if not blocks:
        return False
    expecting_dialogue = False
    for block in blocks:
        block_type = block.get("type")
        if block_type == "character":
            if expecting_dialogue:
                return False
            expecting_dialogue = True
        elif block_type == "parenthetical":
            if not expecting_dialogue:
                return False
        elif block_type == "dialogue":
            if not expecting_dialogue:
                return False
            expecting_dialogue = False
        elif block_type in {"action", "transition"}:
            if expecting_dialogue:
                return False
        else:
            return False
    return not expecting_dialogue


def _screenplay_text_projection(candidate: dict[str, Any]) -> str:
    lines = [
        f"《{candidate.get('title') or '未命名剧本'}》",
        f"版本：{candidate.get('version_label') or 'v1'}",
        f"一句话梗概：{candidate.get('logline') or ''}",
        "",
        "角色",
    ]
    for character in candidate.get("characters") or []:
        lines.append(
            f"- {character.get('name') or '角色'}：目标 {character.get('goal') or '待定'}；"
            f"冲突 {character.get('conflict') or '待定'}；变化 {character.get('change') or '待定'}"
        )
    for scene in candidate.get("scenes") or []:
        lines.extend(["", scene.get("heading") or "场景", f"场景目的：{scene.get('purpose') or '待定'}", ""])
        for block in scene.get("blocks") or []:
            block_type = block.get("type")
            text = block.get("text") or ""
            if block_type == "action":
                lines.extend([text, ""])
            elif block_type == "character":
                lines.append(text)
            elif block_type == "dialogue":
                lines.extend([text, ""])
            elif block_type == "parenthetical":
                lines.append(f"（{text.strip('（）()')}）")
            elif block_type == "transition":
                lines.extend([f"转场：{text}", ""])
    return "\n".join(lines).strip()


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
    task_id: str,
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
        "creative_task": _creative_task(
            task_id,
            project_id,
            request,
            state="failed",
            phase="failed",
            completed_phases=["queued", "context"],
            error_owner="llm_provider",
            error_category=reason,
        ),
        "provider_gate": gate,
        "provider_calls_started": False,
        "safe_manifest": _safe_manifest(project_id, request, gate, target, mode="unavailable", fallback_reason=reason),
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
