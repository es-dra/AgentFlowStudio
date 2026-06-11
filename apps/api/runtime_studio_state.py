from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agentflow.harness.json_io import write_json
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id


FORBIDDEN_STUDIO_KEYS = {
    "api_key",
    "secret",
    "token",
    "cookie",
    "authorization",
    "provider_config",
    "signed_url",
    "provider_raw",
    "provider_response",
    "raw_response",
    "media_bytes",
    "trace",
    "knowledge_weights",
    "hidden_memory",
}
LOCAL_PATH_PATTERN = re.compile(r"([a-zA-Z]:\\|/Users/|/home/|data/processed/runs)")


class StudioStateRequest(BaseModel):
    state: dict[str, Any] = Field(default_factory=dict)


def register_runtime_studio_state_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.get("/projects/{project_id}/studio-state")
    def get_studio_state(project_id: str) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        path = _state_path(store, project_id)
        if not path.exists():
            return {"project_id": project_id, "source": "empty", "state": None}
        payload = read_json(path)
        reject_unsafe_payload(payload)
        return {"project_id": project_id, "source": "runtime", "state": payload.get("state")}

    @app.put("/projects/{project_id}/studio-state")
    def put_studio_state(project_id: str, request: StudioStateRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        try:
            state = sanitize_studio_state(request.state)
            reject_unsafe_payload(state)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        payload = {
            "artifact_type": "afs_studio_state",
            "schema_version": "0.2.0",
            "project_id": project_id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "state": state,
            "does_not_store_secrets": True,
            "does_not_store_private_asset_bytes": True,
        }
        write_json(_state_path(store, project_id), payload)
        return {"project_id": project_id, "source": "runtime", "saved": True, "state": state}


def sanitize_studio_state(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("studio state must be an object")
    _reject_forbidden(value)
    return {
        "meta": _meta(value.get("meta")),
        "viewport": _viewport(value.get("viewport")),
        "nodes": _nodes(value.get("nodes")),
        "edges": _edges(value.get("edges")),
        "order": _order(value.get("order"), value.get("nodes")),
        "assets": _assets(value.get("assets")),
    }


def _state_path(store: RuntimeStore, project_id: str):
    return store.projects_dir / safe_id(project_id) / "studio_state.json"


def _meta(value: Any) -> dict[str, Any]:
    data = value if isinstance(value, dict) else {}
    return {
        "projectName": _text(data.get("projectName"), "未命名项目", 80),
        "canvasName": _text(data.get("canvasName"), "画布 1", 80),
        "seq": _number(data.get("seq"), 1),
        "updated_at": _text(data.get("updated_at"), "", 80),
    }


def _viewport(value: Any) -> dict[str, float]:
    data = value if isinstance(value, dict) else {}
    return {
        "x": _number(data.get("x"), 0),
        "y": _number(data.get("y"), 0),
        "scale": max(0.18, min(2.6, _number(data.get("scale"), 1))),
    }


def _nodes(value: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    source = value if isinstance(value, dict) else {}
    for raw_id, node in source.items():
        if not isinstance(node, dict):
            continue
        node_id = safe_id(str(raw_id))
        params = node.get("params") if isinstance(node.get("params"), dict) else {}
        safe_params = {
            key: params[key]
            for key in (
                "model",
                "spec",
                "camera",
                "motion",
                "styleRef",
                "attachments",
                "directorSetup",
                "isReference",
                "intent",
            )
            if key in params
        }
        result[node_id] = {
            "id": node_id,
            "type": _text(node.get("type"), "text", 40),
            "title": _text(node.get("title"), "未命名节点", 120),
            "x": _number(node.get("x"), 0),
            "y": _number(node.get("y"), 0),
            "w": _number(node.get("w"), 280),
            "h": _number(node.get("h"), 280),
            "prompt": _text(node.get("prompt"), "", 4000),
            "content": _text(node.get("content"), "", 8000),
            "params": _jsonable(safe_params),
            "status": _text(node.get("status"), "idle", 40),
            "result": _text(node.get("result"), "", 4000),
            "collapsed": bool(node.get("collapsed")),
        }
    return result


def _edges(value: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    source = value if isinstance(value, dict) else {}
    for raw_id, edge in source.items():
        if not isinstance(edge, dict):
            continue
        edge_id = safe_id(str(raw_id))
        relation = _text(edge.get("relation_type") or edge.get("relationType"), "generation", 40)
        if relation not in {"generation", "director", "reference"}:
            relation = "generation"
        result[edge_id] = {
            "id": edge_id,
            "from": safe_id(str(edge.get("from", ""))),
            "to": safe_id(str(edge.get("to", ""))),
            "relation_type": relation,
        }
    return result


def _assets(value: Any) -> list[dict[str, Any]]:
    source = value if isinstance(value, list) else []
    result: list[dict[str, Any]] = []
    for item in source[:300]:
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "id": safe_id(str(item.get("id", f"asset_{len(result) + 1}"))),
                "kind": _text(item.get("kind") or item.get("type"), "reference", 60),
                "title": _text(item.get("title"), "未命名资产", 120),
                "safe_summary": _text(item.get("safe_summary") or item.get("summary"), "", 1000),
                "thumbnail_ref": _text(item.get("thumbnail_ref"), "", 160),
                "source_node_id": _text(item.get("source_node_id") or item.get("nodeId"), "", 80) or None,
                "status": _text(item.get("status"), "ready", 40),
            }
        )
    return result


def _order(value: Any, nodes: Any) -> list[str]:
    if isinstance(value, list):
        return [safe_id(str(item)) for item in value]
    if isinstance(nodes, dict):
        return [safe_id(str(item)) for item in nodes]
    return []


def _reject_forbidden(value: Any) -> None:
    serialized = json.dumps(value, ensure_ascii=False)
    lowered = serialized.lower()
    for key in FORBIDDEN_STUDIO_KEYS:
        if key in lowered:
            raise ValueError(f"studio state contains forbidden field: {key}")
    if LOCAL_PATH_PATTERN.search(serialized):
        raise ValueError("studio state contains local path or runtime artifact path")


def _text(value: Any, fallback: str, max_length: int) -> str:
    text = str(value if value is not None else fallback)
    if LOCAL_PATH_PATTERN.search(text):
        raise ValueError("studio state contains local path or runtime artifact path")
    return text[:max_length]


def _number(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _jsonable(value: Any) -> Any:
    dumped = json.dumps(value, ensure_ascii=False)
    _reject_forbidden(value)
    return json.loads(dumped)


__all__ = ("register_runtime_studio_state_routes", "sanitize_studio_state")
