from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apps.api.runtime_external_video_common import (
    EXTERNAL_VIDEO_ACTION,
    EXTERNAL_VIDEO_NON_CLAIMS,
    PUBLIC_PREVIEW_MIME,
    REMOTE_VIDEO_ENV,
    SAFE_OUTPUT_ID,
    external_download_gate,
    parse_time,
    safe_text,
    utc_now,
)
from apps.api.runtime_external_video_models import ExternalVideoJobRequest
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_store import RuntimeStore, read_json, safe_id
from apps.api.runtime_video_gate import video_gate
from apps.api.runtime_video_manifest import write_json_checked


def write_external_video_job(store: RuntimeStore, project_id: str, job_id: str, result: dict[str, Any]) -> dict[str, Any]:
    artifacts = dict(result.get("artifacts") or {})
    if not artifacts:
        try:
            artifacts = dict(store.load_job(job_id).get("artifacts") or {})
        except KeyError:
            artifacts = {}
    job = runtime_job(job_id, project_id, EXTERNAL_VIDEO_ACTION, str(result["status"]), artifacts=artifacts)
    job["progress"].update(external_video_progress(result.get("task_state")))
    job["ui_summary"] = {
        "external_video": {
            "status": result["status"],
            "engine": result.get("engine") or (result.get("safe_manifest") or {}).get("engine"),
            "preview_available": bool((result.get("safe_manifest") or {}).get("preview_available")),
            "download_available": bool((result.get("safe_manifest") or {}).get("download_available")),
            "provider_calls_started": bool((result.get("safe_manifest") or {}).get("provider_calls_started")),
        }
    }
    return store.write_job(job)


def external_video_response(store: RuntimeStore, project_id: str, job: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    job_id = str(job["job_id"])
    safe_manifest = result.get("safe_manifest") or {}
    return {
        "job": job,
        "engine": safe_manifest.get("engine") or result.get("engine"),
        "provider_gate": safe_manifest.get("provider_gate") or video_gate(REMOTE_VIDEO_ENV),
        "external_download_gate": safe_manifest.get("external_download_gate") or external_download_gate(),
        "provider_calls_started": bool(safe_manifest.get("provider_calls_started")),
        "external_download_started": bool(safe_manifest.get("external_download_started")),
        "safe_manifest": safe_manifest,
        "artifacts": job.get("artifacts") or result.get("artifacts") or {},
        "preview": public_preview(project_id, job_id, safe_manifest),
        "flow": {"project_id": project_id},
        "non_claims": EXTERNAL_VIDEO_NON_CLAIMS,
    }


def external_video_progress(task_state: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(task_state, dict):
        return {}
    status = str(task_state.get("status") or "")
    created_at = parse_time(task_state.get("created_at"))
    completed_at = parse_time(task_state.get("completed_at"))
    last_poll_at = parse_time(task_state.get("last_poll_at"))
    observed_at = completed_at or last_poll_at or datetime.now(timezone.utc)
    progress: dict[str, Any] = {"provider_phase": status}
    if created_at:
        progress["elapsed_sec"] = max(0, int(round((observed_at - created_at).total_seconds())))
    return progress


def write_result_artifacts(
    store: RuntimeStore,
    project_id: str,
    job_id: str,
    output_dir: Path,
    request: ExternalVideoJobRequest,
    artifacts: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    manifest = safe_manifest(project_id, job_id, request, state)
    write_json_checked(output_dir / "external_video_safe_manifest.json", manifest)
    artifacts["external_video_safe_manifest"] = store.register_artifact(
        output_dir / "external_video_safe_manifest.json",
        role="external_video_safe_manifest",
    )
    if state.get("status") == "succeeded":
        delivery = delivery_manifest(project_id, job_id, request, state, manifest)
        write_json_checked(output_dir / "external_video_delivery_manifest.json", delivery)
        artifacts["external_video_delivery_manifest"] = store.register_artifact(
            output_dir / "external_video_delivery_manifest.json",
            role="external_video_delivery_manifest",
        )
    return {
        "status": state["status"],
        "engine": request.engine,
        "safe_manifest": manifest,
        "artifacts": artifacts,
        "task_state": state,
    }


def result_from_state(store: RuntimeStore, project_id: str, job_id: str, output_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    request_plan = read_json(output_dir / "external_video_request_plan.json")
    request = ExternalVideoJobRequest(
        node_id=request_plan.get("node_id") or None,
        prompt_text=str(request_plan.get("prompt_text") or "External video job"),
        title=str(request_plan.get("title") or "External video job"),
        engine=str(request_plan.get("engine") or state.get("engine") or "replay"),  # type: ignore[arg-type]
        style=str(request_plan.get("style") or "animated_comic"),
        aspect_ratio=str(request_plan.get("aspect_ratio") or "9:16"),
        duration_sec=int(request_plan.get("duration_sec") or 6),
        scene_count=int(request_plan.get("scene_count") or 3),
        replay_profile="ai_comic_demo",
        generated_at=str(request_plan.get("generated_at") or state.get("created_at") or utc_now()),
    )
    artifacts = {
        "external_video_request_plan": store.register_artifact(
            output_dir / "external_video_request_plan.json",
            role="external_video_request_plan",
        )
    }
    return write_result_artifacts(store, project_id, job_id, output_dir, request, artifacts, state)


def request_plan(project_id: str, job_id: str, request: ExternalVideoJobRequest) -> dict[str, Any]:
    return {
        "artifact_type": "afs_external_video_request_plan",
        "schema_version": "afs_external_video_request_plan.v0.1",
        "project_id": project_id,
        "job_id": job_id,
        "node_id": safe_id(request.node_id or "") if request.node_id else "",
        "engine": request.engine,
        "title": safe_text(request.title, 120),
        "prompt_text": safe_text(request.prompt_text, 800),
        "prompt_sha256": hashlib.sha256(request.prompt_text.encode("utf-8")).hexdigest(),
        "style": safe_text(request.style, 120),
        "aspect_ratio": request.aspect_ratio,
        "duration_sec": request.duration_sec,
        "scene_count": request.scene_count,
        "generated_at": safe_text(request.generated_at, 80),
        "expected_outputs": ["safe_manifest", "preview_route", "download_route"],
        "provider_raw_response_stored": False,
        "provider_urls_persisted": False,
        "media_bytes_returned_by_api": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": EXTERNAL_VIDEO_NON_CLAIMS,
    }


def safe_manifest(project_id: str, job_id: str, request: ExternalVideoJobRequest, state: dict[str, Any]) -> dict[str, Any]:
    output = state.get("output") if isinstance(state.get("output"), dict) else {}
    preview_available = bool(output.get("byte_count"))
    return {
        "artifact_type": "afs_external_video_safe_manifest",
        "schema_version": "afs_external_video_safe_manifest.v0.1",
        "project_id": project_id,
        "job_id": job_id,
        "engine": request.engine,
        "capability": "external_video",
        "status": str(state.get("status") or "failed"),
        "title": safe_text(request.title, 120),
        "style": safe_text(request.style, 120),
        "aspect_ratio": request.aspect_ratio,
        "duration_sec": request.duration_sec,
        "scene_count": request.scene_count,
        "provider_gate": video_gate(REMOTE_VIDEO_ENV),
        "external_download_gate": external_download_gate(),
        "provider_calls_started": bool(state.get("provider_calls_started")),
        "external_download_started": bool(state.get("external_download_started")),
        "preview_available": preview_available,
        "download_available": preview_available,
        "outputs": [public_output(output)] if preview_available else [],
        "blocks": state.get("blocks") if isinstance(state.get("blocks"), list) else [],
        "media_bytes_returned_by_api": False,
        "provider_raw_response_stored": False,
        "provider_urls_persisted": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": EXTERNAL_VIDEO_NON_CLAIMS,
    }


def delivery_manifest(
    project_id: str,
    job_id: str,
    request: ExternalVideoJobRequest,
    state: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": "afs_external_video_delivery_manifest",
        "schema_version": "afs_external_video_delivery_manifest.v0.1",
        "project_id": project_id,
        "job_id": job_id,
        "engine": request.engine,
        "status": state["status"],
        "title": safe_text(request.title, 120),
        "output_id": SAFE_OUTPUT_ID,
        "preview_available": bool(manifest.get("preview_available")),
        "download_available": bool(manifest.get("download_available")),
        "rendered_by": "afs_runtime_replay_adapter" if request.engine == "replay" else "external_video_adapter",
        "scene_count": request.scene_count,
        "safe_manifest_ref": "external_video_safe_manifest",
        "non_claims": EXTERNAL_VIDEO_NON_CLAIMS,
    }


def public_preview(project_id: str, job_id: str, manifest: dict[str, Any]) -> dict[str, Any] | None:
    if not manifest.get("preview_available"):
        return None
    output = (manifest.get("outputs") or [{}])[0]
    base = f"/projects/{safe_id(project_id)}/external-video-jobs/{safe_id(job_id)}"
    return {
        "output_id": SAFE_OUTPUT_ID,
        "media_kind": "video",
        "preview_url": f"{base}/preview",
        "download_url": f"{base}/download",
        "mime_type": PUBLIC_PREVIEW_MIME,
        "byte_count": output.get("byte_count"),
        "sha256": output.get("sha256"),
    }


def public_output(output: dict[str, Any]) -> dict[str, Any]:
    return {
        "output_id": SAFE_OUTPUT_ID,
        "media_kind": "video",
        "byte_count": output.get("byte_count"),
        "sha256": output.get("sha256"),
        "provider_url_persisted": False,
    }


__all__ = (
    "external_video_response",
    "request_plan",
    "result_from_state",
    "write_external_video_job",
    "write_result_artifacts",
)
