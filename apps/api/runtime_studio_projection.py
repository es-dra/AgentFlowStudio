from __future__ import annotations

from typing import Any, Mapping

from apps.api.runtime_studio_safety import (
    OMIT,
    safe_identifier,
    safe_key,
    safe_text,
    sanitize_public_value,
)
from apps.api.runtime_studio_summary import (
    agent_summary as _agent_summary,
    allowed_actions as _allowed_actions,
    delivery_summary as _delivery_summary,
    focused_entity as _focused_entity,
    resume_target as _resume_target,
    rework_preview as _rework_preview,
    surface_summary as _surface_summary,
)

STUDIO_BFF_SCHEMA_VERSION = "afs.studio_bff.v0.2"
STUDIO_SURFACES = (
    "overview",
    "canvas",
    "script",
    "storyboard",
    "asset-bible",
    "review",
    "delivery",
)
SURFACE_CATEGORIES = {
    "overview": {"collection", "location", "unit", "artifact", "delivery"},
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
        empty_entities: list[dict[str, Any]] = []
        empty_tasks: list[dict[str, Any]] = []
        empty_reviews: list[dict[str, Any]] = []
        recovery = _recovery_summary(empty_tasks)
        resume = _resume_target(
            surface=surface,
            entities=empty_entities,
            reviews=empty_reviews,
            recovery=recovery,
        )
        return {
            "schema_version": STUDIO_BFF_SCHEMA_VERSION,
            "project_id": safe_identifier(project_id),
            "project": _project_summary(manifest),
            "authority_mode": "legacy_file",
            "project_version": 0,
            "graph_digest": "",
            "event_cursor": 0,
            "surface": surface,
            "surface_summary": _surface_summary(
                surface=surface,
                entities=empty_entities,
                reviews=empty_reviews,
                tasks=empty_tasks,
                delivery=_delivery_summary(None, empty_reviews, empty_tasks),
            ),
            "focused_entity": None,
            "resume_target": resume,
            "agent_summary": _agent_summary(0, resume, recovery),
            "entities": empty_entities,
            "relations": [],
            "allowed_actions": _allowed_actions(
                surface,
                entities=empty_entities,
                reviews=empty_reviews,
                artifacts=[],
                rework_preview=_rework_preview(surface, empty_reviews),
                delivery=_delivery_summary(None, empty_reviews, empty_tasks),
            ),
            "task_summaries": empty_tasks,
            "review_queue": empty_reviews,
            "artifact_summaries": [],
            "rework_preview": _rework_preview(surface, empty_reviews),
            "delivery_summary": _delivery_summary(None, empty_reviews, empty_tasks),
            "cost_summary": _cost_summary(),
            "recovery_summary": recovery,
            "provider_dispatch_count": 0,
        }

    entities = _surface_entities(graph, surface)
    entity_ids = {str(item["entity_id"]) for item in entities}
    relations = []
    for item in graph.get("relations", []):
        if not isinstance(item, Mapping):
            continue
        from_id = safe_identifier(item.get("from_id"))
        to_id = safe_identifier(item.get("to_id"))
        relation_type = safe_identifier(item.get("relation_type"), 80)
        if from_id in entity_ids and to_id in entity_ids and relation_type:
            relations.append(
                {
                    "from_id": from_id,
                    "to_id": to_id,
                    "relation_type": relation_type,
                }
            )
    task_summaries = _task_summaries(graph)
    reviews = _review_queue(graph)
    artifacts = _artifact_summaries(graph)
    recovery = _recovery_summary(task_summaries)
    delivery = _delivery_summary(graph, reviews, task_summaries)
    resume = _resume_target(
        surface=surface,
        entities=entities,
        reviews=reviews,
        recovery=recovery,
    )
    focused_entity = _focused_entity(entities, resume)
    rework_preview = _rework_preview(surface, reviews)
    return {
        "schema_version": STUDIO_BFF_SCHEMA_VERSION,
        "project_id": safe_identifier(project_id),
        "project": _project_summary(manifest),
        "authority_mode": "graph_v1",
        "project_version": int(graph.get("version") or 0),
        "graph_digest": safe_text(graph.get("graph_digest"), 128),
        "event_cursor": len(graph.get("events", [])),
        "surface": surface,
        "surface_summary": _surface_summary(
            surface=surface,
            entities=entities,
            reviews=reviews,
            tasks=task_summaries,
            delivery=delivery,
        ),
        "focused_entity": focused_entity,
        "resume_target": resume,
        "agent_summary": _agent_summary(
            int(graph.get("version") or 0),
            resume,
            recovery,
        ),
        "entities": entities,
        "relations": relations,
        "allowed_actions": _allowed_actions(
            surface,
            entities=entities,
            reviews=reviews,
            artifacts=artifacts,
            rework_preview=rework_preview,
            delivery=delivery,
        ),
        "task_summaries": task_summaries,
        "review_queue": reviews,
        "artifact_summaries": artifacts,
        "rework_preview": rework_preview,
        "delivery_summary": delivery,
        "cost_summary": _cost_summary(),
        "recovery_summary": recovery,
        "provider_dispatch_count": 0,
    }


def _project_summary(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "project_id": safe_identifier(manifest.get("project_id")),
        "project_type": safe_identifier(manifest.get("project_type"), 80),
        "name": safe_text(manifest.get("goal"), 240) or "未命名项目",
        "status": safe_identifier(manifest.get("status"), 80),
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
    entities = []
    for node_id, node in nodes.items():
        if str(node_id) not in selected_ids or not isinstance(node, Mapping):
            continue
        entity = _public_entity(str(node_id), node)
        if entity is not None:
            entities.append(entity)
    return entities


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


def _public_entity(entity_id: str, node: Mapping[str, Any]) -> dict[str, Any] | None:
    safe_entity_id = safe_identifier(entity_id)
    if not safe_entity_id:
        return None
    metadata = node.get("metadata") if isinstance(node.get("metadata"), Mapping) else {}
    public_metadata = {}
    for key, value in metadata.items():
        public_key = safe_key(key)
        if public_key not in PUBLIC_METADATA_KEYS:
            continue
        public_value = sanitize_public_value(value)
        if public_value is not OMIT:
            public_metadata[public_key] = public_value
    label = next(
        (
            safe_text(public_metadata.get(key), 240)
            for key in ("display_name", "name", "title", "intent")
            if public_metadata.get(key)
        ),
        safe_entity_id,
    )
    return {
        "entity_id": safe_entity_id,
        "entity_type": safe_identifier(node.get("category"), 80) or "unknown",
        "label": label,
        "state": safe_identifier(node.get("state"), 80) or "active",
        "metadata": public_metadata,
    }


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
        safe_work_id = safe_identifier(work_id)
        if not safe_work_id:
            continue
        matching = [item for item in attempts if str(item.get("work_id") or "") == str(work_id)]
        latest = max(matching, key=lambda item: int(item.get("attempt_number") or 0), default={})
        result.append(
            {
                "task_id": safe_work_id,
                "state": safe_identifier(latest.get("state") or work.get("state"), 80) or "planned",
                "depends_on": [
                    safe_ref
                    for item in work.get("depends_on", [])
                    if (safe_ref := safe_identifier(item))
                ],
                "attempt_count": len(matching),
            }
        )
    return result


def _review_queue(graph: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = []
    for review_id, review in graph.get("reviews", {}).items():
        if not isinstance(review, Mapping):
            continue
        safe_review_id = safe_identifier(review_id)
        safe_target_id = safe_identifier(review.get("target_id"))
        if not safe_review_id or not safe_target_id:
            continue
        result.append(
            {
                "review_id": safe_review_id,
                "target_entity_id": safe_target_id,
                "state": safe_identifier(review.get("state"), 80) or "pending",
                "evidence_refs": [
                    safe_ref
                    for item in review.get("evidence_refs", [])
                    if (safe_ref := safe_identifier(item))
                ],
            }
        )
    return result


def _artifact_summaries(graph: Mapping[str, Any]) -> list[dict[str, Any]]:
    selected_ids = {
        str(item.get("artifact_id") or "")
        for item in graph.get("selections", {}).values()
        if isinstance(item, Mapping)
    }
    result = []
    for artifact_id, artifact in graph.get("artifacts", {}).items():
        if not isinstance(artifact, Mapping):
            continue
        safe_artifact_id = safe_identifier(artifact_id)
        if not safe_artifact_id:
            continue
        result.append(
            {
                "artifact_id": safe_artifact_id,
                "state": safe_identifier(artifact.get("state"), 80) or "candidate",
                "version": int(artifact.get("version") or 1),
                "selected": str(artifact_id) in selected_ids,
            }
        )
    return result


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
