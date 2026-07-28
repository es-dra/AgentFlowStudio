from __future__ import annotations

import threading
import time
import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest, load_provider_registry
from apps.api.runtime_image_assets import image_asset_file_path
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_production_graph import ProductionGraphStore
from apps.api.runtime_store import RuntimeStore, safe_id
from apps.api.runtime_video_admission import load_video_admission_manifest
from apps.api.runtime_video_candidates import candidate_file
from apps.api.runtime_video_constants import REMOTE_VIDEO_ENV
from apps.api.runtime_video_dispatch import poll_video_generation
from apps.api.runtime_video_dispatch_outbox import (
    mark_network_may_have_started,
    prepare_dispatch_outbox,
    record_provider_task,
)
from apps.api.runtime_video_gate import provider_not_ready_block, video_gate
from apps.api.runtime_video_manifest import safe_manifest, video_response, write_video_job
from apps.api.runtime_video_task_state import provider_task_for_state, write_task_state
from tools import afs_video_direct_batch_runner as direct_batch


OPERATOR_CONFIRMATION = "AFS_DIRECT_BATCH_SERVICE_PROCESS_20260728"
DIAGNOSTIC_PROMPT = "一枚温润金色棋子在深色摄影棚台面缓慢旋转，柔和暖光扫过表面纹理，稳定横向滑轨镜头，六秒，无文字。"
DIAGNOSTIC_REF_TARGET_ID = "A-PROP-01"
DIAGNOSTIC_TERMINAL_STATUSES = {
    "succeeded",
    "failed",
    "blocked",
    "needs_attention",
    "reconcile_required",
    "poll_failed",
    "cancelled",
    "cancelled_local_only",
}

_ACTIVE_BATCH_THREADS: dict[str, threading.Thread] = {}
_ACTIVE_BATCH_LOCK = threading.Lock()


class VideoDirectBatchProofRequest(BaseModel):
    operator_confirmation: str = Field(min_length=1)
    run_id: str | None = None
    shot_number: int = Field(default=2, ge=1, le=35)
    poll_interval_sec: float = Field(default=10.0, ge=1.0, le=120.0)
    max_poll_sec: int = Field(default=180, ge=30, le=1800)


class VideoDirectBatchStartRequest(BaseModel):
    operator_confirmation: str = Field(min_length=1)
    run_id: str | None = None
    concurrency: int = Field(default=0, ge=0, le=12)
    poll_interval_sec: float = Field(default=20.0, ge=5.0, le=180.0)
    max_poll_sec: int = Field(default=1200, ge=60, le=7200)
    promote_technical_pass: bool = False


class VideoDirectBatchDiagnosticRequest(BaseModel):
    operator_confirmation: str = Field(min_length=1)
    run_id: str | None = None
    step: str = Field(pattern="^(text_only|single_reference)$")
    poll_interval_sec: float = Field(default=20.0, ge=1.0, le=180.0)
    max_poll_sec: int = Field(default=0, ge=0, le=7200)


def register_runtime_video_direct_batch_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/studio/operator/projects/{project_id}/video-direct-batch/proof")
    def video_direct_batch_proof(
        project_id: str,
        body: VideoDirectBatchProofRequest,
        request: Request,
    ) -> dict[str, Any]:
        _require_local_operator(request, body.operator_confirmation)
        store.ensure_project_manifest(project_id)
        target = _target_for_shot_number(store, project_id, body.shot_number)
        run_id = _safe_run_id(body.run_id, prefix="video-direct-proof")
        ledger = direct_batch.load_batch_ledger(store, project_id, run_id)
        ledger["status"] = "proof_running"
        ledger["targets"] = [target.__dict__]
        direct_batch.save_batch_ledger(store, project_id, ledger)
        direct_batch.record_event(
            store,
            project_id,
            ledger,
            "proof_started",
            shot_id=target.shot_id,
            shot_number=target.shot_number,
        )
        try:
            manifest = direct_batch.ensure_manifest(store, project_id, run_id, target)
            manifest = direct_batch.reserve_manifest(store, project_id, run_id, manifest)
            response = direct_batch.dispatch_once(store, project_id, run_id, manifest)
            if response.get("candidate_previews"):
                manifest = direct_batch.record_candidate(
                    store,
                    project_id,
                    run_id,
                    target.shot_id,
                    response,
                )
            else:
                manifest = load_video_admission_manifest(
                    store,
                    project_id,
                    shot_id=target.shot_id,
                )
            proof = _connectivity_proof_summary(response, manifest)
            ledger["status"] = "proof_passed" if proof["connectivity_proof_passed"] else "proof_blocked"
            ledger["results"] = [proof]
            direct_batch.save_batch_ledger(store, project_id, ledger)
            direct_batch.record_event(store, project_id, ledger, "proof_finished", **proof)
            return {
                "schema_version": "afs.video_direct_batch_operator.v0.1",
                "status": ledger["status"],
                "project_id": project_id,
                "run_id": run_id,
                "shot_id": target.shot_id,
                "shot_number": target.shot_number,
                "result": proof,
                "ledger_ref": f"video_direct_batch:{safe_id(run_id)}",
            }
        except Exception as exc:  # noqa: BLE001 - operator proof must return a bounded safe blocker.
            error = {
                "shot_id": target.shot_id,
                "shot_number": target.shot_number,
                "status": "proof_error",
                "error_type": type(exc).__name__,
                "message": str(exc)[:240],
            }
            ledger["status"] = "proof_error"
            ledger["results"] = [error]
            direct_batch.save_batch_ledger(store, project_id, ledger)
            direct_batch.record_event(store, project_id, ledger, "proof_error", **error)
            return {
                "schema_version": "afs.video_direct_batch_operator.v0.1",
                "status": "proof_error",
                "project_id": project_id,
                "run_id": run_id,
                "shot_id": target.shot_id,
                "shot_number": target.shot_number,
                "result": error,
                "ledger_ref": f"video_direct_batch:{safe_id(run_id)}",
            }

    @app.post("/studio/operator/projects/{project_id}/video-direct-batch/start")
    def video_direct_batch_start(
        project_id: str,
        body: VideoDirectBatchStartRequest,
        request: Request,
    ) -> dict[str, Any]:
        _require_local_operator(request, body.operator_confirmation)
        store.ensure_project_manifest(project_id)
        run_id = _safe_run_id(body.run_id, prefix="video-direct-service")
        thread_key = f"{project_id}:{run_id}"
        already_running = False
        with _ACTIVE_BATCH_LOCK:
            _discard_finished_threads()
            existing = _ACTIVE_BATCH_THREADS.get(thread_key)
            if existing and existing.is_alive():
                already_running = True
            else:
                thread = threading.Thread(
                    target=_run_batch_worker,
                    name=f"afs-video-direct-batch-{safe_id(run_id)}",
                    kwargs={
                        "store": store,
                        "project_id": project_id,
                        "run_id": run_id,
                        "concurrency": body.concurrency,
                        "poll_interval_sec": body.poll_interval_sec,
                        "max_poll_sec": body.max_poll_sec,
                        "promote": body.promote_technical_pass,
                    },
                    daemon=True,
                )
                _ACTIVE_BATCH_THREADS[thread_key] = thread
                thread.start()
        return _batch_status_payload(
            store,
            project_id,
            run_id,
            status="already_running" if already_running else "started",
        )

    @app.post("/studio/operator/projects/{project_id}/video-direct-batch/diagnostic")
    def video_direct_batch_diagnostic(
        project_id: str,
        body: VideoDirectBatchDiagnosticRequest,
        request: Request,
    ) -> dict[str, Any]:
        _require_local_operator(request, body.operator_confirmation)
        store.ensure_project_manifest(project_id)
        run_id = _safe_run_id(body.run_id, prefix="video-direct-diagnostic")
        reference_image_paths: tuple[Path, ...] = ()
        reference_asset_id = ""
        input_mode = "text_only"
        if body.step == "single_reference":
            reference_asset_id = _approved_image_asset_for_target(
                store,
                project_id,
                DIAGNOSTIC_REF_TARGET_ID,
            )
            reference_image_paths = (image_asset_file_path(store, project_id, reference_asset_id),)
            input_mode = "reference_images"
        ledger = direct_batch.load_batch_ledger(store, project_id, run_id)
        ledger["status"] = f"diagnostic_{body.step}_running"
        direct_batch.save_batch_ledger(store, project_id, ledger)
        result = _run_provider_connectivity_diagnostic(
            store,
            project_id,
            run_id=run_id,
            step=body.step,
            prompt=DIAGNOSTIC_PROMPT,
            input_mode=input_mode,
            reference_image_paths=reference_image_paths,
            reference_asset_id=reference_asset_id,
            poll_interval_sec=body.poll_interval_sec,
            max_poll_sec=body.max_poll_sec,
        )
        result = direct_batch.safe_ledger_payload(result)
        ledger["status"] = (
            f"diagnostic_{body.step}_accepted"
            if result["connectivity_proof_passed"]
            else f"diagnostic_{body.step}_blocked"
        )
        ledger["results"] = [result]
        direct_batch.save_batch_ledger(store, project_id, ledger)
        direct_batch.record_event(store, project_id, ledger, f"diagnostic_{body.step}_finished", **result)
        return {
            "schema_version": "afs.video_direct_batch_operator.v0.1",
            "status": ledger["status"],
            "project_id": project_id,
            "run_id": run_id,
            "result": result,
            "ledger_ref": f"video_direct_batch:{safe_id(run_id)}",
        }

    @app.get("/studio/operator/projects/{project_id}/video-direct-batch/{run_id}")
    def video_direct_batch_status(
        project_id: str,
        run_id: str,
        request: Request,
    ) -> dict[str, Any]:
        _require_local_operator(request, OPERATOR_CONFIRMATION)
        return _batch_status_payload(store, project_id, _safe_run_id(run_id, prefix="video-direct-service"))


def _run_batch_worker(
    *,
    store: RuntimeStore,
    project_id: str,
    run_id: str,
    concurrency: int,
    poll_interval_sec: float,
    max_poll_sec: int,
    promote: bool,
) -> None:
    try:
        direct_batch.execute_batch(
            store,
            project_id,
            run_id,
            concurrency=direct_batch.target_concurrency(concurrency or None),
            poll_interval_sec=poll_interval_sec,
            max_poll_sec=max_poll_sec,
            promote=promote,
        )
    except Exception as exc:  # noqa: BLE001 - persist bounded operator worker failure.
        ledger = direct_batch.load_batch_ledger(store, project_id, run_id)
        ledger["status"] = "worker_error"
        ledger.setdefault("results", []).append(
            {
                "status": "worker_error",
                "error_type": type(exc).__name__,
                "message": str(exc)[:240],
            }
        )
        direct_batch.save_batch_ledger(store, project_id, ledger)


def _target_for_shot_number(
    store: RuntimeStore,
    project_id: str,
    shot_number: int,
) -> direct_batch.BatchTarget:
    for target in direct_batch.build_targets(store, project_id):
        if target.shot_number == shot_number:
            if target.skip_reason:
                raise HTTPException(
                    status_code=422,
                    detail=f"shot {shot_number} is not dispatchable: {target.skip_reason}",
                )
            if target.reference_count > 4:
                raise HTTPException(
                    status_code=422,
                    detail=f"shot {shot_number} exceeds provider reference slots",
                )
            return target
    raise HTTPException(status_code=404, detail=f"shot {shot_number} not found")


def _connectivity_proof_summary(
    response: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    item = manifest.get("item") if isinstance(manifest.get("item"), Mapping) else {}
    job = response.get("job") if isinstance(response.get("job"), Mapping) else {}
    safe = response.get("safe_manifest") if isinstance(response.get("safe_manifest"), Mapping) else {}
    provider_task_fingerprint = str(item.get("provider_task_fingerprint") or "")
    candidate = item.get("candidate") if isinstance(item.get("candidate"), Mapping) else {}
    proof_passed = bool(provider_task_fingerprint or candidate)
    blocks = [
        {
            "block_id": str(block.get("block_id") or ""),
            "reason": str(block.get("reason") or "")[:180],
            "failure_class": str(block.get("failure_class") or ""),
            "provider_http_status": int(block.get("provider_http_status") or 0),
            "provider_error_code": str(block.get("provider_error_code") or ""),
        }
        for block in safe.get("blocks", [])
        if isinstance(block, Mapping)
    ]
    return {
        "status": "connectivity_proof_passed" if proof_passed else "connectivity_proof_blocked",
        "connectivity_proof_passed": proof_passed,
        "job_id": str(job.get("job_id") or item.get("provider_job_id") or ""),
        "job_status": str(job.get("status") or response.get("status") or ""),
        "manifest_id": str(manifest.get("manifest_id") or ""),
        "manifest_hash": str(manifest.get("manifest_hash") or ""),
        "item_state": str(item.get("state") or ""),
        "network_disposition": str(item.get("network_disposition") or ""),
        "provider_dispatch_count": int(manifest.get("provider_dispatch_count") or 0),
        "has_provider_task_fingerprint": bool(provider_task_fingerprint),
        "has_candidate": bool(candidate),
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "provider_calls_started": bool(response.get("provider_calls_started")),
        "blocks": blocks,
    }


def _run_provider_connectivity_diagnostic(
    store: RuntimeStore,
    project_id: str,
    *,
    run_id: str,
    step: str,
    prompt: str,
    input_mode: str,
    reference_image_paths: tuple[Path, ...],
    reference_asset_id: str,
    poll_interval_sec: float,
    max_poll_sec: int,
) -> dict[str, Any]:
    job_id = store.new_job_id("video_generation", project_id)
    output_dir = store.run_dir(project_id, job_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    store.write_job(runtime_job(job_id, project_id, "video_generation", "dispatch_prepared"))
    manifest_id = f"video-direct-diagnostic-{safe_id(step)}-{run_id}"
    manifest_hash = hashlib.sha256(
        f"{project_id}:{run_id}:{step}:{input_mode}:{bool(reference_image_paths)}".encode("utf-8")
    ).hexdigest()
    prepare_dispatch_outbox(
        output_dir,
        project_id=project_id,
        job_id=job_id,
        manifest_id=manifest_id,
        manifest_hash=manifest_hash,
        item_id=f"diagnostic-{safe_id(step)}",
    )
    request_started = time.perf_counter()
    dispatch_request = ProviderDispatchRequest(
        prompt=prompt,
        output_dir=output_dir,
        aspect_ratio="16:9",
        candidate_count=1,
        reference_image_paths=reference_image_paths,
        subject_reference_image_path=None,
        duration_sec=6,
        resolution="720p",
        motion="稳定横移，柔和灯光下缓慢旋转。",
        input_mode=input_mode,
        input_source={
            "source_mode": input_mode,
            "diagnostic": True,
            "reference_asset_id": reference_asset_id,
        },
        duration_contract={
            "duration_sec": 6,
            "fixed_segment_duration_sec": 6,
            "segment_count": 1,
        },
        model_name_override=direct_batch.MODEL_ID,
        routing_key=f"{project_id}:diagnostic:{safe_id(step)}:{job_id}",
    )
    gate = video_gate(REMOTE_VIDEO_ENV)
    try:
        registry = load_provider_registry()
        mark_network_may_have_started(output_dir)
        provider_task = registry.submit("video", direct_batch.SERVICE_ID, dispatch_request)
        outbox = record_provider_task(output_dir, provider_task)
        safe_task = provider_task_for_state(provider_task)
        state = {
            "schema_version": "afs_video_generation_task_state.v0.1",
            "status": str((safe_task.get("task") or {}).get("status") or "submitted"),
            "provider_service_id": direct_batch.SERVICE_ID,
            "capability": "video",
            "task": safe_task,
            "input_mode": input_mode,
            "reference_image_asset_ids": [reference_asset_id] if reference_asset_id else [],
            "created_at": _utc_now(),
            "submitted_at": _utc_now(),
            "provider_raw_persisted": False,
            "request_id": f"diagnostic-{run_id}-{step}",
            "client_request_id": f"diagnostic-{run_id}-{step}",
            "video_admission": {
                "manifest_id": manifest_id,
                "manifest_hash": manifest_hash,
                "item_id": f"diagnostic-{safe_id(step)}",
                "max_dispatches": 1,
                "auto_retry": 0,
            },
        }
        write_task_state(output_dir, state)
        manifest = safe_manifest(
            project_id,
            status="submitted",
            provider_calls_started=True,
            provider_gate=gate,
            input_source={"source_mode": input_mode, "diagnostic": True},
            input_mode=input_mode,
            video_admission=state["video_admission"],
        )
        write_json(output_dir / "video_generation_safe_manifest.json", manifest)
        store.write_job(runtime_job(job_id, project_id, "video_generation", "submitted"))
        result = {
            "status": "diagnostic_accepted",
            "connectivity_proof_passed": True,
            "step": step,
            "job_id": job_id,
            "manifest_id": manifest_id,
            "input_mode": input_mode,
            "reference_asset_id": reference_asset_id,
            "provider_calls_started": True,
            "has_provider_task_fingerprint": bool(outbox.get("provider_task_fingerprint")),
            "network_disposition": str(outbox.get("network_disposition") or ""),
            "elapsed_ms": int(round((time.perf_counter() - request_started) * 1000)),
        }
        if max_poll_sec > 0:
            result["poll"] = _poll_diagnostic_job_to_terminal(
                store,
                project_id,
                job_id=job_id,
                poll_interval_sec=poll_interval_sec,
                max_poll_sec=max_poll_sec,
            )
        return result
    except (ModelGatewayError, Exception) as exc:
        try:
            mark_network_may_have_started(output_dir)
        except Exception:
            pass
        block = _safe_provider_block(exc)
        manifest = safe_manifest(
            project_id,
            status="blocked",
            provider_calls_started=True,
            provider_gate=gate,
            blocks=[block],
            input_source={"source_mode": input_mode, "diagnostic": True},
            input_mode=input_mode,
            video_admission={
                "manifest_id": manifest_id,
                "manifest_hash": manifest_hash,
                "item_id": f"diagnostic-{safe_id(step)}",
                "max_dispatches": 1,
                "auto_retry": 0,
            },
        )
        write_json(output_dir / "video_generation_safe_manifest.json", manifest)
        store.write_job(runtime_job(job_id, project_id, "video_generation", "blocked"))
        return {
            "status": "diagnostic_blocked",
            "connectivity_proof_passed": False,
            "step": step,
            "job_id": job_id,
            "manifest_id": manifest_id,
            "input_mode": input_mode,
            "reference_asset_id": reference_asset_id,
            "provider_calls_started": True,
            "has_provider_task_fingerprint": False,
            "network_disposition": "may_have_dispatched",
            "block": block,
            "elapsed_ms": int(round((time.perf_counter() - request_started) * 1000)),
        }


def _poll_diagnostic_job_to_terminal(
    store: RuntimeStore,
    project_id: str,
    *,
    job_id: str,
    poll_interval_sec: float,
    max_poll_sec: int,
) -> dict[str, Any]:
    output_dir = store.run_dir(project_id, job_id)
    deadline = time.monotonic() + max_poll_sec
    last: dict[str, Any] = {}
    while True:
        result = poll_video_generation(
            store,
            project_id,
            output_dir,
            load_registry=load_provider_registry,
            request_id=f"diagnostic-poll-{job_id}",
            client_request_id=f"diagnostic-poll-{job_id}",
        )
        job = write_video_job(store, project_id, job_id, result)
        response = video_response(store, project_id, job, result)
        status = str((response.get("job") or {}).get("status") or response.get("status") or "")
        candidates = response.get("candidate_previews") or []
        last = {
            "status": status,
            "job_id": job_id,
            "candidate_count": len(candidates),
            "candidates": [
                _diagnostic_candidate_summary(store, project_id, job_id, item)
                for item in candidates
                if isinstance(item, Mapping)
            ],
            "provider_calls_started": bool(response.get("provider_calls_started")),
            "blocks": [
                {
                    "block_id": str(block.get("block_id") or ""),
                    "reason": str(block.get("reason") or "")[:180],
                    "provider_http_status": _safe_int(block.get("provider_http_status")),
                    "provider_error_code": str(block.get("provider_error_code") or ""),
                }
                for block in ((response.get("safe_manifest") or {}).get("blocks") or [])
                if isinstance(block, Mapping)
            ],
        }
        if candidates or status in DIAGNOSTIC_TERMINAL_STATUSES:
            last["terminal"] = True
            return last
        if time.monotonic() >= deadline:
            last["terminal"] = False
            last["timeout"] = True
            return last
        time.sleep(poll_interval_sec)


def _diagnostic_candidate_summary(
    store: RuntimeStore,
    project_id: str,
    job_id: str,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_id = str(candidate.get("candidate_id") or "")
    path = candidate_file(store.run_dir(project_id, job_id), candidate_id)
    byte_count = path.stat().st_size if path and path.is_file() else int(candidate.get("byte_count") or 0)
    return {
        "candidate_id": candidate_id,
        "sha256": str(candidate.get("sha256") or ""),
        "candidate_preview_ref": f"{safe_id(job_id)}:{safe_id(candidate_id)}" if job_id and candidate_id else "",
        "byte_count": byte_count,
        "technical_qa": {
            "file_present": bool(path and path.is_file()),
            "nonzero_bytes": byte_count > 0,
        },
    }


def _safe_provider_block(exc: Exception) -> dict[str, Any]:
    raw = getattr(exc, "provider_error_summary", None)
    block = dict(provider_not_ready_block(str(exc)[:180]))
    if isinstance(raw, Mapping):
        status = _safe_int(raw.get("provider_http_status"))
        if status:
            block["provider_http_status"] = status
        for key in ("provider_error_stage", "provider_error_code", "provider_error_message"):
            text = _safe_text(raw.get(key), limit=180 if key == "provider_error_message" else 80)
            if text:
                block[key] = text
        if "provider_raw_response_stored" in raw:
            block["provider_raw_response_stored"] = False
    return block


def _safe_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def _safe_text(value: Any, *, limit: int) -> str:
    text = " ".join(str(value or "").split()).strip()
    lowered = text.lower()
    if any(
        fragment in lowered
        for fragment in (
            "api_key",
            "access_token",
            "refresh_token",
            "secret_key",
            "client_secret",
            "authorization:",
            "bearer ",
            "cookie=",
            "signed_url",
        )
    ):
        return "Video provider returned an unsafe error detail."
    return text[:limit]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _approved_image_asset_for_target(
    store: RuntimeStore,
    project_id: str,
    target_id: str,
) -> str:
    graph = ProductionGraphStore(store).load(project_id)
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), Mapping) else {}
    approved_nodes = {
        str(node_id): str((node.get("metadata") or {}).get("image_asset_id") or "")
        for node_id, node in nodes.items()
        if isinstance(node, Mapping)
        and node.get("state") == "active"
        and (node.get("metadata") or {}).get("kind") == "approved_image"
    }
    asset_ids = [
        approved_nodes[str(relation.get("to_id") or "")]
        for relation in graph.get("relations", [])
        if relation.get("relation_type") == "approved_image"
        and str(relation.get("from_id") or "") == target_id
        and str(relation.get("to_id") or "") in approved_nodes
    ]
    asset_ids = [item for item in asset_ids if item]
    if len(asset_ids) != 1:
        raise HTTPException(
            status_code=422,
            detail=f"diagnostic requires exactly one approved image for {target_id}",
        )
    return asset_ids[0]


def _batch_status_payload(
    store: RuntimeStore,
    project_id: str,
    run_id: str,
    *,
    status: str | None = None,
) -> dict[str, Any]:
    ledger = direct_batch.load_batch_ledger(store, project_id, run_id)
    thread_key = f"{project_id}:{run_id}"
    with _ACTIVE_BATCH_LOCK:
        thread = _ACTIVE_BATCH_THREADS.get(thread_key)
        thread_alive = bool(thread and thread.is_alive())
    results = ledger.get("results") if isinstance(ledger.get("results"), list) else []
    return {
        "schema_version": "afs.video_direct_batch_operator.v0.1",
        "status": status or str(ledger.get("status") or "unknown"),
        "project_id": project_id,
        "run_id": run_id,
        "thread_alive": thread_alive,
        "counts": direct_batch.count_results(
            [item for item in results if isinstance(item, Mapping)]
        ),
        "result_count": len(results),
        "event_count": len(ledger.get("events") or []),
        "provider_dispatch_count": int(ledger.get("provider_dispatch_count") or 0),
        "ledger_ref": f"video_direct_batch:{safe_id(run_id)}",
        "updated_at": str(ledger.get("updated_at") or ""),
    }


def _safe_run_id(value: str | None, *, prefix: str) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        candidate = f"{prefix}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    safe = safe_id(candidate)
    if not safe or safe != candidate:
        raise HTTPException(status_code=422, detail="run_id must be a safe identifier")
    return safe


def _require_local_operator(request: Request, confirmation: str) -> None:
    if confirmation != OPERATOR_CONFIRMATION:
        raise HTTPException(status_code=403, detail="operator confirmation is required")
    host = str((request.client.host if request.client else "") or "").lower()
    if host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(status_code=403, detail="operator route is loopback-only")


def _discard_finished_threads() -> None:
    for key, thread in list(_ACTIVE_BATCH_THREADS.items()):
        if not thread.is_alive():
            _ACTIVE_BATCH_THREADS.pop(key, None)


__all__ = ("OPERATOR_CONFIRMATION", "register_runtime_video_direct_batch_routes")
