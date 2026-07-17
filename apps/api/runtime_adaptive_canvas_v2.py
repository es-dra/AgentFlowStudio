from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request

from agentflow_studio.production.adaptive_canvas_v2 import load_adaptive_workspace
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
