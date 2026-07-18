from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from apps.api.runtime_external_video_common import (
    EXTERNAL_DOWNLOAD_ENV,
    EXTERNAL_VIDEO_ACTION,
    EXTERNAL_VIDEO_NON_CLAIMS,
    PUBLIC_PREVIEW_MIME,
    block,
    load_task_state,
    utc_now,
    write_task_state,
)
from apps.api.runtime_external_video_libtv import poll_libtv, submit_libtv
from apps.api.runtime_external_video_manifest import (
    external_video_response,
    request_plan,
    result_from_state,
    write_external_video_job,
    write_result_artifacts,
)
from apps.api.runtime_external_video_media import create_replay_video, external_video_media_path, output_summary
from apps.api.runtime_external_video_models import ExternalVideoJobRequest
from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_video_manifest import write_json_checked


def submit_external_video_job(
    store: RuntimeStore,
    project_id: str,
    job_id: str,
    request: ExternalVideoJobRequest,
    output_dir: Path,
    *,
    request_id: str = "",
    client_request_id: str = "",
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = request_plan(project_id, job_id, request)
    write_json_checked(output_dir / "external_video_request_plan.json", plan)
    artifacts = {
        "external_video_request_plan": store.register_artifact(
            output_dir / "external_video_request_plan.json",
            role="external_video_request_plan",
        )
    }
    if request.engine == "replay":
        return submit_replay(store, project_id, job_id, request, output_dir, artifacts)
    return submit_libtv(
        store,
        project_id,
        job_id,
        request,
        output_dir,
        artifacts,
        request_id=request_id,
        client_request_id=client_request_id,
    )


def poll_external_video_job(
    store: RuntimeStore,
    project_id: str,
    job_id: str,
    output_dir: Path,
    *,
    request_id: str = "",
    client_request_id: str = "",
) -> dict[str, Any]:
    del request_id, client_request_id
    state = load_task_state(output_dir)
    engine = str(state.get("engine") or "")
    if state.get("status") in {"succeeded", "blocked", "needs_attention", "failed"}:
        return result_from_state(store, project_id, job_id, output_dir, state)
    if engine == "libtv":
        return poll_libtv(store, project_id, job_id, output_dir, state)
    state["status"] = "failed"
    state["completed_at"] = utc_now()
    state["blocks"] = [block("external_video_unknown_engine", "External video adapter state is not recognized.")]
    write_task_state(output_dir, state)
    return result_from_state(store, project_id, job_id, output_dir, state)


def submit_replay(
    store: RuntimeStore,
    project_id: str,
    job_id: str,
    request: ExternalVideoJobRequest,
    output_dir: Path,
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    media_path = create_replay_video(output_dir, request)
    now = utc_now()
    state = {
        "schema_version": "afs_external_video_task_state.v0.1",
        "status": "succeeded",
        "engine": "replay",
        "created_at": now,
        "submitted_at": now,
        "completed_at": now,
        "provider_calls_started": False,
        "external_download_started": False,
        "output": output_summary(media_path),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
    }
    write_task_state(output_dir, state)
    return write_result_artifacts(store, project_id, job_id, output_dir, request, artifacts, state)


__all__ = (
    "EXTERNAL_DOWNLOAD_ENV",
    "EXTERNAL_VIDEO_ACTION",
    "EXTERNAL_VIDEO_NON_CLAIMS",
    "PUBLIC_PREVIEW_MIME",
    "external_video_media_path",
    "external_video_response",
    "poll_external_video_job",
    "submit_external_video_job",
    "write_external_video_job",
)
