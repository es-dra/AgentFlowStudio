from __future__ import annotations

import hashlib
import os
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest, load_provider_registry
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_logging import (
    client_request_id_from_request,
    log_business_event,
    request_id_from_request,
    studio_node_id_from_request,
    studio_node_type_from_request,
    user_action_from_request,
)
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload, safe_id
from apps.api.runtime_submit_idempotency import (
    abort_submit_idempotency,
    begin_submit_idempotency,
    complete_submit_idempotency,
    submit_idempotency_error_detail,
)
from apps.api.runtime_tracing import artifact_refs, blocked_refs_from_blocks, write_run_trace


AUDIO_GATE_ENV = "AFS_ALLOW_REMOTE_AUDIO"
AUDIO_ACTION = "audio_generation"
SAFE_AUDIO_CANDIDATE_ID = "candidate_001"
SAFE_AUDIO_FORMAT = "wav"
SAFE_AUDIO_MIME = "audio/wav"
MAX_AUDIO_PROMPT_CHARS = 4000


class AudioGenerationRequest(BaseModel):
    node_id: str | None = None
    prompt_text: str = Field(min_length=1, max_length=MAX_AUDIO_PROMPT_CHARS)
    provider_service_id: str = Field(default="tts_relay", min_length=1, max_length=120)
    episode_id: str | None = Field(default=None, max_length=120)
    scene_id: str | None = Field(default=None, max_length=120)
    shot_id: str | None = Field(default=None, max_length=120)
    voice: str | None = Field(default=None, max_length=64)
    instructions: str | None = Field(default=None, max_length=1000)
    response_format: Literal["wav"] = "wav"
    max_paid_requests: int = Field(default=1, ge=1, le=1)
    cost_cap_cny: float = Field(default=5.0, gt=0, le=300)
    generated_at: str = Field(min_length=1, max_length=80)


def register_runtime_audio_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/projects/{project_id}/audio-generations")
    def audio_generation(project_id: str, request: AudioGenerationRequest, http_request: Request) -> dict[str, Any]:
        started = time.perf_counter()
        store.ensure_project_manifest(project_id)
        request_id = request_id_from_request(http_request)
        client_request_id = client_request_id_from_request(http_request)
        node_id = request.node_id or studio_node_id_from_request(http_request)
        _log_audio_event(
            "audio_generation_submit_started",
            http_request,
            project_id=project_id,
            node_id=node_id,
            provider_service_id=request.provider_service_id,
            shot_id=request.shot_id or "",
        )
        idempotency = begin_submit_idempotency(
            store,
            project_id=project_id,
            action=AUDIO_ACTION,
            request=request,
            request_id=request_id,
            client_request_id=client_request_id,
        )
        if idempotency.state == "replay":
            return idempotency.response or {}
        if idempotency.state in {"conflict", "pending"}:
            detail = submit_idempotency_error_detail(
                idempotency,
                request_id=request_id,
                client_request_id=client_request_id,
                node_id=node_id,
            )
            _log_audio_rejected(http_request, detail, elapsed_ms=_elapsed_ms(started))
            raise HTTPException(status_code=409, detail=detail)

        job_id = store.new_job_id(AUDIO_ACTION, project_id)
        output_dir = store.run_dir(project_id, job_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = _submit_audio_generation(project_id, job_id, request, output_dir)
        except ValueError as exc:
            abort_submit_idempotency(idempotency)
            detail = safe_error_detail(
                "invalid_audio_generation",
                message="音频生成请求无效，请检查项目、镜头和音频文本。",
                user_action="请调整音频生成参数后重试。",
                request_id=request_id,
                client_request_id=client_request_id,
                project_id=project_id,
                node_id=node_id,
                action=AUDIO_ACTION,
                stage="submit",
                details={"reason": str(exc), "job_id": job_id, "provider_calls_started": False},
            )
            _log_audio_rejected(http_request, detail, elapsed_ms=_elapsed_ms(started))
            raise HTTPException(status_code=422, detail=detail) from exc

        artifacts = _audio_generation_artifacts(store, output_dir)
        trace_path = write_run_trace(
            output_dir,
            project_id=project_id,
            job_id=job_id,
            action=AUDIO_ACTION,
            status=str(result["status"]),
            input_refs=[
                {"role": "node_id", "ref": request.node_id or "not_provided"},
                {"role": "episode_id", "ref": request.episode_id or "not_provided"},
                {"role": "scene_id", "ref": request.scene_id or "not_provided"},
                {"role": "shot_id", "ref": request.shot_id or "not_provided"},
                {"role": "prompt_text", "ref": "request_body.prompt_text"},
            ],
            generated_artifact_refs=artifact_refs(artifacts),
            blocked_refs=blocked_refs_from_blocks(result["safe_manifest"].get("blocks") or []),
            tester_feedback={"status": "audio_generation_created"},
            tool_gate_state={
                "remote_audio": "ready_not_run" if _audio_gate_open() else "blocked_by_gate",
                "remote_llm": "not_used",
                "remote_image": "not_used",
                "remote_video": "not_used",
                "remote_asr": "not_used",
            },
        )
        artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
        job = runtime_job(job_id, project_id, AUDIO_ACTION, str(result["status"]), artifacts=artifacts)
        job["ui_summary"] = {
            "audio_generation": {
                "status": result["status"],
                "provider_calls_started": bool(result["provider_calls_started"]),
            }
        }
        public_job = store.write_job(job)
        response = {
            "job": public_job,
            "provider_gate": result["safe_manifest"]["provider_gate"],
            "provider_calls_started": bool(result["provider_calls_started"]),
            "safe_manifest": result["safe_manifest"],
            "artifacts": artifacts,
            "candidate_previews": result["candidate_previews"],
            "call_accounting": result["safe_manifest"]["call_accounting"],
            "cost": result["safe_manifest"]["cost"],
            "writes_long_term_memory": False,
            "writes_company_kb": False,
            "non_claims": [
                "not generated-media QA",
                "not human creative acceptance",
                "not business validation",
            ],
            "request_id": request_id,
            "client_request_id": client_request_id or None,
            "project_id": project_id,
            "node_id": node_id or None,
            "action": AUDIO_ACTION,
            "status": public_job.get("status"),
            "stage": _response_stage(result),
        }
        complete_submit_idempotency(
            idempotency,
            job_id=job_id,
            response=response,
            provider_calls_started=bool(result["provider_calls_started"]),
        )
        _log_audio_event(
            "audio_generation_response_returned" if response["status"] == "succeeded" else "audio_generation_blocked",
            http_request,
            project_id=project_id,
            node_id=node_id,
            job_id=job_id,
            status=response["status"],
            provider_calls_started=response["provider_calls_started"],
            elapsed_ms=_elapsed_ms(started),
        )
        return response

    @app.get("/projects/{project_id}/audio-generations/{job_id}/candidates/{candidate_id}/audio")
    def audio_candidate(project_id: str, job_id: str, candidate_id: str) -> FileResponse:
        try:
            job = store.load_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="candidate not found") from exc
        if job.get("project_id") != project_id or job.get("action") != AUDIO_ACTION:
            raise HTTPException(status_code=404, detail="candidate not found")
        path = _candidate_file(store.run_dir(project_id, job_id), candidate_id)
        if path is None:
            raise HTTPException(status_code=404, detail="candidate not found")
        return FileResponse(path, media_type=SAFE_AUDIO_MIME, headers={"Cache-Control": "no-store"})


def _submit_audio_generation(
    project_id: str,
    job_id: str,
    request: AudioGenerationRequest,
    output_dir: Path,
) -> dict[str, Any]:
    request_plan = _request_plan(project_id, job_id, request)
    _write_json_checked(output_dir / "audio_generation_request_plan.json", request_plan)
    provider_calls_started = False
    try:
        registry = load_provider_registry()
        dispatch_request = ProviderDispatchRequest(
            prompt=request.prompt_text,
            output_dir=output_dir,
            task_type=AUDIO_ACTION,
            timeout_sec=45.0,
            response_format=request.response_format,
            voice=request.voice,
            instructions=request.instructions,
        )
        manifest = registry.dispatch("audio", request.provider_service_id, dispatch_request)
        provider_calls_started = bool(manifest.get("provider_calls_started"))
        output = _safe_output_from_manifest(project_id, job_id, output_dir, manifest)
        status = "succeeded"
        safe_manifest = _safe_manifest(
            project_id,
            job_id,
            request,
            status=status,
            provider_calls_started=provider_calls_started,
            outputs=[output],
            provider_result=manifest,
        )
        candidate_previews = [_candidate_preview(project_id, job_id, output)]
    except (ModelConfigError, ModelGatewayError, TimeoutError) as exc:
        provider_calls_started = _provider_call_may_have_started(exc)
        status = "failed" if provider_calls_started else "blocked"
        safe_manifest = _safe_manifest(
            project_id,
            job_id,
            request,
            status=status,
            provider_calls_started=provider_calls_started,
            blocks=[_provider_block(exc, provider_calls_started=provider_calls_started)],
        )
        candidate_previews = []
    _write_json_checked(output_dir / "audio_generation_safe_manifest.json", safe_manifest)
    return {
        "status": status,
        "provider_calls_started": provider_calls_started,
        "safe_manifest": safe_manifest,
        "candidate_previews": candidate_previews,
    }


def _request_plan(project_id: str, job_id: str, request: AudioGenerationRequest) -> dict[str, Any]:
    prompt_bytes = request.prompt_text.encode("utf-8")
    return {
        "artifact_type": "afs_audio_generation_request_plan",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "job_id": job_id,
        "provider_service_id": safe_id(request.provider_service_id),
        "capability": "audio",
        "scope": _scope(request),
        "prompt_sha256": hashlib.sha256(prompt_bytes).hexdigest(),
        "prompt_char_count": len(request.prompt_text),
        "response_format": request.response_format,
        "max_paid_requests": request.max_paid_requests,
        "cost_cap_cny": request.cost_cap_cny,
        "provider_payload_persisted": False,
        "does_not_store_private_asset_bytes": True,
    }


def _safe_manifest(
    project_id: str,
    job_id: str,
    request: AudioGenerationRequest,
    *,
    status: str,
    provider_calls_started: bool,
    outputs: list[dict[str, Any]] | None = None,
    blocks: list[dict[str, Any]] | None = None,
    provider_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    provider_cost = provider_result.get("cost") if isinstance(provider_result, dict) and isinstance(provider_result.get("cost"), dict) else {}
    first_output = outputs[0] if outputs else {}
    audio_normalization = (
        first_output.get("audio_normalization")
        if isinstance(first_output, dict) and isinstance(first_output.get("audio_normalization"), dict)
        else None
    )
    actual_calls = 1 if provider_calls_started else 0
    manifest = {
        "artifact_type": "afs_audio_generation_safe_manifest",
        "schema_version": "0.1.0",
        "status": status,
        "project_id": project_id,
        "job_id": job_id,
        "capability": "audio",
        "provider_service_id": safe_id(request.provider_service_id),
        "provider_gate": _provider_gate(),
        "provider_calls_started": provider_calls_started,
        "call_accounting": {
            "planned_calls": 1,
            "actual_calls": actual_calls,
            "retry_count": 0,
            "max_paid_requests": request.max_paid_requests,
            "double_dispatch_detected": actual_calls > request.max_paid_requests,
        },
        "cost": {
            "cap_cny": request.cost_cap_cny,
            "estimated_max_cny": request.cost_cap_cny,
            "actual_cost_status": str(provider_cost.get("actual_cost_status") or "not_applicable"),
            "receipt_status": str(provider_cost.get("receipt_status") or "not_applicable"),
        },
        "provenance": {
            "scope": _scope(request),
            "prompt_sha256": hashlib.sha256(request.prompt_text.encode("utf-8")).hexdigest(),
            "model": str((provider_result or {}).get("model") or "configured_provider_model"),
            "voice": str((provider_result or {}).get("voice") or request.voice or "configured_provider_voice"),
            "provider_returned_format": str(first_output.get("provider_audio_format") or "unknown") if isinstance(first_output, dict) else "unknown",
            "audio_normalization": audio_normalization,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "outputs": outputs or [],
        "blocks": blocks or [],
        "media_bytes_returned_by_api": False,
        "provider_raw_response_stored": False,
        "provider_urls_persisted": False,
        "credentialed_urls_persisted": False,
        "private_paths_returned_by_api": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }
    return manifest


def _safe_output_from_manifest(
    project_id: str,
    job_id: str,
    output_dir: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    outputs = manifest.get("outputs") if isinstance(manifest.get("outputs"), list) else []
    first = outputs[0] if outputs and isinstance(outputs[0], dict) else {}
    candidate_id = str(first.get("candidate_id") or SAFE_AUDIO_CANDIDATE_ID)
    path = _candidate_file(output_dir, candidate_id)
    if path is None:
        raise ModelGatewayError("TTS provider output is unavailable")
    duration_sec = _wav_duration_sec(path)
    if duration_sec <= 0:
        raise ModelGatewayError("TTS provider returned invalid WAV audio")
    return {
        "candidate_id": candidate_id,
        "audio_url": _candidate_url(project_id, job_id, candidate_id),
        "mime_type": str(first.get("mime_type") or SAFE_AUDIO_MIME),
        "byte_count": int(first.get("byte_count") or path.stat().st_size),
        "sha256": str(first.get("sha256") or _sha256(path)),
        "duration_sec": duration_sec,
        "provider_audio_format": str(first.get("provider_audio_format") or "unknown"),
        "audio_normalization": first.get("audio_normalization") if isinstance(first.get("audio_normalization"), dict) else None,
        "storage": "runtime_managed_project_artifact",
        "provider_url_persisted": False,
    }


def _candidate_preview(project_id: str, job_id: str, output: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": output["candidate_id"],
        "audio_url": _candidate_url(project_id, job_id, str(output["candidate_id"])),
        "mime_type": output["mime_type"],
        "byte_count": output["byte_count"],
        "sha256": output["sha256"],
        "duration_sec": output["duration_sec"],
        "provider_audio_format": output.get("provider_audio_format", "unknown"),
        "audio_normalization": output.get("audio_normalization"),
    }


def _candidate_file(output_dir: Path, candidate_id: str) -> Path | None:
    if candidate_id != SAFE_AUDIO_CANDIDATE_ID:
        return None
    path = (output_dir / "audio_candidates" / f"{candidate_id}.{SAFE_AUDIO_FORMAT}").resolve()
    try:
        path.relative_to(output_dir.resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


def _candidate_url(project_id: str, job_id: str, candidate_id: str) -> str:
    return f"/projects/{safe_id(project_id)}/audio-generations/{safe_id(job_id)}/candidates/{safe_id(candidate_id)}/audio"


def _audio_generation_artifacts(store: RuntimeStore, output_dir: Path) -> dict[str, Any]:
    return {
        "audio_generation_request_plan": store.register_artifact(
            output_dir / "audio_generation_request_plan.json",
            role="audio_generation_request_plan",
        ),
        "audio_generation_safe_manifest": store.register_artifact(
            output_dir / "audio_generation_safe_manifest.json",
            role="audio_generation_safe_manifest",
        ),
    }


def _provider_block(error: Exception, *, provider_calls_started: bool) -> dict[str, Any]:
    return {
        "block_id": "audio_provider_dispatch_failed" if provider_calls_started else "audio_provider_not_ready",
        "reason": _safe_provider_error(error),
        "provider_calls_started": provider_calls_started,
        "required_gate": AUDIO_GATE_ENV,
    }


def _provider_gate() -> dict[str, Any]:
    return {
        "capability": "audio",
        "required_gate": AUDIO_GATE_ENV,
        "status": "ready_not_run" if _audio_gate_open() else "blocked",
    }


def _audio_gate_open() -> bool:
    return os.environ.get(AUDIO_GATE_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def _provider_call_may_have_started(error: Exception) -> bool:
    text = str(error).lower()
    before_call_markers = (
        "gate is closed",
        "credential is not configured",
        "provider config path is required",
        "provider service not found",
        "base_url is not configured",
        "unsupported tts",
        "prompt_char_limit",
    )
    return not any(marker in text for marker in before_call_markers)


def _safe_provider_error(error: Exception) -> str:
    text = str(error)
    lowered = text.lower()
    if any(marker in lowered for marker in ("api", "key", "secret", "token", "authorization", "bearer")):
        return "Provider configuration or request was not accepted."
    return text[:160]


def _scope(request: AudioGenerationRequest) -> dict[str, str]:
    return {
        "episode_id": safe_id(request.episode_id or "not_provided"),
        "scene_id": safe_id(request.scene_id or "not_provided"),
        "shot_id": safe_id(request.shot_id or "not_provided"),
    }


def _response_stage(result: dict[str, Any]) -> str:
    status = str(result.get("status") or "")
    if status == "succeeded":
        return "completed"
    if status == "blocked":
        return "provider_gate"
    if status == "failed":
        return "provider_dispatch"
    return status or "unknown"


def _wav_duration_sec(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate()
            return round(frames / float(rate), 3) if rate else 0.0
    except (wave.Error, OSError, EOFError):
        return 0.0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json_checked(path: Path, payload: dict[str, Any]) -> None:
    reject_unsafe_payload(payload)
    write_json(path, payload)


def _log_audio_event(event_type: str, http_request: Request, **fields: Any) -> None:
    log_business_event(
        event_type,
        request_id=request_id_from_request(http_request),
        client_request_id=client_request_id_from_request(http_request),
        user_action=user_action_from_request(http_request),
        studio_node_id=str(fields.pop("node_id", "") or studio_node_id_from_request(http_request)),
        studio_node_type=studio_node_type_from_request(http_request),
        project_id=str(fields.pop("project_id", "") or ""),
        **fields,
        file_log_domain="audio",
        file_log_event=event_type.removeprefix("audio_generation_"),
        file_log_level="INFO",
    )


def _log_audio_rejected(http_request: Request, detail: dict[str, Any], *, elapsed_ms: float) -> None:
    details = detail.get("details") if isinstance(detail.get("details"), dict) else {}
    log_business_event(
        "audio_generation_rejected",
        request_id=detail.get("request_id") or request_id_from_request(http_request),
        client_request_id=detail.get("client_request_id") or client_request_id_from_request(http_request),
        user_action=user_action_from_request(http_request),
        studio_node_id=detail.get("node_id") or studio_node_id_from_request(http_request),
        studio_node_type=studio_node_type_from_request(http_request),
        project_id=detail.get("project_id"),
        action=detail.get("action"),
        stage=detail.get("stage"),
        error=detail.get("error"),
        retryable=detail.get("retryable"),
        elapsed_ms=elapsed_ms,
        **details,
        file_log_domain="audio",
        file_log_event="rejected",
        file_log_level="ERROR",
    )


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


__all__ = ("AudioGenerationRequest", "register_runtime_audio_routes")
