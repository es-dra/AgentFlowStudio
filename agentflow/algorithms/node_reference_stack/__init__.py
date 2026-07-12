from __future__ import annotations

from typing import Any

from agentflow.algorithms.asset_auto_binding import ALGORITHM_ID as ASSET_AUTO_BINDING_ALGORITHM_ID
from agentflow.algorithms.node_reference_stack._asset_binding import asset_auto_binding_references
from agentflow.algorithms.node_reference_stack._contract import (
    ALGORITHM_ID,
    ALLOWED_STATES_BY_TYPE,
    ASSET_AUTO_BINDING_REFERENCE_PRIORITY_FLOOR,
    ASSET_AUTO_BINDING_RELATIONSHIP_TYPE,
    DEFAULT_STATE_BY_TYPE,
    EVIDENCE_BOUNDARY,
    FAILURE_MODES,
    INPUT_CONTRACT,
    NON_CLAIMS,
    OUTPUT_CONTRACT,
    REVERSAL_ACTION_BY_REFERENCE_TYPE,
    SCHEMA_VERSION,
    SCOPE_PRECEDENCE,
    STUDIO_REFERENCE_ACTIONS,
    STUDIO_REFERENCE_ENTITIES,
    SUPPORTED_REFERENCE_SCOPES,
    TYPE_PRECEDENCE,
    USABLE_STATES,
)
from agentflow.algorithms.node_reference_stack._target_safety import safe_token as _safe_token
from agentflow.algorithms.node_reference_stack._target_safety import target_ref as _target_ref


def build_node_reference_stack(
    *,
    project_id: str,
    node_id: str,
    references: list[dict[str, Any]] | None = None,
    asset_auto_binding_graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    explicit_refs = [item for item in _list(references) if isinstance(item, dict)]
    binding_refs = asset_auto_binding_references(asset_auto_binding_graph)
    normalized = [
        _normalize_reference(project_id, node_id, item, index=index)
        for index, item in enumerate([*explicit_refs, *binding_refs], start=1)
    ]
    resolved = _resolve_conflicts(normalized)
    selected = [item for item in resolved["references"] if item["selected"]]
    blocked = [item for item in resolved["references"] if item["conflict_state"] == "blocked"]
    shadowed = [item for item in resolved["references"] if item["conflict_state"] == "shadowed"]

    return {
        "artifact_type": "agentflow_node_reference_stack",
        "schema_version": SCHEMA_VERSION,
        "algorithm_id": ALGORITHM_ID,
        "project_id": _safe_token(project_id),
        "node_id": _safe_token(node_id),
        "stack_policy": {
            "studio_reference_entities": list(STUDIO_REFERENCE_ENTITIES),
            "studio_reference_actions": list(STUDIO_REFERENCE_ACTIONS),
            "supported_scopes": list(SUPPORTED_REFERENCE_SCOPES),
            "priority_rule": "higher priority wins before scope and type precedence",
            "scope_precedence": SCOPE_PRECEDENCE,
            "type_precedence": TYPE_PRECEDENCE,
            "conflict_rule": "same scope/slot equal-rank conflicts fail closed for human review",
            "explainability_required": True,
            "reversibility_required": True,
            "fail_closed": True,
        },
        "asset_auto_binding_contract": {
            "algorithm_id": ASSET_AUTO_BINDING_ALGORITHM_ID,
            "relationship_type": ASSET_AUTO_BINDING_RELATIONSHIP_TYPE,
            "reference_type": "binding",
            "priority_floor": ASSET_AUTO_BINDING_REFERENCE_PRIORITY_FLOOR,
        },
        "summary": {
            "input_reference_count": len(explicit_refs),
            "asset_auto_binding_reference_count": len(binding_refs),
            "normalized_reference_count": len(resolved["references"]),
            "selected_reference_count": len(selected),
            "blocked_reference_count": len(blocked),
            "shadowed_reference_count": len(shadowed),
            "conflict_count": len(resolved["conflicts"]),
            "provider_calls_started": False,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
        },
        "reference_stack": selected,
        "references": resolved["references"],
        "conflicts": resolved["conflicts"],
        "relationships": [_selected_relationship(node_id, item) for item in selected],
        "safety_boundary": {
            "provider_calls_started": False,
            "raw_provider_response_stored": False,
            "external_private_link_stored": False,
            "absolute_path_stored": False,
            "media_bytes_stored": False,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
        },
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": NON_CLAIMS,
    }


def _normalize_reference(project_id: str, node_id: str, item: dict[str, Any], *, index: int) -> dict[str, Any]:
    reference_type = _safe_token(item.get("reference_type") or item.get("studio_entity_id"))
    scope = _safe_token(item.get("scope") or "node")
    raw_target = item.get("target_ref") or item.get("asset_id") or item.get("artifact_id")
    target_ref, unsafe_target = _target_ref(raw_target)
    status = _safe_token(item.get("status") or DEFAULT_STATE_BY_TYPE.get(reference_type, "draft"))
    target_slot = _safe_token(item.get("target_slot") or reference_type or "reference")
    reference_id = _safe_token(item.get("reference_id")) or _generated_reference_id(node_id, scope, target_slot, target_ref, index)
    block_reasons = _reference_block_reasons(
        reference_type,
        scope,
        status,
        target_ref,
        unsafe_target,
        item.get("asset_binding_validation_errors"),
    )

    return {
        "reference_id": reference_id,
        "project_id": _safe_token(project_id),
        "node_id": _safe_token(node_id),
        "reference_type": reference_type,
        "studio_entity_id": reference_type,
        "scope": scope,
        "target_slot": target_slot,
        "target_ref": target_ref,
        "status": status,
        "priority": _priority(item.get("priority")),
        "rank": {
            "priority": _priority(item.get("priority")),
            "scope_precedence": SCOPE_PRECEDENCE.get(scope, 0),
            "type_precedence": TYPE_PRECEDENCE.get(reference_type, 0),
            "input_order": index,
        },
        "source": _safe_token(item.get("source") or "explicit_reference"),
        "source_algorithm_id": _safe_token(item.get("source_algorithm_id")),
        "source_relationship_type": _safe_token(item.get("source_relationship_type")),
        "conflict_key": target_slot,
        "selected": False,
        "conflict_state": "candidate" if not block_reasons else "blocked",
        "block_reasons": block_reasons,
        "explainability": _explainability(item, reference_type, scope, target_slot),
        "reversal_plan": _reversal_plan(reference_type),
        "safety_boundary": {
            "provider_calls_started": False,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
            "destructive_asset_write": False,
        },
    }


def _resolve_conflicts(references: list[dict[str, Any]]) -> dict[str, Any]:
    conflicts: list[dict[str, Any]] = []
    by_key: dict[str, list[dict[str, Any]]] = {}
    for item in references:
        by_key.setdefault(item["conflict_key"], []).append(item)

    for conflict_key, items in by_key.items():
        valid = [item for item in items if item["conflict_state"] != "blocked"]
        if not valid:
            conflicts.append(_conflict_record(conflict_key, items, None, "all_candidates_blocked"))
            continue
        best_rank = max(_rank_tuple(item) for item in valid)
        winners = [item for item in valid if _rank_tuple(item) == best_rank]
        if len(winners) > 1:
            for item in winners:
                item["conflict_state"] = "blocked"
                item["block_reasons"].append("unresolved_equal_rank_conflict")
            for item in valid:
                if item not in winners:
                    item["conflict_state"] = "shadowed"
            conflicts.append(_conflict_record(conflict_key, items, None, "unresolved_equal_rank_conflict"))
            continue
        selected = winners[0]
        selected["selected"] = True
        selected["conflict_state"] = "selected"
        for item in valid:
            if item is not selected:
                item["conflict_state"] = "shadowed"
        if len(items) > 1:
            conflicts.append(_conflict_record(conflict_key, items, selected, _resolution_strategy(selected, valid)))

    return {"references": sorted(references, key=lambda item: (-item["selected"], -item["rank"]["priority"], item["rank"]["input_order"])), "conflicts": conflicts}


def _conflict_record(conflict_key: str, items: list[dict[str, Any]], selected: dict[str, Any] | None, resolution_strategy: str) -> dict[str, Any]:
    return {
        "conflict_key": conflict_key,
        "resolution_strategy": resolution_strategy,
        "selected_reference_id": selected["reference_id"] if selected else "",
        "blocked_reference_ids": [item["reference_id"] for item in items if item["conflict_state"] == "blocked"],
        "shadowed_reference_ids": [item["reference_id"] for item in items if item["conflict_state"] == "shadowed"],
        "requires_human_review": selected is None,
        "reversible": True,
    }


def _reference_block_reasons(
    reference_type: str,
    scope: str,
    status: str,
    target_ref: str,
    unsafe_target: bool,
    validation_errors: Any = None,
) -> list[str]:
    reasons: list[str] = []
    if reference_type not in STUDIO_REFERENCE_ENTITIES:
        reasons.append("unsupported_reference_type")
    if scope not in SUPPORTED_REFERENCE_SCOPES:
        reasons.append("unsupported_reference_scope")
    allowed_states = ALLOWED_STATES_BY_TYPE.get(reference_type, ())
    if allowed_states and status not in allowed_states:
        reasons.append("status_not_in_studio_entity_vocabulary")
    if status not in USABLE_STATES:
        reasons.append("reference_state_not_usable")
    if not target_ref:
        reasons.append("missing_target_ref")
    if unsafe_target:
        reasons.append("unsafe_target_ref")
    reasons.extend(_validation_errors(validation_errors))
    return reasons


def _resolution_strategy(selected: dict[str, Any], valid: list[dict[str, Any]]) -> str:
    priorities = {item["rank"]["priority"] for item in valid}
    scopes = {item["rank"]["scope_precedence"] for item in valid if item["rank"]["priority"] == selected["rank"]["priority"]}
    if len(priorities) > 1:
        return "resolved_by_priority"
    if len(scopes) > 1:
        return "resolved_by_scope_precedence"
    return "resolved_by_type_precedence"


def _selected_relationship(node_id: str, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "relationship_type": "node_reference_selected",
        "from_node_id": f"node:{_safe_token(node_id)}",
        "to_ref": item["target_ref"],
        "reference_id": item["reference_id"],
        "reference_type": item["reference_type"],
        "scope": item["scope"],
        "target_slot": item["target_slot"],
        "priority": item["priority"],
        "reversible": True,
        "undo_action": item["reversal_plan"]["action"],
        "source": ALGORITHM_ID,
    }


def _explainability(item: dict[str, Any], reference_type: str, scope: str, target_slot: str) -> dict[str, Any]:
    return {
        "studio_entity_id": reference_type,
        "scope": scope,
        "target_slot": target_slot,
        "priority_source": "explicit_priority" if "priority" in item else "default_priority_zero",
        "source_algorithm_id": _safe_token(item.get("source_algorithm_id")),
        "source_relationship_type": _safe_token(item.get("source_relationship_type")),
        "explanation": "Reference is ranked by explicit priority, then scope precedence, then Studio entity type precedence.",
    }


def _reversal_plan(reference_type: str) -> dict[str, Any]:
    return {
        "reversible": True,
        "action": REVERSAL_ACTION_BY_REFERENCE_TYPE.get(reference_type, "view_evidence"),
        "restores_previous_stack": True,
        "preserve_lineage": True,
        "destructive_asset_write": False,
    }


def _generated_reference_id(node_id: str, scope: str, target_slot: str, target_ref: str, index: int) -> str:
    return f"node-ref:{_safe_token(node_id)}:{scope}:{target_slot}:{_safe_token(target_ref)}:{index}"


def _rank_tuple(item: dict[str, Any]) -> tuple[int, int, int]:
    rank = item["rank"]
    return (rank["priority"], rank["scope_precedence"], rank["type_precedence"])


def _validation_errors(value: Any) -> list[str]:
    return [reason for reason in (_safe_token(item) for item in _list(value)) if reason]


def _priority(value: Any) -> int:
    try:
        return max(0, min(int(value), 100))
    except (TypeError, ValueError):
        return 0


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "ALGORITHM_ID", "ASSET_AUTO_BINDING_REFERENCE_PRIORITY_FLOOR", "ASSET_AUTO_BINDING_RELATIONSHIP_TYPE", "EVIDENCE_BOUNDARY",
    "FAILURE_MODES", "INPUT_CONTRACT", "NON_CLAIMS", "OUTPUT_CONTRACT", "REVERSAL_ACTION_BY_REFERENCE_TYPE",
    "SCHEMA_VERSION", "STUDIO_REFERENCE_ACTIONS", "STUDIO_REFERENCE_ENTITIES", "SUPPORTED_REFERENCE_SCOPES",
    "build_node_reference_stack",
)
