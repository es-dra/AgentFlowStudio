from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from agentflow_studio.production.adaptive_canvas_v2 import load_adaptive_workspace
from agentflow_studio.production.media_operations_review import (
    build_media_operations_command_preview,
    load_media_operations_review,
    media_file_path,
)
from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_store import RuntimeStore


def register_runtime_adaptive_canvas_v2_routes(
    app: FastAPI,
    store: RuntimeStore,
    auth: RuntimeAuthStore,
) -> None:
    @app.get("/projects/{project_id}/adaptive-canvas-v2/workspace")
    def adaptive_canvas_workspace(
        project_id: str,
        request: Request,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        try:
            workspace = load_adaptive_workspace(store, project_id=project_id, run_id=run_id)
        except KeyError as exc:
            raise HTTPException(
                status_code=404,
                detail=safe_error_detail(
                    "adaptive_canvas_v2_workspace_not_found",
                    message="Adaptive Canvas v2 production workspace is not available for this project.",
                    project_id=project_id,
                    action="adaptive_canvas_v2_workspace",
                    stage="workspace_load",
                ),
            ) from exc
        return workspace

    @app.get("/projects/{project_id}/adaptive-canvas-v2/operations-review")
    def adaptive_canvas_operations_review(
        project_id: str,
        request: Request,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        try:
            return load_media_operations_review(store, project_id=project_id, run_id=run_id)
        except KeyError as exc:
            raise HTTPException(
                status_code=404,
                detail=safe_error_detail(
                    "adaptive_canvas_v2_operations_not_found",
                    message="Production media operations review is not available for this project.",
                    project_id=project_id,
                    action="adaptive_canvas_v2_operations_review",
                    stage="operations_review_load",
                ),
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=safe_error_detail(
                    "adaptive_canvas_v2_operations_invalid",
                    message="Production media operations review failed safety validation.",
                    project_id=project_id,
                    action="adaptive_canvas_v2_operations_review",
                    stage="operations_review_validate",
                ),
            ) from exc

    @app.post("/projects/{project_id}/adaptive-canvas-v2/operations/command-preview")
    def adaptive_canvas_operations_command_preview(
        project_id: str,
        body: dict[str, Any],
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        try:
            return build_media_operations_command_preview(
                store,
                project_id=project_id,
                run_id=str(body.get("run_id") or "") or None,
                action=str(body.get("action") or ""),
                shot_id=str(body.get("shot_id") or "") or None,
            )
        except KeyError as exc:
            raise HTTPException(
                status_code=404,
                detail=safe_error_detail(
                    "adaptive_canvas_v2_operations_not_found",
                    message="Production media operations command preview is not available for this project.",
                    project_id=project_id,
                    action="adaptive_canvas_v2_operations_command_preview",
                    stage="operations_command_preview_load",
                ),
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=safe_error_detail(
                    "adaptive_canvas_v2_operations_invalid_command",
                    message=str(exc)[:180] or "Production media operation command is not valid.",
                    project_id=project_id,
                    action="adaptive_canvas_v2_operations_command_preview",
                    stage="operations_command_preview_validate",
                ),
            ) from exc

    @app.get("/projects/{project_id}/adaptive-canvas-v2/media/{media_kind}/{media_id}")
    def adaptive_canvas_media_preview(
        project_id: str,
        media_kind: str,
        media_id: str,
        request: Request,
        run_id: str | None = None,
    ) -> FileResponse:
        _enforce_project_access(auth, request, project_id)
        try:
            path, media_type = media_file_path(
                store,
                project_id=project_id,
                run_id=run_id,
                media_kind=media_kind,
                media_id=media_id,
            )
        except (KeyError, ValueError) as exc:
            raise HTTPException(
                status_code=404,
                detail=safe_error_detail(
                    "adaptive_canvas_v2_media_not_found",
                    message="Production media preview is not available.",
                    project_id=project_id,
                    action="adaptive_canvas_v2_media_preview",
                    stage="media_preview_load",
                ),
            ) from exc
        return FileResponse(path, media_type=media_type, headers={"Cache-Control": "no-store"})

    @app.get("/projects/{project_id}/real-anime-4shot/workspace")
    def real_anime_4shot_workspace(
        project_id: str,
        request: Request,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        try:
            workspace = load_adaptive_workspace(store, project_id=project_id, run_id=run_id)
        except KeyError as exc:
            raise HTTPException(
                status_code=404,
                detail=safe_error_detail(
                    "real_anime_4shot_workspace_not_found",
                    message="Real anime 4-shot workspace is not available for this project.",
                    project_id=project_id,
                    action="real_anime_4shot_workspace",
                    stage="workspace_load",
                ),
            ) from exc
        return {**workspace, "test_profile": "real_anime_4shot_paid_v1"}


def _enforce_project_access(auth: RuntimeAuthStore, request: Request, project_id: str) -> dict[str, Any] | None:
    if not auth.enabled():
        return None
    user = auth.require_user(request)
    if not auth.user_can_access_project(str(user["user_id"]), project_id):
        raise HTTPException(status_code=403, detail="project access denied")
    return user
