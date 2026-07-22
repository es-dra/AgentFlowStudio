from __future__ import annotations

import time
from pathlib import Path
from typing import Any

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
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_llm_enhancement import llm_provider_gate
from apps.api.runtime_production_graph import ProductionGraphStore
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload
from apps.api.runtime_tracing import artifact_refs, write_run_trace


AGENT_CHAT_CONTRACT_ID = "afs.runtime.agent_chat_conversation.v0.1"
AGENT_CHAT_NON_CLAIMS = [
    "not_canvas_mutation",
    "not_paid_image_video_generation",
    "not_human_acceptance",
    "not_business_validation",
]
UNSAFE_MESSAGE_FRAGMENTS = (
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


class AgentChatConversationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=1200)
    node_id: str | None = Field(default=None, max_length=160)
    canvas_summary: dict[str, Any] = Field(default_factory=dict)
    provider_service_id: str = SERVER_CODEX_SERVICE_ID
    generated_at: str = Field(min_length=1, max_length=80)


def register_runtime_agent_chat_conversation_routes(
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

    @app.post("/projects/{project_id}/agent-chat/conversation")
    def agent_chat_conversation(
        project_id: str,
        body: AgentChatConversationRequest,
        request: Request,
    ) -> dict[str, Any]:
        require_access(request, project_id)
        store.ensure_project_manifest(project_id)
        job_id = store.new_job_id("agent_chat_conversation", project_id)
        output_dir = store.run_dir(project_id, job_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        graph_before = graph_store.ensure(project_id)
        started = time.perf_counter()
        result = _agent_chat_reply(project_id, body, output_dir, graph_before)
        result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        graph_after = graph_store.ensure(project_id)
        result["graph_mutation"] = _graph_mutation_summary(graph_before, graph_after)
        artifacts = _write_agent_chat_artifacts(
            store,
            output_dir,
            safe_manifest=result["safe_manifest"],
            reply_payload={
                "project_id": project_id,
                "mode": result["mode"],
                "reply": result["reply"],
                "suggested_actions": result["suggested_actions"],
                "provider_lineage": result.get("provider_lineage") or {},
                "graph_mutation": result["graph_mutation"],
            },
        )
        trace_path = write_run_trace(
            output_dir,
            project_id=project_id,
            job_id=job_id,
            action="agent_chat_conversation",
            status="succeeded" if result["mode"] == "llm" else "blocked",
            input_refs=[
                {"role": "node_id", "ref": body.node_id or "not_provided"},
                {"role": "provider_service_id", "ref": body.provider_service_id},
            ],
            generated_artifact_refs=artifact_refs(artifacts),
            tester_feedback={"status": result["mode"]},
            tool_gate_state={"remote_llm": result["provider_gate"]["status"]},
        )
        artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
        job = runtime_job(job_id, project_id, "agent_chat_conversation", "succeeded", artifacts=artifacts)
        response = {
            "project_id": project_id,
            "job": store.write_job(job),
            "mode": result["mode"],
            "reply": result["reply"],
            "suggested_actions": result["suggested_actions"],
            "provider_gate": result["provider_gate"],
            "provider_calls_started": result["provider_calls_started"],
            "provider_lineage": result.get("provider_lineage") or {},
            "safe_manifest": result["safe_manifest"],
            "graph_mutation": result["graph_mutation"],
            "latency_ms": result["latency_ms"],
            "cost_usd": 0,
            "artifacts": artifacts,
            "non_claims": AGENT_CHAT_NON_CLAIMS,
        }
        reject_unsafe_payload(response)
        return response


def _agent_chat_reply(
    project_id: str,
    request: AgentChatConversationRequest,
    output_dir: Path,
    graph_before: dict[str, Any],
) -> dict[str, Any]:
    gate = llm_provider_gate()
    if request.provider_service_id != SERVER_CODEX_SERVICE_ID:
        return _unavailable_reply(project_id, request, gate, reason="unsupported_provider_service")
    if gate.get("status") != "ready_not_run":
        return _unavailable_reply(project_id, request, gate, reason="remote_llm_gate_closed")
    if _contains_unsafe_fragment(request.message):
        return _unavailable_reply(project_id, request, gate, reason="unsafe_user_message")
    schema = _agent_chat_output_schema()
    schema_digest = structured_output_schema_digest(schema)
    try:
        registry = load_provider_registry()
        provider_result = registry.dispatch(
            "llm",
            SERVER_CODEX_SERVICE_ID,
            ProviderDispatchRequest(
                prompt=_agent_chat_prompt(project_id, request, graph_before, schema_digest),
                output_dir=output_dir,
                task_type="agent_chat_conversation",
                structured_output_contract_id=AGENT_CHAT_CONTRACT_ID,
                structured_output_schema=schema,
                structured_output_schema_digest=schema_digest,
                timeout_sec=90.0,
            ),
        )
        structured = provider_result.get("structured_output") if isinstance(provider_result, dict) else None
        reply = _safe_reply_text(str((structured or {}).get("reply") or provider_result.get("text") or ""))
        actions = _safe_suggested_actions((structured or {}).get("suggested_actions"))
    except (ModelConfigError, ModelGatewayError):
        return _unavailable_reply(project_id, request, gate, reason="llm_not_ready")
    except ValueError:
        return _unavailable_reply(project_id, request, gate, reason="unsafe_llm_reply")
    if not reply:
        return _unavailable_reply(project_id, request, gate, reason="empty_llm_reply")
    lineage = {
        "service_id": SERVER_CODEX_SERVICE_ID,
        "provider": "codex_local",
        "model_surface": "server-codex-login",
        "request_id": f"agent_chat_{project_id}_{int(time.time() * 1000)}",
        "structured_output_contract_id": AGENT_CHAT_CONTRACT_ID,
        "structured_output_schema_digest": schema_digest,
        "provider_calls_started": True,
        "provider_raw_response_stored": False,
        "external_paid_cost_usd": 0,
    }
    return {
        "mode": "llm",
        "reply": reply,
        "suggested_actions": actions,
        "provider_gate": gate,
        "provider_calls_started": True,
        "provider_lineage": lineage,
        "safe_manifest": _safe_manifest(project_id, request, gate, mode="llm", lineage=lineage),
    }


def _unavailable_reply(
    project_id: str,
    request: AgentChatConversationRequest,
    gate: dict[str, str],
    *,
    reason: str,
) -> dict[str, Any]:
    return {
        "mode": "unavailable",
        "reply": "AI 模型当前不可用，我不会用本地固定回答冒充理解；请稍后重试，或先用画布按钮创建节点和预览命令。",
        "suggested_actions": ["检查 LLM gate", "稍后重试", "继续本地可逆画布操作"],
        "provider_gate": gate,
        "provider_calls_started": False,
        "safe_manifest": _safe_manifest(project_id, request, gate, mode="unavailable", fallback_reason=reason),
    }


def _agent_chat_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["reply", "intent", "suggested_actions", "confidence"],
        "properties": {
            "reply": {"type": "string", "minLength": 12},
            "intent": {
                "type": "string",
                "enum": ["greeting", "node_explanation", "next_step", "relation_explanation", "general_question"],
            },
            "suggested_actions": {"type": "array", "maxItems": 3, "items": {"type": "string"}},
            "confidence": {"type": "number"},
        },
    }


def _agent_chat_prompt(
    project_id: str,
    request: AgentChatConversationRequest,
    graph_before: dict[str, Any],
    schema_digest: str,
) -> str:
    summary = _safe_canvas_summary(request.canvas_summary)
    graph_summary = {
        "version": int(graph_before.get("version") or 0),
        "graph_digest": str(graph_before.get("graph_digest") or "")[:16],
        "nodes": len(graph_before.get("nodes") or {}),
        "relations": len(graph_before.get("relations") or []),
    }
    return "\n".join(
        [
            "你是 AFS Studio 的 AI 创作搭档，服务专业影视创作者。",
            "请用自然、具体、简洁的中文回答用户，一到三句话。",
            "你现在只回答问题或给建议；不要声称已经修改画布、生成媒体、保存文件或扣费。",
            "如果用户问节点、连线、下一步或费用，请结合安全上下文回答。",
            "如果上下文不足，只提出最小必要澄清，不要编造不存在的剧本、资产或上游事实。",
            "不要输出内部路径、端口、provider raw、密钥、请求头、schema 名称或调度细节。",
            f"Closed schema digest: {schema_digest}",
            f"Project id: {project_id}",
            f"Selected node id: {request.node_id or 'none'}",
            f"Canvas summary: {summary}",
            f"ProductionGraph summary: {graph_summary}",
            f"User message: {request.message}",
        ]
    )


def _safe_manifest(
    project_id: str,
    request: AgentChatConversationRequest,
    gate: dict[str, str],
    *,
    mode: str,
    fallback_reason: str = "",
    lineage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = {
        "schema_version": "afs_agent_chat_conversation_safe_manifest.v0.1",
        "project_id": project_id,
        "mode": mode,
        "node_id": request.node_id or "",
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
        "action_execution_enabled": False,
    }
    reject_unsafe_payload(manifest)
    return manifest


def _write_agent_chat_artifacts(
    store: RuntimeStore,
    output_dir: Path,
    *,
    safe_manifest: dict[str, Any],
    reply_payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    reject_unsafe_payload(safe_manifest)
    reject_unsafe_payload(reply_payload)
    write_json(output_dir / "agent_chat_conversation_safe_manifest.json", safe_manifest)
    write_json(output_dir / "agent_chat_conversation_reply.json", reply_payload)
    return {
        "agent_chat_conversation_safe_manifest": store.register_artifact(
            output_dir / "agent_chat_conversation_safe_manifest.json",
            role="agent_chat_conversation_safe_manifest",
        ),
        "agent_chat_conversation_reply": store.register_artifact(
            output_dir / "agent_chat_conversation_reply.json",
            role="agent_chat_conversation_reply",
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


def _safe_canvas_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    allowed = {
        "nodes",
        "edges",
        "assets",
        "selected_node_type",
        "selected_node_status",
        "selected_node_title",
        "selected_edge_relation_type",
        "selected_edge_from_title",
        "selected_edge_to_title",
        "section",
    }
    return {key: _safe_summary_value(value.get(key)) for key in allowed if key in value}


def _safe_summary_value(value: Any) -> str | int:
    if isinstance(value, (int, float)):
        return int(value)
    return str(value or "").replace("\\", "/").split("/")[-1][:120]


def _safe_suggested_actions(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_safe_reply_text(str(item)) for item in value[:3] if _safe_reply_text(str(item))]


def _safe_reply_text(value: str) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    if _contains_unsafe_fragment(text) or _contains_prompt_leak_fragment(text):
        raise ValueError("unsafe agent chat reply")
    return text[:360]


def _contains_unsafe_fragment(value: str) -> bool:
    lowered = str(value or "").lower()
    return any(fragment in lowered for fragment in UNSAFE_MESSAGE_FRAGMENTS)


def _contains_prompt_leak_fragment(value: str) -> bool:
    lowered = str(value or "").lower()
    return any(fragment in lowered for fragment in PROMPT_LEAK_FRAGMENTS)


__all__ = ("register_runtime_agent_chat_conversation_routes",)
