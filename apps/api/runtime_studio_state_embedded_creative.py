from __future__ import annotations

from typing import Any, Callable

from apps.api.runtime_store import safe_id


TextSanitizer = Callable[[Any, str, int], str]
NumberSanitizer = Callable[[Any, float], float]


def embedded_creative_action(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    action_type = text(value.get("action_type"), "", 80)
    result = {
        "action_id": text(value.get("action_id"), "", 160),
        "action_type": action_type,
        "mode": text(value.get("mode"), "", 80),
        "status": text(value.get("status"), "", 40),
        "source_text": text(value.get("source_text"), "", 24000),
        "source_node_version": text(value.get("source_node_version"), "", 160),
        "message": text(value.get("message"), "", 600),
        "error": text(value.get("error"), "", 600),
        "error_category": text(value.get("error_category"), "", 120),
        "error_owner": text(value.get("error_owner"), "", 80),
        "error_detail": text(value.get("error_detail"), "", 600),
        "next_action": text(value.get("next_action"), "", 360),
        "preserved_state": text(value.get("preserved_state"), "", 360),
        "requested_at": text(value.get("requested_at"), "", 80),
        "completed_at": text(value.get("completed_at"), "", 80),
        "cancelled_at": text(value.get("cancelled_at"), "", 80),
        "applied_at": text(value.get("applied_at"), "", 80),
        "applied_revision_id": text(value.get("applied_revision_id"), "", 160),
        "latency_ms": int(max(0, min(86_400_000, number(value.get("latency_ms"), 0)))),
        "cost_usd": max(0, min(9999, number(value.get("cost_usd"), 0))),
        "creative_task": creative_task(value.get("creative_task") or value.get("creativeTask"), text=text, number=number),
        "provider_lineage": provider_lineage(value.get("provider_lineage"), text=text, number=number),
        "graph_mutation": graph_mutation(value.get("graph_mutation"), text=text, number=number),
        "preview": embedded_creative_preview(value.get("preview"), action_type=action_type, text=text, number=number),
        "applied_subgraph": shot_candidate_subgraph(value.get("applied_subgraph"), text=text, number=number),
    }
    return _compact(result)


def embedded_creative_revisions(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> list[dict[str, Any]]:
    revisions: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        revisions.append(_compact({
            "revision_id": text(item.get("revision_id"), "", 160),
            "action_type": text(item.get("action_type"), "", 80),
            "mode": text(item.get("mode"), "", 80),
            "before_text": text(item.get("before_text"), "", 24000),
            "after_text": text(item.get("after_text"), "", 24000),
            "change_summary": _text_list(item.get("change_summary"), text=text, max_items=16, max_length=360),
            "rationale": text(item.get("rationale"), "", 1200),
            "source_node_version": text(item.get("source_node_version"), "", 160),
            "provider_lineage": provider_lineage(item.get("provider_lineage"), text=text, number=number),
            "graph_mutation": graph_mutation(item.get("graph_mutation"), text=text, number=number),
            "screenplay_candidate": screenplay_candidate(item.get("screenplay_candidate"), text=text, number=number),
            "shot_plan": shot_plan(item.get("shot_plan"), text=text, number=number),
            "applied_at": text(item.get("applied_at"), "", 80),
            "same_node_identity": bool(item.get("same_node_identity")),
        }))
        if len(revisions) >= 16:
            break
    return revisions


def last_embedded_creative_action_summary(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return _compact({
        "action_type": text(value.get("action_type"), "", 80),
        "mode": text(value.get("mode"), "", 80),
        "revision_id": text(value.get("revision_id"), "", 160),
        "provider_calls_started": bool(value.get("provider_calls_started")),
        "cost_usd": max(0, min(9999, number(value.get("cost_usd"), 0))),
    })


def creative_task(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return _compact({
        "schema_version": text(value.get("schema_version"), "afs.creative_task.v0.1", 80),
        "task_id": text(value.get("task_id"), "", 160),
        "project_id": text(value.get("project_id"), "", 120),
        "node_id": text(value.get("node_id"), "", 160),
        "node_type": text(value.get("node_type"), "", 80),
        "node_version": text(value.get("node_version"), "", 160),
        "action_type": text(value.get("action_type"), "", 80),
        "mode": text(value.get("mode"), "", 80),
        "state": text(value.get("state"), "", 40),
        "phase": text(value.get("phase"), "", 40),
        "completed_phases": _text_list(value.get("completed_phases"), text=text, max_items=12, max_length=40),
        "cancel_requested": bool(value.get("cancel_requested")),
        "result_scope": text(value.get("result_scope"), "", 120),
        "error_owner": text(value.get("error_owner"), "", 80),
        "error_category": text(value.get("error_category"), "", 120),
        "error_detail": text(value.get("error_detail"), "", 600),
        "started_at": text(value.get("started_at"), "", 80),
        "completed_at": text(value.get("completed_at"), "", 80),
        "elapsed_ms": int(max(0, min(86_400_000, number(value.get("elapsed_ms"), 0)))),
    })


def embedded_creative_preview(value: Any, *, action_type: str, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result = {
        "preview_id": text(value.get("preview_id"), "", 160),
        "revised_text": text(value.get("revised_text"), "", 24000),
        "change_summary": _text_list(value.get("change_summary"), text=text, max_items=16, max_length=360),
        "rationale": text(value.get("rationale"), "", 1200),
        "unresolved_decisions": _text_list(value.get("unresolved_decisions"), text=text, max_items=12, max_length=360),
        "quality_flags": _text_list(value.get("quality_flags"), text=text, max_items=12, max_length=180),
    }
    if action_type == "shot_breakdown" or value.get("shot_plan"):
        result["shot_plan"] = shot_plan(value.get("shot_plan"), text=text, number=number)
    if action_type == "script_revision" or value.get("screenplay_candidate"):
        result["screenplay_candidate"] = screenplay_candidate(value.get("screenplay_candidate"), text=text, number=number)
    return _compact(result)


def screenplay_candidate(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    scenes = [_screenplay_scene(item, text=text) for item in _items(value.get("scenes"), 64)]
    characters = [_compact({
        "name": text(item.get("name"), "", 120),
        "goal": text(item.get("goal"), "", 600),
        "conflict": text(item.get("conflict"), "", 600),
        "change": text(item.get("change"), "", 600),
    }) for item in _items(value.get("characters"), 32)]
    return _compact({
        "schema_version": text(value.get("schema_version"), "afs.screenplay_candidate.v0.1", 80),
        "title": text(value.get("title"), "", 180),
        "version_label": text(value.get("version_label"), "", 80),
        "logline": text(value.get("logline"), "", 1000),
        "characters": [item for item in characters if item],
        "scenes": [item for item in scenes if item],
    })


def shot_plan(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    scenes = [_shot_scene(item, text=text, number=number) for item in _items(value.get("scenes"), 64)]
    total_shots = sum(len(scene.get("shots") or []) for scene in scenes)
    return _compact({
        "schema_version": text(value.get("schema_version"), "afs.shot_plan.v0.1", 80),
        "candidate_id": text(value.get("candidate_id"), "", 160),
        "source_revision_id": text(value.get("source_revision_id"), "", 160),
        "title": text(value.get("title"), "", 180),
        "total_shots": int(max(0, min(9999, number(value.get("total_shots") or total_shots, total_shots)))),
        "estimated_duration_sec": max(0, min(86_400, number(value.get("estimated_duration_sec"), 0))),
        "confirmed_at": text(value.get("confirmed_at"), "", 80),
        "scenes": [item for item in scenes if item],
    })


def shot_plan_draft(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    return shot_plan(value, text=text, number=number)


def shot_candidate_subgraph(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return _compact({
        "schema_version": text(value.get("schema_version"), "afs.m6_6.visible_shot_candidate_subgraph.v0.1", 120),
        "candidate_id": text(value.get("candidate_id"), "", 160),
        "source_node_id": text(value.get("source_node_id"), "", 160),
        "source_revision_id": text(value.get("source_revision_id"), "", 160),
        "sequence_node_id": text(value.get("sequence_node_id"), "", 160),
        "first_shot_node_id": text(value.get("first_shot_node_id"), "", 160),
        "scene_count": int(max(0, min(9999, number(value.get("scene_count"), 0)))),
        "shot_count": int(max(0, min(9999, number(value.get("shot_count"), 0)))),
        "estimated_duration_sec": max(0, min(86_400, number(value.get("estimated_duration_sec"), 0))),
        "created_node_ids": _text_list(value.get("created_node_ids"), text=text, max_items=240, max_length=160, safe=True),
        "created_edge_ids": _text_list(value.get("created_edge_ids"), text=text, max_items=240, max_length=220, safe=True),
        "shot_plan": shot_plan(value.get("shot_plan"), text=text, number=number),
    })


def provider_lineage(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return _compact({
        "service_id": text(value.get("service_id"), "", 120),
        "provider": text(value.get("provider"), "", 120),
        "model_surface": text(value.get("model_surface"), "", 160),
        "request_id": text(value.get("request_id"), "", 180),
        "structured_output_contract_id": text(value.get("structured_output_contract_id"), "", 180),
        "structured_output_schema_digest": text(value.get("structured_output_schema_digest"), "", 180),
        "provider_calls_started": bool(value.get("provider_calls_started")),
        "provider_dispatch_count": int(max(0, min(99, number(value.get("provider_dispatch_count"), 0)))),
        "external_paid_cost_usd": max(0, min(9999, number(value.get("external_paid_cost_usd"), 0))),
    })


def graph_mutation(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return _compact({
        "mutated": bool(value.get("mutated")),
        "scope": text(value.get("scope"), "", 120),
        "reason": text(value.get("reason"), "", 240),
        "node_delta": int(max(-9999, min(9999, number(value.get("node_delta"), 0)))),
        "edge_delta": int(max(-9999, min(9999, number(value.get("edge_delta"), 0)))),
    })


def _screenplay_scene(value: dict[str, Any], *, text: TextSanitizer) -> dict[str, Any]:
    blocks = [_compact({
        "type": text(block.get("type"), "", 40),
        "character": text(block.get("character"), "", 120),
        "text": text(block.get("text"), "", 1600),
    }) for block in _items(value.get("blocks"), 120)]
    return _compact({
        "scene_id": text(value.get("scene_id"), "", 120),
        "title": text(value.get("title"), "", 180),
        "heading": text(value.get("heading"), "", 180),
        "space_type": text(value.get("space_type"), "", 40),
        "location": text(value.get("location"), "", 180),
        "time_of_day": text(value.get("time_of_day"), "", 80),
        "purpose": text(value.get("purpose"), "", 800),
        "blocks": [item for item in blocks if item],
    })


def _shot_scene(value: dict[str, Any], *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    shots = [_shot(item, text=text, number=number) for item in _items(value.get("shots"), 120)]
    return _compact({
        "scene_id": text(value.get("scene_id"), "", 120),
        "node_id": text(value.get("node_id"), "", 120),
        "first_shot_node_id": text(value.get("first_shot_node_id"), "", 120),
        "title": text(value.get("title"), "", 180),
        "location": text(value.get("location"), "", 180),
        "time_of_day": text(value.get("time_of_day"), "", 80),
        "purpose": text(value.get("purpose"), "", 1000),
        "shots": [item for item in shots if item],
    })


def _shot(value: dict[str, Any], *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    return _compact({
        "shot_id": text(value.get("shot_id"), "", 120),
        "node_id": text(value.get("node_id"), "", 120),
        "title": text(value.get("title"), "", 180),
        "duration_sec": max(0, min(600, number(value.get("duration_sec"), 0))),
        "shot_size": text(value.get("shot_size"), "", 120),
        "camera_angle": text(value.get("camera_angle"), "", 180),
        "movement": text(value.get("movement"), "", 240),
        "blocking": text(value.get("blocking"), "", 1000),
        "sound": text(value.get("sound"), "", 500),
        "transition": text(value.get("transition"), "", 180),
        "narrative_purpose": text(value.get("narrative_purpose"), "", 1000),
    })


def _items(value: Any, limit: int) -> list[dict[str, Any]]:
    return [item for item in (value if isinstance(value, list) else [])[:limit] if isinstance(item, dict)]


def _text_list(value: Any, *, text: TextSanitizer, max_items: int, max_length: int, safe: bool = False) -> list[str]:
    result = [text(item, "", max_length) for item in (value if isinstance(value, list) else [])[:max_items]]
    return [safe_id(item) if safe else item for item in result if item]


def _compact(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item not in ("", [], {}, None)}

