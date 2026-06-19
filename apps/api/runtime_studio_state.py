from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agentflow.harness.json_io import write_json
from apps.api.runtime_errors import safe_exception_detail
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id
from apps.api.runtime_studio_state_sanitizer import sanitize_studio_state


class StudioStateRequest(BaseModel):
    state: dict[str, Any] = Field(default_factory=dict)
    expected_version: str = Field(default="", max_length=120)


def register_runtime_studio_state_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.get("/projects/{project_id}/studio-state")
    def get_studio_state(project_id: str) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        path = _state_path(store, project_id)
        if not path.exists():
            return {"project_id": project_id, "source": "empty", "state": None, "state_version": "", "saved_at": ""}
        payload = read_json(path)
        reject_unsafe_payload(payload)
        return {
            "project_id": project_id,
            "source": "runtime",
            "state": payload.get("state"),
            "state_version": _payload_version(payload),
            "saved_at": str(payload.get("saved_at", "")),
        }

    @app.put("/projects/{project_id}/studio-state")
    def put_studio_state(project_id: str, request: StudioStateRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        try:
            state = sanitize_studio_state(request.state, project_id=project_id)
            reject_unsafe_payload(state)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=safe_exception_detail(exc, "invalid_studio_state"),
            ) from exc

        path = _state_path(store, project_id)
        current_version = _current_state_version(path)
        expected_version = str(request.expected_version or "").strip()
        if expected_version and current_version and expected_version != current_version:
            raise HTTPException(status_code=409, detail="studio state version conflict")

        saved_at = datetime.now(timezone.utc).isoformat()
        state_version = _state_version(saved_at)
        payload = {
            "artifact_type": "afs_studio_state",
            "schema_version": "0.2.0",
            "project_id": project_id,
            "saved_at": saved_at,
            "state_version": state_version,
            "state": state,
            "does_not_store_secrets": True,
            "does_not_store_private_asset_bytes": True,
        }
        write_json(path, payload)
        return {
            "project_id": project_id,
            "source": "runtime",
            "saved": True,
            "state": state,
            "state_version": state_version,
            "saved_at": saved_at,
        }


def _state_path(store: RuntimeStore, project_id: str):
    return store.projects_dir / safe_id(project_id) / "studio_state.json"


def _current_state_version(path) -> str:
    if not path.exists():
        return ""
    try:
        return _payload_version(read_json(path))
    except (ValueError, OSError):
        return ""


def _payload_version(payload: dict[str, Any]) -> str:
    return str(payload.get("state_version") or payload.get("saved_at") or "")


def _state_version(saved_at: str) -> str:
    return f"studio_state:{safe_id(saved_at)}"


__all__ = ("register_runtime_studio_state_routes", "sanitize_studio_state")
