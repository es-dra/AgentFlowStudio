from __future__ import annotations

from typing import Any

from agentflow.algorithms.asset_auto_binding import ALGORITHM_ID as ASSET_AUTO_BINDING_ALGORITHM_ID
from agentflow.algorithms.node_reference_stack._contract import (
    ASSET_AUTO_BINDING_REFERENCE_PRIORITY_FLOOR,
    ASSET_AUTO_BINDING_RELATIONSHIP_TYPE,
)


def asset_auto_binding_references(graph: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(graph, dict) or graph.get("artifact_type") != "agentflow_asset_auto_binding_graph":
        return []
    relationships_by_binding = {
        str(item.get("binding_id") or ""): item
        for item in _list(graph.get("relationships"))
        if isinstance(item, dict) and item.get("relationship_type") == ASSET_AUTO_BINDING_RELATIONSHIP_TYPE
    }
    refs: list[dict[str, Any]] = []
    for suggestion in _list(graph.get("binding_suggestions")):
        if not isinstance(suggestion, dict) or suggestion.get("binding_state") != "bound":
            continue
        binding_id = str(suggestion.get("binding_id") or "")
        graph_asset_id = _safe_token(suggestion.get("graph_asset_id"))
        fixed_asset_id = _safe_token(suggestion.get("fixed_visual_asset_id"))
        relationship = relationships_by_binding.get(binding_id, {})
        validation_errors = _binding_validation_errors(suggestion, relationship)
        refs.append(
            {
                "reference_id": binding_id,
                "reference_type": "binding",
                "scope": "node",
                "target_slot": f"asset_binding:{graph_asset_id}",
                "target_ref": f"fixed_asset:{fixed_asset_id}" if fixed_asset_id else "",
                "status": "bound",
                "priority": max(ASSET_AUTO_BINDING_REFERENCE_PRIORITY_FLOOR, int(_confidence(suggestion.get("confidence")) * 100)),
                "source": "asset_auto_binding_graph",
                "source_relationship_type": relationship.get("relationship_type", ""),
                "source_algorithm_id": graph.get("algorithm_id"),
                "asset_binding_validation_errors": validation_errors,
            }
        )
    return refs


def _binding_validation_errors(suggestion: dict[str, Any], relationship: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    binding_id = str(suggestion.get("binding_id") or "")
    graph_asset_id = _safe_token(suggestion.get("graph_asset_id"))
    fixed_asset_id = _safe_token(suggestion.get("fixed_visual_asset_id"))
    if not fixed_asset_id:
        reasons.append("asset_binding_missing_fixed_asset_id")
    if not isinstance(relationship, dict) or relationship.get("relationship_type") != ASSET_AUTO_BINDING_RELATIONSHIP_TYPE:
        reasons.append("asset_binding_missing_established_relationship")
        return reasons
    expected_from = f"asset:{graph_asset_id}" if graph_asset_id else ""
    expected_to = f"fixed_asset:{fixed_asset_id}" if fixed_asset_id else ""
    source_relationship_ok = (
        bool(binding_id)
        and relationship.get("binding_id") == binding_id
        and relationship.get("source") == ASSET_AUTO_BINDING_ALGORITHM_ID
        and bool(expected_from)
        and relationship.get("from_node_id") == expected_from
        and bool(expected_to)
        and relationship.get("to_node_id") == expected_to
    )
    if not source_relationship_ok:
        reasons.append("asset_binding_missing_source_relationship")
    return reasons


def _confidence(value: Any) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, min(float(value), 1.0))
    return 0.0


def _safe_token(value: Any) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", ".", ":", "-"} else "_" for ch in str(value or "")).strip("_")[:160]


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
