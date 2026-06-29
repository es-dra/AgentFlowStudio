from __future__ import annotations

from typing import Any


ALGORITHM_ID = "afs.production_graph.v0.1"
INPUT_CONTRACT = "script id, structured shots, candidate asset graph, content quality report"
OUTPUT_CONTRACT = "safe production graph snapshot with script, shot, asset, and quality nodes"
FAILURE_MODES = ("missing_script_node", "missing_shot_nodes", "missing_asset_nodes", "missing_quality_report")
EVIDENCE_BOUNDARY = "candidate production graph only; no fixed asset memory, provider smoke, or human acceptance"

GRAPH_STAGE = "storyboard_candidate_graph"
NON_CLAIMS = [
    "not fixed asset memory",
    "not generated media",
    "not provider smoke",
    "not human acceptance",
    "not business validation",
    "not durable memory promotion",
]


def build_storyboard_production_graph(
    *,
    project_id: str,
    script_node_id: str | None,
    script_text: str,
    shots: list[dict[str, Any]],
    asset_graph: dict[str, Any],
    content_quality_report: dict[str, Any],
) -> dict[str, Any]:
    safe_script_id = _safe_id(script_node_id or "storyboard_script")
    script_graph_node_id = f"script:{safe_script_id}"
    shot_nodes = _shot_nodes(shots)
    asset_nodes = _asset_nodes(asset_graph)
    quality_node = _quality_node(safe_script_id, content_quality_report)
    nodes = [
        _script_node(script_graph_node_id, script_node_id, script_text),
        *shot_nodes,
        *asset_nodes,
        quality_node,
    ]
    relationships = [
        *_script_shot_relationships(script_graph_node_id, shot_nodes),
        *_shot_asset_relationships(asset_graph),
        {
            "relationship_type": "quality_report_evaluates_storyboard",
            "from_node_id": quality_node["node_id"],
            "to_node_id": script_graph_node_id,
            "evidence_state": str(content_quality_report.get("summary", {}).get("status") or "structure_verified"),
        },
    ]
    return {
        "artifact_type": "agentflow_production_graph_snapshot",
        "schema_version": "0.1.0",
        "algorithm_id": ALGORITHM_ID,
        "graph_stage": GRAPH_STAGE,
        "summary": {
            "project_id": project_id,
            "script_node_id": script_node_id or "",
            "node_count": len(nodes),
            "relationship_count": len(relationships),
            "shot_count": len(shot_nodes),
            "asset_count": len(asset_nodes),
            "human_review_needed": True,
            "content_quality_status": str(content_quality_report.get("summary", {}).get("status") or ""),
        },
        "nodes": nodes,
        "relationships": relationships,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": NON_CLAIMS,
    }


def _script_node(node_id: str, script_node_id: str | None, script_text: str) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "node_type": "script",
        "source_node_id": script_node_id or "",
        "label": script_node_id or "storyboard_script",
        "evidence_state": "structure_verified",
        "review_state": "needs_human_review",
        "source_char_count": len(str(script_text or "")),
        "writes_long_term_memory": False,
    }


def _shot_nodes(shots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, shot in enumerate(shots if isinstance(shots, list) else [], start=1):
        if not isinstance(shot, dict):
            continue
        shot_id = str(shot.get("shot_id") or f"shot_{index:02d}")
        source_span = shot.get("source_span") if isinstance(shot.get("source_span"), dict) else {}
        result.append(
            {
                "node_id": f"shot:{shot_id}",
                "node_type": "shot",
                "shot_id": shot_id,
                "index": int(shot.get("index") or index),
                "label": f"Shot {int(shot.get('index') or index):02d}",
                "description": str(shot.get("description") or "")[:500],
                "source_span": {
                    "span_id": str(source_span.get("span_id") or ""),
                    "text": str(source_span.get("text") or "")[:500],
                },
                "grounding_status": str(shot.get("grounding_status") or ""),
                "review_state": "needs_human_review",
                "keyframe_required": isinstance(shot.get("keyframe_requirement"), dict),
                "video_motion_required": bool(_list((shot.get("video_motion_requirement") or {}).get("time_beats") if isinstance(shot.get("video_motion_requirement"), dict) else [])),
                "writes_long_term_memory": False,
            }
        )
    return result


def _asset_nodes(asset_graph: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for asset in _list(asset_graph.get("assets")):
        if not isinstance(asset, dict):
            continue
        graph_asset_id = str(asset.get("graph_asset_id") or "")
        if not graph_asset_id:
            continue
        result.append(
            {
                "node_id": f"asset:{graph_asset_id}",
                "node_type": "asset",
                "graph_asset_id": graph_asset_id,
                "asset_id": str(asset.get("asset_id") or graph_asset_id),
                "asset_type": str(asset.get("asset_type") or ""),
                "label": str(asset.get("label") or "")[:80],
                "status": str(asset.get("status") or "candidate"),
                "review_state": str(asset.get("review_state") or "candidate_review_required"),
                "evidence_span_count": len(_list(asset.get("evidence_spans"))),
                "continuity_locks": [str(item)[:120] for item in _list(asset.get("continuity_locks"))[:8]],
                "negative_locks": [str(item)[:120] for item in _list(asset.get("negative_locks"))[:8]],
                "writes_long_term_memory": False,
            }
        )
    return result


def _quality_node(script_node_id: str, report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "node_id": f"quality:{script_node_id}",
        "node_type": "quality_report",
        "label": "content_quality_report",
        "status": str(summary.get("status") or ""),
        "human_review_needed": bool(summary.get("human_review_needed", True)),
        "failed_check_count": int(summary.get("failed_check_count") or 0),
        "writes_long_term_memory": False,
    }


def _script_shot_relationships(script_node_id: str, shot_nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "relationship_type": "script_contains_shot",
            "from_node_id": script_node_id,
            "to_node_id": shot["node_id"],
            "order": shot["index"],
        }
        for shot in shot_nodes
    ]


def _shot_asset_relationships(asset_graph: dict[str, Any]) -> list[dict[str, Any]]:
    relationships: list[dict[str, Any]] = []
    for item in _list(asset_graph.get("relationships")):
        if not isinstance(item, dict) or item.get("relationship_type") != "shot_contains_asset":
            continue
        graph_asset_id = str(item.get("graph_asset_id") or "")
        shot_id = str(item.get("shot_id") or "")
        if not graph_asset_id or not shot_id:
            continue
        relationships.append(
            {
                "relationship_type": "shot_contains_asset",
                "from_node_id": f"shot:{shot_id}",
                "to_node_id": f"asset:{graph_asset_id}",
                "role": str(item.get("role") or "asset"),
                "source": str(item.get("source") or "candidate"),
            }
        )
    return relationships


def _safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in str(value or "")).strip("_")[:80] or "node"


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "ALGORITHM_ID",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "GRAPH_STAGE",
    "INPUT_CONTRACT",
    "NON_CLAIMS",
    "OUTPUT_CONTRACT",
    "build_storyboard_production_graph",
)
