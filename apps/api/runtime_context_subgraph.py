from __future__ import annotations

from typing import Any

from apps.api.runtime_models import ContextSubgraph


MAX_SUBGRAPH_NODES = 24
MAX_SUBGRAPH_EDGES = 32
MAX_SUBGRAPH_HOPS = 3
MAX_REFERENCE_EDGE_DEPTH = 6
RELATION_PRIORITY = {"reference": 0, "director": 1, "generation": 2}
FORBIDDEN_ASSET_TEXT_KEYS = {"signature", "feature_card", "negative_locks", "visual_asset", "visual_assets"}


def validate_subgraph(subgraph: ContextSubgraph) -> None:
    if len(subgraph.nodes) > MAX_SUBGRAPH_NODES:
        raise ValueError("context_subgraph exceeds the 24 node limit")
    if len(subgraph.edges) > MAX_SUBGRAPH_EDGES:
        raise ValueError("context_subgraph exceeds the 32 edge limit")
    for node in subgraph.nodes:
        extra = getattr(node, "model_extra", {}) or {}
        forbidden = FORBIDDEN_ASSET_TEXT_KEYS.intersection(extra)
        if forbidden:
            raise ValueError("context_subgraph must pass visual asset ids only, not asset text")
    for edge in subgraph.edges:
        extra = getattr(edge, "model_extra", {}) or {}
        forbidden = FORBIDDEN_ASSET_TEXT_KEYS.intersection(extra)
        if forbidden:
            raise ValueError("context_subgraph edge contains forbidden asset text")


def connected_asset_refs(subgraph: ContextSubgraph) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    nodes = {node.id: node for node in subgraph.nodes}
    upstream_by_to: dict[str, list[Any]] = {}
    for edge in subgraph.edges:
        upstream_by_to.setdefault(edge.to_node_id, []).append(edge)
    queue: list[tuple[str, int, int, str]] = [(subgraph.target_node_id, 0, 0, "generation")]
    visited: dict[str, int] = {}
    visited_costs: dict[str, tuple[int, int]] = {}
    refs: dict[str, dict[str, Any]] = {}
    while queue:
        node_id, hop, reference_depth, relation = queue.pop(0)
        if hop > MAX_SUBGRAPH_HOPS or reference_depth > MAX_REFERENCE_EDGE_DEPTH:
            continue
        previous = visited_costs.get(node_id)
        if previous and previous <= (hop, reference_depth):
            continue
        visited_costs[node_id] = (hop, reference_depth)
        visited[node_id] = hop
        node = nodes.get(node_id)
        if node:
            for asset_id in node.visual_asset_ids:
                _remember_ref(refs, str(asset_id), hop, relation, node_id)
        for edge in upstream_by_to.get(node_id, []):
            next_relation = str(edge.relation_type or "generation")
            next_hop = hop if next_relation == "reference" else hop + 1
            next_reference_depth = reference_depth + 1 if next_relation == "reference" else reference_depth
            queue.append((edge.from_node_id, next_hop, next_reference_depth, next_relation))
    return refs, visited


def upstream_summary_lines(subgraph: ContextSubgraph, node_hops: dict[str, int], limit: int = 3) -> list[str]:
    nodes = {node.id: node for node in subgraph.nodes}
    candidates = sorted(
        (
            (hop, node_id)
            for node_id, hop in node_hops.items()
            if node_id != subgraph.target_node_id and node_id in nodes and str(nodes[node_id].prompt or "").strip()
        ),
    )
    lines: list[str] = []
    for _hop, node_id in candidates[:limit]:
        node = nodes[node_id]
        title = str(node.title or node_id).strip()
        prompt = str(node.prompt or "").strip()[:120]
        lines.append(f"{title}: {prompt}")
    return lines


def sort_asset_ids(assets: dict[str, dict[str, Any]], refs: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(
        [asset_id for asset_id in refs if asset_id in assets],
        key=lambda asset_id: (
            refs[asset_id]["hop"],
            RELATION_PRIORITY.get(refs[asset_id]["relation_type"], 9),
            asset_id,
        ),
    )


def _remember_ref(refs: dict[str, dict[str, Any]], asset_id: str, hop: int, relation: str, node_id: str) -> None:
    if not asset_id:
        return
    current = refs.get(asset_id)
    priority = RELATION_PRIORITY.get(relation, 9)
    if current and (current["hop"], RELATION_PRIORITY.get(current["relation_type"], 9)) <= (hop, priority):
        return
    refs[asset_id] = {"hop": hop, "relation_type": relation, "source_node_id": node_id}


__all__ = (
    "MAX_REFERENCE_EDGE_DEPTH",
    "MAX_SUBGRAPH_EDGES",
    "MAX_SUBGRAPH_HOPS",
    "MAX_SUBGRAPH_NODES",
    "RELATION_PRIORITY",
    "connected_asset_refs",
    "sort_asset_ids",
    "upstream_summary_lines",
    "validate_subgraph",
)
