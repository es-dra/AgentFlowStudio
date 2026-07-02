from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from agentflow_studio.model_gateway.provider_adapter import load_provider_registry
from apps.api.runtime_errors import RuntimeApiError, runtime_api_error_detail, safe_error_detail
from apps.api.runtime_generation_preflight import (
    preflight_token_matches,
    provider_submit_preflight_requirement,
    video_generation_preflight,
)
from apps.api.runtime_logging import (
    client_request_id_from_request,
    log_business_event,
    request_id_from_request,
    studio_node_id_from_request,
    studio_node_type_from_request,
    user_action_from_request,
)
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
    def video_generation_preflight_route(project_id: str, request: VideoGenerationRequest, http_request: Request) -> dict[str, Any]:
        started = time.perf_counter()
        store.ensure_project_manifest(project_id)
        request_id = request_id_from_request(http_request)
        client_request_id = client_request_id_from_request(http_request)
        node_id = _node_id(http_request, request)
        _log_video_event(
            "video_generation_preflight_started",
            http_request,
            project_id=project_id,
            node_id=node_id,
            provider_service_id=request.provider_service_id,
        )
        try:
            result = video_generation_preflight(store, project_id, request)
            result.update({
                "request_id": request_id,
                "client_request_id": client_request_id or None,
                "project_id": project_id,
                "node_id": node_id or None,
                "action": "video_generation_preflight",
                "status": "preflight_ready",
            })
            _log_video_event(
                "video_generation_preflight_completed",
                http_request,
                project_id=project_id,
                node_id=node_id,
                included_asset_count=len(result.get("included_assets") or []),
                excluded_asset_count=len(result.get("excluded_assets") or []),
                elapsed_ms=_elapsed_ms(started),
            )
            return result
        except RuntimeApiError as exc:
            _raise_runtime_api_error(http_request, exc, project_id=project_id, node_id=node_id, action="video_generation_preflight")
        except ValueError as exc:
            detail = safe_error_detail(
                "invalid_video_generation",
                message="视频生成前检查失败，请检查视频参数和素材引用。",
                request_id=request_id,
                client_request_id=client_request_id,
                project_id=project_id,
                node_id=node_id,
                action="video_generation_preflight",
                stage="preflight",
            )
            _log_video_rejected(http_request, detail)
            raise HTTPException(status_code=422, detail=detail) from exc

    @app.post("/projects/{project_id}/video-generations")
    def video_generation(project_id: str, request: VideoGenerationRequest, http_request: Request) -> dict[str, Any]:
        started = time.perf_counter()
        store.ensure_project_manifest(project_id)
        request_id = request_id_from_request(http_request)
        client_request_id = client_request_id_from_request(http_request)
        node_id = _node_id(http_request, request)
        _log_video_event(
            "video_generation_submit_started",
            http_request,
            project_id=project_id,
            node_id=node_id,
            provider_service_id=request.provider_service_id,
            first_frame_image_asset_id=request.first_frame_image_asset_id,
            input_source_mode=(request.input_source.source_mode if request.input_source else "explicit_first_frame_selection"),
            duration_sec=request.duration_sec,
            resolution=request.resolution,
            aspect_ratio=request.aspect_ratio,
            candidate_count=request.candidate_count,
            has_preflight_token=bool(request.preflight_token),
        )
        preflight_requirement = provider_submit_preflight_requirement("video", request)
        if preflight_requirement["required"] and not request.preflight_token:
            detail = safe_error_detail(
                "missing_preflight",
                detail_code="preflight_required",
                message="Please run generation preflight again before submitting to a remote video provider.",
                user_action="Run preflight, then resubmit the unchanged generation request.",
                request_id=request_id,
                client_request_id=client_request_id,
                project_id=project_id,
                node_id=node_id,
                action="video_generation",
                stage="preflight_required",
                status="blocked",
                retryable=True,
                details={
                    "provider_calls_started": False,
                    "required_gate": preflight_requirement["required_gate"],
                },
            )
            _log_video_rejected(http_request, detail)
            raise HTTPException(status_code=428, detail=detail)
        if request.preflight_token:
            try:
                expected_preflight = video_generation_preflight(store, project_id, request)
            except RuntimeApiError as exc:
                _raise_runtime_api_error(http_request, exc, project_id=project_id, node_id=node_id, action="video_generation")
            except ValueError as exc:
                detail = safe_error_detail(
                    "invalid_video_generation",
                    message="视频生成前检查失败，请检查视频参数和素材引用。",
                    request_id=request_id,
                    client_request_id=client_request_id,
                    project_id=project_id,
                    node_id=node_id,
                    action="video_generation",
                    stage="preflight",
                )
                _log_video_rejected(http_request, detail)
                raise HTTPException(status_code=422, detail=detail) from exc
            if not preflight_token_matches(expected_preflight, request.preflight_token):
                detail = safe_error_detail(
                    "stale_preflight",
                    message="生成前检查结果已过期，请重新点击生成。",
                    user_action="请重新提交生成请求，让系统重新完成生成前检查。",
                    request_id=request_id,
                    client_request_id=client_request_id,
                    project_id=project_id,
                    node_id=node_id,
                    action="video_generation",
                    stage="preflight_token",
                    details={"provider_calls_started": False},
                )
                _log_video_rejected(http_request, detail)
                raise HTTPException(status_code=409, detail=detail)
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
                request_id=request_id,
                client_request_id=client_request_id,
            )
        except RuntimeApiError as exc:
            _raise_runtime_api_error(http_request, exc, project_id=project_id, node_id=node_id, action="video_generation", job_id=job_id)
        except ValueError as exc:
            detail = safe_error_detail(
                "invalid_video_generation",
                message="视频生成请求参数无效，请检查首帧、画幅、时长、分辨率和候选数量。",
                request_id=request_id,
                client_request_id=client_request_id,
                project_id=project_id,
                node_id=node_id,
                action="video_generation",
                stage="submit",
                details={"reason": str(exc), "job_id": job_id},
            )
            _log_video_rejected(http_request, detail)
            raise HTTPException(status_code=422, detail=detail) from exc
        job = write_video_job(store, project_id, job_id, result)
        response = video_response(store, project_id, job, result)
        response.update({
            "request_id": request_id,
            "client_request_id": client_request_id or None,
            "project_id": project_id,
            "node_id": node_id or None,
            "action": "video_generation",
            "status": response.get("job", {}).get("status") or result.get("status"),
            "stage": _response_stage(result),
        })
        _log_video_event(
            "video_generation_response_returned" if response["status"] not in {"blocked", "poll_failed"} else "video_generation_blocked",
            http_request,
            project_id=project_id,
            node_id=node_id,
            job_id=job_id,
            status=response["status"],
            stage=response["stage"],
            reason=_first_block_reason(result),
            provider_calls_started=response.get("provider_calls_started"),
            elapsed_ms=_elapsed_ms(started),
        )
        return response

    @app.post("/projects/{project_id}/video-generations/{job_id}/poll")
    def poll_video_generation_route(project_id: str, job_id: str, http_request: Request) -> dict[str, Any]:
        started = time.perf_counter()
        request_id = request_id_from_request(http_request)
        client_request_id = client_request_id_from_request(http_request)
        _log_video_event("video_generation_poll_started", http_request, project_id=project_id, job_id=job_id)
        try:
            job = store.load_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc
        if job.get("project_id") != project_id or job.get("action") != "video_generation":
            raise HTTPException(status_code=404, detail="job not found")
        output_dir = store.run_dir(project_id, job_id)
        try:
            result = poll_video_generation(store, project_id, output_dir, load_registry=load_provider_registry, request_id=request_id, client_request_id=client_request_id)
        except RuntimeApiError as exc:
            _raise_runtime_api_error(http_request, exc, project_id=project_id, action="video_generation_poll", job_id=job_id)
        except ValueError as exc:
            detail = safe_error_detail(
                "invalid_video_generation",
                message="视频任务轮询失败，请稍后重试。",
                user_action="请稍后点击继续轮询视频任务。",
                request_id=request_id,
                client_request_id=client_request_id,
                project_id=project_id,
                action="video_generation_poll",
                stage="poll",
                retryable=True,
                details={"job_id": job_id, "reason": str(exc)},
            )
            _log_video_rejected(http_request, detail)
            raise HTTPException(status_code=422, detail=detail) from exc
        job = write_video_job(store, project_id, job_id, result)
        response = video_response(store, project_id, job, result)
        response.update({
            "request_id": request_id,
            "client_request_id": client_request_id or None,
            "project_id": project_id,
            "action": "video_generation_poll",
            "status": response.get("job", {}).get("status") or result.get("status"),
            "stage": "poll",
        })
        _log_video_event(
            "video_generation_poll_completed",
            http_request,
            project_id=project_id,
            job_id=job_id,
            status=response["status"],
            provider_calls_started=response.get("provider_calls_started"),
            elapsed_ms=_elapsed_ms(started),
        )
        return response

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


def _node_id(http_request: Request, request: VideoGenerationRequest) -> str:
    return request.node_id or studio_node_id_from_request(http_request)


def _request_context(http_request: Request, *, project_id: str = "", node_id: str = "") -> dict[str, Any]:
    return {
        "request_id": request_id_from_request(http_request),
        "client_request_id": client_request_id_from_request(http_request),
        "user_action": user_action_from_request(http_request),
        "studio_node_id": node_id or studio_node_id_from_request(http_request),
        "studio_node_type": studio_node_type_from_request(http_request),
        "project_id": project_id,
    }


def _log_video_event(event_type: str, http_request: Request, **fields: Any) -> None:
    domain, event, level = _file_log_mapping(event_type)
    log_business_event(
        event_type,
        **_request_context(
            http_request,
            project_id=str(fields.pop("project_id", "") or ""),
            node_id=str(fields.pop("node_id", "") or ""),
        ),
        **fields,
        file_log_domain=domain,
        file_log_event=event,
        file_log_level=level,
    )


def _log_video_rejected(http_request: Request, detail: dict[str, Any], *, event_type: str = "video_generation_rejected") -> None:
    details = detail.get("details") if isinstance(detail.get("details"), dict) else {}
    log_business_event(
        event_type,
        request_id=detail.get("request_id") or request_id_from_request(http_request),
        client_request_id=detail.get("client_request_id") or client_request_id_from_request(http_request),
        user_action=user_action_from_request(http_request),
        project_id=detail.get("project_id"),
        node_id=detail.get("node_id") or studio_node_id_from_request(http_request),
        action=detail.get("action"),
        stage=detail.get("stage"),
        error=detail.get("error"),
        message=detail.get("message"),
        retryable=detail.get("retryable"),
        **details,
        file_log_domain="video",
        file_log_event="rejected",
        file_log_level="ERROR",
    )


def _raise_runtime_api_error(
    http_request: Request,
    exc: RuntimeApiError,
    *,
    project_id: str = "",
    node_id: str = "",
    action: str = "",
    job_id: str = "",
) -> None:
    detail = runtime_api_error_detail(
        exc,
        request_id=request_id_from_request(http_request),
        client_request_id=client_request_id_from_request(http_request),
        project_id=project_id,
        node_id=node_id or studio_node_id_from_request(http_request),
        action=action,
    )
    if job_id:
        detail.setdefault("details", {})["job_id"] = job_id
    _log_video_rejected(http_request, detail)
    raise HTTPException(status_code=exc.status_code, detail=detail) from exc


def _response_stage(result: dict[str, Any]) -> str:
    status = str(result.get("status") or "")
    safe = result.get("safe_manifest") if isinstance(result.get("safe_manifest"), dict) else {}
    if status == "blocked":
        return "provider_gate" if (safe.get("provider_gate") or {}).get("status") == "blocked" else "blocked"
    if status == "poll_failed":
        return "provider_submit_or_poll"
    if status in {"submitted", "running"}:
        return "provider_task"
    if status == "succeeded":
        return "completed"
    return status or "unknown"


def _first_block_reason(result: dict[str, Any]) -> str:
    safe = result.get("safe_manifest") if isinstance(result.get("safe_manifest"), dict) else {}
    blocks = safe.get("blocks") if isinstance(safe.get("blocks"), list) else []
    first = blocks[0] if blocks and isinstance(blocks[0], dict) else {}
    return str(first.get("reason") or "")


def _file_log_mapping(event_type: str) -> tuple[str, str, str]:
    mapping = {
        "video_generation_preflight_started": ("video", "preflight_start", "INFO"),
        "video_generation_preflight_completed": ("video", "preflight_ok", "INFO"),
        "video_generation_submit_started": ("video", "submit_request", "INFO"),
        "video_generation_response_returned": ("video", "response", "INFO"),
        "video_generation_blocked": ("video", "blocked", "WARNING"),
        "video_generation_poll_started": ("video", "poll_request", "INFO"),
        "video_generation_poll_completed": ("video", "poll_response", "INFO"),
    }
    return mapping.get(event_type, ("video", event_type.removeprefix("video_generation_"), "INFO"))


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


__all__ = (
    "VideoGenerationRequest",
    "_strip_image_edit_language",
    "_video_provider_prompt",
    "load_provider_registry",
    "register_runtime_video_routes",
)
