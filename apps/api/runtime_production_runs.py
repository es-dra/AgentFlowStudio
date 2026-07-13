from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request

from agentflow.harness.json_io import exclusive_file_lock, write_json
from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_production_models import (
    PRODUCTION_CHECKPOINT_SCHEMA_VERSION,
    PRODUCTION_EXPORT_SCHEMA_VERSION,
    PRODUCTION_RUN_SCHEMA_VERSION,
    STUDIO_PRODUCTION_BINDING_SCHEMA_VERSION,
    CreatorDecisionRequest,
    ProductionCheckpoint,
    ProductionExportRequest,
    ProductionQualityReviewRequest,
    ProductionRunCreateRequest,
    canonical_json_digest,
    checkpoint_digest,
)
from apps.api.runtime_store import RuntimeStore, safe_id


def register_runtime_production_run_routes(app: FastAPI, store: RuntimeStore, auth: RuntimeAuthStore) -> None:
    @app.post("/projects/{project_id}/production-runs")
    def create_production_run(
        project_id: str,
        body: ProductionRunCreateRequest,
        request: Request,
    ) -> dict[str, Any]:
        owner_user_id = _require_project_owner(store, auth, request, project_id)
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
                _validate_checkpoint(existing)
                _validate_export_artifacts(store, project_id, existing)
                return _run_response(existing, idempotent_replay=True)

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
                "mutation_idempotency": {},
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
            return _run_response(run, idempotent_replay=False)

    @app.get("/projects/{project_id}/production-runs")
    def list_production_runs(project_id: str, request: Request) -> dict[str, Any]:
        owner_user_id = _require_project_owner(store, auth, request, project_id)
        runs = store.list_production_runs(project_id)
        for run in runs:
            _require_run_owner(run, owner_user_id)
            _validate_checkpoint(run)
            _validate_export_artifacts(store, project_id, run)
        return {"project_id": project_id, "production_runs": runs}

    @app.get("/projects/{project_id}/production-runs/{run_id}")
    def get_production_run(project_id: str, run_id: str, request: Request) -> dict[str, Any]:
        owner_user_id = _require_project_owner(store, auth, request, project_id)
        try:
            run = store.load_production_run(project_id, run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="production run not found") from exc
        _require_run_owner(run, owner_user_id)
        _validate_checkpoint(run)
        _validate_export_artifacts(store, project_id, run)
        return _run_response(run)

    @app.post("/projects/{project_id}/production-runs/{run_id}/creator-decisions")
    def submit_creator_decision(
        project_id: str,
        run_id: str,
        body: CreatorDecisionRequest,
        request: Request,
    ) -> dict[str, Any]:
        owner_user_id = _require_project_owner(store, auth, request, project_id)
        request_digest = canonical_json_digest(body.model_dump(mode="json"))
        with exclusive_file_lock(store.production_run_lock_path(project_id)):
            run = _load_owned_run(store, project_id, run_id, owner_user_id)
            if _mutation_is_replay(run, "creator_decision", body.idempotency_key, request_digest):
                return _run_response(run, idempotent_replay=True)
            _require_checkpoint_version(run, body.expected_checkpoint_version)
            if _record_id_exists(run.get("creator_decisions"), "decision_id", body.decision_id):
                raise HTTPException(status_code=409, detail="creator decision id already exists")
            if body.subject_digest != str(run.get("subject_digest") or ""):
                raise HTTPException(status_code=409, detail="production run subject digest changed")
            candidate = _candidate(run, body.candidate_id)
            if body.candidate_digest != str(candidate.get("canonical_digest") or ""):
                raise HTTPException(status_code=409, detail="candidate digest changed")

            current_revision = run.get("selected_revision") if isinstance(run.get("selected_revision"), dict) else None
            expected_parent_revision_id = str((current_revision or {}).get("revision_id") or "")
            if expected_parent_revision_id != str(body.parent_revision_id or ""):
                raise HTTPException(status_code=409, detail="selected revision lineage changed")

            timestamp = _now()
            decision = {
                **body.model_dump(mode="json"),
                "creator_user_id": owner_user_id,
                "recorded_at": timestamp,
            }
            run.setdefault("creator_decisions", []).append(decision)
            run.setdefault("lineage", []).append(
                {
                    "source_ref": body.candidate_id,
                    "target_ref": body.decision_id,
                    "relation": "candidate_received_creator_decision",
                }
            )
            if body.decision == "reject":
                run["status"] = "creator_revision_required"
            else:
                revision_core = {
                    "revision_id": _revision_id(run_id, body),
                    "candidate_id": body.candidate_id,
                    "candidate_digest": body.candidate_digest,
                    "parent_job_id": str(candidate.get("parent_job_id") or ""),
                    "parent_candidate_id": candidate.get("parent_candidate_id"),
                    "parent_revision_id": body.parent_revision_id,
                    "creator_decision_id": body.decision_id,
                    "decision": body.decision,
                    "revision_intent": body.revision_intent,
                }
                revision = {
                    **revision_core,
                    "canonical_digest": canonical_json_digest(revision_core),
                    "subject_digest": canonical_json_digest(
                        {
                            "run_subject_digest": run["subject_digest"],
                            "candidate_digest": body.candidate_digest,
                            "parent_revision_id": body.parent_revision_id,
                            "revision_intent": body.revision_intent,
                        }
                    ),
                    "created_at": timestamp,
                }
                run["selected_revision"] = revision
                run["status"] = "creator_selected"
                run["lineage"].extend(
                    [
                        {
                            "source_ref": body.candidate_id,
                            "target_ref": revision["revision_id"],
                            "relation": "candidate_selected_as_revision",
                        },
                        {
                            "source_ref": body.decision_id,
                            "target_ref": revision["revision_id"],
                            "relation": "creator_decision_defined_revision",
                        },
                    ]
                )
                if body.parent_revision_id:
                    run["lineage"].append(
                        {
                            "source_ref": body.parent_revision_id,
                            "target_ref": revision["revision_id"],
                            "relation": "revision_revised_to_revision",
                        }
                    )
            _record_mutation_idempotency(run, "creator_decision", body.idempotency_key, request_digest)
            _advance_checkpoint(run)
            store.write_production_run(project_id, run)
            return _run_response(run, idempotent_replay=False)

    @app.post("/projects/{project_id}/production-runs/{run_id}/quality-reviews")
    def record_quality_review(
        project_id: str,
        run_id: str,
        body: ProductionQualityReviewRequest,
        request: Request,
    ) -> dict[str, Any]:
        owner_user_id = _require_project_owner(store, auth, request, project_id)
        request_digest = canonical_json_digest(body.model_dump(mode="json"))
        with exclusive_file_lock(store.production_run_lock_path(project_id)):
            run = _load_owned_run(store, project_id, run_id, owner_user_id)
            if _mutation_is_replay(run, "quality_review", body.idempotency_key, request_digest):
                return _run_response(run, idempotent_replay=True)
            _require_checkpoint_version(run, body.expected_checkpoint_version)
            if _record_id_exists(run.get("quality_reviews"), "review_id", body.review_id):
                raise HTTPException(status_code=409, detail="quality review id already exists")
            if run.get("status") not in {"creator_selected", "quality_rejected"}:
                raise HTTPException(status_code=409, detail="current creator decision is not ready for quality review")
            revision = _selected_revision(run)
            _require_selected_revision_identity(
                revision,
                revision_id=body.selected_revision_id,
                revision_digest=body.selected_revision_digest,
            )
            if body.reviewed_subject_digest != str(revision.get("subject_digest") or ""):
                raise HTTPException(status_code=409, detail="quality review subject digest changed")

            review = {
                **body.model_dump(mode="json"),
                "reviewer_user_id": owner_user_id,
                "recorded_at": _now(),
                "human_acceptance_claimed": False,
            }
            run.setdefault("quality_reviews", []).append(review)
            run.setdefault("lineage", []).append(
                {
                    "source_ref": revision["revision_id"],
                    "target_ref": body.review_id,
                    "relation": "selected_revision_quality_reviewed",
                }
            )
            run["status"] = "quality_approved" if body.decision == "approve" else "quality_rejected"
            _record_mutation_idempotency(run, "quality_review", body.idempotency_key, request_digest)
            _advance_checkpoint(run)
            store.write_production_run(project_id, run)
            return _run_response(run, idempotent_replay=False)

    @app.post("/projects/{project_id}/production-runs/{run_id}/exports")
    def export_production_run(
        project_id: str,
        run_id: str,
        body: ProductionExportRequest,
        request: Request,
    ) -> dict[str, Any]:
        owner_user_id = _require_project_owner(store, auth, request, project_id)
        request_digest = canonical_json_digest(body.model_dump(mode="json"))
        with exclusive_file_lock(store.production_run_lock_path(project_id)):
            run = _load_owned_run(store, project_id, run_id, owner_user_id)
            if _mutation_is_replay(run, "export", body.idempotency_key, request_digest):
                export = _export_by_id(run, body.export_id)
                return _run_response(run, idempotent_replay=True, export=export)
            _require_checkpoint_version(run, body.expected_checkpoint_version)
            revision = _selected_revision(run)
            _require_selected_revision_identity(
                revision,
                revision_id=body.selected_revision_id,
                revision_digest=body.selected_revision_digest,
            )
            review = _approved_review_for_revision(run, revision)
            if _export_by_id(run, body.export_id, required=False):
                raise HTTPException(status_code=409, detail="production export id already exists")

            source_checkpoint = dict(run["checkpoint"])
            delivery = {
                "artifact_type": "afs_production_delivery",
                "schema_version": PRODUCTION_EXPORT_SCHEMA_VERSION,
                "project_id": project_id,
                "run_id": run_id,
                "export_id": body.export_id,
                "selected_revision": revision,
                "creator_decision_ref": str(revision.get("creator_decision_id") or ""),
                "quality_review_ref": str(review.get("review_id") or ""),
                "source_checkpoint": {
                    "schema_version": source_checkpoint["schema_version"],
                    "version": source_checkpoint["version"],
                    "state_digest": source_checkpoint["state_digest"],
                },
                "lineage": list(run.get("lineage") or []),
                "evidence_boundary": dict(run.get("evidence_boundary") or {}),
            }
            export_dir = store.production_run_path(project_id, run_id).parent / "exports" / body.export_id
            export_dir.mkdir(parents=True, exist_ok=True)
            delivery_path = export_dir / "production_delivery.json"
            write_json(delivery_path, delivery)
            delivery_sha256 = hashlib.sha256(delivery_path.read_bytes()).hexdigest()
            artifact_ref = store.register_artifact(delivery_path, role="production_export")
            export = {
                "export_id": body.export_id,
                "selected_revision_id": revision["revision_id"],
                "selected_revision_digest": revision["canonical_digest"],
                "quality_review_id": review["review_id"],
                "delivery_sha256": delivery_sha256,
                "artifact": artifact_ref,
                "created_at": _now(),
            }
            run.setdefault("exports", []).append(export)
            run.setdefault("lineage", []).extend(
                [
                    {
                        "source_ref": revision["revision_id"],
                        "target_ref": body.export_id,
                        "relation": "selected_revision_exported",
                    },
                    {
                        "source_ref": review["review_id"],
                        "target_ref": body.export_id,
                        "relation": "quality_review_authorized_export",
                    },
                ]
            )
            run["status"] = "exported"
            _record_mutation_idempotency(run, "export", body.idempotency_key, request_digest)
            _advance_checkpoint(run)
            store.write_production_run(project_id, run)
            return _run_response(run, idempotent_replay=False, export=export)


def _find_creation_idempotency(store: RuntimeStore, project_id: str, idempotency_key: str) -> dict[str, Any] | None:
    for run in store.list_production_runs(project_id):
        if str(run.get("creation", {}).get("idempotency_key") or "") == idempotency_key:
            return run
    return None


def _load_owned_run(
    store: RuntimeStore,
    project_id: str,
    run_id: str,
    owner_user_id: str,
) -> dict[str, Any]:
    try:
        run = store.load_production_run(project_id, run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="production run not found") from exc
    _require_run_owner(run, owner_user_id)
    _validate_checkpoint(run)
    _validate_export_artifacts(store, project_id, run)
    return run


def _validate_checkpoint(run: dict[str, Any]) -> None:
    checkpoint = run.get("checkpoint")
    if not isinstance(checkpoint, dict):
        raise HTTPException(status_code=409, detail="production checkpoint is missing")
    try:
        ProductionCheckpoint.model_validate(checkpoint)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="production checkpoint control metadata is invalid") from exc
    if str(checkpoint.get("state_digest") or "") != checkpoint_digest(run):
        raise HTTPException(status_code=409, detail="production checkpoint integrity mismatch")


def _validate_export_artifacts(store: RuntimeStore, project_id: str, run: dict[str, Any]) -> None:
    run_id = str(run.get("run_id") or "")
    for export in run.get("exports") or []:
        if not isinstance(export, dict):
            raise HTTPException(status_code=409, detail="production export record is invalid")
        export_id = safe_id(str(export.get("export_id") or ""))
        path = store.production_run_path(project_id, run_id).parent / "exports" / export_id / "production_delivery.json"
        if not path.is_file():
            raise HTTPException(status_code=409, detail="production export artifact is missing")
        actual_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_digest != str(export.get("delivery_sha256") or ""):
            raise HTTPException(status_code=409, detail="production export artifact integrity mismatch")


def _require_checkpoint_version(run: dict[str, Any], expected_version: int) -> None:
    actual = int(run.get("checkpoint", {}).get("version") or 0)
    if actual != expected_version:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "stale_production_checkpoint",
                "expected_checkpoint_version": expected_version,
                "actual_checkpoint_version": actual,
            },
        )


def _advance_checkpoint(run: dict[str, Any]) -> None:
    current = dict(run.get("checkpoint") or {})
    timestamp = _now()
    run["updated_at"] = timestamp
    run["checkpoint"] = {
        "schema_version": PRODUCTION_CHECKPOINT_SCHEMA_VERSION,
        "version": int(current.get("version") or 0) + 1,
        "previous_digest": str(current.get("state_digest") or "") or None,
        "state_digest": "",
        "updated_at": timestamp,
    }
    run["checkpoint"]["state_digest"] = checkpoint_digest(run)


def _mutation_is_replay(run: dict[str, Any], action: str, idempotency_key: str, request_digest: str) -> bool:
    actions = run.get("mutation_idempotency")
    if not isinstance(actions, dict):
        return False
    entry = actions.get(f"{action}:{idempotency_key}")
    if not isinstance(entry, dict):
        return False
    if str(entry.get("request_digest") or "") != request_digest:
        raise HTTPException(status_code=409, detail=f"{action} idempotency conflict")
    return True


def _record_mutation_idempotency(
    run: dict[str, Any],
    action: str,
    idempotency_key: str,
    request_digest: str,
) -> None:
    actions = run.setdefault("mutation_idempotency", {})
    actions[f"{action}:{idempotency_key}"] = {
        "action": action,
        "idempotency_key": idempotency_key,
        "request_digest": request_digest,
        "recorded_at": _now(),
    }


def _candidate(run: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    for candidate in run.get("candidates") or []:
        if isinstance(candidate, dict) and str(candidate.get("candidate_id") or "") == candidate_id:
            return candidate
    raise HTTPException(status_code=409, detail="selected candidate is not part of this production run")


def _selected_revision(run: dict[str, Any]) -> dict[str, Any]:
    revision = run.get("selected_revision")
    if not isinstance(revision, dict):
        raise HTTPException(status_code=409, detail="creator selection is required")
    return revision


def _require_selected_revision_identity(
    revision: dict[str, Any],
    *,
    revision_id: str,
    revision_digest: str,
) -> None:
    if str(revision.get("revision_id") or "") != revision_id:
        raise HTTPException(status_code=409, detail="selected revision changed")
    if str(revision.get("canonical_digest") or "") != revision_digest:
        raise HTTPException(status_code=409, detail="selected revision digest changed")


def _approved_review_for_revision(run: dict[str, Any], revision: dict[str, Any]) -> dict[str, Any]:
    reviews = [item for item in run.get("quality_reviews") or [] if isinstance(item, dict)]
    if not reviews:
        raise HTTPException(status_code=409, detail="approved quality review is required before export")
    review = reviews[-1]
    if review.get("decision") != "approve":
        raise HTTPException(status_code=409, detail="latest quality review does not approve export")
    if str(review.get("selected_revision_id") or "") != str(revision.get("revision_id") or ""):
        raise HTTPException(status_code=409, detail="quality review selected revision changed")
    if str(review.get("selected_revision_digest") or "") != str(revision.get("canonical_digest") or ""):
        raise HTTPException(status_code=409, detail="quality review revision digest changed")
    if str(review.get("reviewed_subject_digest") or "") != str(revision.get("subject_digest") or ""):
        raise HTTPException(status_code=409, detail="quality review subject digest changed")
    return review


def _revision_id(run_id: str, body: CreatorDecisionRequest) -> str:
    digest = canonical_json_digest(
        {
            "run_id": run_id,
            "decision_id": body.decision_id,
            "candidate_id": body.candidate_id,
            "candidate_digest": body.candidate_digest,
            "parent_revision_id": body.parent_revision_id,
            "revision_intent": body.revision_intent,
        }
    )
    return f"revision-{digest[:16]}"


def _export_by_id(run: dict[str, Any], export_id: str, *, required: bool = True) -> dict[str, Any] | None:
    for item in run.get("exports") or []:
        if isinstance(item, dict) and str(item.get("export_id") or "") == export_id:
            return item
    if required:
        raise HTTPException(status_code=409, detail="production export idempotency record is missing")
    return None


def _record_id_exists(records: Any, field: str, value: str) -> bool:
    return any(
        isinstance(item, dict) and str(item.get(field) or "") == value
        for item in (records if isinstance(records, list) else [])
    )


def _run_response(
    run: dict[str, Any],
    *,
    idempotent_replay: bool | None = None,
    export: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "production_run": run,
        "studio_binding": _studio_binding(run),
    }
    if idempotent_replay is not None:
        payload["idempotent_replay"] = idempotent_replay
    if export is not None:
        payload["export"] = export
    return payload


def _studio_binding(run: dict[str, Any]) -> dict[str, Any]:
    checkpoint = run.get("checkpoint") if isinstance(run.get("checkpoint"), dict) else {}
    revision = run.get("selected_revision") if isinstance(run.get("selected_revision"), dict) else {}
    exports = [item for item in run.get("exports") or [] if isinstance(item, dict)]
    binding = {
        "schema_version": STUDIO_PRODUCTION_BINDING_SCHEMA_VERSION,
        "authoritative_source": "runtime_production_run",
        "compatibility_mode": "backend_authoritative_summary_only",
        "active_run_id": str(run.get("run_id") or ""),
        "checkpoint_version": int(checkpoint.get("version") or 0),
        "checkpoint_digest": str(checkpoint.get("state_digest") or ""),
        "subject_digest": str(run.get("subject_digest") or ""),
        "selected_candidate_id": str(revision.get("candidate_id") or ""),
        "selected_candidate_digest": str(revision.get("candidate_digest") or ""),
        "selected_revision_id": str(revision.get("revision_id") or ""),
        "selected_revision_digest": str(revision.get("canonical_digest") or ""),
        "last_export_id": str((exports[-1] if exports else {}).get("export_id") or ""),
    }
    return {key: value for key, value in binding.items() if value not in ("", 0)}


def resolve_project_studio_binding(
    store: RuntimeStore,
    project_id: str,
    *,
    owner_user_id: str | None = None,
) -> dict[str, Any]:
    if store.is_project_deleted(project_id):
        return {}
    runs = store.list_production_runs(project_id)
    if owner_user_id:
        runs = [run for run in runs if str(run.get("owner_user_id") or "") == owner_user_id]
    if not runs:
        return {}
    run = max(runs, key=lambda item: (str(item.get("updated_at") or ""), str(item.get("run_id") or "")))
    _validate_checkpoint(run)
    _validate_export_artifacts(store, project_id, run)
    return _studio_binding(run)


def _require_project_owner(
    store: RuntimeStore,
    auth: RuntimeAuthStore,
    request: Request,
    project_id: str,
) -> str:
    if not auth.enabled():
        raise HTTPException(status_code=403, detail="authenticated production runs require runtime auth")
    if store.is_project_deleted(project_id):
        raise HTTPException(status_code=404, detail="project not found")
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


__all__ = ("register_runtime_production_run_routes", "resolve_project_studio_binding")
