from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


STUDIO_BFF_SCHEMA_VERSION = "afs.studio_bff.v0.1"
STUDIO_SURFACES = ("canvas", "script", "storyboard", "asset-bible", "review", "delivery")
SURFACE_CATEGORIES = {
    "script": {"input", "revision"},
    "storyboard": {"collection", "location", "unit"},
    "asset-bible": {"entity", "location", "resource"},
    "review": {"unit", "artifact"},
    "delivery": {"unit", "artifact", "delivery"},
}
PUBLIC_METADATA_KEYS = {
    "aliases",
    "appearance",
    "blocking",
    "classification",
    "display_name",
    "duration_seconds",
    "intent",
    "kind",
    "lineage",
    "name",
    "space",
    "style",
    "style_domain",
    "target_duration_seconds",
    "title",
}


def build_studio_surface_envelope(
    *,
    project_id: str,
    manifest: Mapping[str, Any],
    graph: Mapping[str, Any] | None,
    surface: str,
) -> dict[str, Any]:
    if surface not in STUDIO_SURFACES:
        raise ValueError("unsupported studio surface")
    if graph is None:
        return {
            "schema_version": STUDIO_BFF_SCHEMA_VERSION,
            "project_id": project_id,
            "project": _project_summary(manifest),
            "authority_mode": "legacy_file",
            "project_version": 0,
            "graph_digest": "",
            "surface": surface,
            "entities": [],
            "relations": [],
            "allowed_actions": _allowed_actions(surface, has_graph=False),
            "task_summaries": [],
            "review_queue": [],
            "artifact_summaries": [],
            "cost_summary": _cost_summary(),
            "recovery_summary": _recovery_summary([]),
            "provider_dispatch_count": 0,
        }

    entities = _surface_entities(graph, surface)
    entity_ids = {str(item["entity_id"]) for item in entities}
    relations = [
        {
            "from_id": str(item.get("from_id") or ""),
            "to_id": str(item.get("to_id") or ""),
            "relation_type": str(item.get("relation_type") or ""),
        }
        for item in graph.get("relations", [])
        if isinstance(item, Mapping)
        and str(item.get("from_id") or "") in entity_ids
        and str(item.get("to_id") or "") in entity_ids
    ]
    task_summaries = _task_summaries(graph)
    return {
        "schema_version": STUDIO_BFF_SCHEMA_VERSION,
        "project_id": project_id,
        "project": _project_summary(manifest),
        "authority_mode": "graph_v1",
        "project_version": int(graph.get("version") or 0),
        "graph_digest": str(graph.get("graph_digest") or ""),
        "surface": surface,
        "entities": entities,
        "relations": relations,
        "allowed_actions": _allowed_actions(surface, has_graph=True),
        "task_summaries": task_summaries,
        "review_queue": _review_queue(graph),
        "artifact_summaries": _artifact_summaries(graph),
        "cost_summary": _cost_summary(),
        "recovery_summary": _recovery_summary(task_summaries),
        "provider_dispatch_count": 0,
    }


def _project_summary(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "project_id": str(manifest.get("project_id") or ""),
        "project_type": str(manifest.get("project_type") or ""),
        "name": str(manifest.get("goal") or "未命名项目"),
        "status": str(manifest.get("status") or ""),
    }


def _surface_entities(graph: Mapping[str, Any], surface: str) -> list[dict[str, Any]]:
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), Mapping) else {}
    selected_categories = SURFACE_CATEGORIES.get(surface)
    selected_ids = {
        str(node_id)
        for node_id, node in nodes.items()
        if isinstance(node, Mapping)
        and (selected_categories is None or str(node.get("category") or "") in selected_categories)
    }
    if surface in {"storyboard", "review", "delivery"}:
        selected_ids = _expand_required_neighbors(graph, selected_ids)
    return [
        _public_entity(str(node_id), node)
        for node_id, node in nodes.items()
        if str(node_id) in selected_ids and isinstance(node, Mapping)
    ]


def _expand_required_neighbors(graph: Mapping[str, Any], selected_ids: set[str]) -> set[str]:
    expanded = set(selected_ids)
    for relation in graph.get("relations", []):
        if not isinstance(relation, Mapping):
            continue
        from_id = str(relation.get("from_id") or "")
        to_id = str(relation.get("to_id") or "")
        relation_type = str(relation.get("relation_type") or "")
        if relation_type in {"contains", "required_by", "contributes_to", "approved_image", "approved_video"}:
            if from_id in selected_ids or to_id in selected_ids:
                expanded.update({from_id, to_id})
    return expanded


def _public_entity(entity_id: str, node: Mapping[str, Any]) -> dict[str, Any]:
    metadata = node.get("metadata") if isinstance(node.get("metadata"), Mapping) else {}
    public_metadata = {
        str(key): deepcopy(value)
        for key, value in metadata.items()
        if str(key) in PUBLIC_METADATA_KEYS and _is_public_value(value)
    }
    label = next(
        (
            str(public_metadata.get(key) or "")
            for key in ("display_name", "name", "title", "intent")
            if public_metadata.get(key)
        ),
        entity_id,
    )
    return {
        "entity_id": entity_id,
        "entity_type": str(node.get("category") or "unknown"),
        "label": label,
        "state": str(node.get("state") or "active"),
        "metadata": public_metadata,
    }


def _is_public_value(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return len(value) <= 50 and all(_is_public_value(item) for item in value)
    if isinstance(value, Mapping):
        return len(value) <= 50 and all(
            isinstance(key, str) and _is_public_value(item)
            for key, item in value.items()
        )
    return False


def _task_summaries(graph: Mapping[str, Any]) -> list[dict[str, Any]]:
    attempts = [
        item
        for item in graph.get("attempts", {}).values()
        if isinstance(item, Mapping)
    ]
    result = []
    for work_id, work in graph.get("work", {}).items():
        if not isinstance(work, Mapping):
            continue
        matching = [item for item in attempts if str(item.get("work_id") or "") == str(work_id)]
        latest = max(matching, key=lambda item: int(item.get("attempt_number") or 0), default={})
        result.append(
            {
                "task_id": str(work_id),
                "state": str(latest.get("state") or work.get("state") or "planned"),
                "depends_on": [str(item) for item in work.get("depends_on", [])],
                "attempt_count": len(matching),
            }
        )
    return result


def _review_queue(graph: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "review_id": str(review_id),
            "target_entity_id": str(review.get("target_id") or ""),
            "state": str(review.get("state") or "pending"),
            "evidence_refs": [str(item) for item in review.get("evidence_refs", [])],
        }
        for review_id, review in graph.get("reviews", {}).items()
        if isinstance(review, Mapping)
    ]


def _artifact_summaries(graph: Mapping[str, Any]) -> list[dict[str, Any]]:
    selected_ids = {
        str(item.get("artifact_id") or "")
        for item in graph.get("selections", {}).values()
        if isinstance(item, Mapping)
    }
    return [
        {
            "artifact_id": str(artifact_id),
            "state": str(artifact.get("state") or "candidate"),
            "version": int(artifact.get("version") or 1),
            "selected": str(artifact_id) in selected_ids,
        }
        for artifact_id, artifact in graph.get("artifacts", {}).items()
        if isinstance(artifact, Mapping)
    ]


def _allowed_actions(surface: str, *, has_graph: bool) -> list[dict[str, Any]]:
    actions = [
        {"action": "inspect_entity", "enabled": has_graph},
        {"action": "open_agent_context", "enabled": True},
    ]
    if surface == "canvas":
        actions.append({"action": "inspect_lineage", "enabled": has_graph})
    if surface == "review":
        actions.append({"action": "inspect_candidate", "enabled": has_graph})
    if surface == "delivery":
        actions.append({"action": "inspect_delivery_version", "enabled": has_graph})
    return actions


def _cost_summary() -> dict[str, Any]:
    return {
        "available": False,
        "reserved": 0,
        "committed": 0,
        "currency": "",
        "message": "费用账本尚未迁移到统一 Studio 投影。",
    }


def _recovery_summary(tasks: list[Mapping[str, Any]]) -> dict[str, Any]:
    attention_states = {"dispatched", "submission_unknown", "reconcile_required"}
    attention = [item for item in tasks if str(item.get("state") or "") in attention_states]
    return {
        "attention_required": bool(attention),
        "attention_task_count": len(attention),
        "safe_to_repeat_provider_dispatch": False,
        "message": (
            "存在远端身份待对账，禁止重复派发。"
            if attention
            else "统一远端任务账本尚未迁移，不能据此重复派发。"
        ),
    }


__all__ = (
    "STUDIO_BFF_SCHEMA_VERSION",
    "STUDIO_SURFACES",
    "build_studio_surface_envelope",
)
