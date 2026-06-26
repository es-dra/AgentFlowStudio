from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentflow.algorithms.request_projection import build_request_plan
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest
from apps.api.runtime_generation_preflight import video_generation_preflight
from apps.api.runtime_image_assets import image_asset_file_path, image_asset_metadata
from apps.api.runtime_media_validation import reference_image_size_blocks
from apps.api.runtime_model_call_context import video_generation_model_call_context
from apps.api.runtime_models import VideoGenerationRequest
from apps.api.runtime_store import RuntimeStore, read_json
from apps.api.runtime_video_candidates import safe_outputs
from apps.api.runtime_video_constants import REMOTE_VIDEO_ENV
from apps.api.runtime_video_gate import gate_closed_block, provider_not_ready_block, video_gate
from apps.api.runtime_video_manifest import (
    result_from_manifest,
    safe_manifest,
    write_json_checked,
    write_model_call_artifacts,
)
from apps.api.runtime_video_prompt import video_provider_prompt
from apps.api.runtime_video_task_state import (
    daily_submit_count,
    daily_submit_limit,
    increment_daily_submit_count,
    load_task_state,
    provider_task_for_poll,
    provider_task_for_state,
    write_task_state,
)


def submit_video_generation(
    store: RuntimeStore,
    project_id: str,
    job_id: str,
    request: VideoGenerationRequest,
    output_dir: Path,
    *,
    load_registry: Callable[[], Any],
) -> dict[str, Any]:
    if request.candidate_count != 1:
        raise ValueError("video candidate_count must be 1")
    first_frame_path = image_asset_file_path(store, project_id, request.first_frame_image_asset_id)
    frame_metadata = [image_asset_metadata(store, project_id, request.first_frame_image_asset_id)]
    last_frame_path = None
    if request.last_frame_image_asset_id:
        last_frame_path = image_asset_file_path(store, project_id, request.last_frame_image_asset_id)
        frame_metadata.append(image_asset_metadata(store, project_id, request.last_frame_image_asset_id))
    preflight = video_generation_preflight(store, project_id, request)
    context_bundle = preflight.get("context_bundle")
    provider_prompt = video_provider_prompt(request, context_bundle)
    model_call_context = _model_call_context(project_id, request, context_bundle)
    model_request_plan = build_request_plan(
        model_call_context=model_call_context,
        canonical_brief={"canonical_prompt": provider_prompt},
        provider_service_id=request.provider_service_id,
    )
    artifacts = write_model_call_artifacts(store, output_dir, model_call_context, model_request_plan)
    try:
        registry = load_registry()
        descriptor = registry.descriptor(request.provider_service_id)
    except ModelGatewayError as exc:
        return _blocked_result(project_id, output_dir, context_bundle, model_call_context, artifacts, model_request_plan, provider_not_ready_block(str(exc)))
    required_gate = str(getattr(descriptor, "required_gate", REMOTE_VIDEO_ENV) or REMOTE_VIDEO_ENV)
    gate = video_gate(required_gate)
    if gate["status"] == "blocked":
        return _blocked_result(project_id, output_dir, context_bundle, model_call_context, artifacts, model_request_plan, gate_closed_block(required_gate), gate)
    min_edge = int(getattr(descriptor, "min_reference_image_edge_px", 0) or 0)
    if size_blocks := reference_image_size_blocks(frame_metadata, min_edge_px=min_edge, capability="video", required_gate=required_gate):
        return _blocked_result(project_id, output_dir, context_bundle, model_call_context, artifacts, model_request_plan, size_blocks[0], gate, blocks=size_blocks)
    if daily_submit_count(store, project_id) >= daily_submit_limit() and not request.quota_override_confirmed:
        raise ValueError("daily video submit quota requires quota_override_confirmed")
    reference_paths = (first_frame_path, last_frame_path) if last_frame_path else (first_frame_path,)
    dispatch_request = ProviderDispatchRequest(
        prompt=provider_prompt,
        output_dir=output_dir,
        aspect_ratio=request.aspect_ratio,
        candidate_count=1,
        reference_image_paths=reference_paths,
        subject_reference_image_path=first_frame_path,
        duration_sec=request.duration_sec,
        resolution=request.resolution,
        motion=request.motion,
    )
    try:
        provider_task = registry.submit("video", request.provider_service_id, dispatch_request)
    except (ModelGatewayError, Exception) as exc:
        return _poll_failed_result(project_id, output_dir, context_bundle, model_call_context, artifacts, model_request_plan, gate, str(exc))
    increment_daily_submit_count(store, project_id)
    task_state = _task_state(request, provider_task, context_bundle, model_call_context)
    write_task_state(output_dir, task_state)
    if task_state["status"] == "already_complete":
        return complete_video_result(
            output_dir,
            project_id,
            provider_task.get("task", {}).get("raw") or {},
            task_state,
            gate,
            artifacts=artifacts,
            model_call_context=model_call_context,
            model_request_plan=model_request_plan,
        )
    manifest = safe_manifest(project_id, status="submitted", provider_calls_started=True, provider_gate=gate, context_bundle=context_bundle, model_call_context_id=model_call_context["context_id"])
    write_json_checked(output_dir / "video_generation_safe_manifest.json", manifest)
    return result_from_manifest(status="submitted", safe_manifest=manifest, task_state=task_state, context_bundle=context_bundle, artifacts=artifacts, model_call_context=model_call_context, model_request_plan=model_request_plan)


def poll_video_generation(store: RuntimeStore, project_id: str, output_dir: Path, *, load_registry: Callable[[], Any]) -> dict[str, Any]:
    state = load_task_state(output_dir)
    if state.get("status") in {"succeeded", "cancelled_local_only"}:
        return result_from_manifest(status=str(state["status"]), safe_manifest=read_json(output_dir / "video_generation_safe_manifest.json"), task_state=state)
    provider_service_id = str(state.get("provider_service_id") or "")
    poll_time = _utc_now()
    try:
        raw = load_registry().poll("video", provider_service_id, provider_task_for_poll(state.get("task"), output_dir))
    except (ModelGatewayError, Exception) as exc:
        manifest = safe_manifest(project_id, status="poll_failed", provider_calls_started=True, blocks=[provider_not_ready_block(str(exc))], context_bundle=_context_bundle(state))
        write_json_checked(output_dir / "video_generation_safe_manifest.json", manifest)
        state["status"] = "poll_failed"
        state["last_poll_at"] = poll_time
        state["completed_at"] = poll_time
        write_task_state(output_dir, state)
        return result_from_manifest(status="poll_failed", safe_manifest=manifest, task_state=state)
    if str(raw.get("status") or "").lower() == "running":
        manifest = safe_manifest(project_id, status="running", provider_calls_started=True, blocks=[], context_bundle=_context_bundle(state))
        write_json_checked(output_dir / "video_generation_safe_manifest.json", manifest)
        state["status"] = "running"
        state.setdefault("running_started_at", poll_time)
        state["last_poll_at"] = poll_time
        state["last_provider_poll"] = {"status": "running", "task": raw.get("task") or {}, "provider_raw_persisted": False}
        write_task_state(output_dir, state)
        return result_from_manifest(status="running", safe_manifest=manifest, task_state=state)
    return complete_video_result(output_dir, project_id, raw, state, video_gate(REMOTE_VIDEO_ENV))


def complete_video_result(
    output_dir: Path,
    project_id: str,
    raw: dict[str, Any],
    task_state: dict[str, Any],
    provider_gate: dict[str, str],
    *,
    artifacts: dict[str, Any] | None = None,
    model_call_context: dict[str, Any] | None = None,
    model_request_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    outputs = safe_outputs(output_dir, raw)
    context_bundle = _context_bundle(task_state)
    completed_at = _utc_now()
    task_state["status"] = "succeeded"
    task_state.setdefault("running_started_at", task_state.get("created_at") or completed_at)
    task_state["last_poll_at"] = completed_at
    task_state["completed_at"] = completed_at
    write_task_state(output_dir, task_state)
    manifest = safe_manifest(project_id, status="succeeded", provider_calls_started=True, provider_gate=provider_gate, outputs=outputs, context_bundle=context_bundle, model_call_context_id=str(task_state.get("model_call_context_id") or ""))
    write_json_checked(output_dir / "video_generation_safe_manifest.json", manifest)
    return result_from_manifest(status="succeeded", safe_manifest=manifest, task_state=task_state, outputs=outputs, context_bundle=context_bundle, artifacts=artifacts, model_call_context=model_call_context, model_request_plan=model_request_plan)


def _model_call_context(project_id: str, request: VideoGenerationRequest, context_bundle: dict[str, Any] | None) -> dict[str, Any]:
    return video_generation_model_call_context(
        project_id=project_id,
        request=request,
        context_bundle=context_bundle,
        provider_constraints={
            "capability": "video",
            "provider_service_id": request.provider_service_id,
            "required_gate": REMOTE_VIDEO_ENV,
            "duration_sec": request.duration_sec,
            "resolution": request.resolution,
            "aspect_ratio": request.aspect_ratio,
            "reference_image_slots": 1 + int(bool(request.last_frame_image_asset_id)),
        },
    )


def _blocked_result(project_id: str, output_dir: Path, context_bundle: dict[str, Any] | None, model_call_context: dict[str, Any], artifacts: dict[str, Any], model_request_plan: dict[str, Any], block: dict[str, str], provider_gate: dict[str, str] | None = None, *, blocks: list[dict[str, str]] | None = None) -> dict[str, Any]:
    manifest = safe_manifest(project_id, status="blocked", provider_calls_started=False, provider_gate=provider_gate, blocks=blocks or [block], context_bundle=context_bundle, model_call_context_id=model_call_context["context_id"])
    write_json_checked(output_dir / "video_generation_safe_manifest.json", manifest)
    return result_from_manifest(status="blocked", safe_manifest=manifest, context_bundle=context_bundle, artifacts=artifacts, model_call_context=model_call_context, model_request_plan=model_request_plan)


def _poll_failed_result(project_id: str, output_dir: Path, context_bundle: dict[str, Any] | None, model_call_context: dict[str, Any], artifacts: dict[str, Any], model_request_plan: dict[str, Any], gate: dict[str, str], reason: str) -> dict[str, Any]:
    manifest = safe_manifest(project_id, status="poll_failed", provider_calls_started=True, provider_gate=gate, blocks=[provider_not_ready_block(reason)], context_bundle=context_bundle, model_call_context_id=model_call_context["context_id"])
    write_json_checked(output_dir / "video_generation_safe_manifest.json", manifest)
    return result_from_manifest(status="poll_failed", safe_manifest=manifest, context_bundle=context_bundle, artifacts=artifacts, model_call_context=model_call_context, model_request_plan=model_request_plan)


def _task_state(request: VideoGenerationRequest, provider_task: dict[str, Any], context_bundle: dict[str, Any] | None, model_call_context: dict[str, Any]) -> dict[str, Any]:
    now = _utc_now()
    return {
        "schema_version": "afs_video_generation_task_state.v0.1",
        "status": str((provider_task.get("task") or {}).get("status") or "submitted"),
        "provider_service_id": request.provider_service_id,
        "capability": "video",
        "task": provider_task_for_state(provider_task),
        "first_frame_image_asset_id": request.first_frame_image_asset_id,
        "last_frame_image_asset_id": request.last_frame_image_asset_id,
        "created_at": now,
        "submitted_at": now,
        "provider_raw_persisted": False,
        "context_bundle": context_bundle,
        "model_call_context_id": model_call_context["context_id"],
        "model_request_plan_ref": "model_request_plan.json",
    }


def _context_bundle(state: dict[str, Any]) -> dict[str, Any] | None:
    return state.get("context_bundle") if isinstance(state.get("context_bundle"), dict) else None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
