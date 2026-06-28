from __future__ import annotations

from typing import Any


def asset_graph_from_context_bundle(context_bundle: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(context_bundle, dict):
        return {}
    graph = _extract_asset_graph_from_mapping(context_bundle)
    return graph if graph else {}


def asset_graph_from_context_subgraph(context_subgraph: Any) -> dict[str, Any]:
    if context_subgraph is None:
        return {}
    if isinstance(context_subgraph, dict):
        graph = _extract_asset_graph_from_mapping(context_subgraph)
        if graph:
            return graph
        nodes = context_subgraph.get("nodes")
    else:
        graph = _extract_asset_graph_from_mapping(_as_mapping(context_subgraph))
        if graph:
            return graph
        nodes = getattr(context_subgraph, "nodes", None)
    for node in _list(nodes):
        graph = _extract_asset_graph_from_mapping(_as_mapping(node))
        if graph:
            return graph
        params = _as_mapping(getattr(node, "node_parameters", None) if not isinstance(node, dict) else node.get("node_parameters"))
        graph = _extract_asset_graph_from_mapping(params)
        if graph:
            return graph
    return {}


def summarize_asset_graph_for_plan(asset_graph: dict[str, Any] | None, *, max_assets: int = 8) -> dict[str, Any]:
    if not isinstance(asset_graph, dict) or not asset_graph:
        return _empty_summary()
    if isinstance(asset_graph.get("locked_assets"), list):
        return _normalize_existing_summary(asset_graph, max_assets=max_assets)

    assets = _list(asset_graph.get("assets"))
    locked_assets = [_summarize_asset(asset) for asset in assets if isinstance(asset, dict)]
    locked_assets = [asset for asset in locked_assets if asset.get("graph_asset_id") or asset.get("asset_id")][:max_assets]
    unsupported = _summarize_unsupported(asset_graph.get("unsupported_additions"))
    review_state = str(
        asset_graph.get("review_state")
        or ("needs_review_unsupported_addition" if unsupported else ("asset_graph_available" if locked_assets else "not_available"))
    )
    return {
        "artifact_type": "agentflow_asset_graph_context",
        "schema_version": "0.1.0",
        "source_artifact_type": str(asset_graph.get("artifact_type") or ""),
        "asset_count": _int(asset_graph.get("asset_count"), default=len(assets)),
        "selected_asset_count": len(locked_assets),
        "graph_asset_ids": [str(asset.get("graph_asset_id") or asset.get("asset_id") or "") for asset in locked_assets],
        "locked_assets": locked_assets,
        "unsupported_additions": unsupported,
        "review_state": review_state,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def format_asset_graph_prompt_lines(asset_graph_context: dict[str, Any] | None, *, max_assets: int = 6) -> str:
    if not isinstance(asset_graph_context, dict):
        return ""
    assets = _list(asset_graph_context.get("locked_assets"))[:max_assets]
    if not assets:
        return ""
    lines = ["Asset graph continuity:"]
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        label = str(asset.get("label") or asset.get("graph_asset_id") or "asset")
        graph_asset_id = str(asset.get("graph_asset_id") or asset.get("asset_id") or "")
        kind = "/".join(part for part in (str(asset.get("asset_type") or ""), str(asset.get("role") or "")) if part)
        locks = "; ".join(_strings(asset.get("continuity_locks"), limit=4)) or "identity, layout, material"
        avoids = "; ".join(_strings(asset.get("negative_locks"), limit=3)) or "unrequested changes"
        lines.append(f"- {graph_asset_id} {label} ({kind}): lock {locks}; avoid {avoids}")
    unsupported = _list(asset_graph_context.get("unsupported_additions"))
    if unsupported:
        additions = ", ".join(str(item.get("addition") or "") for item in unsupported[:4] if isinstance(item, dict))
        if additions:
            lines.append(f"- Review guard: upstream unsupported additions need review before becoming visual facts: {additions}")
    return "\n".join(line for line in lines if line.strip())


def _extract_asset_graph_from_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(mapping, dict):
        return {}
    for key in ("asset_graph", "assetGraph", "asset_graph_channel", "assetGraphChannel"):
        value = mapping.get(key)
        if _looks_like_asset_graph(value):
            return value
    for key in ("asset_graph_context", "assetGraphContext"):
        value = mapping.get(key)
        if _looks_like_asset_graph_summary(value):
            return value
    for key in ("node_parameters", "runtime_context", "structured_shot", "structuredShot"):
        nested = mapping.get(key)
        if isinstance(nested, dict):
            graph = _extract_asset_graph_from_mapping(nested)
            if graph:
                return graph
    return {}


def _looks_like_asset_graph(value: Any) -> bool:
    return isinstance(value, dict) and isinstance(value.get("assets"), list)


def _looks_like_asset_graph_summary(value: Any) -> bool:
    return isinstance(value, dict) and isinstance(value.get("locked_assets"), list)


def _normalize_existing_summary(summary: dict[str, Any], *, max_assets: int) -> dict[str, Any]:
    assets = [_summarize_asset(asset) for asset in _list(summary.get("locked_assets")) if isinstance(asset, dict)]
    assets = [asset for asset in assets if asset.get("graph_asset_id") or asset.get("asset_id")][:max_assets]
    unsupported = _summarize_unsupported(summary.get("unsupported_additions"))
    return {
        "artifact_type": "agentflow_asset_graph_context",
        "schema_version": "0.1.0",
        "source_artifact_type": str(summary.get("source_artifact_type") or summary.get("artifact_type") or ""),
        "asset_count": _int(summary.get("asset_count"), default=len(assets)),
        "selected_asset_count": len(assets),
        "graph_asset_ids": [str(asset.get("graph_asset_id") or asset.get("asset_id") or "") for asset in assets],
        "locked_assets": assets,
        "unsupported_additions": unsupported,
        "review_state": str(summary.get("review_state") or ("needs_review_unsupported_addition" if unsupported else "asset_graph_available")),
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def _summarize_asset(asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "graph_asset_id": str(asset.get("graph_asset_id") or asset.get("asset_id") or ""),
        "asset_id": str(asset.get("asset_id") or asset.get("graph_asset_id") or ""),
        "asset_type": str(asset.get("asset_type") or "asset"),
        "label": str(asset.get("label") or asset.get("title") or ""),
        "role": str(asset.get("role") or asset.get("asset_type") or "asset"),
        "status": str(asset.get("status") or asset.get("review_state") or "candidate"),
        "confidence": _confidence(asset.get("confidence")),
        "shot_refs": _strings(asset.get("shot_refs"), limit=8),
        "evidence_text": _evidence_text(asset),
        "continuity_locks": _strings(asset.get("continuity_locks"), limit=8),
        "negative_locks": _strings(asset.get("negative_locks"), limit=8),
    }


def _summarize_unsupported(value: Any) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for item in _list(value)[:16]:
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "shot_id": str(item.get("shot_id") or ""),
                "addition": str(item.get("addition") or "")[:120],
                "source_span_id": str(item.get("source_span_id") or ""),
                "evidence_text": str(item.get("evidence_text") or "")[:240],
            }
        )
    return result


def _evidence_text(asset: dict[str, Any]) -> str:
    if asset.get("evidence_text"):
        return str(asset.get("evidence_text") or "")[:240]
    spans = _list(asset.get("evidence_spans"))
    texts = [str(span.get("text") or "").strip() for span in spans if isinstance(span, dict)]
    return " ".join(text for text in texts if text)[:240]


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        return dumped if isinstance(dumped, dict) else {}
    return {key: getattr(value, key) for key in dir(value) if not key.startswith("_") and not callable(getattr(value, key, None))}


def _empty_summary() -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_asset_graph_context",
        "schema_version": "0.1.0",
        "source_artifact_type": "",
        "asset_count": 0,
        "selected_asset_count": 0,
        "graph_asset_ids": [],
        "locked_assets": [],
        "unsupported_additions": [],
        "review_state": "not_available",
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def _strings(value: Any, *, limit: int) -> list[str]:
    result: list[str] = []
    for item in _list(value):
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text[:160])
        if len(result) >= limit:
            break
    return result


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _confidence(value: Any) -> float:
    if isinstance(value, (int, float)):
        return round(max(0.0, min(float(value), 1.0)), 3)
    return 0.0


def _int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


__all__ = (
    "asset_graph_from_context_bundle",
    "asset_graph_from_context_subgraph",
    "format_asset_graph_prompt_lines",
    "summarize_asset_graph_for_plan",
)
