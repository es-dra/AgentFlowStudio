from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json

from apps.api.runtime_file_logging import runtime_file_event
from apps.api.runtime_keyframe_payloads import keyframe_candidate_summary, keyframe_safe_manifest
from apps.api.runtime_keyframes import (
    KEYFRAME_NON_CLAIMS,
    REMOTE_IMAGE_ENV,
    _safe_error,
    build_keyframe_generation,
    image_provider_gate,
)
from apps.api.runtime_models import KeyframeGenerationRequest
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload, safe_id


BACKGROUND_WORKER_MODE = "sync_provider_thread"
BACKGROUND_WORKERS_ENV = "AFS_KEYFRAME_BACKGROUND_SYNC_WORKERS"
TERMINAL_STATUSES = {"succeeded", "partially_complete", "failed", "blocked"}

_EXECUTOR: ThreadPoolExecutor | None = None
_EXECUTOR_LOCK = threading.Lock()


def submit_background_sync_keyframe_generation(
    store: RuntimeStore,
    project_id: str,
    request: KeyframeGenerationRequest,
    output_dir: Path,
    *,
    provider_gate: dict[str, str] | None = None,
    request_id: str = "",
    client_request_id: str = "",
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    gate = provider_gate or image_provider_gate()
    initial = _initial_payloads(
        project_id,
        request,
        output_dir,
        provider_gate=gate,
    )
    _write_initial_artifacts(output_dir, initial)
    _write_task_state(
        output_dir,
        _background_task_state(
            request=request,
            status="running",
            provider_gate=gate,
            request_id=request_id,
            client_request_id=client_request_id,
            reference_image_count=0,
            context_bundle=None,
        ),
    )
    runtime_file_event(
        "keyframe",
        "background_submitted",
        request_id=request_id,
        client_request_id=client_request_id,
        project_id=project_id,
        node_id=request.node_id,
        provider_service_id=request.provider_service_id,
        job_id=output_dir.name,
    )
    _executor().submit(
        _run_background_generation,
        store,
        project_id,
        request,
        output_dir,
        request_id,
        client_request_id,
        gate,
    )
    return {
        "status": "running",
        "provider_gate": gate,
        "provider_calls_started": True,
        "provider_outputs": [],
        "safe_manifest": initial["safe_manifest"],
        "context_bundle": None,
        "model_call_context": initial["model_call_context"],
        "model_request_plan": initial["model_request_plan"],
        "generation_bridge": None,
        "progress": {"mode": "indeterminate", "stage": "keyframe_generation", "terminal": False},
        "tool_gate_state": {
            "remote_llm": "not_requested",
            "remote_asr": "blocked_by_default",
            "remote_image": str(gate.get("status") or "blocked"),
            "remote_video": "blocked_by_default",
        },
    }


def _run_background_generation(
    store: RuntimeStore,
    project_id: str,
    request: KeyframeGenerationRequest,
    output_dir: Path,
    request_id: str,
    client_request_id: str,
    provider_gate: dict[str, str],
) -> None:
    started = time.perf_counter()
    try:
        result = build_keyframe_generation(
            store,
            project_id,
            request,
            output_dir,
            request_id=request_id,
            client_request_id=client_request_id,
        )
        manifest = result.get("safe_manifest") if isinstance(result.get("safe_manifest"), dict) else {}
        status = str(result.get("status") or manifest.get("status") or "failed")
        _write_task_state(
            output_dir,
            _background_task_state(
                request=request,
                status=status,
                provider_gate=dict(result.get("provider_gate") or provider_gate),
                request_id=request_id,
                client_request_id=client_request_id,
                reference_image_count=int(manifest.get("reference_image_count") or 0),
                context_bundle=result.get("context_bundle") if isinstance(result.get("context_bundle"), dict) else None,
                completed=True,
            ),
        )
        runtime_file_event(
            "keyframe",
            "background_completed",
            request_id=request_id,
            client_request_id=client_request_id,
            project_id=project_id,
            node_id=request.node_id,
            provider_service_id=request.provider_service_id,
            job_id=output_dir.name,
            status=status,
            output_count=len(result.get("provider_outputs") or []),
            elapsed_ms=_elapsed_ms(started),
        )
    except Exception as exc:
        safe_reason = _safe_error(str(exc))
        manifest = keyframe_safe_manifest(
            project_id,
            request,
            status="failed",
            provider_gate=provider_gate,
            blocks=[
                {
                    "block_id": "remote_image_provider_not_ready",
                    "reason": safe_reason or type(exc).__name__,
                    "required_gate": str(provider_gate.get("env") or REMOTE_IMAGE_ENV),
                }
            ],
            provider_calls_started=True,
            output_count=0,
            reference_image_count=0,
            retry_count=0,
            context_bundle=None,
            non_claims=KEYFRAME_NON_CLAIMS,
            job_id=output_dir.name,
        )
        candidates = keyframe_candidate_summary(
            request,
            "",
            [],
            KEYFRAME_NON_CLAIMS,
            project_id=project_id,
            job_id=output_dir.name,
        )
        for payload in (manifest, candidates):
            reject_unsafe_payload(payload)
        write_json(output_dir / "keyframe_candidates_summary.json", candidates)
        write_json(output_dir / "keyframe_generation_safe_manifest.json", manifest)
        _write_task_state(
            output_dir,
            _background_task_state(
                request=request,
                status="failed",
                provider_gate=provider_gate,
                request_id=request_id,
                client_request_id=client_request_id,
                reference_image_count=0,
                context_bundle=None,
                completed=True,
                error=safe_reason or type(exc).__name__,
            ),
        )
        runtime_file_event(
            "keyframe",
            "background_failed",
            level="ERROR",
            request_id=request_id,
            client_request_id=client_request_id,
            project_id=project_id,
            node_id=request.node_id,
            provider_service_id=request.provider_service_id,
            job_id=output_dir.name,
            error=type(exc).__name__,
            reason=safe_reason,
            elapsed_ms=_elapsed_ms(started),
        )


def _initial_payloads(
    project_id: str,
    request: KeyframeGenerationRequest,
    output_dir: Path,
    *,
    provider_gate: dict[str, str],
) -> dict[str, dict[str, Any]]:
    context_id = f"keyframe_background_{safe_id(output_dir.name)}"
    model_call_context = {
        "artifact_type": "agentflow_model_call_context",
        "schema_version": "0.1.0",
        "context_id": context_id,
        "project_id": project_id,
        "node_id": request.node_id,
        "operation_intent": "image_keyframe_generation",
        "background_execution": {
            "mode": BACKGROUND_WORKER_MODE,
            "provider_execution_mode": "sync",
            "status": "running",
        },
        "safety_boundary": {
            "no_provider_raw": True,
            "no_provider_secret": True,
            "media_bytes_returned": False,
        },
    }
    model_request_plan = {
        "artifact_type": "agentflow_model_request_plan",
        "schema_version": "0.1.0",
        "context_id": context_id,
        "provider_service_id": request.provider_service_id,
        "capability": "image",
        "execution": "background_sync_provider",
        "status": "running",
        "provider_gate": provider_gate,
        "raw_provider_response_persisted": False,
        "media_bytes_returned_by_api": False,
    }
    request_plan = {
        "artifact_type": "agentflow_keyframe_request_plan",
        "schema_version": "0.1.0",
        "node_id": request.node_id,
        "requested_capability": "image_keyframe",
        "provider": request.provider_service_id,
        "provider_gate": provider_gate,
        "live_call_authorized": provider_gate["status"] != "blocked",
        "status": "running",
        "target_platform": request.target_platform,
        "aspect_ratio": request.aspect_ratio,
        "candidate_count": request.candidate_count,
        "seed": request.seed,
        "prompt_source": "request.optimized_prompt" if request.optimized_prompt else "request.prompt_text",
        "context_path": "background_sync_submit_pending",
        "reference_image_count": 0,
        "reference_images": [],
        "provider_prompt": "pending_background_generation",
        "model_call_context_id": context_id,
        "model_request_plan_ref": "model_request_plan.json",
        "claim_boundary": "provider_background_submit_pending",
        "artifact_policy": {
            "provider_config_path_persisted": False,
            "authorization_header_persisted": False,
            "secret_material_persisted": False,
            "raw_provider_response_persisted": False,
            "media_bytes_returned_by_api": False,
        },
        "non_claims": KEYFRAME_NON_CLAIMS,
    }
    candidates = keyframe_candidate_summary(
        request,
        "",
        [],
        KEYFRAME_NON_CLAIMS,
        project_id=project_id,
        job_id=output_dir.name,
    )
    safe_manifest = keyframe_safe_manifest(
        project_id,
        request,
        status="running",
        provider_gate=provider_gate,
        blocks=[],
        provider_calls_started=True,
        output_count=0,
        reference_image_count=0,
        retry_count=0,
        context_bundle=None,
        non_claims=KEYFRAME_NON_CLAIMS,
        job_id=output_dir.name,
    )
    return {
        "model_call_context": model_call_context,
        "model_request_plan": model_request_plan,
        "keyframe_request_plan": request_plan,
        "keyframe_candidates_summary": candidates,
        "safe_manifest": safe_manifest,
    }


def _write_initial_artifacts(output_dir: Path, payloads: dict[str, dict[str, Any]]) -> None:
    files = {
        "model_call_context.json": payloads["model_call_context"],
        "model_request_plan.json": payloads["model_request_plan"],
        "keyframe_request_plan.json": payloads["keyframe_request_plan"],
        "keyframe_candidates_summary.json": payloads["keyframe_candidates_summary"],
        "keyframe_generation_safe_manifest.json": payloads["safe_manifest"],
    }
    for payload in files.values():
        reject_unsafe_payload(payload)
    for filename, payload in files.items():
        write_json(output_dir / filename, payload)


def _background_task_state(
    *,
    request: KeyframeGenerationRequest,
    status: str,
    provider_gate: dict[str, str],
    request_id: str,
    client_request_id: str,
    reference_image_count: int,
    context_bundle: dict[str, Any] | None,
    completed: bool = False,
    error: str = "",
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "schema_version": "afs_keyframe_generation_task_state.v0.1",
        "status": status,
        "provider_service_id": request.provider_service_id,
        "capability": "image",
        "request": request.model_dump(mode="json"),
        "provider_prompt": "",
        "provider_gate": provider_gate,
        "reference_image_count": reference_image_count,
        "image_operation": "",
        "context_bundle": context_bundle,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provider_raw_persisted": False,
        "request_id": request_id,
        "client_request_id": client_request_id,
        "background_execution": {
            "mode": BACKGROUND_WORKER_MODE,
            "provider_execution_mode": "sync",
            "status": "completed" if completed or status in TERMINAL_STATUSES else status,
        },
    }
    if completed:
        state["completed_at"] = datetime.now(timezone.utc).isoformat()
    if error:
        state["error"] = error
    reject_unsafe_payload(state)
    return state


def _write_task_state(output_dir: Path, state: dict[str, Any]) -> None:
    write_json(output_dir / "keyframe_task_state.json", state)


def _executor() -> ThreadPoolExecutor:
    global _EXECUTOR
    with _EXECUTOR_LOCK:
        if _EXECUTOR is None:
            _EXECUTOR = ThreadPoolExecutor(max_workers=_worker_count(), thread_name_prefix="afs-keyframe-bg")
        return _EXECUTOR


def _worker_count() -> int:
    try:
        return max(1, min(int(os.environ.get(BACKGROUND_WORKERS_ENV, "3")), 8))
    except ValueError:
        return 3


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


__all__ = (
    "BACKGROUND_WORKER_MODE",
    "submit_background_sync_keyframe_generation",
)
