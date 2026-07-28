from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any, Mapping

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from apps.api.runtime_store import RuntimeStore, safe_id
from apps.api.runtime_video_admission import load_video_admission_manifest
from tools import afs_video_direct_batch_runner as direct_batch


OPERATOR_CONFIRMATION = "AFS_DIRECT_BATCH_SERVICE_PROCESS_20260728"

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
                "ledger_path": str(direct_batch.batch_path(store, project_id, run_id)),
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
                "ledger_path": str(direct_batch.batch_path(store, project_id, run_id)),
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
        "ledger_path": str(direct_batch.batch_path(store, project_id, run_id)),
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
