from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_external_video_adapters import (
    EXTERNAL_VIDEO_ACTION,
    PUBLIC_PREVIEW_MIME,
    external_video_media_path,
    external_video_response,
    poll_external_video_job,
    submit_external_video_job,
    write_external_video_job,
)
from apps.api.runtime_external_video_models import ExternalVideoJobRequest
from apps.api.runtime_logging import client_request_id_from_request, request_id_from_request
from apps.api.runtime_store import RuntimeStore


def register_runtime_external_video_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/projects/{project_id}/external-video-jobs")
    def create_external_video_job(project_id: str, request: ExternalVideoJobRequest, http_request: Request) -> dict[str, Any]:
        started = time.perf_counter()
        store.ensure_project_manifest(project_id)
        request_id = request_id_from_request(http_request)
        client_request_id = client_request_id_from_request(http_request)
        job_id = store.new_job_id(EXTERNAL_VIDEO_ACTION, project_id)
        output_dir = store.run_dir(project_id, job_id)
        try:
            result = submit_external_video_job(
                store,
                project_id,
                job_id,
                request,
                output_dir,
                request_id=request_id,
                client_request_id=client_request_id,
            )
        except ValueError as exc:
            detail = safe_error_detail(
                "invalid_external_video_generation",
                message="外部视频任务无法创建，请检查提示词、引擎和输出规格。",
                request_id=request_id,
                client_request_id=client_request_id,
                project_id=project_id,
                action=EXTERNAL_VIDEO_ACTION,
                stage="submit",
                details={"reason": str(exc)},
            )
            raise HTTPException(status_code=422, detail=detail) from exc
        job = write_external_video_job(store, project_id, job_id, result)
        response = external_video_response(store, project_id, job, result)
        response.update(
            {
                "request_id": request_id,
                "client_request_id": client_request_id or None,
                "project_id": project_id,
                "node_id": request.node_id or None,
                "action": EXTERNAL_VIDEO_ACTION,
                "status": response.get("job", {}).get("status") or result.get("status"),
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            }
        )
        return response

    @app.post("/projects/{project_id}/external-video-jobs/{job_id}/poll")
    def poll_external_video_job_route(project_id: str, job_id: str, http_request: Request) -> dict[str, Any]:
        request_id = request_id_from_request(http_request)
        client_request_id = client_request_id_from_request(http_request)
        try:
            job = store.load_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc
        if job.get("project_id") != project_id or job.get("action") != EXTERNAL_VIDEO_ACTION:
            raise HTTPException(status_code=404, detail="job not found")
        output_dir = store.run_dir(project_id, job_id)
        try:
            result = poll_external_video_job(
                store,
                project_id,
                job_id,
                output_dir,
                request_id=request_id,
                client_request_id=client_request_id,
            )
        except (KeyError, ValueError) as exc:
            detail = safe_error_detail(
                "invalid_external_video_poll",
                message="外部视频任务轮询失败，请稍后重试。",
                request_id=request_id,
                client_request_id=client_request_id,
                project_id=project_id,
                action=f"{EXTERNAL_VIDEO_ACTION}_poll",
                stage="poll",
                details={"job_id": job_id, "reason": str(exc)},
            )
            raise HTTPException(status_code=422, detail=detail) from exc
        job = write_external_video_job(store, project_id, job_id, result)
        response = external_video_response(store, project_id, job, result)
        response.update(
            {
                "request_id": request_id,
                "client_request_id": client_request_id or None,
                "project_id": project_id,
                "action": f"{EXTERNAL_VIDEO_ACTION}_poll",
                "status": response.get("job", {}).get("status") or result.get("status"),
            }
        )
        return response

    @app.get("/projects/{project_id}/external-video-jobs/{job_id}/preview")
    def external_video_preview(project_id: str, job_id: str) -> FileResponse:
        return _external_video_file_response(store, project_id, job_id, disposition="inline")

    @app.get("/projects/{project_id}/external-video-jobs/{job_id}/download")
    def external_video_download(project_id: str, job_id: str) -> FileResponse:
        return _external_video_file_response(store, project_id, job_id, disposition="attachment")


def _external_video_file_response(store: RuntimeStore, project_id: str, job_id: str, *, disposition: str) -> FileResponse:
    try:
        job = store.load_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="video not found") from exc
    if job.get("project_id") != project_id or job.get("action") != EXTERNAL_VIDEO_ACTION:
        raise HTTPException(status_code=404, detail="video not found")
    path = external_video_media_path(store, project_id, job_id)
    if path is None:
        raise HTTPException(status_code=404, detail="video not found")
    return FileResponse(
        path,
        media_type=PUBLIC_PREVIEW_MIME,
        filename="afs-external-video.mp4",
        headers={"Cache-Control": "no-store", "Content-Disposition": f'{disposition}; filename="afs-external-video.mp4"'},
    )


__all__ = ("register_runtime_external_video_routes",)
