from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agentflow.harness.json_io import write_json
from apps.api.runtime_errors import safe_exception_detail
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
SAFE_PREVIEW_URL_PATTERN = re.compile(
    r"^/projects/([a-zA-Z0-9_.-]+)/(?:"
    r"image-assets/[a-zA-Z0-9_.-]+/preview|"
    r"keyframe-generations/[a-zA-Z0-9_.-]+/candidates/[a-zA-Z0-9_.-]+/preview|"
    r"video-generations/[a-zA-Z0-9_.-]+/candidates/[a-zA-Z0-9_.-]+/preview"
    r")$"
)
SAFE_NODE_PARAM_KEYS = (
    "model",
    "spec",
    "camera",
    "motion",
    "styleRef",
    "attachments",
    "directorSetup",
    "isReference",
    "intent",
    "uploads",
    "previewAspectRatio",
    "visualAssets",
    "visual_asset_ids",
    "firstFrameImageAssetId",
    "lastFrameImageAssetId",
    "lastVideoJobId",
    "lastVideoPreviewUrl",
    "quotaOverrideConfirmed",
    "lastContextBundle",
    )
PRUNED_RUNTIME_PARAM_KEYS = {
    "lastContextBundle",
    "temporaryLockOverrides",
}


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
            state = sanitize_studio_state(request.state, project_id=project_id)
            reject_unsafe_payload(state)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=safe_exception_detail(exc, "invalid_studio_state"),
            ) from exc

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


def sanitize_studio_state(value: dict[str, Any], *, project_id: str | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("studio state must be an object")
    _reject_forbidden_known_surfaces(value)
    sanitized = {
        "meta": _meta(value.get("meta")),
        "viewport": _viewport(value.get("viewport")),
        "nodes": _nodes(value.get("nodes"), project_id=project_id),
        "edges": _edges(value.get("edges")),
        "order": _order(value.get("order"), value.get("nodes")),
        "assets": _assets(value.get("assets"), project_id=project_id),
    }
    _reject_forbidden(sanitized)
    return sanitized


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


def _nodes(value: Any, *, project_id: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {}
    source = value if isinstance(value, dict) else {}
    for raw_id, node in source.items():
        if not isinstance(node, dict):
            continue
        node_id = safe_id(str(raw_id))
        node_type = _text(node.get("type"), "text", 40)
        params = node.get("params") if isinstance(node.get("params"), dict) else {}
        safe_params = _node_params(params, project_id=project_id)
        preview_url = _node_preview_url(node.get("previewUrl"), node_type=node_type, project_id=project_id)
        safe_node = {
            "id": node_id,
            "type": node_type,
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
        if preview_url:
            safe_node["previewUrl"] = preview_url
        result[node_id] = safe_node
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


def _assets(value: Any, *, project_id: str | None = None) -> list[dict[str, Any]]:
    source = value if isinstance(value, list) else []
    result: list[dict[str, Any]] = []
    for item in source[:300]:
        if not isinstance(item, dict):
            continue
        asset = {
            "id": safe_id(str(item.get("id", f"asset_{len(result) + 1}"))),
            "kind": _text(item.get("kind") or item.get("type"), "reference", 60),
            "title": _text(item.get("title"), "未命名资产", 120),
            "safe_summary": _text(item.get("safe_summary") or item.get("summary"), "", 1000),
            "thumbnail_ref": _text(item.get("thumbnail_ref"), "", 160),
            "source_node_id": _text(item.get("source_node_id") or item.get("nodeId"), "", 80) or None,
            "status": _text(item.get("status"), "ready", 40),
        }
        for key in ("asset_id", "visual_asset_id", "asset_type"):
            value_text = _text(item.get(key), "", 120)
            if value_text:
                asset[key] = safe_id(value_text) if key.endswith("_id") else value_text
        signature = _text(item.get("signature"), "", 1000)
        if signature:
            asset["signature"] = signature
        feature_card = _text_map(item.get("feature_card"), max_items=24, max_value_length=1000)
        if feature_card:
            asset["feature_card"] = feature_card
        negative_locks = _text_list(item.get("negative_locks"), max_items=24, max_item_length=500)
        if negative_locks:
            asset["negative_locks"] = negative_locks
        preview_url = item.get("preview_url")
        if preview_url:
            asset["preview_url"] = _preview_url(preview_url, project_id=project_id)
        result.append(asset)
    return result


def _text_map(value: Any, *, max_items: int, max_value_length: int) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key, item in list(value.items())[:max_items]:
        safe_key = safe_id(str(key))[:80]
        if not safe_key:
            continue
        safe_value = _text(item, "", max_value_length)
        if safe_value:
            result[safe_key] = safe_value
    return result


def _text_list(value: Any, *, max_items: int, max_item_length: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_text(item, "", max_item_length) for item in value[:max_items] if _text(item, "", max_item_length)]


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


def _reject_forbidden_known_surfaces(value: dict[str, Any]) -> None:
    nodes = value.get("nodes")
    if isinstance(nodes, dict):
        for node in nodes.values():
            if not isinstance(node, dict):
                continue
            _preview_url(node.get("previewUrl"))
            node_shallow = {key: item for key, item in node.items() if key not in {"params", "previewUrl"}}
            _reject_forbidden(node_shallow)
            params = node.get("params")
            if not isinstance(params, dict):
                continue
            for key, item in params.items():
                if key in PRUNED_RUNTIME_PARAM_KEYS:
                    continue
                lowered = str(key).lower()
                if any(forbidden in lowered for forbidden in FORBIDDEN_STUDIO_KEYS):
                    raise ValueError(f"studio state contains forbidden field: {key}")
                if key in SAFE_NODE_PARAM_KEYS:
                    if key == "uploads":
                        _uploads(item)
                    _reject_forbidden(item)
    assets = value.get("assets")
    if isinstance(assets, list):
        for item in assets:
            if isinstance(item, dict):
                _reject_forbidden(item)


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


def _node_params(value: dict[str, Any], *, project_id: str | None = None) -> dict[str, Any]:
    safe_params: dict[str, Any] = {}
    for key in SAFE_NODE_PARAM_KEYS:
        if key not in value:
            continue
        if key == "uploads":
            safe_params[key] = _uploads(value[key], project_id=project_id)
        elif key in {"firstFrameImageAssetId", "lastFrameImageAssetId", "lastVideoJobId"}:
            safe_params[key] = safe_id(str(value[key]))
        elif key == "lastVideoPreviewUrl":
            safe_params[key] = _preview_url(value[key], project_id=project_id)
        elif key == "quotaOverrideConfirmed":
            safe_params[key] = bool(value[key])
        elif key == "lastContextBundle":
            bundle = _context_bundle(value[key])
            if bundle:
                safe_params[key] = bundle
        else:
            safe_params[key] = value[key]
    return safe_params


def _context_bundle(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for key in ("schema_version", "resolver_version", "mode", "subject_reference_asset_id"):
        text = _text(value.get(key), "", 120)
        if text:
            result[key] = safe_id(text) if key.endswith("_id") else text
    for key in ("included_assets", "excluded_assets", "available_project_assets"):
        items = _bundle_asset_list(value.get(key))
        if items:
            result[key] = items
    warnings = _bundle_warning_list(value.get("warnings"))
    if warnings:
        result["warnings"] = warnings
    overrides = _bundle_override_list(value.get("temporary_lock_overrides"))
    if overrides:
        result["temporary_lock_overrides"] = overrides
    budget = _bundle_budget(value.get("budget"))
    if budget:
        result["budget"] = budget
    return result


def _bundle_asset_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    for item in value[:80]:
        if not isinstance(item, dict):
            continue
        asset: dict[str, Any] = {}
        for key in ("asset_id", "visual_asset_id", "source_node_id", "feature_card_hash"):
            text = _text(item.get(key), "", 160)
            if text:
                asset[key] = safe_id(text) if key.endswith("_id") or key == "source_node_id" else text
        for key in ("asset_type", "label", "signature", "status", "reason", "channel", "connected_state"):
            text = _text(item.get(key), "", 1000 if key in {"signature", "reason"} else 160)
            if text:
                asset[key] = text
        for key in ("hop_count", "hop_distance"):
            if key in item:
                asset[key] = _number(item.get(key), 0)
        if "lock_count" in item:
            asset["lock_count"] = int(_number(item.get("lock_count"), 0))
        if item.get("subject_reference") is not None:
            asset["subject_reference"] = bool(item.get("subject_reference"))
        if asset:
            result.append(asset)
    return result


def _bundle_warning_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    allowed = {
        "warning_id",
        "asset_id",
        "label",
        "lock_text",
        "attribute",
        "lock_value",
        "prompt_value",
        "reason",
    }
    for item in value[:80]:
        if not isinstance(item, dict):
            continue
        warning: dict[str, Any] = {}
        for key in allowed:
            text = _text(item.get(key), "", 500)
            if text:
                warning[key] = safe_id(text) if key.endswith("_id") else text
        if warning:
            result.append(warning)
    return result


def _bundle_override_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    for item in value[:40]:
        if not isinstance(item, dict):
            continue
        override: dict[str, Any] = {}
        asset_id = _text(item.get("asset_id"), "", 160)
        if asset_id:
            override["asset_id"] = safe_id(asset_id)
        for key in ("lock_text", "reason"):
            text = _text(item.get(key), "", 500)
            if text:
                override[key] = text
        if override:
            result.append(override)
    return result


def _bundle_budget(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for key in ("limit", "total_limit", "used", "total_used"):
        if key in value:
            result[key] = _number(value.get(key), 0)
    if "enforcement_applied" in value:
        result["enforcement_applied"] = bool(value.get("enforcement_applied"))
    segments = value.get("segments")
    if isinstance(segments, dict):
        safe_segments: dict[str, Any] = {}
        for name, segment in list(segments.items())[:20]:
            if not isinstance(segment, dict):
                continue
            safe_segment: dict[str, Any] = {}
            for key in ("allocated", "used"):
                if key in segment:
                    safe_segment[key] = _number(segment.get(key), 0)
            if "truncated" in segment:
                safe_segment["truncated"] = bool(segment.get("truncated"))
            if safe_segment:
                safe_segments[safe_id(str(name))[:80]] = safe_segment
        if safe_segments:
            result["segments"] = safe_segments
    return result


def _uploads(value: Any, *, project_id: str | None = None) -> list[Any]:
    if not isinstance(value, list):
        return []
    result: list[Any] = []
    for item in value[:24]:
        if not isinstance(item, dict):
            continue
        upload = dict(item)
        if "preview_url" in upload:
            upload["preview_url"] = _preview_url(upload.get("preview_url"), project_id=project_id)
        result.append(upload)
    return result


def _preview_url(value: Any, *, project_id: str | None = None) -> str:
    if value in {None, ""}:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    match = SAFE_PREVIEW_URL_PATTERN.fullmatch(text)
    if not match:
        raise ValueError("studio state previewUrl must be a safe Runtime preview route")
    if project_id is not None and match.group(1) != safe_id(project_id):
        raise ValueError("studio state previewUrl must belong to the current project")
    return text


def _node_preview_url(value: Any, *, node_type: str, project_id: str | None = None) -> str:
    text = _preview_url(value, project_id=project_id)
    if not text:
        return ""
    if node_type == "video" and "/video-generations/" not in text:
        return ""
    return text


__all__ = ("register_runtime_studio_state_routes", "sanitize_studio_state")
