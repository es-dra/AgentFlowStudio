from __future__ import annotations

from typing import Any


ALGORITHM_ID = "afs.content_quality_evaluation.v0.1"
INPUT_CONTRACT = "script text, structured shots, candidate asset graph, provider gate observation"
OUTPUT_CONTRACT = "safe content quality report with deterministic checks and human-review boundary"
FAILURE_MODES = ("missing_source_grounding", "fixed_template_risk", "missing_asset_evidence", "missing_story_intent")
EVIDENCE_BOUNDARY = "structure quality only; not human creative acceptance, provider smoke, or business validation"

REPORT_NON_CLAIMS = [
    "not human acceptance",
    "not creative quality acceptance",
    "not provider smoke when provider_calls_started is false",
    "not business validation",
    "not durable memory promotion",
    "human review required before fixed assets or quality acceptance",
]


def evaluate_storyboard_content_quality(
    *,
    project_id: str,
    node_id: str | None,
    script_text: str,
    shots: list[dict[str, Any]],
    asset_graph: dict[str, Any],
    provider_calls_started: bool,
    shot_count_hint: int | None,
) -> dict[str, Any]:
    shot_items = [shot for shot in shots if isinstance(shot, dict)]
    checks = [
        _script_understanding_check(script_text, shot_items, asset_graph),
        _source_grounding_check(shot_items, asset_graph),
        _dynamic_shot_count_check(shot_items, shot_count_hint),
        _asset_evidence_check(shot_items, asset_graph),
        _keyframe_and_video_intent_check(shot_items),
        _safe_boundary_check(asset_graph, provider_calls_started),
    ]
    needs_review = True
    failed = [item for item in checks if item["status"] == "failed"]
    status = "failed_needs_repair" if failed else "structure_verified_needs_human_review"
    return {
        "artifact_type": "agentflow_content_quality_report",
        "schema_version": "0.1.0",
        "algorithm_id": ALGORITHM_ID,
        "pipeline": "storyboard_breakdown",
        "project_id": project_id,
        "node_id": node_id,
        "summary": {
            "status": status,
            "shot_count": len(shot_items),
            "check_count": len(checks),
            "failed_check_count": len(failed),
            "human_review_needed": needs_review,
            "provider_calls_started": provider_calls_started,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
        },
        "checks": checks,
        "content_quality_log": {
            "pipeline_step": "storyboard_breakdown",
            "expected_behavior": (
                "understand script signals, split shots from narrative structure, preserve source grounding, "
                "identify candidate assets with evidence, and keep keyframe/video intent reviewable"
            ),
            "actual_output_summary": {
                "shot_count": len(shot_items),
                "asset_types": _asset_types(shot_items, asset_graph),
                "unsupported_addition_count": _unsupported_count(shot_items, asset_graph),
            },
            "human_review_needed": needs_review,
            "regression_case_added": False,
            "feedback_candidate": "not_created",
        },
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": REPORT_NON_CLAIMS,
    }


def _script_understanding_check(
    script_text: str,
    shots: list[dict[str, Any]],
    asset_graph: dict[str, Any],
) -> dict[str, Any]:
    labels_by_type = _labels_by_type(shots, asset_graph)
    character_count = len(labels_by_type.get("character", []))
    scene_count = len(labels_by_type.get("scene", []))
    prop_count = len(labels_by_type.get("prop", []))
    status = "passed" if shots and (character_count or scene_count or prop_count) else "failed"
    return {
        "id": "script_understanding",
        "status": status,
        "message": "script signals are represented by candidate content objects",
        "details": {
            "script_char_count": len(str(script_text or "")),
            "character_labels": labels_by_type.get("character", []),
            "scene_labels": labels_by_type.get("scene", []),
            "prop_labels": labels_by_type.get("prop", []),
        },
    }


def _source_grounding_check(shots: list[dict[str, Any]], asset_graph: dict[str, Any]) -> dict[str, Any]:
    missing = [
        str(shot.get("shot_id") or shot.get("index") or "")
        for shot in shots
        if not _source_text(shot)
    ]
    unsupported_count = _unsupported_count(shots, asset_graph)
    status = "failed" if missing else "needs_review" if unsupported_count else "passed"
    return {
        "id": "script_source_grounding",
        "status": status,
        "message": "shots remain grounded to source spans and unsupported additions stay visible",
        "details": {
            "missing_source_span_shot_ids": missing,
            "unsupported_addition_count": unsupported_count,
        },
    }


def _dynamic_shot_count_check(shots: list[dict[str, Any]], shot_count_hint: int | None) -> dict[str, Any]:
    planning = [shot.get("planning_agent") for shot in shots if isinstance(shot.get("planning_agent"), dict)]
    dynamic_flags = [bool(item.get("dynamic_shot_count")) for item in planning]
    fixed_template_claimed = bool(shot_count_hint is None and dynamic_flags and not all(dynamic_flags))
    status = "passed" if shots and not fixed_template_claimed else "failed"
    return {
        "id": "dynamic_shot_count",
        "status": status,
        "message": "shot count is recorded as narrative-driven unless the caller gives an explicit hint",
        "details": {
            "shot_count_hint": shot_count_hint,
            "resolved_shot_count": len(shots),
            "dynamic_count_detected": bool(dynamic_flags and all(dynamic_flags)),
            "fixed_template_claimed": fixed_template_claimed,
            "policy": "caller_hint_respected" if shot_count_hint else "narrative_driven_from_script_units",
        },
    }


def _asset_evidence_check(shots: list[dict[str, Any]], asset_graph: dict[str, Any]) -> dict[str, Any]:
    refs = _shot_refs(shots)
    graph_assets = _graph_assets(asset_graph)
    missing_ref_evidence = [
        f"{ref.get('asset_type')}:{ref.get('label')}"
        for ref in refs
        if not str(ref.get("evidence_text") or "").strip()
    ]
    missing_graph_evidence = [
        f"{asset.get('asset_type')}:{asset.get('label')}"
        for asset in graph_assets
        if not _list(asset.get("evidence_spans"))
    ]
    status = "passed" if refs and not missing_ref_evidence and not missing_graph_evidence else "failed"
    return {
        "id": "asset_evidence",
        "status": status,
        "message": "candidate character scene prop assets carry evidence before becoming fixed assets",
        "details": {
            "asset_ref_count": len(refs),
            "asset_graph_asset_count": len(graph_assets),
            "asset_types": _asset_types(shots, asset_graph),
            "missing_ref_evidence": missing_ref_evidence[:12],
            "missing_graph_evidence": missing_graph_evidence[:12],
        },
    }


def _keyframe_and_video_intent_check(shots: list[dict[str, Any]]) -> dict[str, Any]:
    missing_keyframe = [
        str(shot.get("shot_id") or shot.get("index") or "")
        for shot in shots
        if not isinstance(shot.get("keyframe_requirement"), dict)
    ]
    missing_video = [
        str(shot.get("shot_id") or shot.get("index") or "")
        for shot in shots
        if not _list((shot.get("video_motion_requirement") or {}).get("time_beats") if isinstance(shot.get("video_motion_requirement"), dict) else [])
    ]
    status = "passed" if shots and not missing_keyframe and not missing_video else "failed"
    return {
        "id": "keyframe_and_video_intent",
        "status": status,
        "message": "each shot exposes reviewable keyframe and video motion intent",
        "details": {
            "missing_keyframe_requirement_shot_ids": missing_keyframe,
            "missing_video_motion_requirement_shot_ids": missing_video,
        },
    }


def _safe_boundary_check(asset_graph: dict[str, Any], provider_calls_started: bool) -> dict[str, Any]:
    writes_long_term_memory = bool(asset_graph.get("writes_long_term_memory"))
    writes_company_kb = bool(asset_graph.get("writes_company_kb"))
    status = "failed" if writes_long_term_memory or writes_company_kb else "passed"
    return {
        "id": "safe_boundary",
        "status": status,
        "message": "quality report is safe structure evidence and does not promote memory or business claims",
        "details": {
            "provider_calls_started": provider_calls_started,
            "writes_long_term_memory": writes_long_term_memory,
            "writes_company_kb": writes_company_kb,
            "provider_raw_response_stored": False,
            "generated_media_bytes_stored": False,
        },
    }


def _labels_by_type(shots: list[dict[str, Any]], asset_graph: dict[str, Any]) -> dict[str, list[str]]:
    labels: dict[str, list[str]] = {"character": [], "scene": [], "prop": []}
    for item in [*_shot_refs(shots), *_graph_assets(asset_graph)]:
        asset_type = str(item.get("asset_type") or "")
        label = str(item.get("label") or "").strip()
        if asset_type in labels and label and label not in labels[asset_type]:
            labels[asset_type].append(label)
    return {key: sorted(value) for key, value in labels.items() if value}


def _asset_types(shots: list[dict[str, Any]], asset_graph: dict[str, Any]) -> list[str]:
    return sorted(_labels_by_type(shots, asset_graph))


def _unsupported_count(shots: list[dict[str, Any]], asset_graph: dict[str, Any]) -> int:
    shot_count = sum(len(_list(shot.get("unsupported_additions"))) for shot in shots)
    graph_count = len(_list(asset_graph.get("unsupported_additions")))
    return max(shot_count, graph_count)


def _source_text(shot: dict[str, Any]) -> str:
    span = shot.get("source_span") if isinstance(shot.get("source_span"), dict) else {}
    return str(span.get("text") or shot.get("source_text") or "").strip()


def _shot_refs(shots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for shot in shots:
        for ref in _list(shot.get("asset_refs")):
            if isinstance(ref, dict):
                refs.append(ref)
    return refs


def _graph_assets(asset_graph: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in _list(asset_graph.get("assets")) if isinstance(item, dict)]


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "ALGORITHM_ID",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "OUTPUT_CONTRACT",
    "REPORT_NON_CLAIMS",
    "evaluate_storyboard_content_quality",
)
