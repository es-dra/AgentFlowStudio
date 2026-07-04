from __future__ import annotations

from typing import Any, Callable

from apps.api.runtime_store import safe_id


TextSanitizer = Callable[[Any, str, int], str]
NumberSanitizer = Callable[[Any, float], float]


def asset_auto_binding_graph(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("artifact_type") != "agentflow_asset_auto_binding_graph":
        return {}
    summary = value.get("summary") if isinstance(value.get("summary"), dict) else {}
    result = {
        "artifact_type": "agentflow_asset_auto_binding_graph",
        "schema_version": text(value.get("schema_version"), "", 40),
        "algorithm_id": text(value.get("algorithm_id"), "", 120),
        "graph_stage": text(value.get("graph_stage"), "", 120),
        "summary": {
            "suggested_binding_count": int(max(0, min(99, number(summary.get("suggested_binding_count"), 0)))),
            "established_binding_count": int(max(0, min(99, number(summary.get("established_binding_count"), 0)))),
            "blocked_candidate_count": int(max(0, min(99, number(summary.get("blocked_candidate_count"), 0)))),
            "provider_calls_started": bool(summary.get("provider_calls_started")),
            "writes_long_term_memory": bool(summary.get("writes_long_term_memory")),
            "writes_company_kb": bool(summary.get("writes_company_kb")),
        },
        "binding_suggestions": _binding_suggestions(value.get("binding_suggestions"), text=text, number=number),
        "relationships": _binding_relationships(value.get("relationships"), text=text, number=number),
        "blocked_candidates": _blocked_binding_candidates(value.get("blocked_candidates"), text=text, number=number),
        "writes_long_term_memory": bool(value.get("writes_long_term_memory")),
        "writes_company_kb": bool(value.get("writes_company_kb")),
    }
    return result if result["binding_suggestions"] or result["blocked_candidates"] else {}


def node_reference_stack(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    refs = _node_references(value.get("references") or value.get("reference_stack"), text=text, number=number)
    if not refs:
        return {}
    summary = value.get("summary") if isinstance(value.get("summary"), dict) else {}
    return {
        "artifact_type": text(value.get("artifact_type"), "studio_node_reference_stack", 80),
        "schema_version": text(value.get("schema_version"), "", 40),
        "node_id": safe_id(text(value.get("node_id"), "", 120)),
        "summary": {
            "asset_auto_binding_reference_count": int(max(0, min(99, number(summary.get("asset_auto_binding_reference_count"), len(refs))))),
            "selected_reference_count": int(max(0, min(99, number(summary.get("selected_reference_count"), len(refs))))),
            "provider_calls_started": bool(summary.get("provider_calls_started")),
            "writes_long_term_memory": bool(summary.get("writes_long_term_memory")),
            "writes_company_kb": bool(summary.get("writes_company_kb")),
        },
        "reference_stack": [item for item in refs if item.get("selected")],
        "references": refs,
    }


def _binding_suggestions(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        suggestion = {
            "binding_id": safe_id(text(item.get("binding_id"), "", 160)),
            "binding_state": text(item.get("binding_state"), "", 40),
            "graph_asset_id": safe_id(text(item.get("graph_asset_id"), "", 160)),
            "fixed_visual_asset_id": safe_id(text(item.get("fixed_visual_asset_id"), "", 160)),
            "asset_type": _asset_type(item.get("asset_type")),
            "label": text(item.get("label"), "", 120),
            "confidence": max(0, min(number(item.get("confidence"), 0), 1)),
            "lineage_refs": _lineage_refs(item.get("lineage_refs"), text=text),
            "reversal_plan": _reversal_plan(item.get("reversal_plan"), text=text),
        }
        if suggestion["binding_id"] and suggestion["fixed_visual_asset_id"]:
            suggestions.append(suggestion)
        if len(suggestions) >= 24:
            break
    return suggestions


def _binding_relationships(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> list[dict[str, Any]]:
    relationships: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        relationship = {
            "relationship_type": text(item.get("relationship_type"), "", 80),
            "from_node_id": safe_id(text(item.get("from_node_id"), "", 160)),
            "to_node_id": safe_id(text(item.get("to_node_id"), "", 160)),
            "binding_id": safe_id(text(item.get("binding_id"), "", 160)),
            "binding_state": text(item.get("binding_state"), "", 40),
            "confidence": max(0, min(number(item.get("confidence"), 0), 1)),
            "source": text(item.get("source"), "", 120),
        }
        if relationship["relationship_type"] and relationship["binding_id"]:
            relationships.append(relationship)
        if len(relationships) >= 48:
            break
    return relationships


def _blocked_binding_candidates(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> list[dict[str, Any]]:
    blocked: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        candidate = {
            "graph_asset_id": safe_id(text(item.get("graph_asset_id"), "", 160)),
            "asset_type": _asset_type(item.get("asset_type")),
            "label": text(item.get("label"), "", 120),
            "confidence": max(0, min(number(item.get("confidence"), 0), 1)),
            "binding_state": text(item.get("binding_state"), "", 40),
            "block_reasons": _text_list(item.get("block_reasons"), text=text, max_items=12, max_length=120, safe=True),
        }
        if candidate["graph_asset_id"] or candidate["label"]:
            blocked.append(candidate)
        if len(blocked) >= 24:
            break
    return blocked


def _lineage_refs(value: Any, *, text: TextSanitizer) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    keys = (
        "candidate_graph_asset_id",
        "fixed_visual_asset_id",
        "fixed_source_node_id",
        "source_human_gate_id",
        "source_asset_card_candidate_id",
    )
    return {key: safe_id(text(value.get(key), "", 180)) for key in keys if text(value.get(key), "", 180)}


def _reversal_plan(value: Any, *, text: TextSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "reversible": bool(value.get("reversible")),
        "action": text(value.get("action"), "", 80),
        "preserve_lineage": bool(value.get("preserve_lineage")),
        "destructive_asset_write": bool(value.get("destructive_asset_write")),
    }


def _node_references(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        ref = {
            "reference_id": safe_id(text(item.get("reference_id"), "", 160)),
            "reference_type": text(item.get("reference_type"), "", 80),
            "studio_entity_id": text(item.get("studio_entity_id") or item.get("reference_type"), "", 80),
            "scope": text(item.get("scope"), "", 40),
            "target_slot": safe_id(text(item.get("target_slot"), "", 160)),
            "target_ref": safe_id(text(item.get("target_ref"), "", 160)),
            "status": text(item.get("status"), "", 40),
            "priority": int(max(0, min(999, number(item.get("priority"), 0)))),
            "source": text(item.get("source"), "", 80),
            "source_algorithm_id": text(item.get("source_algorithm_id"), "", 120),
            "source_relationship_type": text(item.get("source_relationship_type"), "", 120),
            "selected": bool(item.get("selected")),
            "conflict_state": text(item.get("conflict_state"), "", 80),
            "block_reasons": _text_list(item.get("block_reasons"), text=text, max_items=12, max_length=120, safe=True),
        }
        if ref["reference_id"] and ref["target_ref"]:
            refs.append(ref)
        if len(refs) >= 24:
            break
    return refs


def _text_list(value: Any, *, text: TextSanitizer, max_items: int, max_length: int, safe: bool = False) -> list[str]:
    source = value if isinstance(value, list) else []
    result = []
    for item in source[:max_items]:
        clean = text(item, "", max_length)
        if clean:
            result.append(safe_id(clean) if safe else clean)
    return result


def _asset_type(value: Any) -> str:
    clean = str(value or "").strip()
    return clean if clean in {"character", "scene", "prop", "video"} else "character"


__all__ = ("asset_auto_binding_graph", "node_reference_stack")
