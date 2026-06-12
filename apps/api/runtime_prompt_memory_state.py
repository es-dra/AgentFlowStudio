from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from apps.api.runtime_prompt_memory_constants import PROMPT_MEMORY_NON_CLAIMS
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id


BACKGROUND_FIELDS = ("characters", "scenes", "style_preferences", "user_preferences")


def load_creative_memory_state(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    path = _creative_memory_path(store, project_id)
    if path.exists():
        state = read_json(path)
    else:
        state = _default_state(project_id)
    for field in (*BACKGROUND_FIELDS, "extracted_context"):
        if not isinstance(state.get(field), list):
            state[field] = []
    state["writes_long_term_memory"] = False
    state["writes_company_kb"] = False
    state["non_claims"] = PROMPT_MEMORY_NON_CLAIMS
    if any(state.get(field) for field in BACKGROUND_FIELDS):
        state["legacy_background_context"] = True
    reject_unsafe_payload(state)
    return state


def write_creative_memory_state(store: RuntimeStore, project_id: str, state: dict[str, Any]) -> Path:
    reject_unsafe_payload(state)
    path = _creative_memory_path(store, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, state)
    return path


def background_context_refs(state: dict[str, Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for field in BACKGROUND_FIELDS:
        for item in _list(state.get(field)):
            if isinstance(item, dict):
                refs.append(
                    {
                        "memory_id": str(item.get("memory_id") or ""),
                        "memory_type": str(item.get("memory_type") or ""),
                        "label": str(item.get("label") or ""),
                        "priority": str(item.get("priority") or _priority_for_type(str(item.get("memory_type") or ""))),
                    }
                )
    return refs


def extracted_context_refs(extracted: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "memory_id": str(item.get("memory_id") or ""),
            "memory_type": str(item.get("memory_type") or ""),
            "label": str(item.get("label") or ""),
            "source": "prompt_optimization_background",
        }
        for item in extracted
        if isinstance(item, dict)
    ]


def merge_background_context(state: dict[str, Any], extracted: list[dict[str, Any]]) -> dict[str, Any]:
    for item in extracted:
        if not isinstance(item, dict):
            continue
        field = _field_for_type(str(item.get("memory_type") or "user_preference"))
        existing = [entry for entry in _list(state.get(field)) if isinstance(entry, dict)]
        if all(_dedupe_key(entry) != _dedupe_key(item) for entry in existing):
            existing.append(item)
        state[field] = existing
    existing_context = [entry for entry in _list(state.get("extracted_context")) if isinstance(entry, dict)]
    known_ids = {str(entry.get("memory_id") or "") for entry in existing_context}
    state["extracted_context"] = [
        *existing_context,
        *[item for item in extracted if isinstance(item, dict) and str(item.get("memory_id") or "") not in known_ids],
    ]
    return state


def append_extracted_context(
    state: dict[str, Any],
    extracted: list[dict[str, Any]],
    *,
    limit: int = 80,
) -> dict[str, Any]:
    existing_context = [entry for entry in _list(state.get("extracted_context")) if isinstance(entry, dict)]
    known_ids = {str(entry.get("memory_id") or "") for entry in existing_context}
    merged = [
        *existing_context,
        *[item for item in extracted if isinstance(item, dict) and str(item.get("memory_id") or "") not in known_ids],
    ]
    state["extracted_context"] = merged[-limit:]
    state["legacy_background_context"] = any(state.get(field) for field in BACKGROUND_FIELDS)
    return state


def background_memory_record(
    project_id: str,
    memory_type: str,
    label: str,
    summary: str,
    generated_at: str,
    *,
    source_node_id: str | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    digest = hashlib.sha1(f"{project_id}:{memory_type}:{label}:{generated_at}".encode("utf-8")).hexdigest()[:8]
    return {
        "memory_id": f"context-{memory_type}-{safe_id(label)}-{digest}",
        "memory_type": memory_type,
        "label": label,
        "summary": summary,
        "source": "prompt_optimization_background",
        "source_node_id": source_node_id,
        "confidence": confidence,
        "created_at": generated_at,
        "priority": _priority_for_type(memory_type),
        "durable_memory": False,
    }


def public_background_counts(state: dict[str, Any]) -> dict[str, int]:
    return {field: len(_list(state.get(field))) for field in BACKGROUND_FIELDS}


def _default_state(project_id: str) -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_creative_memory_state",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "characters": [],
        "scenes": [],
        "style_preferences": [],
        "user_preferences": [],
        "extracted_context": [],
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": PROMPT_MEMORY_NON_CLAIMS,
    }


def _creative_memory_path(store: RuntimeStore, project_id: str) -> Path:
    return store.root / "creative_memory" / safe_id(project_id) / "creative_memory_state.json"


def _field_for_type(memory_type: str) -> str:
    return {
        "character": "characters",
        "scene": "scenes",
        "style_preference": "style_preferences",
        "user_preference": "user_preferences",
    }.get(memory_type, "user_preferences")


def _priority_for_type(memory_type: str) -> str:
    return {
        "character": "script_character_scene_assets",
        "scene": "script_character_scene_assets",
        "style_preference": "user_preferences",
        "user_preference": "user_preferences",
    }.get(memory_type, "user_preferences")


def _dedupe_key(item: dict[str, Any]) -> tuple[str, str]:
    return (str(item.get("memory_type") or ""), str(item.get("label") or "").casefold())


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "background_context_refs",
    "background_memory_record",
    "append_extracted_context",
    "extracted_context_refs",
    "load_creative_memory_state",
    "merge_background_context",
    "public_background_counts",
    "write_creative_memory_state",
)
