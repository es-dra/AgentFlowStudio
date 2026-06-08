from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

from agentflow.contracts.project_manifest import validate_project_manifest
from apps.api.runtime_models import ProjectImportRequest
from apps.api.runtime_store import RuntimeStore, project_summary, read_json, reject_unsafe_payload


NON_CLAIMS = ["not human acceptance", "not business validation", "not durable memory"]


def register_runtime_v02_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.get("/projects")
    def list_projects() -> dict[str, Any]:
        return {
            "projects": store.list_project_summaries(),
            "safe_ref_policy": "frontend receives summaries and artifact_id refs only",
            "non_claims": NON_CLAIMS,
        }

    @app.post("/projects/import")
    def import_project(request: ProjectImportRequest) -> dict[str, Any]:
        try:
            manifest = store.import_project_manifest(request.manifest)
            artifact = store.register_artifact(store.project_manifest_path(str(manifest["project_id"])), role="project_manifest")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "project_id": manifest["project_id"],
            "manifest": manifest,
            "summary": project_summary(manifest, artifact),
            "artifact": artifact,
            "non_claims": NON_CLAIMS,
        }

    @app.get("/projects/{project_id}/export")
    def export_project(project_id: str) -> dict[str, Any]:
        path = store.project_manifest_path(project_id)
        if not path.exists():
            raise HTTPException(status_code=404, detail="project manifest not found")
        manifest = read_json(path)
        reject_unsafe_payload(manifest)
        validate_project_manifest(manifest)
        artifact = store.register_artifact(path, role="project_manifest")
        return {
            "project_id": project_id,
            "download_filename": f"{project_id}.project_manifest.json",
            "manifest": manifest,
            "artifact": artifact,
            "non_claims": NON_CLAIMS,
        }


__all__ = ("NON_CLAIMS", "register_runtime_v02_routes")
