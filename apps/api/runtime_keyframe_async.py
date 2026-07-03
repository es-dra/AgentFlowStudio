from __future__ import annotations

import json
import hashlib
import time
from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.image_utils import image_dimensions
from agentflow_studio.model_gateway.provider_adapter import load_provider_registry
from apps.api.runtime_file_logging import runtime_file_event
from apps.api.runtime_keyframe_payloads import (
    keyframe_candidate_summary,
    keyframe_review_preview_refs,
    keyframe_safe_manifest,
)
from apps.api.runtime_keyframes import (
    KEYFRAME_NON_CLAIMS,
    REMOTE_IMAGE_ENV,
    _provider_outputs,
    _safe_error,
    image_provider_gate,
)
from apps.api.runtime_models import KeyframeGenerationRequest
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload


def poll_keyframe_generation(
    store: RuntimeStore,
    project_id: str,
    output_dir: Path,
    *,
    request_id: str = "",
    client_request_id: str = "",
) -> dict[str, Any]:
    started = time.perf_counter()
    state = _load_task_state(output_dir)
    request = KeyframeGenerationRequest.model_validate(state["request"])
    request_id = request_id or str(state.get("request_id") or "")
    client_request_id = client_request_id or str(state.get("client_request_id") or "")
    job_id = output_dir.name
    context_bundle = state.get("context_bundle") if isinstance(state.get("context_bundle"), dict) else None
    provider_gate = state.get("provider_gate") if isinstance(state.get("provider_gate"), dict) else image_provider_gate()
    runtime_file_event(
        "keyframe",
        "poll_start",
        request_id=request_id,
        client_request_id=client_request_id,
        project_id=project_id,
        node_id=request.node_id,
        job_id=job_id,
        provider_service_id=str(state.get("provider_service_id") or request.provider_service_id),
        status=state.get("status"),
    )
    if state.get("status") in {"succeeded", "failed", "blocked"}:
        recovered = _recovered_terminal_provider_result(
            output_dir,
            project_id,
            request,
            state,
            provider_gate,
            context_bundle,
            request_id=request_id,
            client_request_id=client_request_id,
            started=started,
        )
        if recovered:
            return recovered
        manifest = read_json(output_dir / "keyframe_generation_safe_manifest.json")
        outputs = manifest.get("outputs") if isinstance(manifest.get("outputs"), list) else []
        if not outputs:
            outputs = _provider_outputs_from_candidate_files(output_dir)
        runtime_file_event(
            "keyframe",
            "poll_terminal_cached",
            request_id=request_id,
            client_request_id=client_request_id,
            project_id=project_id,
            node_id=request.node_id,
            job_id=job_id,
            provider_service_id=str(state.get("provider_service_id") or request.provider_service_id),
            status=state.get("status"),
            output_count=len(outputs),
            elapsed_ms=_elapsed_ms(started),
        )
        return _result(
            status=str(state["status"]),
            provider_gate=provider_gate,
            provider_calls_started=bool(manifest.get("provider_calls_started")),
            provider_outputs=outputs,
            safe_manifest=manifest,
            context_bundle=context_bundle,
        )

    provider_service_id = str(state.get("provider_service_id") or request.provider_service_id)
    try:
        runtime_file_event(
            "keyframe",
            "poll_provider_call",
            request_id=request_id,
            client_request_id=client_request_id,
            project_id=project_id,
            node_id=request.node_id,
            job_id=job_id,
            provider_service_id=provider_service_id,
        )
        provider_started = time.perf_counter()
        registry = load_provider_registry()
        raw = registry.poll("image", provider_service_id, _provider_task_for_poll(state.get("task"), output_dir))
        provider_elapsed_ms = _elapsed_ms(provider_started)
    except ModelGatewayError as exc:
        provider_elapsed_ms = _elapsed_ms(provider_started) if "provider_started" in locals() else ""
        runtime_file_event(
            "keyframe",
            "poll_failed",
            level="ERROR",
            request_id=request_id,
            client_request_id=client_request_id,
            project_id=project_id,
            node_id=request.node_id,
            job_id=job_id,
            provider_service_id=provider_service_id,
            error=type(exc).__name__,
            reason=_safe_error(str(exc)),
            provider_elapsed_ms=provider_elapsed_ms,
            elapsed_ms=_elapsed_ms(started),
        )
        return _keyframe_poll_failed_result(
            output_dir,
            project_id,
            request,
            state,
            provider_gate,
            context_bundle,
            _safe_error(str(exc)),
        )
    except Exception as exc:
        provider_elapsed_ms = _elapsed_ms(provider_started) if "provider_started" in locals() else ""
        runtime_file_event(
            "keyframe",
            "poll_exception",
            level="ERROR",
            request_id=request_id,
            client_request_id=client_request_id,
            project_id=project_id,
            node_id=request.node_id,
            job_id=job_id,
            provider_service_id=provider_service_id,
            error=type(exc).__name__,
            reason=_safe_error(str(exc)),
            provider_elapsed_ms=provider_elapsed_ms,
            elapsed_ms=_elapsed_ms(started),
        )
        raise

    status = str(raw.get("status") or "").lower()
    if status in {"running", "submitted", "pending"}:
        progress = raw.get("progress") if isinstance(raw.get("progress"), dict) else None
        runtime_file_event(
            "keyframe",
            "poll_running",
            request_id=request_id,
            client_request_id=client_request_id,
            project_id=project_id,
            node_id=request.node_id,
            job_id=job_id,
            provider_service_id=provider_service_id,
            status=status,
            provider_elapsed_ms=provider_elapsed_ms,
            elapsed_ms=_elapsed_ms(started),
        )
        return _keyframe_active_result(
            output_dir,
            project_id,
            request,
            state,
            provider_gate,
            context_bundle,
            status=status,
            progress=progress,
        )
    if status in {"failed", "blocked", "poll_failed"}:
        if _provider_outputs(raw):
            result = _keyframe_succeeded_result(output_dir, project_id, request, state, provider_gate, context_bundle, raw)
            runtime_file_event(
                "keyframe",
                "poll_partially_complete",
                request_id=request_id,
                client_request_id=client_request_id,
                project_id=project_id,
                node_id=request.node_id,
                job_id=job_id,
                provider_service_id=provider_service_id,
                status=result.get("status"),
                output_count=len(result.get("provider_outputs") or []),
                provider_elapsed_ms=provider_elapsed_ms,
                elapsed_ms=_elapsed_ms(started),
            )
            return result
        reason = _safe_error(_json_dumps_safe(raw.get("blocks") or raw))
        runtime_file_event(
            "keyframe",
            "poll_failed",
            level="ERROR",
            request_id=request_id,
            client_request_id=client_request_id,
            project_id=project_id,
            node_id=request.node_id,
            job_id=job_id,
            provider_service_id=provider_service_id,
            status=status,
            reason=reason,
            provider_elapsed_ms=provider_elapsed_ms,
            elapsed_ms=_elapsed_ms(started),
        )
        return _keyframe_poll_failed_result(output_dir, project_id, request, state, provider_gate, context_bundle, reason)
    result = _keyframe_succeeded_result(output_dir, project_id, request, state, provider_gate, context_bundle, raw)
    runtime_file_event(
        "keyframe",
        "poll_succeeded",
        request_id=request_id,
        client_request_id=client_request_id,
        project_id=project_id,
        node_id=request.node_id,
        job_id=job_id,
        provider_service_id=provider_service_id,
        output_count=len(result.get("provider_outputs") or []),
        provider_elapsed_ms=provider_elapsed_ms,
        elapsed_ms=_elapsed_ms(started),
    )
    return result


def _recovered_terminal_provider_result(
    output_dir: Path,
    project_id: str,
    request: KeyframeGenerationRequest,
    state: dict[str, Any],
    provider_gate: dict[str, str],
    context_bundle: dict[str, Any] | None,
    *,
    request_id: str = "",
    client_request_id: str = "",
    started: float | None = None,
) -> dict[str, Any] | None:
    if state.get("status") == "succeeded" or not isinstance(state.get("task"), dict):
        return None
    provider_service_id = str(state.get("provider_service_id") or request.provider_service_id)
    try:
        provider_started = time.perf_counter()
        registry = load_provider_registry()
        raw = registry.poll("image", provider_service_id, _provider_task_for_poll(state.get("task"), output_dir))
        provider_elapsed_ms = _elapsed_ms(provider_started)
    except ModelGatewayError:
        return None
    if str(raw.get("status") or "").lower().replace("-", "_") not in {"succeeded", "complete", "completed", "partial", "partially_complete"}:
        return None
    result = _keyframe_succeeded_result(output_dir, project_id, request, state, provider_gate, context_bundle, raw)
    runtime_file_event(
        "keyframe",
        "poll_recovered_succeeded",
        request_id=request_id,
        client_request_id=client_request_id,
        project_id=project_id,
        node_id=request.node_id,
        job_id=output_dir.name,
        provider_service_id=provider_service_id,
        output_count=len(result.get("provider_outputs") or []),
        provider_elapsed_ms=provider_elapsed_ms,
        elapsed_ms=_elapsed_ms(started) if started is not None else "",
    )
    return result


def _keyframe_active_result(
    output_dir: Path,
    project_id: str,
    request: KeyframeGenerationRequest,
    state: dict[str, Any],
    provider_gate: dict[str, str],
    context_bundle: dict[str, Any] | None,
    *,
    status: str,
    progress: dict[str, Any] | None,
) -> dict[str, Any]:
    state["status"] = status
    state["last_provider_poll"] = {"status": status, "provider_raw_persisted": False}
    _write_task_state(output_dir, state)
    manifest = keyframe_safe_manifest(
        project_id,
        request,
        status=status,
        provider_gate=provider_gate,
        blocks=[],
        provider_calls_started=True,
        output_count=0,
        reference_image_count=int(state.get("reference_image_count") or 0),
        retry_count=0,
        context_bundle=context_bundle,
        non_claims=KEYFRAME_NON_CLAIMS,
        job_id=output_dir.name,
    )
    _write_json_checked(output_dir / "keyframe_generation_safe_manifest.json", manifest)
    return _result(
        status=status,
        provider_gate=provider_gate,
        provider_calls_started=True,
        provider_outputs=[],
        safe_manifest=manifest,
        context_bundle=context_bundle,
        progress=progress,
    )


def _keyframe_succeeded_result(
    output_dir: Path,
    project_id: str,
    request: KeyframeGenerationRequest,
    state: dict[str, Any],
    provider_gate: dict[str, str],
    context_bundle: dict[str, Any] | None,
    raw: dict[str, Any],
) -> dict[str, Any]:
    provider_outputs = _provider_outputs(raw)
    blocks = _provider_manifest_blocks(
        raw,
        str(provider_gate.get("env") or REMOTE_IMAGE_ENV),
        request.candidate_count,
        len(provider_outputs),
    )
    status = _keyframe_result_status(str(raw.get("status") or "succeeded"), request.candidate_count, provider_outputs, blocks)
    state["status"] = status
    _write_task_state(output_dir, state)
    prompt = str(state.get("provider_prompt") or request.optimized_prompt or request.prompt_text)
    review_preview_refs = keyframe_review_preview_refs(project_id, output_dir.name, provider_outputs)
    candidates = keyframe_candidate_summary(
        request,
        prompt,
        provider_outputs,
        KEYFRAME_NON_CLAIMS,
        project_id=project_id,
        job_id=output_dir.name,
    )
    manifest = keyframe_safe_manifest(
        project_id,
        request,
        status=status,
        provider_gate=provider_gate,
        blocks=blocks,
        provider_calls_started=True,
        output_count=len(provider_outputs),
        reference_image_count=int(state.get("reference_image_count") or 0),
        retry_count=0,
        context_bundle=context_bundle,
        non_claims=KEYFRAME_NON_CLAIMS,
        job_id=output_dir.name,
        review_preview_refs=review_preview_refs,
    )
    _write_json_checked(output_dir / "keyframe_candidates_summary.json", candidates)
    _write_json_checked(output_dir / "keyframe_generation_safe_manifest.json", manifest)
    progress = raw.get("progress") if isinstance(raw.get("progress"), dict) else None
    return _result(
        status=status,
        provider_gate=provider_gate,
        provider_calls_started=True,
        provider_outputs=provider_outputs,
        safe_manifest=manifest,
        context_bundle=context_bundle,
        progress=progress,
    )


def _keyframe_poll_failed_result(
    output_dir: Path,
    project_id: str,
    request: KeyframeGenerationRequest,
    state: dict[str, Any],
    provider_gate: dict[str, str],
    context_bundle: dict[str, Any] | None,
    reason: str,
) -> dict[str, Any]:
    state["status"] = "failed"
    _write_task_state(output_dir, state)
    manifest = keyframe_safe_manifest(
        project_id,
        request,
        status="failed",
        provider_gate=provider_gate,
        blocks=[
            {
                "block_id": "remote_image_provider_not_ready",
                "reason": _safe_error(reason),
                "required_gate": str(provider_gate.get("env") or REMOTE_IMAGE_ENV),
            }
        ],
        provider_calls_started=True,
        output_count=0,
        reference_image_count=int(state.get("reference_image_count") or 0),
        retry_count=0,
        context_bundle=context_bundle,
        non_claims=KEYFRAME_NON_CLAIMS,
        job_id=output_dir.name,
    )
    _write_json_checked(output_dir / "keyframe_generation_safe_manifest.json", manifest)
    return _result(
        status="failed",
        provider_gate=provider_gate,
        provider_calls_started=True,
        provider_outputs=[],
        safe_manifest=manifest,
        context_bundle=context_bundle,
    )


def _provider_task_for_poll(task: Any, output_dir: Path) -> dict[str, Any]:
    payload = dict(task) if isinstance(task, dict) else {}
    inner = payload.get("task")
    if isinstance(inner, dict):
        poll_inner = dict(inner)
        poll_inner["output_dir"] = str(output_dir)
        payload["task"] = poll_inner
    else:
        payload["output_dir"] = str(output_dir)
    return payload


def _provider_outputs_from_candidate_files(output_dir: Path) -> list[dict[str, Any]]:
    image_dir = (output_dir / "image_candidates").resolve()
    root = output_dir.resolve()
    try:
        image_dir.relative_to(root)
    except ValueError:
        return []
    outputs: list[dict[str, Any]] = []
    for path in sorted(image_dir.glob("candidate_*.*")):
        try:
            resolved = path.resolve()
            resolved.relative_to(root)
        except ValueError:
            continue
        if resolved.suffix.lower() not in {".png", ".jpg", ".jpeg"} or not resolved.is_file():
            continue
        candidate_id = resolved.stem
        if not candidate_id.startswith("candidate_"):
            continue
        data = resolved.read_bytes()
        dimensions = image_dimensions(data) or {}
        outputs.append(
            {
                "candidate_id": candidate_id,
                "byte_count": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "width": dimensions.get("width"),
                "height": dimensions.get("height"),
                "aspect_ratio": dimensions.get("aspect_ratio"),
                "provider_url_persisted": False,
            }
        )
    return outputs


def _write_task_state(output_dir: Path, state: dict[str, Any]) -> None:
    _write_json_checked(output_dir / "keyframe_task_state.json", state)


def _load_task_state(output_dir: Path) -> dict[str, Any]:
    path = output_dir / "keyframe_task_state.json"
    if not path.is_file():
        raise ValueError("keyframe task state not found")
    return read_json(path)


def _write_json_checked(path: Path, payload: dict[str, Any]) -> None:
    reject_unsafe_payload(payload)
    write_json(path, payload)


def _result(
    *,
    status: str,
    provider_gate: dict[str, str],
    provider_calls_started: bool,
    provider_outputs: list[dict[str, Any]],
    safe_manifest: dict[str, Any],
    context_bundle: dict[str, Any] | None,
    progress: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "status": status,
        "provider_gate": provider_gate,
        "provider_calls_started": provider_calls_started,
        "provider_outputs": provider_outputs,
        "safe_manifest": safe_manifest,
        "context_bundle": context_bundle,
        "tool_gate_state": {
            "remote_llm": "not_requested",
            "remote_asr": "blocked_by_default",
            "remote_image": str(provider_gate.get("status") or "blocked"),
            "remote_video": "blocked_by_default",
        },
    }
    if progress:
        result["progress"] = progress
    return result


def _json_dumps_safe(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


def _provider_manifest_blocks(
    manifest: dict[str, Any],
    required_gate: str,
    requested_count: int,
    output_count: int,
) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    raw_blocks = manifest.get("blocks") if isinstance(manifest.get("blocks"), list) else []
    for item in raw_blocks:
        if not isinstance(item, dict):
            continue
        block = {
            "block_id": str(item.get("block_id") or item.get("code") or "remote_image_provider_not_ready")[:100],
            "reason": _safe_error(str(item.get("reason") or item.get("message") or item.get("error") or "Image provider did not complete this item.")),
            "required_gate": str(item.get("required_gate") or required_gate),
        }
        candidate_id = str(item.get("candidate_id") or "")
        if candidate_id.startswith("candidate_"):
            block["candidate_id"] = candidate_id[:32]
        blocks.append(block)
    if output_count < requested_count and _provider_status_allows_partial(str(manifest.get("status") or "")):
        blocks.append(
            {
                "block_id": "remote_image_candidate_missing",
                "reason": "Image provider returned fewer reviewable candidates than requested.",
                "required_gate": required_gate,
            }
        )
    return blocks


def _keyframe_result_status(
    provider_status: str,
    requested_count: int,
    provider_outputs: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
) -> str:
    normalized = str(provider_status or "").strip().lower().replace("-", "_")
    output_count = len(provider_outputs)
    if output_count > 0 and (normalized in {"partial", "partially_complete"} or output_count < requested_count or blocks):
        return "partially_complete"
    if normalized in {"failed", "blocked", "timed_out", "timeout", "skipped"}:
        return "partially_complete" if output_count else "failed"
    return "succeeded"


def _provider_status_allows_partial(status: str) -> bool:
    normalized = str(status or "").strip().lower().replace("-", "_")
    return normalized in {"", "succeeded", "success", "complete", "completed", "partial", "partially_complete"}


__all__ = ("poll_keyframe_generation",)
