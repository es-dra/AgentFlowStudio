from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from agentflow_studio.production.manga_first_l4a import (
    MangaFirstBrief,
    MangaFirstError,
    MangaFirstReferenceApprovalError,
    approve_manga_first_reference_set,
    build_manga_first_provider_call_plan,
    build_studio_demo_projection,
    compile_manga_first_manifest,
    load_manga_first_studio_workspace,
    manga_first_gap_map,
    persist_manga_first_project,
)
from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_episode_domain_contract import TenantScope
from apps.api.runtime_episode_domain_routes import LOCAL_ACTOR_ID, LOCAL_ORG_ID
from apps.api.runtime_episode_domain_store import AggregateVersionConflictError
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_store import RuntimeStore


class MangaFirstCompilePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: MangaFirstBrief
    include_manifest: bool = Field(default=True)


class MangaFirstProductionTruthRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: MangaFirstBrief
    idempotency_key: str = Field(min_length=1, max_length=160)
    include_manifest: bool = Field(default=False)


class MangaFirstReferenceApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1, max_length=160)
    expected_aggregate_version: int = Field(ge=1)
    reference_set_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    idempotency_key: str = Field(min_length=1, max_length=160)


def register_runtime_manga_first_l4a_routes(
    app: FastAPI,
    store: RuntimeStore,
    auth: RuntimeAuthStore,
) -> None:
    @app.post("/projects/{project_id}/manga-first-l4a/compile-preview")
    def compile_preview(
        project_id: str,
        body: MangaFirstCompilePreviewRequest,
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        if body.brief.project_id != project_id:
            raise HTTPException(
                status_code=422,
                detail=safe_error_detail(
                    "manga_first_project_mismatch",
                    message="brief.project_id must match the route project_id.",
                    project_id=project_id,
                    action="manga_first_l4a_compile_preview",
                    stage="validation",
                ),
            )
        try:
            manifest = compile_manga_first_manifest(body.brief)
        except (ValueError, ValidationError) as exc:
            raise HTTPException(
                status_code=422,
                detail=safe_error_detail(
                    "manga_first_l4a_invalid_brief",
                    message=str(exc),
                    project_id=project_id,
                    action="manga_first_l4a_compile_preview",
                    stage="validation",
                ),
            ) from exc
        projection = build_studio_demo_projection(manifest)
        response: dict[str, Any] = {
            "schema_version": "afs.manga_first_l4a.compile_preview_response.v0.1",
            "project_id": project_id,
            "provider_dispatch_count": 0,
            "studio_projection": projection,
            "manifest_sha256": manifest.manifest_sha256,
            "non_claims": [
                "not_provider_smoke",
                "not_generated_media_qa",
                "not_human_acceptance",
                "not_business_validation",
                "not_owner_facing_release",
            ],
        }
        if body.include_manifest:
            response["manifest"] = manifest.model_dump(mode="json")
        return response

    @app.post("/projects/{project_id}/manga-first-l4b/production-truth")
    def create_production_truth(
        project_id: str,
        body: MangaFirstProductionTruthRequest,
        request: Request,
    ) -> dict[str, Any]:
        user = _enforce_project_access(auth, request, project_id)
        if body.brief.project_id != project_id:
            raise _validation_error(project_id, "brief.project_id must match the route project_id.")
        scope = _scope_for_project(user, project_id)
        try:
            manifest = compile_manga_first_manifest(body.brief)
            persisted = persist_manga_first_project(
                store,
                manifest,
                scope=scope,
                idempotency_key=body.idempotency_key,
            )
            provider_plan = build_manga_first_provider_call_plan(manifest)
        except AggregateVersionConflictError as exc:
            raise HTTPException(
                status_code=409,
                detail=safe_error_detail(
                    "manga_first_l4b_existing_aggregate_requires_migration",
                    message=str(exc),
                    project_id=project_id,
                    action="manga_first_l4b_create_production_truth",
                    stage="aggregate_persistence",
                    details={"gap_map": list(manga_first_gap_map())},
                ),
            ) from exc
        except (ValueError, ValidationError, MangaFirstError) as exc:
            raise _validation_error(project_id, str(exc)) from exc
        response: dict[str, Any] = {
            "schema_version": "afs.manga_first_l4b.production_truth_response.v0.1",
            "project_id": project_id,
            "provider_dispatch_count": 0,
            "manifest_sha256": persisted.manifest.manifest_sha256,
            "aggregate": {
                "store": "EpisodeDomainAggregateStore",
                "aggregate_version": persisted.aggregate_result.aggregate.aggregate_version,
                "aggregate_sha256": persisted.aggregate_result.aggregate_sha256,
                "replayed": persisted.aggregate_result.replayed,
            },
            "artifacts": {
                "manifest": persisted.manifest_artifact,
                "checkpoint_ledger": persisted.checkpoint_artifact,
            },
            "reference_approval_gate": persisted.studio_workspace["reference_approval_gate"],
            "studio_workspace": persisted.studio_workspace,
            "provider_call_plan": provider_plan,
            "non_claims": [
                "not_provider_smoke",
                "not_generated_media_qa",
                "not_human_acceptance",
                "not_business_validation",
                "not_owner_facing_release",
            ],
        }
        if body.include_manifest:
            response["manifest"] = persisted.manifest.model_dump(mode="json")
        return response

    @app.get("/projects/{project_id}/manga-first-l4b/workspace")
    def load_workspace(project_id: str, request: Request) -> dict[str, Any]:
        user = _enforce_project_access(auth, request, project_id)
        scope = _scope_for_project(user, project_id)
        try:
            workspace = load_manga_first_studio_workspace(store, project_id=project_id, scope=scope)
        except (KeyError, FileNotFoundError) as exc:
            raise HTTPException(
                status_code=404,
                detail=safe_error_detail(
                    "manga_first_l4b_workspace_not_found",
                    message="Manga-first L4B workspace has not been persisted for this project.",
                    project_id=project_id,
                    action="manga_first_l4b_load_workspace",
                    stage="workspace_load",
                ),
            ) from exc
        return {
            "schema_version": "afs.manga_first_l4b.workspace_response.v0.1",
            "project_id": project_id,
            "provider_dispatch_count": 0,
            "studio_workspace": workspace,
        }

    @app.post("/projects/{project_id}/manga-first-l4b/reference-set-approvals")
    def approve_reference_set(
        project_id: str,
        body: MangaFirstReferenceApprovalRequest,
        request: Request,
    ) -> dict[str, Any]:
        user = _enforce_project_access(auth, request, project_id)
        scope = _scope_for_project(user, project_id)
        try:
            approved = approve_manga_first_reference_set(
                store,
                scope=scope,
                decision_id=body.decision_id,
                expected_aggregate_version=body.expected_aggregate_version,
                reference_set_digest_value=body.reference_set_digest,
                idempotency_key=body.idempotency_key,
            )
            workspace = load_manga_first_studio_workspace(store, project_id=project_id, scope=scope)
        except AggregateVersionConflictError as exc:
            raise HTTPException(
                status_code=409,
                detail=safe_error_detail(
                    "manga_first_l4b_reference_approval_cas_conflict",
                    message=str(exc),
                    project_id=project_id,
                    action="manga_first_l4b_approve_reference_set",
                    stage="aggregate_cas",
                ),
            ) from exc
        except MangaFirstReferenceApprovalError as exc:
            raise HTTPException(
                status_code=409,
                detail=safe_error_detail(
                    "manga_first_l4b_reference_approval_rejected",
                    message=str(exc),
                    project_id=project_id,
                    action="manga_first_l4b_approve_reference_set",
                    stage="reference_approval",
                ),
            ) from exc
        except (KeyError, FileNotFoundError) as exc:
            raise HTTPException(
                status_code=404,
                detail=safe_error_detail(
                    "manga_first_l4b_workspace_not_found",
                    message="Manga-first L4B workspace has not been persisted for this project.",
                    project_id=project_id,
                    action="manga_first_l4b_approve_reference_set",
                    stage="workspace_load",
                ),
            ) from exc
        return {
            "schema_version": "afs.manga_first_l4b.reference_approval_response.v0.1",
            "project_id": project_id,
            "provider_dispatch_count": 0,
            "aggregate": {
                "store": "EpisodeDomainAggregateStore",
                "aggregate_version": approved.aggregate_result.aggregate.aggregate_version,
                "aggregate_sha256": approved.aggregate_result.aggregate_sha256,
                "replayed": approved.aggregate_result.replayed,
            },
            "reference_approval_gate": approved.reference_approval_gate,
            "decision_ref": approved.decision_ref,
            "studio_workspace": workspace,
            "non_claims": [
                "not_provider_smoke",
                "not_creative_qa",
                "not_human_final_acceptance",
                "not_business_validation",
                "not_owner_facing_release",
            ],
        }


def _enforce_project_access(auth: RuntimeAuthStore, request: Request, project_id: str) -> dict[str, Any] | None:
    if not auth.enabled():
        return None
    user = auth.require_user(request)
    if not auth.user_can_access_project(str(user["user_id"]), project_id):
        raise HTTPException(status_code=403, detail="project access denied")
    return dict(user)


def _scope_for_project(user: dict[str, Any] | None, project_id: str) -> TenantScope:
    actor_id = str(user["user_id"]) if user else LOCAL_ACTOR_ID
    return TenantScope(
        org_id=str(user["user_id"]) if user else LOCAL_ORG_ID,
        project_id=project_id,
        actor_id=actor_id,
    )


def _validation_error(project_id: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail=safe_error_detail(
            "manga_first_l4b_invalid_brief",
            message=message,
            project_id=project_id,
            action="manga_first_l4b_create_production_truth",
            stage="validation",
        ),
    )


__all__ = (
    "MangaFirstCompilePreviewRequest",
    "MangaFirstProductionTruthRequest",
    "MangaFirstReferenceApprovalRequest",
    "register_runtime_manga_first_l4a_routes",
)
