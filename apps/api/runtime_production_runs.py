from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request

from agentflow.harness.json_io import exclusive_file_lock
from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_production_models import (
    PRODUCTION_CHECKPOINT_SCHEMA_VERSION,
    PRODUCTION_RUN_SCHEMA_VERSION,
    ProductionRunCreateRequest,
    canonical_json_digest,
    checkpoint_digest,
)
from apps.api.runtime_store import RuntimeStore


def register_runtime_production_run_routes(app: FastAPI, store: RuntimeStore, auth: RuntimeAuthStore) -> None:
    @app.post("/projects/{project_id}/production-runs")
    def create_production_run(
        project_id: str,
        body: ProductionRunCreateRequest,
        request: Request,
    ) -> dict[str, Any]:
        owner_user_id = _require_project_owner(auth, request, project_id)
        request_payload = body.model_dump(mode="json")
        request_digest = canonical_json_digest(request_payload)
        runs_dir = store.production_runs_dir(project_id)
        runs_dir.mkdir(parents=True, exist_ok=True)
        with exclusive_file_lock(store.production_run_lock_path(project_id)):
            existing = _find_creation_idempotency(store, project_id, body.idempotency_key)
            if existing:
                if str(existing.get("creation", {}).get("request_digest") or "") != request_digest:
                    raise HTTPException(status_code=409, detail="production run idempotency conflict")
                _require_run_owner(existing, owner_user_id)
                return {"production_run": existing, "idempotent_replay": True}

            run_id = body.run_id or f"production-run-{uuid4().hex[:12]}"
            try:
                conflicting_run = store.load_production_run(project_id, run_id)
            except KeyError:
                conflicting_run = None
            if conflicting_run is not None:
                raise HTTPException(status_code=409, detail="production run id already exists")

            timestamp = _now()
            run = {
                "artifact_type": "afs_runtime_production_run",
                "schema_version": PRODUCTION_RUN_SCHEMA_VERSION,
                "project_id": project_id,
                "run_id": run_id,
                "owner_user_id": owner_user_id,
                "status": "candidates_ready",
                "subject_digest": body.subject_digest,
                "candidates": [candidate.model_dump(mode="json") for candidate in body.candidates],
                "selected_revision": None,
                "creator_decisions": [],
                "quality_reviews": [],
                "exports": [],
                "lineage": [
                    {
                        "source_ref": candidate.parent_job_id,
                        "target_ref": candidate.candidate_id,
                        "relation": "job_produced_candidate",
                    }
                    for candidate in body.candidates
                ],
                "creation": {
                    "idempotency_key": body.idempotency_key,
                    "request_digest": request_digest,
                },
                "created_at": timestamp,
                "updated_at": timestamp,
                "checkpoint": {
                    "schema_version": PRODUCTION_CHECKPOINT_SCHEMA_VERSION,
                    "version": 1,
                    "previous_digest": None,
                    "state_digest": "",
                    "updated_at": timestamp,
                },
                "evidence_boundary": {
                    "runtime_persistence": True,
                    "provider_smoke": False,
                    "media_quality": False,
                    "human_acceptance": False,
                    "business_validation": False,
                },
            }
            run["checkpoint"]["state_digest"] = checkpoint_digest(run)
            store.write_production_run(project_id, run)
            return {"production_run": run, "idempotent_replay": False}

    @app.get("/projects/{project_id}/production-runs")
    def list_production_runs(project_id: str, request: Request) -> dict[str, Any]:
        owner_user_id = _require_project_owner(auth, request, project_id)
        runs = store.list_production_runs(project_id)
        for run in runs:
            _require_run_owner(run, owner_user_id)
        return {"project_id": project_id, "production_runs": runs}

    @app.get("/projects/{project_id}/production-runs/{run_id}")
    def get_production_run(project_id: str, run_id: str, request: Request) -> dict[str, Any]:
        owner_user_id = _require_project_owner(auth, request, project_id)
        try:
            run = store.load_production_run(project_id, run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="production run not found") from exc
        _require_run_owner(run, owner_user_id)
        return {"production_run": run}


def _find_creation_idempotency(store: RuntimeStore, project_id: str, idempotency_key: str) -> dict[str, Any] | None:
    for run in store.list_production_runs(project_id):
        if str(run.get("creation", {}).get("idempotency_key") or "") == idempotency_key:
            return run
    return None


def _require_project_owner(auth: RuntimeAuthStore, request: Request, project_id: str) -> str:
    if not auth.enabled():
        raise HTTPException(status_code=403, detail="authenticated production runs require runtime auth")
    user = auth.require_user(request)
    user_id = str(user.get("user_id") or "")
    if not user_id or not auth.user_can_access_project(user_id, project_id):
        raise HTTPException(status_code=403, detail="project access denied")
    return user_id


def _require_run_owner(run: dict[str, Any], owner_user_id: str) -> None:
    if not owner_user_id or str(run.get("owner_user_id") or "") != owner_user_id:
        raise HTTPException(status_code=403, detail="production run access denied")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = ("register_runtime_production_run_routes",)
