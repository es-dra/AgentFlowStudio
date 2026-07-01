from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload
from apps.api.runtime_video_candidates import candidate_previews
from apps.api.runtime_video_constants import REMOTE_VIDEO_ENV, VIDEO_NON_CLAIMS
from apps.api.runtime_video_gate import video_gate


def video_response(store: RuntimeStore, project_id: str, job: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    job_id = str(job["job_id"])
    outputs = result.get("outputs") or []
    model_call_context = result.get("model_call_context") if isinstance(result.get("model_call_context"), dict) else {}
    model_call_context_id = str(model_call_context.get("context_id") or (result.get("safe_manifest") or {}).get("model_call_context_id") or "")
    safe = result.get("safe_manifest") or {}
    return {
        "job": job,
        "provider_gate": safe.get("provider_gate") or video_gate(REMOTE_VIDEO_ENV),
        "provider_calls_started": bool(safe.get("provider_calls_started")),
        "safe_manifest": result.get("safe_manifest"),
        "context_bundle": result.get("context_bundle"),
        "model_call_context_id": model_call_context_id or None,
        "video_generation_plan": result.get("video_generation_plan") or safe.get("video_generation_plan"),
        "artifacts": job.get("artifacts") or result.get("artifacts") or {},
        "candidate_previews": candidate_previews(project_id, job_id, outputs),
        "flow": {"project_id": project_id},
        "non_claims": VIDEO_NON_CLAIMS,
    }


def write_video_job(store: RuntimeStore, project_id: str, job_id: str, result: dict[str, Any]) -> dict[str, Any]:
    artifacts = dict(result.get("artifacts") or {})
    if not artifacts:
        try:
            artifacts = dict((store.load_job(job_id).get("artifacts") or {}))
        except KeyError:
            artifacts = {}
    job = runtime_job(job_id, project_id, "video_generation", str(result["status"]), artifacts=artifacts)
    job["progress"].update(video_progress(result.get("task_state")))
    job["ui_summary"] = {
        "video_generation": {
            "status": result["status"],
            "provider_calls_started": bool((result.get("safe_manifest") or {}).get("provider_calls_started")),
        }
    }
    return store.write_job(job)


def video_progress(task_state: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(task_state, dict):
        return {}
    status = str(task_state.get("status") or "")
    created_at = _parse_time(task_state.get("created_at"))
    submitted_at = _parse_time(task_state.get("submitted_at")) or created_at
    running_started_at = _parse_time(task_state.get("running_started_at"))
    completed_at = _parse_time(task_state.get("completed_at"))
    last_poll_at = _parse_time(task_state.get("last_poll_at"))
    observed_at = completed_at or last_poll_at or datetime.now(timezone.utc)
    progress: dict[str, Any] = {"provider_phase": status}
    if created_at:
        progress["elapsed_sec"] = _seconds(observed_at, created_at)
    if submitted_at and running_started_at:
        progress["queued_sec"] = _seconds(running_started_at, submitted_at)
    elif submitted_at and status in {"submitted", "pending"}:
        progress["queued_sec"] = _seconds(observed_at, submitted_at)
    if running_started_at:
        progress["running_sec"] = _seconds(observed_at, running_started_at)
    return progress


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _seconds(later: datetime, earlier: datetime) -> int:
    return max(0, int(round((later - earlier).total_seconds())))


def result_from_manifest(
    *,
    status: str,
    safe_manifest: dict[str, Any],
    task_state: dict[str, Any] | None = None,
    outputs: list[dict[str, Any]] | None = None,
    context_bundle: dict[str, Any] | None = None,
    artifacts: dict[str, Any] | None = None,
    model_call_context: dict[str, Any] | None = None,
    model_request_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bundle = context_bundle
    if bundle is None and isinstance(task_state, dict) and isinstance(task_state.get("context_bundle"), dict):
        bundle = task_state.get("context_bundle")
    generation_plan = None
    if isinstance(model_request_plan, dict):
        generation_plan = model_request_plan.get("generation_plan")
    if generation_plan is None and isinstance(task_state, dict):
        generation_plan = task_state.get("video_generation_plan")
    if generation_plan is None:
        generation_plan = safe_manifest.get("video_generation_plan")
    return {
        "status": status,
        "safe_manifest": safe_manifest,
        "task_state": task_state,
        "outputs": outputs or safe_manifest.get("outputs") or [],
        "context_bundle": bundle,
        "video_generation_plan": generation_plan,
        "artifacts": artifacts or {},
        "model_call_context": model_call_context,
        "model_request_plan": model_request_plan,
    }


def safe_manifest(
    project_id: str,
    *,
    status: str,
    provider_calls_started: bool,
    provider_gate: dict[str, str] | None = None,
    blocks: list[dict[str, Any]] | None = None,
    outputs: list[dict[str, Any]] | None = None,
    context_bundle: dict[str, Any] | None = None,
    model_call_context_id: str | None = None,
    input_source: dict[str, Any] | None = None,
    input_mode: str | None = None,
    duration_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = {
        "schema_version": "afs_video_generation_safe_manifest.v0.1",
        "status": status,
        "project_id": project_id,
        "provider": "registry",
        "capability": "video",
        "provider_gate": provider_gate or video_gate(REMOTE_VIDEO_ENV),
        "provider_calls_started": provider_calls_started,
        "blocks": blocks or [],
        "outputs": outputs or [],
        "media_bytes_returned_by_api": False,
        "provider_raw_response_stored": False,
        "provider_urls_persisted": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": VIDEO_NON_CLAIMS,
    }
    if model_call_context_id:
        manifest["model_call_context_id"] = model_call_context_id
        manifest["model_request_plan_ref"] = "model_request_plan.json"
    if input_source:
        manifest["input_source"] = input_source
    if input_mode:
        manifest["input_mode"] = input_mode
    if duration_contract:
        manifest["duration_contract"] = duration_contract
    if context_bundle:
        manifest["context_bundle_mode"] = context_bundle.get("mode")
        manifest["context_included_asset_count"] = len(context_bundle.get("included_assets") or [])
        manifest["context_excluded_asset_count"] = len(context_bundle.get("excluded_assets") or [])
        manifest["context_asset_conflict_count"] = len(context_bundle.get("asset_conflicts") or [])
    return manifest


def write_json_checked(path: Path, payload: dict[str, Any]) -> None:
    reject_unsafe_payload(payload)
    write_json(path, payload)


def write_model_call_artifacts(
    store: RuntimeStore,
    output_dir: Path,
    model_call_context: dict[str, Any],
    model_request_plan: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    write_json_checked(output_dir / "model_call_context.json", model_call_context)
    write_json_checked(output_dir / "model_request_plan.json", model_request_plan)
    return {
        "model_call_context": store.register_artifact(output_dir / "model_call_context.json", role="model_call_context"),
        "model_request_plan": store.register_artifact(output_dir / "model_request_plan.json", role="model_request_plan"),
    }
