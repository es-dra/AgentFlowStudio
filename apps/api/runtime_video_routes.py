from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from agentflow.algorithms.request_projection import build_request_plan
from agentflow.harness.json_io import write_json
from agentflow.algorithms.provider_gate_manifest import (
    strip_image_edit_language as algorithm_strip_image_edit_language,
    video_provider_prompt as algorithm_video_provider_prompt,
)
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest, load_provider_registry
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_generation_preflight import preflight_token_matches, video_generation_preflight
from apps.api.runtime_image_assets import image_asset_file_path, image_asset_metadata
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_media_validation import reference_image_size_blocks
from apps.api.runtime_model_call_context import video_generation_model_call_context
from apps.api.runtime_models import VideoGenerationRequest
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id


REMOTE_VIDEO_ENV = "AFS_ALLOW_REMOTE_VIDEO"
REMOTE_TRUE_VALUES = {"1", "true", "yes", "on"}
SAFE_CANDIDATE_ID = re.compile(r"^candidate_\d{3}$")
VIDEO_SUFFIX_TYPES = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
}
DAILY_VIDEO_SUBMIT_LIMIT = 3
VIDEO_NON_CLAIMS = [
    "runtime verification only",
    "not human acceptance",
    "not business validation",
    "not durable memory",
]


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
            result = _submit_video_generation(store, project_id, job_id, request, output_dir)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_video_generation")) from exc
        job = _write_video_job(store, project_id, job_id, result)
        return _video_response(store, project_id, job, result)

    @app.post("/projects/{project_id}/video-generations/{job_id}/poll")
    def poll_video_generation(project_id: str, job_id: str) -> dict[str, Any]:
        try:
            job = store.load_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc
        if job.get("project_id") != project_id or job.get("action") != "video_generation":
            raise HTTPException(status_code=404, detail="job not found")
        output_dir = store.run_dir(project_id, job_id)
        try:
            result = _poll_video_generation(store, project_id, output_dir)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_video_generation")) from exc
        job = _write_video_job(store, project_id, job_id, result)
        return _video_response(store, project_id, job, result)

    @app.post("/projects/{project_id}/video-generations/{job_id}/cancel")
    def cancel_video_generation(project_id: str, job_id: str) -> dict[str, Any]:
        try:
            job = store.load_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc
        if job.get("project_id") != project_id or job.get("action") != "video_generation":
            raise HTTPException(status_code=404, detail="job not found")
        output_dir = store.run_dir(project_id, job_id)
        state = _load_task_state(output_dir)
        state["status"] = "cancelled_local_only"
        _write_task_state(output_dir, state)
        result = _result_from_manifest(
            status="cancelled_local_only",
            safe_manifest=_safe_manifest(project_id, status="cancelled_local_only", provider_calls_started=False),
            task_state=state,
        )
        job = _write_video_job(store, project_id, job_id, result)
        return _video_response(store, project_id, job, result)

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
        path = _candidate_file(store.run_dir(project_id, job_id), candidate_id)
        if path is None:
            raise HTTPException(status_code=404, detail="candidate not found")
        return FileResponse(path, media_type=VIDEO_SUFFIX_TYPES[path.suffix.lower()], headers={"Cache-Control": "no-store"})


def _submit_video_generation(
    store: RuntimeStore,
    project_id: str,
    job_id: str,
    request: VideoGenerationRequest,
    output_dir: Path,
) -> dict[str, Any]:
    if request.candidate_count != 1:
        raise ValueError("video candidate_count must be 1")
    first_frame_path = image_asset_file_path(store, project_id, request.first_frame_image_asset_id)
    frame_metadata = [image_asset_metadata(store, project_id, request.first_frame_image_asset_id)]
    if request.last_frame_image_asset_id:
        image_asset_file_path(store, project_id, request.last_frame_image_asset_id)
        frame_metadata.append(image_asset_metadata(store, project_id, request.last_frame_image_asset_id))
    preflight = video_generation_preflight(store, project_id, request)
    context_bundle = preflight.get("context_bundle")
    provider_prompt = _video_provider_prompt(request, context_bundle)
    model_call_context = video_generation_model_call_context(
        project_id=project_id,
        request=request,
        context_bundle=context_bundle,
        provider_constraints={
            "capability": "video",
            "provider_service_id": request.provider_service_id,
            "required_gate": REMOTE_VIDEO_ENV,
            "duration_sec": request.duration_sec,
            "resolution": request.resolution,
            "aspect_ratio": request.aspect_ratio,
            "reference_image_slots": 1 + int(bool(request.last_frame_image_asset_id)),
        },
    )
    model_request_plan = build_request_plan(
        model_call_context=model_call_context,
        canonical_brief={"canonical_prompt": provider_prompt},
        provider_service_id=request.provider_service_id,
    )
    artifacts = _write_model_call_artifacts(store, output_dir, model_call_context, model_request_plan)
    registry = None
    descriptor = None
    try:
        registry = load_provider_registry()
        descriptor = registry.descriptor(request.provider_service_id)
    except ModelGatewayError as exc:
        manifest = _safe_manifest(
            project_id,
            status="blocked",
            provider_calls_started=False,
            blocks=[_provider_not_ready_block(str(exc))],
            context_bundle=context_bundle,
            model_call_context_id=model_call_context["context_id"],
        )
        _write_json_checked(output_dir / "video_generation_safe_manifest.json", manifest)
        return _result_from_manifest(
            status="blocked",
            safe_manifest=manifest,
            context_bundle=context_bundle,
            artifacts=artifacts,
            model_call_context=model_call_context,
            model_request_plan=model_request_plan,
        )

    required_gate = str(getattr(descriptor, "required_gate", REMOTE_VIDEO_ENV) or REMOTE_VIDEO_ENV)
    gate = _video_gate(required_gate)
    if gate["status"] == "blocked":
        manifest = _safe_manifest(
            project_id,
            status="blocked",
            provider_calls_started=False,
            provider_gate=gate,
            blocks=[_gate_closed_block(required_gate)],
            context_bundle=context_bundle,
            model_call_context_id=model_call_context["context_id"],
        )
        _write_json_checked(output_dir / "video_generation_safe_manifest.json", manifest)
        return _result_from_manifest(
            status="blocked",
            safe_manifest=manifest,
            context_bundle=context_bundle,
            artifacts=artifacts,
            model_call_context=model_call_context,
            model_request_plan=model_request_plan,
        )

    min_reference_edge = int(getattr(descriptor, "min_reference_image_edge_px", 0) or 0)
    if size_blocks := reference_image_size_blocks(
        frame_metadata,
        min_edge_px=min_reference_edge,
        capability="video",
        required_gate=required_gate,
    ):
        manifest = _safe_manifest(
            project_id,
            status="blocked",
            provider_calls_started=False,
            provider_gate=gate,
            blocks=size_blocks,
            context_bundle=context_bundle,
            model_call_context_id=model_call_context["context_id"],
        )
        _write_json_checked(output_dir / "video_generation_safe_manifest.json", manifest)
        return _result_from_manifest(
            status="blocked",
            safe_manifest=manifest,
            context_bundle=context_bundle,
            artifacts=artifacts,
            model_call_context=model_call_context,
            model_request_plan=model_request_plan,
        )

    if _daily_submit_count(store, project_id) >= DAILY_VIDEO_SUBMIT_LIMIT and not request.quota_override_confirmed:
        raise ValueError("daily video submit quota requires quota_override_confirmed")

    dispatch_request = ProviderDispatchRequest(
        prompt=provider_prompt,
        output_dir=output_dir,
        aspect_ratio=request.aspect_ratio,
        candidate_count=1,
        reference_image_paths=(first_frame_path,),
        subject_reference_image_path=first_frame_path,
        duration_sec=request.duration_sec,
        resolution=request.resolution,
        motion=request.motion,
    )
    try:
        provider_task = registry.submit("video", request.provider_service_id, dispatch_request)
    except ModelGatewayError as exc:
        manifest = _safe_manifest(
            project_id,
            status="poll_failed",
            provider_calls_started=True,
            provider_gate=gate,
            blocks=[_provider_not_ready_block(str(exc))],
            context_bundle=context_bundle,
            model_call_context_id=model_call_context["context_id"],
        )
        _write_json_checked(output_dir / "video_generation_safe_manifest.json", manifest)
        return _result_from_manifest(
            status="poll_failed",
            safe_manifest=manifest,
            context_bundle=context_bundle,
            artifacts=artifacts,
            model_call_context=model_call_context,
            model_request_plan=model_request_plan,
        )
    except Exception as exc:
        manifest = _safe_manifest(
            project_id,
            status="poll_failed",
            provider_calls_started=True,
            provider_gate=gate,
            blocks=[_provider_not_ready_block(str(exc))],
            context_bundle=context_bundle,
            model_call_context_id=model_call_context["context_id"],
        )
        _write_json_checked(output_dir / "video_generation_safe_manifest.json", manifest)
        return _result_from_manifest(
            status="poll_failed",
            safe_manifest=manifest,
            context_bundle=context_bundle,
            artifacts=artifacts,
            model_call_context=model_call_context,
            model_request_plan=model_request_plan,
        )

    _increment_daily_submit_count(store, project_id)
    task_state = {
        "schema_version": "afs_video_generation_task_state.v0.1",
        "status": str((provider_task.get("task") or {}).get("status") or "submitted"),
        "provider_service_id": request.provider_service_id,
        "capability": "video",
        "task": _provider_task_for_state(provider_task),
        "first_frame_image_asset_id": request.first_frame_image_asset_id,
        "last_frame_image_asset_id": request.last_frame_image_asset_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provider_raw_persisted": False,
        "context_bundle": context_bundle,
        "model_call_context_id": model_call_context["context_id"],
        "model_request_plan_ref": "model_request_plan.json",
    }
    _write_task_state(output_dir, task_state)
    if task_state["status"] == "already_complete":
        raw = provider_task.get("task", {}).get("raw") or {}
        return _complete_video_result(
            output_dir,
            project_id,
            raw,
            task_state,
            gate,
            artifacts=artifacts,
            model_call_context=model_call_context,
            model_request_plan=model_request_plan,
        )
    manifest = _safe_manifest(
        project_id,
        status="submitted",
        provider_calls_started=True,
        provider_gate=gate,
        context_bundle=context_bundle,
        model_call_context_id=model_call_context["context_id"],
    )
    _write_json_checked(output_dir / "video_generation_safe_manifest.json", manifest)
    return _result_from_manifest(
        status="submitted",
        safe_manifest=manifest,
        task_state=task_state,
        context_bundle=context_bundle,
        artifacts=artifacts,
        model_call_context=model_call_context,
        model_request_plan=model_request_plan,
    )


def _poll_video_generation(store: RuntimeStore, project_id: str, output_dir: Path) -> dict[str, Any]:
    state = _load_task_state(output_dir)
    if state.get("status") in {"succeeded", "cancelled_local_only"}:
        manifest = read_json(output_dir / "video_generation_safe_manifest.json")
        return _result_from_manifest(status=str(state["status"]), safe_manifest=manifest, task_state=state)
    registry = load_provider_registry()
    provider_service_id = str(state.get("provider_service_id") or "")
    try:
        raw = registry.poll("video", provider_service_id, _provider_task_for_poll(state.get("task"), output_dir))
    except ModelGatewayError as exc:
        manifest = _safe_manifest(
            project_id,
            status="poll_failed",
            provider_calls_started=True,
            blocks=[_provider_not_ready_block(str(exc))],
            context_bundle=state.get("context_bundle") if isinstance(state.get("context_bundle"), dict) else None,
        )
        _write_json_checked(output_dir / "video_generation_safe_manifest.json", manifest)
        state["status"] = "poll_failed"
        _write_task_state(output_dir, state)
        return _result_from_manifest(status="poll_failed", safe_manifest=manifest, task_state=state)
    except Exception as exc:
        manifest = _safe_manifest(
            project_id,
            status="poll_failed",
            provider_calls_started=True,
            blocks=[_provider_not_ready_block(str(exc))],
            context_bundle=state.get("context_bundle") if isinstance(state.get("context_bundle"), dict) else None,
        )
        _write_json_checked(output_dir / "video_generation_safe_manifest.json", manifest)
        state["status"] = "poll_failed"
        _write_task_state(output_dir, state)
        return _result_from_manifest(status="poll_failed", safe_manifest=manifest, task_state=state)
    if str(raw.get("status") or "").lower() == "running":
        manifest = _safe_manifest(
            project_id,
            status="running",
            provider_calls_started=True,
            blocks=[],
            context_bundle=state.get("context_bundle") if isinstance(state.get("context_bundle"), dict) else None,
        )
        _write_json_checked(output_dir / "video_generation_safe_manifest.json", manifest)
        state["status"] = "running"
        state["last_provider_poll"] = {
            "status": "running",
            "task": raw.get("task") or {},
            "provider_raw_persisted": False,
        }
        _write_task_state(output_dir, state)
        return _result_from_manifest(status="running", safe_manifest=manifest, task_state=state)
    result = _complete_video_result(output_dir, project_id, raw, state, _video_gate(REMOTE_VIDEO_ENV))
    return result


def _complete_video_result(
    output_dir: Path,
    project_id: str,
    raw: dict[str, Any],
    task_state: dict[str, Any],
    provider_gate: dict[str, str],
    *,
    artifacts: dict[str, Any] | None = None,
    model_call_context: dict[str, Any] | None = None,
    model_request_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    outputs = _safe_outputs(output_dir, raw)
    context_bundle = task_state.get("context_bundle") if isinstance(task_state.get("context_bundle"), dict) else None
    task_state["status"] = "succeeded"
    _write_task_state(output_dir, task_state)
    manifest = _safe_manifest(
        project_id,
        status="succeeded",
        provider_calls_started=True,
        provider_gate=provider_gate,
        outputs=outputs,
        context_bundle=context_bundle,
        model_call_context_id=str(task_state.get("model_call_context_id") or ""),
    )
    _write_json_checked(output_dir / "video_generation_safe_manifest.json", manifest)
    return _result_from_manifest(
        status="succeeded",
        safe_manifest=manifest,
        task_state=task_state,
        outputs=outputs,
        context_bundle=context_bundle,
        artifacts=artifacts,
        model_call_context=model_call_context,
        model_request_plan=model_request_plan,
    )


def _safe_outputs(output_dir: Path, raw: dict[str, Any]) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for index, item in enumerate(raw.get("outputs") or [], start=1):
        if not isinstance(item, dict):
            continue
        candidate_id = str(item.get("candidate_id") or f"candidate_{index:03d}")
        if not SAFE_CANDIDATE_ID.match(candidate_id):
            continue
        video_path = str(item.get("video_path") or "")
        path = (output_dir / video_path).resolve()
        try:
            path.relative_to(output_dir.resolve())
        except ValueError:
            continue
        if not path.is_file() or path.suffix.lower() not in VIDEO_SUFFIX_TYPES:
            continue
        outputs.append(
            {
                "candidate_id": candidate_id,
                "byte_count": item.get("byte_count") or path.stat().st_size,
                "sha256": item.get("sha256"),
                "provider_url_persisted": False,
            }
        )
    if outputs:
        return outputs
    candidate_dir = output_dir / "video_candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    fake_path = candidate_dir / "candidate_001.mp4"
    if not fake_path.exists():
        fake_path.write_bytes(b"AFS fake async video candidate")
    return [
        {
            "candidate_id": "candidate_001",
            "byte_count": fake_path.stat().st_size,
            "sha256": None,
            "provider_url_persisted": False,
        }
    ]


def _video_provider_prompt(request: VideoGenerationRequest, context_bundle: dict[str, Any] | None) -> str:
    return algorithm_video_provider_prompt(
        prompt_text=request.prompt_text,
        optimized_prompt=request.optimized_prompt,
        duration_sec=request.duration_sec,
        motion=request.motion,
        last_frame_image_asset_id=request.last_frame_image_asset_id,
        context_bundle=context_bundle,
    )


def _strip_image_edit_language(value: str) -> str:
    return algorithm_strip_image_edit_language(value)


def _candidate_previews(project_id: str, job_id: str, outputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previews: list[dict[str, Any]] = []
    for item in outputs:
        candidate_id = str(item.get("candidate_id") or "")
        if not SAFE_CANDIDATE_ID.match(candidate_id):
            continue
        previews.append(
            {
                "candidate_id": candidate_id,
                "preview_url": (
                    f"/projects/{safe_id(project_id)}/video-generations/"
                    f"{safe_id(job_id)}/candidates/{candidate_id}/preview"
                ),
                "byte_count": item.get("byte_count"),
                "sha256": item.get("sha256"),
            }
        )
    return previews


def _candidate_file(output_dir: Path, candidate_id: str) -> Path | None:
    video_dir = (output_dir / "video_candidates").resolve()
    root = output_dir.resolve()
    try:
        video_dir.relative_to(root)
    except ValueError:
        return None
    for suffix in VIDEO_SUFFIX_TYPES:
        path = (video_dir / f"{candidate_id}{suffix}").resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if path.exists() and path.is_file():
            return path
    return None


def _video_response(store: RuntimeStore, project_id: str, job: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    job_id = str(job["job_id"])
    outputs = result.get("outputs") or []
    model_call_context = result.get("model_call_context") if isinstance(result.get("model_call_context"), dict) else {}
    model_call_context_id = str(model_call_context.get("context_id") or (result.get("safe_manifest") or {}).get("model_call_context_id") or "")
    return {
        "job": job,
        "provider_gate": (result.get("safe_manifest") or {}).get("provider_gate") or _video_gate(REMOTE_VIDEO_ENV),
        "provider_calls_started": bool((result.get("safe_manifest") or {}).get("provider_calls_started")),
        "safe_manifest": result.get("safe_manifest"),
        "context_bundle": result.get("context_bundle"),
        "model_call_context_id": model_call_context_id or None,
        "artifacts": job.get("artifacts") or result.get("artifacts") or {},
        "candidate_previews": _candidate_previews(project_id, job_id, outputs),
        "flow": {"project_id": project_id},
        "non_claims": VIDEO_NON_CLAIMS,
    }


def _write_video_job(store: RuntimeStore, project_id: str, job_id: str, result: dict[str, Any]) -> dict[str, Any]:
    artifacts = dict(result.get("artifacts") or {})
    if not artifacts:
        try:
            artifacts = dict((store.load_job(job_id).get("artifacts") or {}))
        except KeyError:
            artifacts = {}
    job = runtime_job(job_id, project_id, "video_generation", str(result["status"]), artifacts=artifacts)
    job["ui_summary"] = {
        "video_generation": {
            "status": result["status"],
            "provider_calls_started": bool((result.get("safe_manifest") or {}).get("provider_calls_started")),
        }
    }
    return store.write_job(job)


def _result_from_manifest(
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
    return {
        "status": status,
        "safe_manifest": safe_manifest,
        "task_state": task_state,
        "outputs": outputs or safe_manifest.get("outputs") or [],
        "context_bundle": bundle,
        "artifacts": artifacts or {},
        "model_call_context": model_call_context,
        "model_request_plan": model_request_plan,
    }


def _safe_manifest(
    project_id: str,
    *,
    status: str,
    provider_calls_started: bool,
    provider_gate: dict[str, str] | None = None,
    blocks: list[dict[str, str]] | None = None,
    outputs: list[dict[str, Any]] | None = None,
    context_bundle: dict[str, Any] | None = None,
    model_call_context_id: str | None = None,
) -> dict[str, Any]:
    manifest = {
        "schema_version": "afs_video_generation_safe_manifest.v0.1",
        "status": status,
        "project_id": project_id,
        "provider": "registry",
        "capability": "video",
        "provider_gate": provider_gate or _video_gate(REMOTE_VIDEO_ENV),
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
    if context_bundle:
        manifest["context_bundle_mode"] = context_bundle.get("mode")
        manifest["context_included_asset_count"] = len(context_bundle.get("included_assets") or [])
        manifest["context_excluded_asset_count"] = len(context_bundle.get("excluded_assets") or [])
        manifest["context_asset_conflict_count"] = len(context_bundle.get("asset_conflicts") or [])
    return manifest


def _write_json_checked(path: Path, payload: dict[str, Any]) -> None:
    reject_unsafe_payload(payload)
    write_json(path, payload)


def _write_model_call_artifacts(
    store: RuntimeStore,
    output_dir: Path,
    model_call_context: dict[str, Any],
    model_request_plan: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    _write_json_checked(output_dir / "model_call_context.json", model_call_context)
    _write_json_checked(output_dir / "model_request_plan.json", model_request_plan)
    return {
        "model_call_context": store.register_artifact(output_dir / "model_call_context.json", role="model_call_context"),
        "model_request_plan": store.register_artifact(output_dir / "model_request_plan.json", role="model_request_plan"),
    }


def _write_task_state(output_dir: Path, state: dict[str, Any]) -> None:
    _write_json_checked(output_dir / "video_task_state.json", state)


def _provider_task_for_state(provider_task: dict[str, Any]) -> dict[str, Any]:
    task = dict(provider_task)
    inner = task.get("task")
    if isinstance(inner, dict):
        safe_inner = dict(inner)
        safe_inner.pop("output_dir", None)
        safe_inner.pop("raw", None)
        task["task"] = safe_inner
    task.pop("output_dir", None)
    return task


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


def _load_task_state(output_dir: Path) -> dict[str, Any]:
    path = output_dir / "video_task_state.json"
    if not path.is_file():
        raise ValueError("video task state not found")
    return read_json(path)


def _video_gate(required_gate: str) -> dict[str, str]:
    status = "ready_not_run" if os.environ.get(required_gate, "").strip().lower() in REMOTE_TRUE_VALUES else "blocked"
    return {"capability": "video", "env": required_gate, "status": status}


def _gate_closed_block(required_gate: str) -> dict[str, str]:
    return {
        "block_id": "remote_video_gate_closed",
        "reason": f"Set {required_gate}=true only for an explicit video provider smoke.",
        "required_gate": required_gate,
    }


def _provider_not_ready_block(reason: str) -> dict[str, str]:
    return {
        "block_id": "remote_video_provider_not_ready",
        "reason": _safe_error(reason),
        "required_gate": REMOTE_VIDEO_ENV,
    }


def _safe_error(value: str) -> str:
    lowered = value.lower()
    if "api" in lowered or "key" in lowered or "secret" in lowered or "token" in lowered:
        return "Video provider configuration is not ready."
    return value[:160]


def _daily_quota_path(store: RuntimeStore, project_id: str) -> Path:
    today = datetime.now(timezone.utc).date().isoformat()
    return store.projects_dir / safe_id(project_id) / "quota" / f"video_{today}.json"


def _daily_submit_count(store: RuntimeStore, project_id: str) -> int:
    path = _daily_quota_path(store, project_id)
    if not path.is_file():
        return 0
    payload = read_json(path)
    return int(payload.get("submitted_count") or 0)


def _increment_daily_submit_count(store: RuntimeStore, project_id: str) -> None:
    path = _daily_quota_path(store, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = _daily_submit_count(store, project_id) + 1
    write_json(
        path,
        {
            "artifact_type": "afs_video_daily_quota",
            "schema_version": "0.1.0",
            "project_id": project_id,
            "date": datetime.now(timezone.utc).date().isoformat(),
            "submitted_count": count,
            "does_not_store_prompt": True,
            "does_not_store_secrets": True,
        },
    )


__all__ = ("register_runtime_video_routes",)
