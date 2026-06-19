from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from agentflow_studio.model_gateway.provider_adapter import load_provider_registry
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_generation_preflight import preflight_token_matches, video_generation_preflight
from apps.api.runtime_models import VideoGenerationRequest
from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_video_candidates import candidate_file
from apps.api.runtime_video_constants import SAFE_CANDIDATE_ID, VIDEO_SUFFIX_TYPES
from apps.api.runtime_video_dispatch import poll_video_generation, submit_video_generation
from apps.api.runtime_video_manifest import result_from_manifest, safe_manifest, video_response, write_video_job
from apps.api.runtime_video_prompt import strip_image_edit_language as _strip_image_edit_language
from apps.api.runtime_video_prompt import video_provider_prompt as _video_provider_prompt
from apps.api.runtime_video_task_state import load_task_state, write_task_state


def register_runtime_video_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/projects/{project_id}/video-generations/preflight")
    def video_generation_preflight_route(project_id: str, request: VideoGenerationRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        try:
            return video_generation_preflight(store, project_id, request)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_video_generation")) from exc

    @app.post("/projects/{project_id}/video-generations")
    def video_generation(project_id: str, request: VideoGenerationRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        if request.preflight_token:
            try:
                expected_preflight = video_generation_preflight(store, project_id, request)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=safe_error_detail("invalid_video_generation")) from exc
            if not preflight_token_matches(expected_preflight, request.preflight_token):
                raise HTTPException(status_code=409, detail=safe_error_detail("stale_preflight"))
        job_id = store.new_job_id("video_generation", project_id)
        output_dir = store.run_dir(project_id, job_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = submit_video_generation(
                store,
                project_id,
                job_id,
                request,
                output_dir,
                load_registry=load_provider_registry,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_video_generation")) from exc
        job = write_video_job(store, project_id, job_id, result)
        return video_response(store, project_id, job, result)

    @app.post("/projects/{project_id}/video-generations/{job_id}/poll")
    def poll_video_generation_route(project_id: str, job_id: str) -> dict[str, Any]:
        try:
            job = store.load_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc
        if job.get("project_id") != project_id or job.get("action") != "video_generation":
            raise HTTPException(status_code=404, detail="job not found")
        output_dir = store.run_dir(project_id, job_id)
        try:
            result = poll_video_generation(store, project_id, output_dir, load_registry=load_provider_registry)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_video_generation")) from exc
        job = write_video_job(store, project_id, job_id, result)
        return video_response(store, project_id, job, result)

    @app.post("/projects/{project_id}/video-generations/{job_id}/cancel")
    def cancel_video_generation(project_id: str, job_id: str) -> dict[str, Any]:
        try:
            job = store.load_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc
        if job.get("project_id") != project_id or job.get("action") != "video_generation":
            raise HTTPException(status_code=404, detail="job not found")
        output_dir = store.run_dir(project_id, job_id)
        state = load_task_state(output_dir)
        state["status"] = "cancelled_local_only"
        write_task_state(output_dir, state)
        result = result_from_manifest(
            status="cancelled_local_only",
            safe_manifest=safe_manifest(project_id, status="cancelled_local_only", provider_calls_started=False),
            task_state=state,
        )
        job = write_video_job(store, project_id, job_id, result)
        return video_response(store, project_id, job, result)

    @app.get("/projects/{project_id}/video-generations/{job_id}/candidates/{candidate_id}/preview")
    def video_candidate_preview(project_id: str, job_id: str, candidate_id: str) -> FileResponse:
        try:
            job = store.load_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="candidate not found") from exc
        if job.get("project_id") != project_id or job.get("action") != "video_generation":
            raise HTTPException(status_code=404, detail="candidate not found")
        if not SAFE_CANDIDATE_ID.match(candidate_id):
            raise HTTPException(status_code=404, detail="candidate not found")
        path = candidate_file(store.run_dir(project_id, job_id), candidate_id)
        if path is None:
            raise HTTPException(status_code=404, detail="candidate not found")
        return FileResponse(path, media_type=VIDEO_SUFFIX_TYPES[path.suffix.lower()], headers={"Cache-Control": "no-store"})


__all__ = (
    "VideoGenerationRequest",
    "_strip_image_edit_language",
    "_video_provider_prompt",
    "load_provider_registry",
    "register_runtime_video_routes",
)
