from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import load_provider_registry
from apps.api.runtime_keyframe_payloads import keyframe_candidate_summary, keyframe_safe_manifest
from apps.api.runtime_keyframes import (
    KEYFRAME_NON_CLAIMS,
    REMOTE_IMAGE_ENV,
    _provider_outputs,
    _safe_error,
    image_provider_gate,
)
from apps.api.runtime_models import KeyframeGenerationRequest
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload


def poll_keyframe_generation(store: RuntimeStore, project_id: str, output_dir: Path) -> dict[str, Any]:
    state = _load_task_state(output_dir)
    request = KeyframeGenerationRequest.model_validate(state["request"])
    context_bundle = state.get("context_bundle") if isinstance(state.get("context_bundle"), dict) else None
    provider_gate = state.get("provider_gate") if isinstance(state.get("provider_gate"), dict) else image_provider_gate()
    if state.get("status") in {"succeeded", "failed", "blocked"}:
        recovered = _recovered_terminal_provider_result(
            output_dir,
            project_id,
            request,
            state,
            provider_gate,
            context_bundle,
        )
        if recovered:
            return recovered
        manifest = read_json(output_dir / "keyframe_generation_safe_manifest.json")
        outputs = manifest.get("outputs") if isinstance(manifest.get("outputs"), list) else []
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
        registry = load_provider_registry()
        raw = registry.poll("image", provider_service_id, _provider_task_for_poll(state.get("task"), output_dir))
    except ModelGatewayError as exc:
        return _keyframe_poll_failed_result(
            output_dir,
            project_id,
            request,
            state,
            provider_gate,
            context_bundle,
            _safe_error(str(exc)),
        )

    status = str(raw.get("status") or "").lower()
    if status in {"running", "submitted", "pending"}:
        progress = raw.get("progress") if isinstance(raw.get("progress"), dict) else None
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
        return _keyframe_poll_failed_result(
            output_dir,
            project_id,
            request,
            state,
            provider_gate,
            context_bundle,
            _safe_failed_blocks(raw, provider_gate),
        )
    return _keyframe_succeeded_result(output_dir, project_id, request, state, provider_gate, context_bundle, raw)


def _recovered_terminal_provider_result(
    output_dir: Path,
    project_id: str,
    request: KeyframeGenerationRequest,
    state: dict[str, Any],
    provider_gate: dict[str, str],
    context_bundle: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if state.get("status") == "succeeded" or not isinstance(state.get("task"), dict):
        return None
    provider_service_id = str(state.get("provider_service_id") or request.provider_service_id)
    try:
        registry = load_provider_registry()
        raw = registry.poll("image", provider_service_id, _provider_task_for_poll(state.get("task"), output_dir))
    except ModelGatewayError:
        return None
    if str(raw.get("status") or "").lower() != "succeeded":
        return None
    return _keyframe_succeeded_result(output_dir, project_id, request, state, provider_gate, context_bundle, raw)


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
    state["status"] = "succeeded"
    _write_task_state(output_dir, state)
    prompt = str(state.get("provider_prompt") or request.optimized_prompt or request.prompt_text)
    candidates = keyframe_candidate_summary(request, prompt, provider_outputs, KEYFRAME_NON_CLAIMS)
    manifest = keyframe_safe_manifest(
        project_id,
        request,
        status="succeeded",
        provider_gate=provider_gate,
        blocks=[],
        provider_calls_started=True,
        output_count=len(provider_outputs),
        reference_image_count=int(state.get("reference_image_count") or 0),
        retry_count=0,
        context_bundle=context_bundle,
        non_claims=KEYFRAME_NON_CLAIMS,
    )
    manifest["outputs"] = provider_outputs
    _write_json_checked(output_dir / "keyframe_candidates_summary.json", candidates)
    _write_json_checked(output_dir / "keyframe_generation_safe_manifest.json", manifest)
    progress = raw.get("progress") if isinstance(raw.get("progress"), dict) else None
    return _result(
        status="succeeded",
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
    reason_or_blocks: str | list[dict[str, str]],
) -> dict[str, Any]:
    state["status"] = "failed"
    _write_task_state(output_dir, state)
    blocks = (
        _safe_blocks(reason_or_blocks, provider_gate)
        if isinstance(reason_or_blocks, list)
        else _safe_blocks(
            [
                {
                    "block_id": "remote_image_provider_not_ready",
                    "reason": _safe_error(reason_or_blocks),
                    "required_gate": str(provider_gate.get("env") or REMOTE_IMAGE_ENV),
                }
            ],
            provider_gate,
        )
    )
    manifest = keyframe_safe_manifest(
        project_id,
        request,
        status="failed",
        provider_gate=provider_gate,
        blocks=blocks,
        provider_calls_started=True,
        output_count=0,
        reference_image_count=int(state.get("reference_image_count") or 0),
        retry_count=0,
        context_bundle=context_bundle,
        non_claims=KEYFRAME_NON_CLAIMS,
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


def _safe_failed_blocks(raw: dict[str, Any], provider_gate: dict[str, str]) -> list[dict[str, str]]:
    raw_blocks = raw.get("blocks")
    if isinstance(raw_blocks, list) and raw_blocks:
        return _safe_blocks(raw_blocks, provider_gate)
    return _safe_blocks(
        [
            {
                "block_id": "remote_image_provider_not_ready",
                "reason": _safe_error(_json_dumps_safe(raw)),
                "required_gate": str(provider_gate.get("env") or REMOTE_IMAGE_ENV),
            }
        ],
        provider_gate,
    )


def _safe_blocks(values: list[Any], provider_gate: dict[str, str]) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    required_gate = str(provider_gate.get("env") or REMOTE_IMAGE_ENV)
    for value in values:
        if not isinstance(value, dict):
            reason = _safe_error(str(value))
            block_id = "remote_image_provider_not_ready"
        else:
            block_id = str(value.get("block_id") or "remote_image_provider_not_ready")[:80]
            reason = _safe_error(str(value.get("reason") or value.get("error") or "image provider did not complete"))
        blocks.append({"block_id": block_id, "reason": reason, "required_gate": required_gate})
    return blocks or [{"block_id": "remote_image_provider_not_ready", "reason": "Image provider did not complete.", "required_gate": required_gate}]


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


__all__ = ("poll_keyframe_generation",)
