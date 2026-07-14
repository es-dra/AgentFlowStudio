from __future__ import annotations

import hashlib
import re
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from agentflow.harness.json_io import exclusive_file_lock, write_json
from agentflow_studio.production.representative_episode_media import (
    RepresentativeEpisodeMediaError,
    admit_authoritative_media,
    assemble_authoritative_episode,
    revalidate_authoritative_media,
    safe_media_projection,
)
from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_generated_image_assets import resolve_generated_candidate_authority
from apps.api.runtime_production_models import (
    PRODUCTION_CHECKPOINT_SCHEMA_VERSION,
    PRODUCTION_EXPORT_SCHEMA_VERSION,
    PRODUCTION_RUN_SCHEMA_VERSION,
    REPRESENTATIVE_EPISODE_BINDING_SCHEMA_VERSION,
    STUDIO_PRODUCTION_BINDING_SCHEMA_VERSION,
    CreatorDecisionRequest,
    ProductionCheckpoint,
    ProductionExportRequest,
    ProductionQualityReviewRequest,
    ProductionRunCreateRequest,
    RepresentativeEpisodeBindingRequest,
    RepresentativeEpisodeMediaAssemblyRequest,
    RepresentativeEpisodeMediaIntakeRequest,
    canonical_json_digest,
    checkpoint_digest,
)
from apps.api.runtime_store import RuntimeStore, safe_id
from apps.api.runtime_video_constants import SAFE_CANDIDATE_ID, VIDEO_SUFFIX_TYPES


SAFE_SHA256 = re.compile(r"^[a-f0-9]{64}$")
SAFE_PREVIEW_JOB_STATUSES = frozenset({"succeeded", "partially_complete", "complete"})


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
                "representative_episode_binding": None,
                "representative_episode_media": None,
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

    @app.get("/projects/{project_id}/production-runs/{run_id}/representative-episode-media")
    def get_representative_episode_media(
        project_id: str,
        run_id: str,
        request: Request,
    ) -> dict[str, Any]:
        owner_user_id = _require_project_owner(store, auth, request, project_id)
        run = _load_owned_run(store, project_id, run_id, owner_user_id)
        media = run.get("representative_episode_media")
        if not isinstance(media, dict):
            raise HTTPException(status_code=404, detail="representative episode media not found")
        return {
            "project_id": project_id,
            "run_id": run_id,
            "media": _media_run_projection(media),
            "checkpoint": dict(run["checkpoint"]),
        }

    @app.post("/projects/{project_id}/production-runs/{run_id}/representative-episode-media/intake")
    def intake_representative_episode_media(
        project_id: str,
        run_id: str,
        body: RepresentativeEpisodeMediaIntakeRequest,
        request: Request,
    ) -> dict[str, Any]:
        owner_user_id = _require_project_owner(store, auth, request, project_id)
        request_digest = canonical_json_digest(body.model_dump(mode="json"))
        media_root = _representative_episode_media_root(store, project_id, run_id)
        with exclusive_file_lock(store.production_run_lock_path(project_id)):
            run = _load_owned_run(store, project_id, run_id, owner_user_id)
            if _mutation_is_replay(run, "representative_episode_media_intake", body.idempotency_key, request_digest):
                return _run_response(run, idempotent_replay=True)
            _require_checkpoint_version(run, body.expected_checkpoint_version)
            binding = _current_episode_binding(run)
            _require_media_binding_identity(
                binding,
                expected_binding_digest=body.expected_binding_digest,
                expected_episode_version_id=body.expected_episode_version_id,
            )
            if isinstance(run.get("representative_episode_media"), dict):
                raise HTTPException(status_code=409, detail="representative episode media already admitted")
            try:
                media = admit_authoritative_media(
                    binding,
                    [item.model_dump(mode="json") for item in body.assets],
                    media_root,
                    project_id=project_id,
                    run_id=run_id,
                )
            except RepresentativeEpisodeMediaError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            run["representative_episode_media"] = media
            run.setdefault("lineage", []).append(
                {
                    "source_ref": binding["binding_digest"],
                    "target_ref": media["manifest_sha256"],
                    "relation": "canonical_episode_binding_admitted_controlled_media",
                }
            )
            _record_mutation_idempotency(
                run,
                "representative_episode_media_intake",
                body.idempotency_key,
                request_digest,
            )
            _advance_checkpoint(run)
            try:
                store.write_production_run(project_id, run)
            except Exception:
                shutil.rmtree(media_root, ignore_errors=True)
                raise
            return _run_response(run, idempotent_replay=False)

    @app.post("/projects/{project_id}/production-runs/{run_id}/representative-episode-media/assemble")
    def assemble_representative_episode_media(
        project_id: str,
        run_id: str,
        body: RepresentativeEpisodeMediaAssemblyRequest,
        request: Request,
    ) -> dict[str, Any]:
        owner_user_id = _require_project_owner(store, auth, request, project_id)
        request_digest = canonical_json_digest(body.model_dump(mode="json"))
        media_root = _representative_episode_media_root(store, project_id, run_id)
        with exclusive_file_lock(store.production_run_lock_path(project_id)):
            run = _load_owned_run(store, project_id, run_id, owner_user_id)
            if _mutation_is_replay(run, "representative_episode_media_assembly", body.idempotency_key, request_digest):
                return _run_response(run, idempotent_replay=True)
            _require_checkpoint_version(run, body.expected_checkpoint_version)
            binding = _current_episode_binding(run)
            _require_media_binding_identity(
                binding,
                expected_binding_digest=body.expected_binding_digest,
                expected_episode_version_id="ep-rainlight-001-v2",
            )
            media = run.get("representative_episode_media")
            if not isinstance(media, dict):
                raise HTTPException(status_code=409, detail="all authoritative media must be admitted before assembly")
            if media.get("manifest_sha256") != body.expected_media_manifest_sha256:
                raise HTTPException(status_code=409, detail="representative episode media manifest changed")
            if isinstance(media.get("delivery"), dict):
                raise HTTPException(status_code=409, detail="representative episode technical delivery already exists")
            try:
                delivery = assemble_authoritative_episode(binding, media, media_root)
            except RepresentativeEpisodeMediaError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            media["delivery"] = delivery
            run.setdefault("lineage", []).append(
                {
                    "source_ref": media["manifest_sha256"],
                    "target_ref": delivery["episode_sha256"],
                    "relation": "controlled_media_assembled_as_technical_episode_delivery",
                }
            )
            _record_mutation_idempotency(
                run,
                "representative_episode_media_assembly",
                body.idempotency_key,
                request_digest,
            )
            _advance_checkpoint(run)
            write_json(media_root / "media_manifest.json", media)
            store.write_production_run(project_id, run)
            return _run_response(run, idempotent_replay=False)

    @app.get(
        "/projects/{project_id}/production-runs/{run_id}/"
        "representative-episode-media/assets/{asset_id}/preview"
    )
    def representative_episode_media_preview(
        project_id: str,
        run_id: str,
        asset_id: str,
        request: Request,
    ) -> FileResponse:
        owner_user_id = _require_project_owner(store, auth, request, project_id)
        run = _load_owned_run(store, project_id, run_id, owner_user_id)
        media = run.get("representative_episode_media")
        if not isinstance(media, dict) or safe_id(asset_id) != asset_id:
            raise HTTPException(status_code=404, detail="controlled media preview not found")
        assets = revalidate_authoritative_media(
            _current_episode_binding(run), media, _representative_episode_media_root(store, project_id, run_id)
        )
        asset = next((item for item in assets if item.get("asset_id") == asset_id), None)
        if not asset:
            raise HTTPException(status_code=404, detail="controlled media preview not found")
        path = _safe_media_file(_representative_episode_media_root(store, project_id, run_id), asset["relative_ref"])
        return FileResponse(
            path,
            media_type=asset["mime_type"],
            filename=f"preview{path.suffix}",
            content_disposition_type="inline",
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    @app.get(
        "/projects/{project_id}/production-runs/{run_id}/"
        "representative-episode-media/delivery/preview"
    )
    def representative_episode_delivery_preview(
        project_id: str,
        run_id: str,
        request: Request,
    ) -> FileResponse:
        owner_user_id = _require_project_owner(store, auth, request, project_id)
        run = _load_owned_run(store, project_id, run_id, owner_user_id)
        media = run.get("representative_episode_media")
        delivery = media.get("delivery") if isinstance(media, dict) and isinstance(media.get("delivery"), dict) else {}
        if delivery.get("assembly_complete") is not True:
            raise HTTPException(status_code=404, detail="technical episode delivery not found")
        path = _representative_episode_media_root(store, project_id, run_id) / "delivery" / "episode.mp4"
        if not path.is_file() or _file_sha256(path) != delivery.get("episode_sha256"):
            raise HTTPException(status_code=409, detail="technical episode delivery integrity mismatch")
        return FileResponse(
            path,
            media_type="video/mp4",
            filename="episode-preview.mp4",
            content_disposition_type="inline",
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    @app.get("/projects/{project_id}/production-runs")
    def list_production_runs(project_id: str, request: Request) -> dict[str, Any]:
        owner_user_id = _require_project_owner(store, auth, request, project_id)
        runs = store.list_production_runs(project_id)
        for run in runs:
            _require_run_owner(run, owner_user_id)
            _validate_checkpoint(run)
            _validate_export_artifacts(store, project_id, run)
            media = run.get("representative_episode_media")
            if isinstance(media, dict):
                try:
                    revalidate_authoritative_media(
                        _current_episode_binding(run),
                        media,
                        _representative_episode_media_root(store, project_id, str(run.get("run_id") or "")),
                    )
                except RepresentativeEpisodeMediaError as exc:
                    raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {
            "project_id": project_id,
            "production_runs": [_production_run_read_projection(store, project_id, run) for run in runs],
        }

    @app.get("/projects/{project_id}/production-runs/{run_id}")
    def get_production_run(project_id: str, run_id: str, request: Request) -> dict[str, Any]:
        owner_user_id = _require_project_owner(store, auth, request, project_id)
        run = _load_owned_run(store, project_id, run_id, owner_user_id)
        return _run_response(_production_run_read_projection(store, project_id, run))

    @app.get("/projects/{project_id}/production-runs/{run_id}/representative-episode-binding")
    def get_representative_episode_binding(
        project_id: str,
        run_id: str,
        request: Request,
    ) -> dict[str, Any]:
        owner_user_id = _require_project_owner(store, auth, request, project_id)
        run = _load_owned_run(store, project_id, run_id, owner_user_id)
        binding = run.get("representative_episode_binding")
        if not isinstance(binding, dict):
            raise HTTPException(status_code=404, detail="representative episode binding not found")
        return {
            "project_id": project_id,
            "run_id": run_id,
            "representative_episode_binding": binding,
            "checkpoint": dict(run["checkpoint"]),
        }

    @app.put("/projects/{project_id}/production-runs/{run_id}/representative-episode-binding")
    def bind_representative_episode_package(
        project_id: str,
        run_id: str,
        body: RepresentativeEpisodeBindingRequest,
        request: Request,
    ) -> dict[str, Any]:
        owner_user_id = _require_project_owner(store, auth, request, project_id)
        request_payload = body.model_dump(mode="json")
        request_digest = canonical_json_digest(request_payload)
        with exclusive_file_lock(store.production_run_lock_path(project_id)):
            run = _load_owned_run(store, project_id, run_id, owner_user_id)
            if _mutation_is_replay(run, "representative_episode_binding", body.idempotency_key, request_digest):
                return _run_response(run, idempotent_replay=True)
            _require_checkpoint_version(run, body.expected_checkpoint_version)
            if body.expected_subject_digest != str(run.get("subject_digest") or ""):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "representative_episode_subject_conflict",
                        "expected_subject_digest": body.expected_subject_digest,
                        "actual_subject_digest": str(run.get("subject_digest") or ""),
                    },
                )
            if body.package_project_id != project_id:
                raise HTTPException(status_code=409, detail="representative episode package belongs to another project")
            current = run.get("representative_episode_binding")
            current_digest = str(current.get("package_sha256") or "") if isinstance(current, dict) else ""
            expected_digest = str(body.expected_package_sha256 or "")
            if current_digest != expected_digest:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "stale_representative_episode_package",
                        "expected_package_sha256": expected_digest or None,
                        "actual_package_sha256": current_digest or None,
                    },
                )

            timestamp = _now()
            episode_canon = _persisted_episode_canon(body)
            canon_digest = canonical_json_digest(episode_canon)
            binding_core = {
                "schema_version": REPRESENTATIVE_EPISODE_BINDING_SCHEMA_VERSION,
                "package_sha256": body.package_sha256,
                "package_project_id": body.package_project_id,
                "subject_digest": body.expected_subject_digest,
                "episode_id": body.episode_id,
                "episode_version_id": body.episode_version_id,
                "episode_title": episode_canon["episode_title"],
                "canon_digest": canon_digest,
                "episode_canon": episode_canon,
                "character_refs": [item.model_dump(mode="json") for item in body.character_refs],
                "scene_refs": [item.model_dump(mode="json") for item in body.scene_refs],
                "shot_refs": [item.model_dump(mode="json") for item in body.shot_refs],
                "asset_refs": [item.model_dump(mode="json") for item in body.asset_refs],
                "counts": {
                    "characters": len(body.character_refs),
                    "scenes": len(body.scene_refs),
                    "shots": len(body.shot_refs),
                    "assets": len(body.asset_refs),
                    "audio_items": 4,
                },
                "asset_readiness": {
                    "ready_count": sum(item.status == "ready" for item in body.asset_refs),
                    "pending_media_count": body.pending_media_count,
                    "provider_needed_count": sum(item.provider_needed for item in body.asset_refs),
                    "all_assets_ready": body.pending_media_count == 0,
                },
                "creator_decision_ref": body.creator_decision_ref,
                "authoritative_affected_task_refs": list(body.authoritative_affected_task_refs),
                "downstream_reconfirmations": [
                    item.model_dump(mode="json") for item in body.downstream_reconfirmations
                ],
                "propagation_complete": all(
                    item.status == "reconfirmed" for item in body.downstream_reconfirmations
                ),
                "lineage": [
                    {
                        "source_ref": body.package_sha256,
                        "target_ref": body.episode_version_id,
                        "relation": "package_defined_episode_version",
                    },
                    {
                        "source_ref": canon_digest,
                        "target_ref": body.episode_version_id,
                        "relation": "safe_canon_defined_episode_version",
                    },
                    {
                        "source_ref": body.creator_decision_ref,
                        "target_ref": body.episode_version_id,
                        "relation": "creator_decision_approved_episode_version",
                    },
                ],
            }
            if isinstance(current, dict) and str(current.get("binding_digest") or ""):
                binding_core["previous_binding_digest"] = str(current["binding_digest"])
                binding_core["lineage"].append(
                    {
                        "source_ref": str(current["binding_digest"]),
                        "target_ref": canon_digest,
                        "relation": "previous_episode_binding_superseded_by_safe_canon",
                    }
                )
            binding = {
                **binding_core,
                "binding_digest": canonical_json_digest(binding_core),
                "bound_by_user_id": owner_user_id,
                "bound_at": timestamp,
            }
            run["representative_episode_binding"] = binding
            run.setdefault("lineage", []).append(
                {
                    "source_ref": body.package_sha256,
                    "target_ref": binding["binding_digest"],
                    "relation": "representative_episode_package_bound_to_production_run",
                }
            )
            _record_mutation_idempotency(
                run,
                "representative_episode_binding",
                body.idempotency_key,
                request_digest,
            )
            _advance_checkpoint(run)
            store.write_production_run(project_id, run)
            return _run_response(run, idempotent_replay=False)

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


def _persisted_episode_canon(body: RepresentativeEpisodeBindingRequest) -> dict[str, Any]:
    canon = body.episode_canon.model_dump(mode="json")
    assets_by_id = {
        item.asset_id: item.model_dump(mode="json") for item in body.asset_refs
    }
    audio = canon["audio"]
    audio_asset_ids = [
        audio["dialogue_asset_ref"]["asset_id"],
        audio["music_asset_ref"]["asset_id"],
        audio["sfx_asset_ref"]["asset_id"],
        audio["master_asset_ref"]["asset_id"],
    ]
    pending_audio_count = sum(assets_by_id[item]["status"] != "ready" for item in audio_asset_ids)
    audio["readiness"] = {
        "asset_count": len(audio_asset_ids),
        "ready_count": len(audio_asset_ids) - pending_audio_count,
        "pending_count": pending_audio_count,
        "all_audio_ready": pending_audio_count == 0,
    }
    audio_coverage = set(audio["coverage_shot_refs"])
    for shot in canon["shots"]:
        required_assets = [assets_by_id[item] for item in shot["required_asset_ids"]]
        pending_media_count = sum(item["status"] != "ready" for item in required_assets)
        shot["asset_readiness"] = {
            "required_count": len(required_assets),
            "ready_count": len(required_assets) - pending_media_count,
            "pending_media_count": pending_media_count,
            "all_required_assets_ready": pending_media_count == 0,
        }
        shot["audio_coverage"] = {
            "covered": shot["entity_id"] in audio_coverage,
            "status": "ready" if pending_audio_count == 0 else "pending",
            "pending_audio_asset_count": pending_audio_count,
        }
    return canon


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
    media = run.get("representative_episode_media")
    if isinstance(media, dict):
        try:
            revalidate_authoritative_media(
                _current_episode_binding(run),
                media,
                _representative_episode_media_root(store, project_id, run_id),
            )
        except RepresentativeEpisodeMediaError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
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
    projected = deepcopy(run)
    if (
        isinstance(projected.get("representative_episode_media"), dict)
        and projected["representative_episode_media"].get("schema_version")
    ):
        projected["representative_episode_media"] = _media_run_projection(
            projected["representative_episode_media"]
        )
    payload: dict[str, Any] = {
        "production_run": projected,
        "studio_binding": _studio_binding(run),
    }
    if idempotent_replay is not None:
        payload["idempotent_replay"] = idempotent_replay
    if export is not None:
        payload["export"] = export
    return payload


def _production_run_read_projection(
    store: RuntimeStore,
    project_id: str,
    run: dict[str, Any],
) -> dict[str, Any]:
    projected = deepcopy(run)
    if isinstance(projected.get("representative_episode_media"), dict):
        projected["representative_episode_media"] = _media_run_projection(
            projected["representative_episode_media"]
        )
    candidates = projected.get("candidates")
    if not isinstance(candidates, list):
        return projected
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        candidate.pop("safe_preview", None)
        descriptor = _candidate_safe_preview(store, project_id, candidate)
        if descriptor is not None:
            candidate["safe_preview"] = descriptor
    return projected


def _candidate_safe_preview(
    store: RuntimeStore,
    project_id: str,
    candidate: dict[str, Any],
) -> dict[str, str] | None:
    candidate_id = candidate.get("candidate_id")
    parent_job_id = candidate.get("parent_job_id")
    canonical_digest = candidate.get("canonical_digest")
    if (
        not isinstance(candidate_id, str)
        or not isinstance(parent_job_id, str)
        or not isinstance(canonical_digest, str)
        or safe_id(project_id) != project_id
        or safe_id(parent_job_id) != parent_job_id
        or SAFE_SHA256.fullmatch(canonical_digest) is None
    ):
        return None
    try:
        job = store.load_job(parent_job_id)
    except (KeyError, OSError, ValueError):
        return None
    if (
        job.get("job_id") != parent_job_id
        or job.get("project_id") != project_id
        or job.get("status") not in SAFE_PREVIEW_JOB_STATUSES
    ):
        return None
    action = job.get("action")
    if action == "keyframe_generation":
        return _image_candidate_safe_preview(
            store,
            project_id,
            parent_job_id,
            candidate_id,
            canonical_digest,
        )
    if action == "video_generation":
        return _video_candidate_safe_preview(
            store,
            project_id,
            parent_job_id,
            candidate_id,
            canonical_digest,
        )
    return None


def _image_candidate_safe_preview(
    store: RuntimeStore,
    project_id: str,
    parent_job_id: str,
    candidate_id: str,
    canonical_digest: str,
) -> dict[str, str] | None:
    try:
        authority = resolve_generated_candidate_authority(
            store,
            project_id,
            source_job_id=parent_job_id,
            source_candidate_id=candidate_id,
            require_existing_asset=True,
        )
    except (OSError, ValueError):
        return None
    if (
        authority.get("source_job_id") != parent_job_id
        or authority.get("source_candidate_id") != candidate_id
        or authority.get("sha256") != canonical_digest
    ):
        return None
    return {
        "media_kind": "image",
        "preview_url": (
            f"/projects/{project_id}/keyframe-generations/{parent_job_id}/"
            f"candidates/{candidate_id}/preview"
        ),
    }


def _video_candidate_safe_preview(
    store: RuntimeStore,
    project_id: str,
    parent_job_id: str,
    candidate_id: str,
    canonical_digest: str,
) -> dict[str, str] | None:
    if SAFE_CANDIDATE_ID.fullmatch(candidate_id) is None:
        return None
    output_dir = store.run_dir(project_id, parent_job_id).resolve()
    video_dir = (output_dir / "video_candidates").resolve()
    root = store.root.resolve()
    try:
        output_dir.relative_to(root)
        video_dir.relative_to(output_dir)
    except ValueError:
        return None
    if not video_dir.is_dir():
        return None
    candidate_files = [path for path in video_dir.glob(f"{candidate_id}.*") if path.is_file()]
    if len(candidate_files) != 1:
        return None
    path = candidate_files[0].resolve()
    try:
        path.relative_to(video_dir)
    except ValueError:
        return None
    if (
        path.parent != video_dir
        or path.name != f"{candidate_id}{path.suffix}"
        or path.suffix not in VIDEO_SUFFIX_TYPES
    ):
        return None
    try:
        actual_digest = _file_sha256(path)
    except OSError:
        return None
    if actual_digest != canonical_digest:
        return None
    return {
        "media_kind": "video",
        "preview_url": (
            f"/projects/{project_id}/video-generations/{parent_job_id}/"
            f"candidates/{candidate_id}/preview"
        ),
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _current_episode_binding(run: dict[str, Any]) -> dict[str, Any]:
    binding = run.get("representative_episode_binding")
    if not isinstance(binding, dict):
        raise HTTPException(status_code=409, detail="representative episode binding is required")
    if str(binding.get("canon_digest") or "") != canonical_json_digest(binding.get("episode_canon")):
        raise HTTPException(status_code=409, detail="representative episode canon integrity mismatch")
    binding_core = {
        key: value
        for key, value in binding.items()
        if key not in {"binding_digest", "bound_by_user_id", "bound_at"}
    }
    if str(binding.get("binding_digest") or "") != canonical_json_digest(binding_core):
        raise HTTPException(status_code=409, detail="representative episode binding integrity mismatch")
    return binding


def _require_media_binding_identity(
    binding: dict[str, Any],
    *,
    expected_binding_digest: str,
    expected_episode_version_id: str,
) -> None:
    if binding.get("binding_digest") != expected_binding_digest:
        raise HTTPException(status_code=409, detail="representative episode binding changed")
    if binding.get("episode_version_id") != expected_episode_version_id:
        raise HTTPException(status_code=409, detail="representative episode version changed")
    if binding.get("propagation_complete") is not True:
        raise HTTPException(status_code=409, detail="downstream episode propagation is incomplete")


def _representative_episode_media_root(
    store: RuntimeStore,
    project_id: str,
    run_id: str,
) -> Path:
    root = store.production_run_path(project_id, run_id).parent.resolve()
    media_root = (root / "representative_episode_media").resolve()
    if root not in media_root.parents:
        raise HTTPException(status_code=409, detail="representative episode media root is unsafe")
    return media_root


def _safe_media_file(root: Path, relative_ref: str) -> Path:
    relative = Path(str(relative_ref or ""))
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise HTTPException(status_code=409, detail="controlled media ref is unsafe")
    path = (root.resolve() / relative).resolve()
    if root.resolve() not in path.parents:
        raise HTTPException(status_code=409, detail="controlled media ref escapes its project")
    return path


def _media_run_projection(media: dict[str, Any]) -> dict[str, Any]:
    safe = safe_media_projection(media)
    safe["manifest_sha256"] = str(media.get("manifest_sha256") or "")
    safe["episode_version_id"] = str(media.get("episode_version_id") or "")
    safe["assets"] = [
        {
            "ordinal": int(item.get("ordinal") or 0),
            "asset_id": str(item.get("asset_id") or ""),
            "revision_id": str(item.get("revision_id") or ""),
            "category": str(item.get("category") or ""),
            "media_kind": str(item.get("media_kind") or ""),
            "mime_type": str(item.get("mime_type") or ""),
            "sha256": str(item.get("sha256") or ""),
            "safe_preview": {
                "media_kind": str(item.get("media_kind") or ""),
                "preview_url": str(item.get("safe_preview_url") or ""),
            },
        }
        for item in media.get("assets") or []
        if isinstance(item, dict)
    ]
    return safe


def _studio_binding(run: dict[str, Any]) -> dict[str, Any]:
    checkpoint = run.get("checkpoint") if isinstance(run.get("checkpoint"), dict) else {}
    revision = run.get("selected_revision") if isinstance(run.get("selected_revision"), dict) else {}
    exports = [item for item in run.get("exports") or [] if isinstance(item, dict)]
    episode = (
        run.get("representative_episode_binding")
        if isinstance(run.get("representative_episode_binding"), dict)
        else {}
    )
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
        "representative_episode": _episode_studio_summary(episode),
    }
    return {key: value for key, value in binding.items() if value not in ("", 0, {})}


def _episode_studio_summary(binding: dict[str, Any]) -> dict[str, Any]:
    if not binding:
        return {}
    counts = binding.get("counts") if isinstance(binding.get("counts"), dict) else {}
    readiness = binding.get("asset_readiness") if isinstance(binding.get("asset_readiness"), dict) else {}
    canon = binding.get("episode_canon") if isinstance(binding.get("episode_canon"), dict) else {}
    lineage = [item for item in binding.get("lineage") or [] if isinstance(item, dict)]
    return {
        "authoritative_source": "runtime_production_run_checkpoint",
        "package_sha256": str(binding.get("package_sha256") or ""),
        "binding_digest": str(binding.get("binding_digest") or ""),
        "canon_digest": str(binding.get("canon_digest") or ""),
        "episode_id": str(binding.get("episode_id") or ""),
        "episode_title": str(binding.get("episode_title") or ""),
        "episode_version_id": str(binding.get("episode_version_id") or ""),
        "duration_seconds": int(canon.get("duration_seconds") or 0),
        "character_count": int(counts.get("characters") or 0),
        "scene_count": int(counts.get("scenes") or 0),
        "shot_count": int(counts.get("shots") or 0),
        "asset_count": int(counts.get("assets") or 0),
        "audio_item_count": int(counts.get("audio_items") or 0),
        "pending_media_count": int(readiness.get("pending_media_count") or 0),
        "provider_needed_count": int(readiness.get("provider_needed_count") or 0),
        "all_assets_ready": readiness.get("all_assets_ready") is True,
        "creator_decision_ref": str(binding.get("creator_decision_ref") or ""),
        "propagation_complete": binding.get("propagation_complete") is True,
        "lineage": lineage,
    }


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
