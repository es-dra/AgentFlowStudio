from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import httpx

from apps.api.runtime_external_video_common import (
    DEFAULT_LIBTV_BASE_URL,
    EXTERNAL_DOWNLOAD_ENV,
    LIBTV_ACCESS_KEY_ENV,
    LIBTV_BASE_URL_ENVS,
    REMOTE_VIDEO_ENV,
    block,
    external_download_gate,
    safe_provider_error,
    safe_provider_id,
    safe_text,
    utc_now,
    write_task_state,
)
from apps.api.runtime_external_video_manifest import result_from_state, write_result_artifacts
from apps.api.runtime_external_video_media import download_external_video, output_summary
from apps.api.runtime_external_video_models import ExternalVideoJobRequest
from apps.api.runtime_store import RuntimeStore, safe_id
from apps.api.runtime_video_gate import gate_closed_block, video_gate


URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
VIDEO_URL_HINT_RE = re.compile(r"\.(?:mp4|mov|webm)(?:[?#]|$)", re.IGNORECASE)


def submit_libtv(
    store: RuntimeStore,
    project_id: str,
    job_id: str,
    request: ExternalVideoJobRequest,
    output_dir: Path,
    artifacts: dict[str, Any],
    *,
    request_id: str,
    client_request_id: str,
) -> dict[str, Any]:
    now = utc_now()
    if video_gate(REMOTE_VIDEO_ENV)["status"] == "blocked":
        state = _terminal_state(
            "blocked",
            now,
            provider_calls_started=False,
            blocks=[gate_closed_block(REMOTE_VIDEO_ENV)],
        )
        write_task_state(output_dir, state)
        return write_result_artifacts(store, project_id, job_id, output_dir, request, artifacts, state)
    access_key = os.environ.get(LIBTV_ACCESS_KEY_ENV, "").strip()
    if not access_key:
        state = _terminal_state(
            "blocked",
            now,
            provider_calls_started=False,
            blocks=[block("libtv_credentials_missing", "LibTV credentials are not configured.", required_gate=REMOTE_VIDEO_ENV)],
        )
        write_task_state(output_dir, state)
        return write_result_artifacts(store, project_id, job_id, output_dir, request, artifacts, state)
    try:
        response = httpx.post(
            libtv_url("/session"),
            headers={"Authorization": f"Bearer {access_key}", "Content-Type": "application/json"},
            json=libtv_create_session_payload(project_id, job_id, request),
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        provider_data = libtv_response_data(data)
    except Exception as exc:
        state = _terminal_state(
            "failed",
            now,
            provider_calls_started=True,
            submitted_at=now,
            blocks=[block("libtv_submit_failed", safe_provider_error(exc), required_gate=REMOTE_VIDEO_ENV)],
        )
        write_task_state(output_dir, state)
        return write_result_artifacts(store, project_id, job_id, output_dir, request, artifacts, state)
    state = {
        "schema_version": "afs_external_video_task_state.v0.1",
        "status": "submitted",
        "engine": "libtv",
        "created_at": now,
        "submitted_at": now,
        "provider_calls_started": True,
        "external_download_started": False,
        "provider_task": {
            "session_id": libtv_session_id(data),
            "project_uuid": safe_provider_id(provider_data.get("projectUuid") or provider_data.get("project_uuid")),
        },
        "request_id": request_id,
        "client_request_id": client_request_id,
    }
    write_task_state(output_dir, state)
    return write_result_artifacts(store, project_id, job_id, output_dir, request, artifacts, state)


def poll_libtv(
    store: RuntimeStore,
    project_id: str,
    job_id: str,
    output_dir: Path,
    state: dict[str, Any],
) -> dict[str, Any]:
    session_id = str((state.get("provider_task") or {}).get("session_id") or "")
    state["last_poll_at"] = utc_now()
    if not session_id:
        state.update({"status": "failed", "completed_at": state["last_poll_at"]})
        state["blocks"] = [block("libtv_session_missing", "LibTV session id is unavailable.", required_gate=REMOTE_VIDEO_ENV)]
        write_task_state(output_dir, state)
        return result_from_state(store, project_id, job_id, output_dir, state)
    access_key = os.environ.get(LIBTV_ACCESS_KEY_ENV, "").strip()
    if not access_key:
        state.update({"status": "blocked", "completed_at": state["last_poll_at"], "provider_calls_started": False})
        state["blocks"] = [block("libtv_credentials_missing", "LibTV credentials are not configured.", required_gate=REMOTE_VIDEO_ENV)]
        write_task_state(output_dir, state)
        return result_from_state(store, project_id, job_id, output_dir, state)
    try:
        response = httpx.get(libtv_url(f"/session/{session_id}"), headers={"Authorization": f"Bearer {access_key}"}, timeout=30.0)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        state.update({"status": "failed", "completed_at": state["last_poll_at"]})
        state["blocks"] = [block("libtv_poll_failed", safe_provider_error(exc), required_gate=REMOTE_VIDEO_ENV)]
        write_task_state(output_dir, state)
        return result_from_state(store, project_id, job_id, output_dir, state)
    video_urls = extract_video_urls(data)
    if not video_urls:
        state["status"] = "running"
        state["last_provider_status"] = libtv_provider_status(data)
        write_task_state(output_dir, state)
        return result_from_state(store, project_id, job_id, output_dir, state)
    if external_download_gate()["status"] == "blocked":
        state.update({"status": "needs_attention", "completed_at": state["last_poll_at"]})
        state["blocks"] = [
            block(
                "external_video_download_gate_closed",
                f"Set {EXTERNAL_DOWNLOAD_ENV}=true only after the source, purpose, storage, and cleanup policy are approved.",
                required_gate=EXTERNAL_DOWNLOAD_ENV,
            )
        ]
        write_task_state(output_dir, state)
        return result_from_state(store, project_id, job_id, output_dir, state)
    try:
        media_path = download_external_video(video_urls[0], output_dir)
    except Exception as exc:
        state.update({"status": "failed", "completed_at": state["last_poll_at"], "external_download_started": True})
        state["blocks"] = [block("external_video_download_failed", safe_provider_error(exc), required_gate=EXTERNAL_DOWNLOAD_ENV)]
        write_task_state(output_dir, state)
        return result_from_state(store, project_id, job_id, output_dir, state)
    state.update(
        {
            "status": "succeeded",
            "completed_at": utc_now(),
            "external_download_started": True,
            "output": output_summary(media_path),
        }
    )
    write_task_state(output_dir, state)
    return result_from_state(store, project_id, job_id, output_dir, state)


def libtv_create_session_payload(project_id: str, job_id: str, request: ExternalVideoJobRequest) -> dict[str, Any]:
    return {
        "message": safe_text(
            f"{request.title}\nStyle: {request.style}\nAspect: {request.aspect_ratio}\nDuration: {request.duration_sec}s\n{request.prompt_text}",
            2400,
        ),
        "metadata": {
            "source": "agentflow_studio_runtime",
            "project_id": safe_id(project_id),
            "job_id": safe_id(job_id),
            "scene_count": request.scene_count,
        },
    }


def libtv_url(path: str) -> str:
    base = libtv_openapi_base_url()
    return f"{base}{path}"


def libtv_openapi_base_url() -> str:
    base = ""
    for env_name in LIBTV_BASE_URL_ENVS:
        base = os.environ.get(env_name, "").strip()
        if base:
            break
    if not base:
        base = DEFAULT_LIBTV_BASE_URL
    base = base.rstrip("/")
    if not base.startswith(("http://", "https://")):
        base = DEFAULT_LIBTV_BASE_URL
    return base if base.endswith("/openapi") else f"{base}/openapi"


def libtv_response_data(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload if isinstance(payload, dict) else {}


def libtv_session_id(payload: Any) -> str:
    data = libtv_response_data(payload)
    return safe_provider_id(
        data.get("session_id")
        or data.get("sessionId")
        or data.get("id")
        or (payload.get("session_id") if isinstance(payload, dict) else "")
        or (payload.get("sessionId") if isinstance(payload, dict) else "")
        or (payload.get("id") if isinstance(payload, dict) else "")
    )


def libtv_provider_status(payload: Any) -> str:
    data = libtv_response_data(payload)
    return safe_provider_id(
        data.get("status")
        or data.get("state")
        or (payload.get("status") if isinstance(payload, dict) else "")
        or (payload.get("state") if isinstance(payload, dict) else "")
    )


def extract_video_urls(payload: Any) -> list[str]:
    urls: list[str] = []
    for match in URL_RE.finditer(flatten_json_text(payload)):
        url = match.group(0).rstrip(".,;)")
        if VIDEO_URL_HINT_RE.search(url) and url not in urls:
            urls.append(url)
    return urls[:3]


def flatten_json_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(flatten_json_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(flatten_json_text(item) for item in value)
    return str(value)


def _terminal_state(
    status: str,
    now: str,
    *,
    provider_calls_started: bool,
    blocks: list[dict[str, Any]],
    submitted_at: str | None = None,
) -> dict[str, Any]:
    state = {
        "schema_version": "afs_external_video_task_state.v0.1",
        "status": status,
        "engine": "libtv",
        "created_at": now,
        "completed_at": utc_now(),
        "provider_calls_started": provider_calls_started,
        "external_download_started": False,
        "blocks": blocks,
    }
    if submitted_at:
        state["submitted_at"] = submitted_at
    return state


__all__ = ("poll_libtv", "submit_libtv")
