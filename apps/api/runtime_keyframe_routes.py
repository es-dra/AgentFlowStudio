from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from agentflow_studio.model_gateway.image_utils import image_dimensions
from apps.api.runtime_artifacts import keyframe_generation_artifacts
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_flow import build_flow_summary
from apps.api.runtime_generated_image_assets import register_generated_image_asset
from apps.api.runtime_generation_preflight import (
    keyframe_generation_preflight,
    preflight_token_matches,
    provider_submit_preflight_requirement,
)
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_keyframe_async import poll_keyframe_generation
from apps.api.runtime_keyframe_background import submit_background_sync_keyframe_generation
from apps.api.runtime_keyframes import KEYFRAME_NON_CLAIMS, build_keyframe_generation, keyframe_sync_background_plan
from apps.api.runtime_logging import (
    client_request_id_from_request,
    log_business_event,
    request_id_from_request,
    studio_node_id_from_request,
    studio_node_type_from_request,
    user_action_from_request,
)
from apps.api.runtime_models import KeyframeGenerationRequest, KeyframeGenerationResponse
from apps.api.runtime_recovery_contract import runtime_recovery_envelope
from apps.api.runtime_store import safe_id
from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_submit_idempotency import (
    abort_submit_idempotency,
    begin_submit_idempotency,
    complete_submit_idempotency,
    submit_idempotency_error_detail,
)
from apps.api.runtime_tracing import artifact_refs, blocked_refs_from_blocks, write_run_trace


SAFE_CANDIDATE_ID = re.compile(r"^candidate_\d{3}$")
IMAGE_SUFFIX_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def register_runtime_keyframe_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/projects/{project_id}/keyframe-generations/preflight")
    def keyframe_generation_preflight_route(project_id: str, request: KeyframeGenerationRequest, http_request: Request) -> dict[str, Any]:
        started = time.perf_counter()
        store.ensure_project_manifest(project_id)
        node_id = _node_id(http_request, request)
        _log_keyframe_event(
            "keyframe_generation_preflight_started",
            http_request,
            project_id=project_id,
            node_id=node_id,
            provider_service_id=request.provider_service_id,
            aspect_ratio=request.aspect_ratio,
            candidate_count=request.candidate_count,
        )
        try:
            result = keyframe_generation_preflight(store, project_id, request)
            _log_keyframe_event(
                "keyframe_generation_preflight_completed",
                http_request,
                project_id=project_id,
                node_id=node_id,
                included_asset_count=len(result.get("included_assets") or []),
                excluded_asset_count=len(result.get("excluded_assets") or []),
                reference_image_count=len(result.get("reference_image_channel") or []),
                elapsed_ms=_elapsed_ms(started),
            )
            return result
        except ValueError as exc:
            detail = safe_error_detail(
                "invalid_keyframe_generation",
                request_id=request_id_from_request(http_request),
                client_request_id=client_request_id_from_request(http_request),
                project_id=project_id,
                node_id=node_id,
                action="keyframe_generation_preflight",
                stage="preflight",
                details={"reason": str(exc)},
            )
            _log_keyframe_rejected(http_request, detail, elapsed_ms=_elapsed_ms(started))
            raise HTTPException(status_code=422, detail=detail) from exc

    @app.post(
        "/projects/{project_id}/keyframe-generations",
        response_model=KeyframeGenerationResponse,
        response_model_exclude_unset=True,
    )
    def keyframe_generation(project_id: str, request: KeyframeGenerationRequest, http_request: Request) -> dict[str, Any]:
        started = time.perf_counter()
        store.ensure_project_manifest(project_id)
        request_id = request_id_from_request(http_request)
        client_request_id = client_request_id_from_request(http_request)
        node_id = _node_id(http_request, request)
        _log_keyframe_event(
            "keyframe_generation_submit_started",
            http_request,
            project_id=project_id,
            node_id=node_id,
            provider_service_id=request.provider_service_id,
            aspect_ratio=request.aspect_ratio,
            candidate_count=request.candidate_count,
            asset_ref_count=len(request.asset_refs or []),
            has_preflight_token=bool(request.preflight_token),
        )
        preflight_requirement = provider_submit_preflight_requirement("keyframe", request)
        if preflight_requirement["required"] and not request.preflight_token:
            detail = safe_error_detail(
                "missing_preflight",
                detail_code="preflight_required",
                request_id=request_id,
                client_request_id=client_request_id,
                project_id=project_id,
                node_id=node_id,
                action="keyframe_generation",
                stage="preflight_required",
                status="blocked",
                retryable=True,
                details={
                    "provider_calls_started": False,
                    "required_gate": preflight_requirement["required_gate"],
                },
            )
            _log_keyframe_rejected(http_request, detail, status_code=428, elapsed_ms=_elapsed_ms(started))
            raise HTTPException(status_code=428, detail=detail)
        if request.preflight_token:
            try:
                expected_preflight = keyframe_generation_preflight(store, project_id, request)
            except ValueError as exc:
                detail = safe_error_detail(
                    "invalid_keyframe_generation",
                    request_id=request_id,
                    client_request_id=client_request_id,
                    project_id=project_id,
                    node_id=node_id,
                    action="keyframe_generation",
                    stage="preflight",
                    details={"reason": str(exc)},
                )
                _log_keyframe_rejected(http_request, detail, elapsed_ms=_elapsed_ms(started))
                raise HTTPException(status_code=422, detail=detail) from exc
            if not preflight_token_matches(expected_preflight, request.preflight_token):
                detail = safe_error_detail(
                    "stale_preflight",
                    request_id=request_id,
                    client_request_id=client_request_id,
                    project_id=project_id,
                    node_id=node_id,
                    action="keyframe_generation",
                    stage="preflight_token",
                    retryable=True,
                    details={"provider_calls_started": False},
                )
                _log_keyframe_rejected(http_request, detail, status_code=409, elapsed_ms=_elapsed_ms(started))
                raise HTTPException(status_code=409, detail=detail)
        idempotency = begin_submit_idempotency(
            store,
            project_id=project_id,
            action="keyframe_generation",
            request=request,
            request_id=request_id,
            client_request_id=client_request_id,
        )
        if idempotency.state == "replay":
            return _rebind_replay_candidate_authority(
                store,
                project_id,
                source_node_id=request.node_id,
                response=idempotency.response or {},
            )
        if idempotency.state in {"conflict", "pending"}:
            detail = submit_idempotency_error_detail(
                idempotency,
                request_id=request_id,
                client_request_id=client_request_id,
                node_id=node_id,
            )
            _log_keyframe_rejected(http_request, detail, status_code=409, elapsed_ms=_elapsed_ms(started))
            raise HTTPException(status_code=409, detail=detail)
        job_id = store.new_job_id("keyframe_generation", project_id)
        output_dir = store.run_dir(project_id, job_id)
        try:
            background_plan = keyframe_sync_background_plan(request)
            if background_plan.get("enabled"):
                service_id = str(background_plan.get("provider_service_id") or request.provider_service_id)
                background_request = request.model_copy(update={"provider_service_id": service_id})
                result = submit_background_sync_keyframe_generation(
                    store,
                    project_id,
                    background_request,
                    output_dir,
                    provider_gate=dict(background_plan.get("provider_gate") or {}),
                    request_id=request_id,
                    client_request_id=client_request_id,
                )
            else:
                result = build_keyframe_generation(
                    store,
                    project_id,
                    request,
                    output_dir,
                    request_id=request_id,
                    client_request_id=client_request_id,
                )
            artifacts = keyframe_generation_artifacts(store, output_dir)
            safe_manifest = dict(result["safe_manifest"])
            status = str(result["status"])
            trace_path = write_run_trace(
                output_dir,
                project_id=project_id,
                job_id=job_id,
                action="keyframe_generation",
                status=status,
                input_refs=[
                    {"role": "node_id", "ref": request.node_id or "not_provided"},
                    {"role": "prompt_text", "ref": "request_body.prompt_text"},
                    {"role": "target_platform", "ref": request.target_platform},
                    {"role": "aspect_ratio", "ref": request.aspect_ratio},
                    {"role": "candidate_count", "ref": str(request.candidate_count)},
                    {"role": "seed", "ref": str(request.seed) if request.seed is not None else "not_provided"},
                ],
                generated_artifact_refs=artifact_refs(artifacts),
                blocked_refs=blocked_refs_from_blocks(safe_manifest.get("blocks", [])),
                tester_feedback={
                    "status": "keyframe_request_created",
                    "provider_policy": "image_gate_required",
                },
                tool_gate_state=dict(result["tool_gate_state"]),
            )
        except ValueError as exc:
            detail = safe_error_detail(
                "invalid_keyframe_generation",
                request_id=request_id,
                client_request_id=client_request_id,
                project_id=project_id,
                node_id=node_id,
                action="keyframe_generation",
                stage="submit",
                details={"reason": str(exc), "job_id": job_id},
            )
            abort_submit_idempotency(idempotency)
            _log_keyframe_rejected(http_request, detail, elapsed_ms=_elapsed_ms(started))
            raise HTTPException(status_code=422, detail=detail) from exc
        artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
        job = runtime_job(job_id, project_id, "keyframe_generation", status, artifacts=artifacts)
        if result.get("progress"):
            job["progress"].update(result["progress"])
        job["ui_summary"] = {
            "provider_gate": {
                "status": safe_manifest.get("status", status),
                "provider_calls_started": result["provider_calls_started"],
                "blockers": safe_manifest.get("blocks") or [],
            }
        }
        public_job = store.write_job(job)
        candidate_records = _candidate_records(output_dir, result.get("provider_outputs") or [])
        candidate_previews = _candidate_previews(project_id, job_id, candidate_records)
        reusable_image_assets = _reusable_image_assets(
            store,
            project_id,
            source_node_id=request.node_id,
            job_id=job_id,
            records=candidate_records,
        )
        runtime_recovery = runtime_recovery_envelope(
            project_id=project_id,
            job_id=job_id,
            capability="image_keyframe",
            status=status,
            requested_count=request.candidate_count,
            output_count=len(candidate_previews),
            blocks=safe_manifest.get("blocks") or [],
            provider_gate=result["provider_gate"],
            provider_calls_started=bool(result["provider_calls_started"]),
            retry_count=int(safe_manifest.get("retry_count") or 0),
            artifacts=artifacts,
            candidate_previews=candidate_previews,
            reusable_assets=reusable_image_assets,
            stage=str(safe_manifest.get("stage") or ""),
            non_claims=KEYFRAME_NON_CLAIMS,
        )
        _log_keyframe_event(
            "keyframe_generation_response_returned" if status not in {"blocked", "failed"} else "keyframe_generation_blocked",
            http_request,
            project_id=project_id,
            node_id=node_id,
            job_id=job_id,
            status=status,
            provider_calls_started=result.get("provider_calls_started"),
            output_count=len(result.get("provider_outputs") or []),
            block_count=len(safe_manifest.get("blocks") or []),
            elapsed_ms=_elapsed_ms(started),
        )
        response_payload = {
            "job": public_job,
            "provider_gate": result["provider_gate"],
            "provider_calls_started": result["provider_calls_started"],
            "writes_long_term_memory": False,
            "writes_company_kb": False,
            "safe_manifest": safe_manifest,
            "context_bundle": result.get("context_bundle"),
            "generation_bridge": result.get("generation_bridge"),
            "model_call_context_id": result["model_call_context"]["context_id"],
            "artifacts": artifacts,
            "candidate_previews": candidate_previews,
            "reusable_image_assets": reusable_image_assets,
            "runtime_recovery": runtime_recovery,
            "flow": build_flow_summary(store, project_id),
            "non_claims": KEYFRAME_NON_CLAIMS,
        }
        complete_submit_idempotency(
            idempotency,
            job_id=job_id,
            response=response_payload,
            provider_calls_started=bool(result["provider_calls_started"]),
        )
        return response_payload

    @app.post(
        "/projects/{project_id}/keyframe-generations/{job_id}/poll",
        response_model=KeyframeGenerationResponse,
        response_model_exclude_unset=True,
    )
    def poll_keyframe_generation_route(project_id: str, job_id: str, http_request: Request) -> dict[str, Any]:
        started = time.perf_counter()
        request_id = request_id_from_request(http_request)
        client_request_id = client_request_id_from_request(http_request)
        _log_keyframe_event(
            "keyframe_generation_poll_started",
            http_request,
            project_id=project_id,
            job_id=job_id,
        )
        try:
            existing = store.load_job(job_id)
        except KeyError as exc:
            _log_keyframe_event(
                "keyframe_generation_rejected",
                http_request,
                project_id=project_id,
                job_id=job_id,
                status_code=404,
                error="job_not_found",
                stage="poll_load_job",
                elapsed_ms=_elapsed_ms(started),
            )
            raise HTTPException(status_code=404, detail="job not found") from exc
        if existing.get("project_id") != project_id or existing.get("action") != "keyframe_generation":
            _log_keyframe_event(
                "keyframe_generation_rejected",
                http_request,
                project_id=project_id,
                job_id=job_id,
                status_code=404,
                error="job_not_found",
                stage="poll_job_scope",
                elapsed_ms=_elapsed_ms(started),
            )
            raise HTTPException(status_code=404, detail="job not found")
        output_dir = store.run_dir(project_id, job_id)
        try:
            result = poll_keyframe_generation(
                store,
                project_id,
                output_dir,
                request_id=request_id,
                client_request_id=client_request_id,
            )
        except ValueError as exc:
            detail = safe_error_detail(
                "invalid_keyframe_generation",
                request_id=request_id,
                client_request_id=client_request_id,
                project_id=project_id,
                action="keyframe_generation_poll",
                stage="poll",
                retryable=True,
                details={"reason": str(exc), "job_id": job_id},
            )
            _log_keyframe_rejected(http_request, detail, elapsed_ms=_elapsed_ms(started))
            raise HTTPException(status_code=422, detail=detail) from exc
        artifacts = keyframe_generation_artifacts(store, output_dir)
        safe_manifest = dict(result["safe_manifest"])
        status = str(result["status"])
        job = runtime_job(job_id, project_id, "keyframe_generation", status, artifacts=artifacts)
        if result.get("progress"):
            job["progress"].update(result["progress"])
        job["ui_summary"] = {
            "provider_gate": {
                "status": safe_manifest.get("status", status),
                "provider_calls_started": result["provider_calls_started"],
                "blockers": safe_manifest.get("blocks") or [],
            }
        }
        public_job = store.write_job(job)
        provider_outputs = result.get("provider_outputs") or []
        candidate_records = _candidate_records(output_dir, provider_outputs)
        candidate_previews = _candidate_previews(project_id, job_id, candidate_records)
        reusable_image_assets = _reusable_image_assets(
            store,
            project_id,
            source_node_id=safe_manifest.get("node_id"),
            job_id=job_id,
            records=candidate_records,
        )
        requested_count = int((safe_manifest.get("batch_summary") or {}).get("requested_count") or len(provider_outputs) or 1)
        runtime_recovery = runtime_recovery_envelope(
            project_id=project_id,
            job_id=job_id,
            capability="image_keyframe",
            status=status,
            requested_count=requested_count,
            output_count=len(candidate_previews),
            blocks=safe_manifest.get("blocks") or [],
            provider_gate=result["provider_gate"],
            provider_calls_started=bool(result["provider_calls_started"]),
            retry_count=int(safe_manifest.get("retry_count") or 0),
            artifacts=artifacts,
            candidate_previews=candidate_previews,
            reusable_assets=reusable_image_assets,
            stage=str(safe_manifest.get("stage") or ""),
            non_claims=KEYFRAME_NON_CLAIMS,
        )
        _log_keyframe_event(
            "keyframe_generation_poll_completed",
            http_request,
            project_id=project_id,
            job_id=job_id,
            status=status,
            provider_calls_started=result.get("provider_calls_started"),
            output_count=len(provider_outputs),
            block_count=len(safe_manifest.get("blocks") or []),
            elapsed_ms=_elapsed_ms(started),
        )
        return {
            "job": public_job,
            "provider_gate": result["provider_gate"],
            "provider_calls_started": result["provider_calls_started"],
            "writes_long_term_memory": False,
            "writes_company_kb": False,
            "safe_manifest": safe_manifest,
            "context_bundle": result.get("context_bundle"),
            "model_call_context_id": (result.get("model_call_context") or {}).get("context_id"),
            "artifacts": artifacts,
            "candidate_previews": candidate_previews,
            "reusable_image_assets": reusable_image_assets,
            "runtime_recovery": runtime_recovery,
            "flow": build_flow_summary(store, project_id),
            "non_claims": KEYFRAME_NON_CLAIMS,
        }

    @app.get("/projects/{project_id}/keyframe-generations/{job_id}/candidates/{candidate_id}/preview")
    def keyframe_candidate_preview(project_id: str, job_id: str, candidate_id: str) -> FileResponse:
        try:
            job = store.load_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="job not found") from exc
        if job.get("project_id") != project_id or job.get("action") != "keyframe_generation":
            raise HTTPException(status_code=404, detail="candidate not found")
        if not SAFE_CANDIDATE_ID.match(candidate_id):
            raise HTTPException(status_code=404, detail="candidate not found")
        path = _candidate_file(store.run_dir(project_id, job_id), candidate_id)
        if path is None:
            raise HTTPException(status_code=404, detail="candidate not found")
        return FileResponse(
            path,
            media_type=IMAGE_SUFFIX_TYPES[path.suffix.lower()],
            headers={"Cache-Control": "no-store"},
        )


def _candidate_records(output_dir: Path, outputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in outputs:
        status = str(item.get("status") or "succeeded").strip().lower().replace("-", "_")
        if status not in {"succeeded", "success", "completed"}:
            continue
        candidate_id = item.get("candidate_id")
        if not isinstance(candidate_id, str) or not SAFE_CANDIDATE_ID.fullmatch(candidate_id):
            continue
        path = _candidate_file(output_dir, candidate_id)
        if path is None:
            continue
        image_bytes = path.read_bytes()
        dimensions = image_dimensions(image_bytes)
        if not dimensions:
            continue
        records.append(
            {
                "candidate_id": candidate_id,
                "path": path,
                "status": "succeeded",
                "byte_count": len(image_bytes),
                "sha256": hashlib.sha256(image_bytes).hexdigest(),
                "width": dimensions["width"],
                "height": dimensions["height"],
                "aspect_ratio": dimensions["aspect_ratio"],
            }
        )
    return records


def _rebind_replay_candidate_authority(
    store: RuntimeStore,
    project_id: str,
    *,
    source_node_id: str | None,
    response: dict[str, Any],
) -> dict[str, Any]:
    payload = dict(response)
    job = payload.get("job") if isinstance(payload.get("job"), dict) else {}
    job_id = str(job.get("job_id") or "")
    candidate_ids: list[str] = []
    for collection, field in (
        (payload.get("candidate_previews"), "candidate_id"),
        (payload.get("reusable_image_assets"), "source_candidate_id"),
    ):
        if not isinstance(collection, list):
            continue
        for item in collection:
            candidate_id = item.get(field) if isinstance(item, dict) else None
            if isinstance(candidate_id, str) and candidate_id not in candidate_ids:
                candidate_ids.append(candidate_id)
    records = _candidate_records(
        store.run_dir(project_id, job_id),
        [{"candidate_id": candidate_id, "status": "succeeded"} for candidate_id in candidate_ids],
    )
    payload["candidate_previews"] = _candidate_previews(project_id, job_id, records)
    payload["reusable_image_assets"] = _reusable_image_assets(
        store,
        project_id,
        source_node_id=source_node_id,
        job_id=job_id,
        records=records,
    )
    return payload


def _candidate_previews(project_id: str, job_id: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previews: list[dict[str, Any]] = []
    for item in records:
        candidate_id = item["candidate_id"]
        previews.append(
            {
                "candidate_id": candidate_id,
                "preview_url": (
                    f"/projects/{safe_id(project_id)}/keyframe-generations/"
                    f"{safe_id(job_id)}/candidates/{candidate_id}/preview"
                ),
                "byte_count": item.get("byte_count"),
                "sha256": item.get("sha256"),
                "width": item.get("width"),
                "height": item.get("height"),
                "aspect_ratio": item.get("aspect_ratio"),
            }
        )
    return previews


def _reusable_image_assets(
    store: RuntimeStore,
    project_id: str,
    *,
    source_node_id: str | None,
    job_id: str,
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for item in records:
        candidate_id = item["candidate_id"]
        try:
            registered = register_generated_image_asset(
                store,
                project_id,
                source_node_id=source_node_id,
                source_job_id=job_id,
                source_candidate_id=candidate_id,
                image_path=item["path"],
                source_candidate_digest=item["sha256"],
                source_candidate_status=item["status"],
            )
        except ValueError:
            continue
        assets.append(registered["asset"])
    return assets


def _candidate_file(output_dir: Path, candidate_id: str) -> Path | None:
    image_dir = (output_dir / "image_candidates").resolve()
    root = output_dir.resolve()
    try:
        image_dir.relative_to(root)
    except ValueError:
        return None
    for suffix in IMAGE_SUFFIX_TYPES:
        path = (image_dir / f"{candidate_id}{suffix}").resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if path.exists() and path.is_file():
            return path
    return None


def _node_id(http_request: Request, request: KeyframeGenerationRequest) -> str:
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


def _log_keyframe_event(event_type: str, http_request: Request, **fields: Any) -> None:
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


def _log_keyframe_rejected(
    http_request: Request,
    detail: dict[str, Any],
    *,
    status_code: int = 422,
    elapsed_ms: float | None = None,
) -> None:
    details = detail.get("details") if isinstance(detail.get("details"), dict) else {}
    log_business_event(
        "keyframe_generation_rejected",
        request_id=detail.get("request_id") or request_id_from_request(http_request),
        client_request_id=detail.get("client_request_id") or client_request_id_from_request(http_request),
        user_action=user_action_from_request(http_request),
        project_id=detail.get("project_id"),
        node_id=detail.get("node_id") or studio_node_id_from_request(http_request),
        action=detail.get("action"),
        stage=detail.get("stage"),
        status_code=status_code,
        error=detail.get("error"),
        message=detail.get("message"),
        retryable=detail.get("retryable"),
        elapsed_ms=elapsed_ms,
        **details,
        file_log_domain="keyframe",
        file_log_event="rejected",
        file_log_level="ERROR",
    )


def _file_log_mapping(event_type: str) -> tuple[str, str, str]:
    mapping = {
        "keyframe_generation_preflight_started": ("keyframe", "preflight_start", "INFO"),
        "keyframe_generation_preflight_completed": ("keyframe", "preflight_ok", "INFO"),
        "keyframe_generation_submit_started": ("keyframe", "submit_request", "INFO"),
        "keyframe_generation_response_returned": ("keyframe", "response", "INFO"),
        "keyframe_generation_blocked": ("keyframe", "blocked", "WARNING"),
        "keyframe_generation_poll_started": ("keyframe", "poll_request", "INFO"),
        "keyframe_generation_poll_completed": ("keyframe", "poll_response", "INFO"),
        "keyframe_generation_rejected": ("keyframe", "rejected", "ERROR"),
    }
    return mapping.get(event_type, ("keyframe", event_type.removeprefix("keyframe_generation_"), "INFO"))


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


__all__ = ("register_runtime_keyframe_routes",)
