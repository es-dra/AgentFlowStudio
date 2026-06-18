from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest, load_provider_registry
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_flow import build_flow_summary
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_llm_enhancement import llm_provider_gate
from apps.api.runtime_models import SpriteChatRequest
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload
from apps.api.runtime_tracing import artifact_refs, write_run_trace


SPRITE_REMOTE_PROMPT_FORBIDDEN_FRAGMENTS = ("signed url", "provider raw", "api key")


def register_runtime_sprite_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/projects/{project_id}/sprite/chat")
    def sprite_chat(project_id: str, request: SpriteChatRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        job_id = store.new_job_id("sprite_chat", project_id)
        output_dir = store.run_dir(project_id, job_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            gate = llm_provider_gate()
            result = _sprite_reply(project_id, request, output_dir, gate)
            artifacts = _write_sprite_artifacts(
                store,
                output_dir,
                safe_manifest=result["safe_manifest"],
                reply_payload={
                    "project_id": project_id,
                    "mode": result["mode"],
                    "reply": result["reply"],
                    "suggested_actions": result["suggested_actions"],
                },
            )
            trace_path = write_run_trace(
                output_dir,
                project_id=project_id,
                job_id=job_id,
                action="sprite_chat",
                status="succeeded",
                input_refs=[
                    {"role": "node_id", "ref": request.node_id or "not_provided"},
                    {"role": "provider_service_id", "ref": request.provider_service_id},
                ],
                generated_artifact_refs=artifact_refs(artifacts),
                tester_feedback={"status": "decorative_chat_reply_recorded"},
                tool_gate_state={"remote_llm": str(gate.get("status") or "unknown")},
            )
            artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_sprite_chat")) from exc
        job = runtime_job(job_id, project_id, "sprite_chat", "succeeded", artifacts=artifacts)
        return {
            "project_id": project_id,
            "job": store.write_job(job),
            "mode": result["mode"],
            "reply": result["reply"],
            "suggested_actions": result["suggested_actions"],
            "provider_gate": gate,
            "provider_calls_started": result["provider_calls_started"],
            "safe_manifest": result["safe_manifest"],
            "artifacts": artifacts,
            "flow": build_flow_summary(store, project_id),
        }


def _sprite_reply(
    project_id: str,
    request: SpriteChatRequest,
    output_dir: Path,
    gate: dict[str, str],
) -> dict[str, Any]:
    if gate.get("status") != "ready_not_run":
        return _local_sprite_reply(project_id, request, gate)
    if _contains_unsafe_private_fragment(request.message):
        return _local_sprite_reply(project_id, request, gate, fallback_reason="unsafe_user_message")
    try:
        registry = load_provider_registry()
        provider_result = registry.dispatch(
            "llm",
            request.provider_service_id,
            ProviderDispatchRequest(
                prompt=_sprite_llm_prompt(project_id, request),
                output_dir=output_dir,
                task_type="sprite_chat",
                timeout_sec=45.0,
            ),
        )
        reply = _safe_reply_text(str(provider_result.get("text") or ""))
    except ModelGatewayError:
        return _local_sprite_reply(project_id, request, gate, mode="local_rules", fallback_reason="llm_not_ready")
    except ValueError:
        return _local_sprite_reply(project_id, request, gate, mode="local_rules", fallback_reason="unsafe_llm_reply")
    if not reply:
        return _local_sprite_reply(project_id, request, gate, mode="local_rules", fallback_reason="empty_llm_reply")
    return {
        "mode": "llm",
        "reply": reply,
        "suggested_actions": [],
        "provider_calls_started": True,
        "safe_manifest": _safe_manifest(project_id, request, gate, mode="llm"),
    }


def _local_sprite_reply(
    project_id: str,
    request: SpriteChatRequest,
    gate: dict[str, str],
    *,
    mode: str = "local_rules",
    fallback_reason: str = "",
) -> dict[str, Any]:
    message = request.message.strip()
    summary = request.canvas_summary if isinstance(request.canvas_summary, dict) else {}
    node_count = _safe_int(summary.get("nodes"))
    asset_count = _safe_int(summary.get("assets"))
    lowered = message.lower()
    if "下一步" in message or "继续" in message or "next" in lowered:
        reply = f"下一步建议先选中当前关键节点，确认它需要的参考图和已确认资产；当前画布约有 {node_count} 个节点、{asset_count} 个素材。"
    elif "素材" in message or "资产" in message:
        reply = "可以先把候选素材整理成已确认资产，再进入下一次生成。只有确认后的角色或场景资产会默认参与上下文调度。"
    elif "连线" in message or "节点" in message:
        reply = "可以从节点右侧加号拖到下游节点，形成生成链路；连线只表达上下文引用，不会自动触发远程生成。"
    else:
        reply = "我现在先作为画布小助手陪跑：可以回答下一步、素材确认、节点连线和生成前检查这类问题。"
    return {
        "mode": mode,
        "reply": reply,
        "suggested_actions": [],
        "provider_calls_started": False,
        "safe_manifest": _safe_manifest(project_id, request, gate, mode=mode, fallback_reason=fallback_reason),
    }


def _sprite_llm_prompt(project_id: str, request: SpriteChatRequest) -> str:
    summary = _safe_canvas_summary(request.canvas_summary)
    return "\n".join(
        [
            "You are AFS Studio's decorative canvas sprite assistant.",
            "Answer in concise Chinese, one or two sentences.",
            "Do not include local paths, signed URLs, credentials, raw provider responses, or media bytes.",
            "Do not execute actions. Do not claim generation has run.",
            f"Project id: {project_id}",
            f"Selected node id: {request.node_id or 'none'}",
            f"Canvas summary: {summary}",
            f"User message: {request.message}",
        ]
    )


def _safe_manifest(
    project_id: str,
    request: SpriteChatRequest,
    gate: dict[str, str],
    *,
    mode: str,
    fallback_reason: str = "",
) -> dict[str, Any]:
    manifest = {
        "schema_version": "afs_sprite_chat_safe_manifest.v0.1",
        "project_id": project_id,
        "mode": mode,
        "node_id": request.node_id or "",
        "provider_service_id": request.provider_service_id,
        "provider_gate": gate,
        "fallback_reason": fallback_reason,
        "provider_raw_response_stored": False,
        "credentialed_urls_returned_by_api": False,
        "local_paths_returned_by_api": False,
        "media_bytes_returned_by_api": False,
        "action_execution_enabled": False,
    }
    reject_unsafe_payload(manifest)
    return manifest


def _write_sprite_artifacts(
    store: RuntimeStore,
    output_dir: Path,
    *,
    safe_manifest: dict[str, Any],
    reply_payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    reject_unsafe_payload(safe_manifest)
    reject_unsafe_payload(reply_payload)
    write_json(output_dir / "sprite_chat_safe_manifest.json", safe_manifest)
    write_json(output_dir / "sprite_chat_reply.json", reply_payload)
    return {
        "sprite_chat_safe_manifest": store.register_artifact(
            output_dir / "sprite_chat_safe_manifest.json",
            role="sprite_chat_safe_manifest",
        ),
        "sprite_chat_reply": store.register_artifact(output_dir / "sprite_chat_reply.json", role="sprite_chat_reply"),
    }


def _safe_canvas_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    allowed = {"nodes", "assets", "edges", "selected_node_type", "selected_node_status"}
    return {key: _safe_summary_value(value.get(key)) for key in allowed if key in value}


def _safe_summary_value(value: Any) -> str | int:
    if isinstance(value, (int, float)):
        return int(value)
    return str(value or "").replace("\\", "/").split("/")[-1][:80]


def _safe_reply_text(value: str) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    if _contains_unsafe_private_fragment(text):
        raise ValueError("unsafe sprite reply")
    return text[:600]


def _contains_unsafe_private_fragment(value: str) -> bool:
    lowered = str(value or "").lower()
    fragments = AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS + SPRITE_REMOTE_PROMPT_FORBIDDEN_FRAGMENTS
    return any(fragment.lower() in lowered for fragment in fragments)


def _safe_int(value: Any) -> int:
    try:
        return max(0, min(int(value or 0), 999))
    except (TypeError, ValueError):
        return 0


__all__ = ("register_runtime_sprite_routes",)
