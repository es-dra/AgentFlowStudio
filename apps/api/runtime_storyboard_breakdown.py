from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest, load_provider_registry
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_flow import build_flow_summary
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_llm_enhancement_dispatch import dispatch_llm_with_fallback
from apps.api.runtime_llm_enhancement_gate import llm_provider_gate
from apps.api.runtime_models import PromptOptimizationRequest, StoryboardBreakdownRequest
from apps.api.runtime_storyboard_local import local_storyboard_shots, normalize_asset_ref, structured_shot
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload
from apps.api.runtime_tracing import artifact_refs, write_run_trace


STORYBOARD_NON_CLAIMS = [
    "not human acceptance",
    "not fixed asset memory",
    "not provider smoke when provider_calls_started is false",
]


def register_runtime_storyboard_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/projects/{project_id}/storyboard-breakdowns")
    def storyboard_breakdown(project_id: str, request: StoryboardBreakdownRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        job_id = store.new_job_id("storyboard_breakdown", project_id)
        output_dir = store.run_dir(project_id, job_id)
        try:
            result = build_storyboard_breakdown(project_id, request, output_dir)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_storyboard_breakdown")) from exc

        artifacts = _write_storyboard_artifacts(store, output_dir, result)
        trace_path = write_run_trace(
            output_dir,
            project_id=project_id,
            job_id=job_id,
            action="storyboard_breakdown",
            status="succeeded",
            input_refs=[
                {"role": "node_id", "ref": request.node_id or "not_provided"},
                {"role": "script_text", "ref": "request_body.script_text"},
                {"role": "target_platform", "ref": request.target_platform},
                {"role": "style", "ref": request.style},
            ],
            generated_artifact_refs=artifact_refs(artifacts),
            tester_feedback={"status": "storyboard_breakdown_ready_for_human_review"},
            tool_gate_state={
                "remote_llm": str(result["provider_gate"].get("status") or "blocked"),
                "remote_asr": "not_requested",
                "remote_image": "not_requested",
                "remote_video": "not_requested",
                "remote_vision": "not_requested",
            },
        )
        artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
        public_job = store.write_job(runtime_job(job_id, project_id, "storyboard_breakdown", "succeeded", artifacts=artifacts))
        return {
            "job": public_job,
            "shots": result["shots"],
            "provider_gate": result["provider_gate"],
            "provider_calls_started": result["provider_calls_started"],
            "writes_long_term_memory": False,
            "writes_company_kb": False,
            "safe_manifest": result["safe_manifest"],
            "artifacts": artifacts,
            "flow": build_flow_summary(store, project_id),
            "non_claims": STORYBOARD_NON_CLAIMS,
        }


def build_storyboard_breakdown(project_id: str, request: StoryboardBreakdownRequest, output_dir: Path) -> dict[str, Any]:
    gate = llm_provider_gate()
    provider_calls_started = False
    shots: list[dict[str, Any]] | None = None
    status = "local_fallback"
    discard_reason = None
    if gate["status"] != "blocked":
        try:
            registry = load_provider_registry()
            llm_request = _llm_request(request)
            dispatch_request = ProviderDispatchRequest(
                prompt=_storyboard_instruction(request),
                output_dir=output_dir,
                task_type="storyboard_breakdown",
            )
            provider_result = dispatch_llm_with_fallback(registry, llm_request, dispatch_request)
            provider_calls_started = bool(provider_result.get("provider_calls_started", True))
            shots = _shots_from_provider_text(str(provider_result.get("text") or ""))
            status = "provider_structured"
        except ValueError as exc:
            discard_reason = _safe_reason(str(exc))
            shots = None
            status = "local_fallback"
        except ModelGatewayError as exc:
            discard_reason = _safe_reason(str(exc))
            shots = None
            provider_calls_started = False
            status = "local_fallback"
    if not shots:
        shots = local_storyboard_shots(request.script_text, request.shot_count_hint)
    safe_manifest = {
        "artifact_type": "agentflow_storyboard_breakdown_safe_manifest",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "node_id": request.node_id,
        "status": status,
        "provider_gate": gate,
        "provider_calls_started": provider_calls_started,
        "raw_provider_response_stored": False,
        "generated_media_bytes_stored": False,
        "asset_nodes_created": False,
        "shot_count": len(shots),
        "discard_reason": discard_reason,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": STORYBOARD_NON_CLAIMS,
    }
    artifact = {
        "artifact_type": "agentflow_storyboard_breakdown_safe_artifact",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "node_id": request.node_id,
        "provider_output": provider_calls_started,
        "shots": shots,
        "asset_nodes_created": False,
        "review_state": "needs_human_review_before_asset_identification",
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }
    request_plan = {
        "artifact_type": "agentflow_storyboard_breakdown_request_plan",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "node_id": request.node_id,
        "target_platform": request.target_platform,
        "style": request.style,
        "shot_count_hint": request.shot_count_hint,
        "provider_gate": gate,
        "provider_calls_started": provider_calls_started,
        "raw_provider_response_stored": False,
    }
    for payload in (safe_manifest, artifact, request_plan):
        reject_unsafe_payload(payload)
    return {
        "shots": shots,
        "provider_gate": gate,
        "provider_calls_started": provider_calls_started,
        "safe_manifest": safe_manifest,
        "safe_artifact": artifact,
        "request_plan": request_plan,
    }


def _write_storyboard_artifacts(store: RuntimeStore, output_dir: Path, result: dict[str, Any]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "storyboard_breakdown_request_plan.json", result["request_plan"])
    write_json(output_dir / "storyboard_breakdown_safe_artifact.json", result["safe_artifact"])
    write_json(output_dir / "storyboard_breakdown_safe_manifest.json", result["safe_manifest"])
    return {
        "storyboard_breakdown_request_plan": store.register_artifact(
            output_dir / "storyboard_breakdown_request_plan.json",
            role="storyboard_breakdown_request_plan",
        ),
        "storyboard_breakdown_safe_artifact": store.register_artifact(
            output_dir / "storyboard_breakdown_safe_artifact.json",
            role="storyboard_breakdown_safe_artifact",
        ),
        "storyboard_breakdown_safe_manifest": store.register_artifact(
            output_dir / "storyboard_breakdown_safe_manifest.json",
            role="storyboard_breakdown_safe_manifest",
        ),
    }


def _llm_request(request: StoryboardBreakdownRequest) -> PromptOptimizationRequest:
    params = dict(request.node_parameters or {})
    params.setdefault("llm_provider", "prompt_optimizer")
    return PromptOptimizationRequest(
        node_id=request.node_id,
        node_type="text",
        prompt_text=request.script_text,
        generation_target="script",
        target_platform=request.target_platform,
        style=request.style,
        node_parameters=params,
        generated_at=request.generated_at,
    )


def _storyboard_instruction(request: StoryboardBreakdownRequest) -> str:
    count_line = f"建议镜头数量：{request.shot_count_hint}" if request.shot_count_hint else "根据剧情自动决定镜头数量，避免机械三段切分。"
    return "\n".join(
        [
            "你是影视分镜导演。请把输入剧本拆成专业分镜脚本，输出严格 JSON，不要 Markdown。",
            count_line,
            "JSON 格式：{\"shots\":[{shot_id,index,duration,description,shot_size,light_atmosphere,camera_motion,dialogue,sound,asset_refs}]}",
            "asset_refs 每项必须包含 label, asset_type(character|scene|prop), status, source。描述中涉及角色、场景、道具时必须用 @名称 显式标注。",
            "每个镜头要包含时长、画面描述、景别、光影氛围、运镜、对白/旁白、音效。",
            f"平台：{request.target_platform}；风格：{request.style}",
            "剧本：",
            request.script_text,
        ]
    )


def _shots_from_provider_text(text: str) -> list[dict[str, Any]]:
    payload = _json_from_text(text)
    raw_shots = payload.get("shots")
    if not isinstance(raw_shots, list):
        raise ValueError("provider storyboard response missing shots")
    shots = [_normalize_provider_shot(item, index + 1) for index, item in enumerate(raw_shots)]
    shots = [item for item in shots if item]
    if not shots:
        raise ValueError("provider storyboard response has no usable shots")
    return shots


def _json_from_text(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("provider storyboard response is not json") from None
        payload = json.loads(text[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("provider storyboard response root is not object")
    return payload


def _normalize_provider_shot(item: Any, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    description = _clean(item.get("description") or item.get("source_text") or "")
    fallback = structured_shot(description, index)
    asset_refs = item.get("asset_refs")
    if isinstance(asset_refs, list) and asset_refs:
        refs = [normalize_asset_ref(asset, idx) for idx, asset in enumerate(asset_refs)]
        refs = [ref for ref in refs if ref]
    else:
        refs = fallback["asset_refs"]
    return {
        **fallback,
        "shot_id": str(item.get("shot_id") or fallback["shot_id"]),
        "index": int(item.get("index") or index),
        "duration": str(item.get("duration") or fallback["duration"]),
        "description": description or fallback["description"],
        "shot_size": str(item.get("shot_size") or fallback["shot_size"]),
        "light_atmosphere": str(item.get("light_atmosphere") or fallback["light_atmosphere"]),
        "camera_motion": str(item.get("camera_motion") or fallback["camera_motion"]),
        "dialogue": str(item.get("dialogue") or fallback["dialogue"]),
        "sound": str(item.get("sound") or fallback["sound"]),
        "asset_refs": refs,
        "source_text": _clean(item.get("source_text") or description),
    }


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _safe_reason(value: str) -> str:
    lowered = value.lower()
    if any(term in lowered for term in ("api", "key", "secret", "token", "authorization", "cookie")):
        return "llm provider configuration is not ready"
    return " ".join(value.split())[:160] or "llm provider is not ready"


__all__ = (
    "STORYBOARD_NON_CLAIMS",
    "build_storyboard_breakdown",
    "local_storyboard_shots",
    "register_runtime_storyboard_routes",
)
