from __future__ import annotations

import hashlib
from typing import Any

from agentflow.harness.json_io import write_json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id


SPRITE_MEMORY_SCHEMA_VERSION = "afs_sprite_project_memory.v0.1"
SPRITE_MEMORY_TYPES = {
    "style_preference",
    "workflow_preference",
    "negative_preference",
    "collaboration_preference",
}
SPRITE_MEMORY_UNSAFE_FRAGMENTS = (
    "provider raw",
    "raw provider",
    "signed url",
    "signed_url",
    "customer:",
    "customer ",
    "client:",
    "client ",
    "private customer",
)


class SpriteMemoryWriteRequest(BaseModel):
    memory_type: str = Field(min_length=1)
    label: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=600)
    source_message_id: str = ""
    scope: str = "project"
    confidence: float | None = None
    user_confirmed: bool = False
    created_at: str = Field(min_length=1)


def register_runtime_sprite_memory_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.get("/projects/{project_id}/sprite/memory")
    def list_sprite_memory(project_id: str) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        return public_sprite_memory_state(load_sprite_memory_state(store, project_id))

    @app.post("/projects/{project_id}/sprite/memory")
    def write_sprite_memory(project_id: str, request: SpriteMemoryWriteRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        try:
            state = load_sprite_memory_state(store, project_id)
            memory = sprite_memory_record(project_id, request)
            state["memories"] = [item for item in state["memories"] if item.get("memory_id") != memory["memory_id"]]
            state["memories"].append(memory)
            write_sprite_memory_state(store, project_id, state)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_sprite_memory")) from exc
        return {
            "project_id": project_id,
            "memory": memory,
            "state": public_sprite_memory_state(state),
        }

    @app.delete("/projects/{project_id}/sprite/memory/{memory_id}")
    def delete_sprite_memory(project_id: str, memory_id: str) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        state = load_sprite_memory_state(store, project_id)
        before = len(state["memories"])
        state["memories"] = [item for item in state["memories"] if item.get("memory_id") != memory_id]
        deleted = len(state["memories"]) != before
        write_sprite_memory_state(store, project_id, state)
        return {
            "project_id": project_id,
            "memory_id": memory_id,
            "deleted": deleted,
            "state": public_sprite_memory_state(state),
        }

    @app.post("/projects/{project_id}/sprite/memory/clear")
    def clear_sprite_memory(project_id: str) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        state = load_sprite_memory_state(store, project_id)
        cleared = bool(state["memories"])
        state["memories"] = []
        write_sprite_memory_state(store, project_id, state)
        return {
            "project_id": project_id,
            "cleared": cleared,
            "state": public_sprite_memory_state(state),
        }


def load_sprite_memory_state(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    path = _sprite_memory_path(store, project_id)
    state = read_json(path) if path.exists() else _default_state(project_id)
    if not isinstance(state.get("memories"), list):
        state["memories"] = []
    state["schema_version"] = SPRITE_MEMORY_SCHEMA_VERSION
    state["writes_company_kb"] = False
    state["writes_long_term_memory"] = False
    state["non_claims"] = ["not Company OS durable memory", "not business validation", "not human acceptance"]
    reject_unsafe_payload(state)
    _reject_sprite_memory_unsafe_text(state)
    return state


def write_sprite_memory_state(store: RuntimeStore, project_id: str, state: dict[str, Any]) -> None:
    reject_unsafe_payload(state)
    _reject_sprite_memory_unsafe_text(state)
    path = _sprite_memory_path(store, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, state)


def sprite_memory_record(project_id: str, request: SpriteMemoryWriteRequest) -> dict[str, Any]:
    if not request.user_confirmed:
        raise ValueError("sprite memory requires user confirmation")
    memory_type = request.memory_type.strip()
    if memory_type not in SPRITE_MEMORY_TYPES:
        raise ValueError("unsupported sprite memory type")
    scope = request.scope.strip() or "project"
    if scope != "project":
        raise ValueError("sprite memory scope must be project")
    seed = f"{project_id}:{memory_type}:{request.label.strip()}:{request.created_at}".encode("utf-8")
    memory = {
        "memory_id": f"sprite-{memory_type}-{safe_id(request.label)}-{hashlib.sha1(seed).hexdigest()[:8]}",
        "memory_type": memory_type,
        "label": request.label.strip(),
        "summary": request.summary.strip(),
        "source_message_id": request.source_message_id.strip(),
        "scope": scope,
        "confidence": request.confidence,
        "user_confirmed": True,
        "created_at": request.created_at.strip(),
        "writes_company_kb": False,
        "writes_long_term_memory": False,
    }
    reject_unsafe_payload(memory)
    _reject_sprite_memory_unsafe_text(memory)
    return memory


def public_sprite_memory_state(state: dict[str, Any]) -> dict[str, Any]:
    memories = [item for item in state.get("memories", []) if isinstance(item, dict)]
    return {
        "artifact_type": "agentflow_sprite_project_memory",
        "schema_version": SPRITE_MEMORY_SCHEMA_VERSION,
        "project_id": str(state.get("project_id") or ""),
        "memories": memories,
        "memory_count": len(memories),
        "writes_company_kb": False,
        "writes_long_term_memory": False,
        "non_claims": state.get("non_claims", []),
    }


def _default_state(project_id: str) -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_sprite_project_memory",
        "schema_version": SPRITE_MEMORY_SCHEMA_VERSION,
        "project_id": project_id,
        "memories": [],
        "writes_company_kb": False,
        "writes_long_term_memory": False,
        "non_claims": ["not Company OS durable memory", "not business validation", "not human acceptance"],
    }


def _sprite_memory_path(store: RuntimeStore, project_id: str):
    return store.projects_dir / safe_id(project_id) / "sprite_memory.json"


def _reject_sprite_memory_unsafe_text(payload: dict[str, Any]) -> None:
    lowered = str(payload).lower()
    if any(fragment in lowered for fragment in SPRITE_MEMORY_UNSAFE_FRAGMENTS):
        raise ValueError("sprite memory contains unsafe private fragment")


__all__ = (
    "load_sprite_memory_state",
    "public_sprite_memory_state",
    "register_runtime_sprite_memory_routes",
    "sprite_memory_record",
    "write_sprite_memory_state",
)
