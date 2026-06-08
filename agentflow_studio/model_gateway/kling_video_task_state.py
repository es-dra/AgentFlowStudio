from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.errors import ModelProviderError


TASK_STATE_SCHEMA_VERSION = "kling_video_task_state.v1"
I2V_TASK_STATE_NAME = "kling_i2v_task_state.json"
T2V_TASK_STATE_NAME = "kling_t2v_task_state.json"
I2V_MANIFEST_NAME = "kling_i2v_smoke_manifest.json"
T2V_MANIFEST_NAME = "kling_t2v_smoke_manifest.json"


def task_state_name_for_api_family(api_family: str) -> str:
    if api_family == "i2v":
        return I2V_TASK_STATE_NAME
    if api_family == "t2v":
        return T2V_TASK_STATE_NAME
    raise ModelProviderError(f"Unsupported Kling video api_family for task state: {api_family}")


def manifest_name_for_api_family(api_family: str) -> str:
    if api_family == "i2v":
        return I2V_MANIFEST_NAME
    if api_family == "t2v":
        return T2V_MANIFEST_NAME
    raise ModelProviderError(f"Unsupported Kling video api_family for manifest: {api_family}")


def safe_input_image_state(source_image: Path) -> dict[str, Any]:
    image_bytes = source_image.read_bytes()
    return {
        "path_persisted": False,
        "byte_count": len(image_bytes),
        "sha256": hashlib.sha256(image_bytes).hexdigest(),
    }


def build_task_state(
    *,
    plan: dict[str, Any],
    task_id: str,
    task_data: dict[str, Any],
    input_image: dict[str, Any] | None = None,
    status: str = "submitted",
) -> dict[str, Any]:
    api_family = str(plan.get("api_family") or "")
    created_at = _utc_now()
    state: dict[str, Any] = {
        "schema_version": TASK_STATE_SCHEMA_VERSION,
        "status": status,
        "provider": "kling",
        "service_id": plan.get("service_id"),
        "api_family": api_family,
        "capability": plan.get("capability"),
        "model": (plan.get("create_request") or {}).get("json", {}).get("model_name"),
        "required_gate": plan.get("required_gate"),
        "gate_status": plan.get("gate_status"),
        "task": _safe_task(task_id, task_data),
        "artifact_policy": {
            "provider_urls_persisted": False,
            "authorization_header_persisted": False,
            "jwt_persisted": False,
            "source_image_path_persisted": False,
            "writes_long_term_memory": False,
        },
        "timestamps": {"created_at": created_at, "updated_at": created_at},
        "claim_boundary": "provider_task_recovery_state_only_not_creative_quality",
    }
    if input_image is not None:
        state["input_image"] = input_image
    return state


def write_task_state(output_dir: str | Path, state: dict[str, Any]) -> Path:
    api_family = _required_str(state, "api_family")
    return write_json(Path(output_dir) / task_state_name_for_api_family(api_family), state)


def load_task_state(path: str | Path) -> dict[str, Any]:
    state_path = Path(path)
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ModelProviderError(f"Kling task state JSON is invalid: {state_path}") from exc
    if not isinstance(payload, dict):
        raise ModelProviderError(f"Kling task state JSON must be an object: {state_path}")
    if payload.get("schema_version") != TASK_STATE_SCHEMA_VERSION:
        raise ModelProviderError("Kling task state schema_version is unsupported")
    if payload.get("provider") != "kling":
        raise ModelProviderError("Kling task state provider is unsupported")
    _required_str(payload, "service_id")
    _required_str(payload, "api_family")
    task = payload.get("task")
    if not isinstance(task, dict) or not isinstance(task.get("task_id"), str) or not task["task_id"].strip():
        raise ModelProviderError("Kling task state missing task.task_id")
    return payload


def updated_task_state(
    state: dict[str, Any],
    *,
    status: str,
    task_data: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    updated = dict(state)
    updated["status"] = status
    task = dict(updated.get("task") or {})
    task_id = str(task.get("task_id") or "")
    if task_data is not None:
        task = _safe_task(task_id, task_data)
    updated["task"] = task
    if error_message:
        updated["last_error"] = {"message": sanitize_runtime_error(error_message)}
    else:
        updated.pop("last_error", None)
    timestamps = dict(updated.get("timestamps") or {})
    timestamps["updated_at"] = _utc_now()
    updated["timestamps"] = timestamps
    return updated


def build_success_manifest(
    *,
    state: dict[str, Any],
    task_data: dict[str, Any],
    video_ref: str,
    video_bytes: bytes,
    content_type: str,
    latency_ms: int,
    resumed_from_task_state: bool = False,
) -> dict[str, Any]:
    api_family = _required_str(state, "api_family")
    manifest: dict[str, Any] = {
        "schema_version": f"kling_{api_family}_smoke_manifest.v1",
        "status": "succeeded",
        "service_id": state.get("service_id"),
        "provider": "kling",
        "api_family": api_family,
        "model": state.get("model"),
        "capability": state.get("capability"),
        "required_gate": state.get("required_gate"),
        "gate_status": state.get("gate_status"),
        "task": _safe_task(str((state.get("task") or {}).get("task_id") or ""), task_data),
        "outputs": [
            {
                "candidate_id": "candidate_001",
                "video_path": video_ref,
                "byte_count": len(video_bytes),
                "sha256": hashlib.sha256(video_bytes).hexdigest(),
                "content_type": content_type,
                "provider_url_persisted": False,
            }
        ],
        "timing": {"latency_ms": latency_ms},
        "artifact_policy": state.get("artifact_policy") or {},
        "claim_boundary": "provider_smoke_only_not_creative_quality",
    }
    if "input_image" in state:
        manifest["input_image"] = state["input_image"]
    if resumed_from_task_state:
        manifest["resumed_from_task_state"] = True
    return manifest


def sanitize_runtime_error(message: str) -> str:
    sanitized = re.sub(r"https?://\S+", "<redacted-url>", message)
    sanitized = re.sub(r"(?i)(bearer\s+)[^\s]+", r"\1<redacted>", sanitized)
    sanitized = re.sub(
        r"(?i)((?:authorization|access_key|secret_key|token|secret|key)[=:]\s*)[^\s]+",
        r"\1<redacted>",
        sanitized,
    )
    return sanitized[:300]


def _safe_task(task_id: str, task_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "task_status": task_data.get("task_status"),
        "task_status_msg_present": bool(task_data.get("task_status_msg")),
    }


def _required_str(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ModelProviderError(f"Kling task state missing {field}")
    return value.strip()


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
