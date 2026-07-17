from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from agentflow_studio.production.manga_first_l4a import (
    MangaFirstBrief,
    build_studio_demo_projection,
    compile_manga_first_manifest,
)
from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_store import RuntimeStore


class MangaFirstCompilePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: MangaFirstBrief
    include_manifest: bool = Field(default=True)


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


def _enforce_project_access(auth: RuntimeAuthStore, request: Request, project_id: str) -> None:
    if not auth.enabled():
        return
    user = auth.require_user(request)
    if not auth.user_can_access_project(str(user["user_id"]), project_id):
        raise HTTPException(status_code=403, detail="project access denied")


__all__ = ("MangaFirstCompilePreviewRequest", "register_runtime_manga_first_l4a_routes")
