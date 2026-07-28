from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request

from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_production_graph import (
    GraphIntegrityError,
    ProductionGraphStore,
    graph_path,
)
from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_store import reject_unsafe_payload
from apps.api.runtime_studio_models import StudioSurface, StudioSurfaceEnvelope
from apps.api.runtime_studio_projection import (
    build_studio_surface_envelope,
)


def register_runtime_studio_bff_routes(
    app: FastAPI,
    store: RuntimeStore,
    auth: RuntimeAuthStore,
) -> None:
    @app.get(
        "/api/v1/projects/{project_id}/studio",
        tags=["studio-v1"],
        response_model=StudioSurfaceEnvelope,
    )
    def studio_surface(
        project_id: str,
        request: Request,
        surface: StudioSurface = Query(default="canvas"),
    ) -> StudioSurfaceEnvelope:
        _require_project_access(store, auth, request, project_id)
        payload = build_studio_surface_envelope(
            project_id=project_id,
            manifest=store.ensure_project_manifest(project_id),
            graph=_load_authoritative_graph(store, project_id),
            surface=surface,
        )
        try:
            reject_unsafe_payload(payload)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail="studio projection failed safety check") from exc
        return StudioSurfaceEnvelope.model_validate(payload)


def _load_authoritative_graph(store: RuntimeStore, project_id: str) -> dict[str, Any] | None:
    if not graph_path(store, project_id).is_file():
        return None
    try:
        graph = ProductionGraphStore(store).load(project_id)
    except GraphIntegrityError as exc:
        raise HTTPException(status_code=409, detail="production graph integrity check failed") from exc
    return graph if graph.get("nodes") else None


def _require_project_access(
    store: RuntimeStore,
    auth: RuntimeAuthStore,
    request: Request,
    project_id: str,
) -> None:
    if not project_id or store.is_project_deleted(project_id) or not store.project_manifest_path(project_id).is_file():
        raise HTTPException(status_code=404, detail="project not found")
    if not auth.enabled():
        return
    user = auth.require_user(request)
    if not auth.user_can_access_project(str(user.get("user_id") or ""), project_id):
        raise HTTPException(status_code=403, detail="project access denied")


__all__ = ("register_runtime_studio_bff_routes",)
