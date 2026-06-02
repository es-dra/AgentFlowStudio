from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow_studio.utils import write_json


SCHEMA_VERSION = "0.1.0"
PROTOCOL_TYPE = "agentflow_memory_video_pipeline_protocol"
PLAN_TYPE = "agentflow_memory_video_pipeline_plan"
REUSABLE_MEMORY_STATUSES = frozenset({"promoted", "merged"})
UNSAFE_FRAGMENTS = (
    "D:\\",
    "C:\\",
    "file://",
    "data:image/",
    "Bearer ",
    "signed_url",
    "signature=",
    "token=",
    "api_key",
    "secret_key",
)


def build_memory_video_pipeline_plan(protocol: dict[str, Any]) -> dict[str, Any]:
    """Build a no-call baseline-vs-memory video plan from one protocol file."""
    _validate_protocol_shape(protocol)
    _reject_unsafe_refs(protocol)
    memory_by_id = _memory_by_id(protocol)
    source_assets = _source_asset_ids(protocol)
    lanes = _lanes(protocol)
    _validate_lane_parity(protocol, lanes)
    lane_plans = [_lane_plan(protocol, lane, memory_by_id, source_assets) for lane in lanes]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": PLAN_TYPE,
        "protocol_id": protocol["protocol_id"],
        "project_brief": protocol["project_brief"],
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "source_assets": protocol["source_assets"],
        "provider_route": protocol["provider_route"],
        "lane_parity": _lane_parity(protocol, lane_plans),
        "lane_plans": lane_plans,
        "review_plan": _review_plan(protocol),
        "claim_boundaries": protocol["claim_boundaries"],
    }


def write_memory_video_pipeline_plan(plan: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    paths = [
        write_json(
            output_root / "protocol_summary.json",
            {
                "protocol_id": plan["protocol_id"],
                "project_brief": plan["project_brief"],
                "provider_calls_started": False,
                "writes_long_term_memory": False,
                "claim_boundaries": plan["claim_boundaries"],
            },
        ),
        write_json(
            output_root / "request_plan.json",
            {
                "protocol_id": plan["protocol_id"],
                "lane_parity": plan["lane_parity"],
                "lane_plans": plan["lane_plans"],
            },
        ),
        write_json(output_root / "review_plan.json", plan["review_plan"]),
        write_json(
            output_root / "run_plan.json",
            {
                "artifact_type": plan["artifact_type"],
                "protocol_id": plan["protocol_id"],
                "provider_calls_started": False,
                "writes_long_term_memory": False,
                "claim_boundaries": plan["claim_boundaries"],
            },
        ),
    ]
    report_path = output_root / "memory_video_pipeline_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_memory_video_pipeline_report(plan), encoding="utf-8")
    paths.append(report_path)
    return paths


def render_memory_video_pipeline_report(plan: dict[str, Any]) -> str:
    lanes = "\n".join(
        f"- {lane['lane_id']}: {lane['production_mode']} "
        f"({len(lane['memory_sources_loaded'])} memory refs)"
        for lane in plan["lane_plans"]
    )
    return "\n".join(
        [
            "# Memory Video Pipeline Plan",
            "",
            f"- Protocol: `{plan['protocol_id']}`",
            "- Provider calls: not started",
            "- Durable Memory runtime: not implemented",
            "- Human acceptance: not reviewed",
            "- Business validation: not validated",
            "- Quality improvement claim: not claimed",
            "",
            "## Lanes",
            "",
            lanes,
            "",
        ]
    )


def _validate_protocol_shape(protocol: dict[str, Any]) -> None:
    if protocol.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("memory video protocol schema_version must be 0.1.0")
    if protocol.get("artifact_type") != PROTOCOL_TYPE:
        raise ValueError(f"memory video protocol artifact_type must be {PROTOCOL_TYPE}")
    for key in [
        "protocol_id",
        "project_brief",
        "source_assets",
        "provider_route",
        "memory_context",
        "lanes",
        "storyboard",
        "review_rubric",
        "claim_boundaries",
    ]:
        if key not in protocol:
            raise ValueError(f"memory video protocol missing {key}")
    if len(_lanes(protocol)) != 2:
        raise ValueError("memory video protocol requires exactly two lanes")


def _reject_unsafe_refs(protocol: dict[str, Any]) -> None:
    serialized = str(protocol)
    if any(fragment.lower() in serialized.lower() for fragment in UNSAFE_FRAGMENTS):
        raise ValueError("memory video protocol contains unsafe local path, secret, or signed media reference")


def _memory_by_id(protocol: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cards = protocol.get("memory_context", {}).get("cards")
    if not isinstance(cards, list):
        raise ValueError("memory_context.cards must be a list")
    result: dict[str, dict[str, Any]] = {}
    for card in cards:
        memory_id = str(card.get("memory_id") or "")
        if not memory_id:
            raise ValueError("memory card missing memory_id")
        status = card.get("promotion_status")
        if status not in REUSABLE_MEMORY_STATUSES:
            raise ValueError(f"memory card {memory_id} is not reusable: {status}")
        if card.get("writes_long_term_memory") is not False:
            raise ValueError(f"memory card {memory_id} must not write long-term memory")
        result[memory_id] = card
    return result


def _source_asset_ids(protocol: dict[str, Any]) -> set[str]:
    assets = protocol.get("source_assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("source_assets must be a non-empty list")
    ids = {str(asset.get("asset_id") or "") for asset in assets}
    if "" in ids:
        raise ValueError("source asset missing asset_id")
    return ids


def _lanes(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    lanes = protocol.get("lanes")
    if not isinstance(lanes, list):
        raise ValueError("lanes must be a list")
    return lanes


def _validate_lane_parity(protocol: dict[str, Any], lanes: list[dict[str, Any]]) -> None:
    resolved_tasks = [_resolve_user_task(protocol, lane) for lane in lanes]
    if len(set(resolved_tasks)) != 1:
        raise ValueError("baseline and memory-backed lanes must share the same user_task")
    if any(lane.get("provider_route") != "{provider_route}" for lane in lanes):
        raise ValueError("baseline and memory-backed lanes must share the same provider route")
    source_refs = [tuple(lane.get("source_asset_refs") or []) for lane in lanes]
    if len(set(source_refs)) != 1:
        raise ValueError("baseline and memory-backed lanes must share the same source assets")


def _lane_plan(
    protocol: dict[str, Any],
    lane: dict[str, Any],
    memory_by_id: dict[str, dict[str, Any]],
    source_assets: set[str],
) -> dict[str, Any]:
    memory_refs = list(lane.get("memory_refs") or [])
    missing_memory = [ref for ref in memory_refs if ref not in memory_by_id]
    if missing_memory:
        raise ValueError(f"lane {lane.get('lane_id')} references missing memory: {missing_memory}")
    missing_assets = [ref for ref in lane.get("source_asset_refs", []) if ref not in source_assets]
    if missing_assets:
        raise ValueError(f"lane {lane.get('lane_id')} references missing source assets: {missing_assets}")
    return {
        "lane_id": lane["lane_id"],
        "production_mode": lane["production_mode"],
        "user_task": _resolve_user_task(protocol, lane),
        "source_asset_refs": lane.get("source_asset_refs", []),
        "memory_sources_loaded": memory_refs,
        "prompt_instructions": lane.get("prompt_instructions"),
        "request_projection": {
            "provider_calls_started": False,
            "image_service_id": protocol["provider_route"].get("image_service_id"),
            "video_service_id": protocol["provider_route"].get("video_service_id"),
            "duration_sec": protocol["provider_route"].get("duration_sec"),
            "mode": protocol["provider_route"].get("mode"),
            "aspect_ratio": protocol["provider_route"].get("aspect_ratio"),
            "storyboard_ref": protocol["storyboard"].get("scene_id"),
        },
    }


def _resolve_user_task(protocol: dict[str, Any], lane: dict[str, Any]) -> str:
    if lane.get("user_task") == "{project_brief.user_task}":
        return str(protocol["project_brief"].get("user_task") or "")
    return str(lane.get("user_task") or "")


def _lane_parity(protocol: dict[str, Any], lane_plans: list[dict[str, Any]]) -> dict[str, bool]:
    return {
        "same_user_task": len({lane["user_task"] for lane in lane_plans}) == 1,
        "same_source_assets": len({tuple(lane["source_asset_refs"]) for lane in lane_plans}) == 1,
        "same_provider_route": True,
        "same_duration": bool(protocol["provider_route"].get("duration_sec")),
        "same_script": True,
        "only_memory_context_differs": lane_plans[0]["memory_sources_loaded"] != lane_plans[1]["memory_sources_loaded"],
    }


def _review_plan(protocol: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_id": protocol["protocol_id"],
        "rubric": protocol["review_rubric"],
        "storyboard": protocol["storyboard"],
        "technical_visual_review": "not_reviewed",
        "human_acceptance": "not_reviewed",
        "business_validation": "not_validated",
        "quality_improvement_claim": "not_claimed",
        "cross_run_stability": {
            "status": "available_when_repeated_runs_exist",
            "criteria": [
                "shot_structure_consistency",
                "identity_anchor_retention",
                "scene_anchor_retention",
                "occlusion_recovery_repeatability",
            ],
        },
    }
