from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow_studio.harness.highlight_artifact_checks import (
    all_have_ranking_factors,
    clip_order_matches_highlights,
    final_score,
    final_scores_valid,
    has_source_segment_ids,
    has_time_range,
    has_valid_time_range,
    ids_are_unique,
    number,
    numeric_fields_valid,
    range_values,
    segment_has_highlight_id,
    segment_has_ranking_factors,
    segment_has_valid_time_range,
    type_distribution,
)

HIGHLIGHT_PLAN_PROFILE = "highlight_plan"
HIGHLIGHT_CLIP_PLAN_PROFILE = "highlight_clip_plan"
HIGHLIGHT_QUALITY_PROFILES = {HIGHLIGHT_PLAN_PROFILE, HIGHLIGHT_CLIP_PLAN_PROFILE}


def is_highlight_quality_profile(value: object) -> bool:
    return str(value or "") in HIGHLIGHT_QUALITY_PROFILES


def highlight_artifacts_to_inspect(quality_profile: object) -> list[str]:
    artifacts = ["highlight_plan.json", "manifest.json", "run_manifest.json", "trace.json"]
    if str(quality_profile or "") == HIGHLIGHT_CLIP_PLAN_PROFILE:
        artifacts.insert(1, "clip_plan.json")
    return artifacts


def build_highlight_quality_report(root: str | Path, quality_profile: object) -> dict[str, Any]:
    run_dir = Path(root)
    profile = str(quality_profile or "")
    highlight_plan = _read_json_object(run_dir / "highlight_plan.json")
    clip_plan = _read_json_object(run_dir / "clip_plan.json")

    checks: list[dict[str, Any]] = []
    _add_file_check(run_dir / "manifest.json", "manifest_file_exists", checks)
    _add_file_check(run_dir / "run_manifest.json", "run_manifest_file_exists", checks)
    _add_file_check(run_dir / "trace.json", "trace_file_exists", checks)
    _add_file_check(run_dir / "highlight_plan.json", "highlight_plan_exists", checks)
    _add_check(checks, "highlight_plan_json_object", "pass" if highlight_plan is not None else "fail")

    if highlight_plan is not None:
        _add_highlight_plan_checks(checks, highlight_plan)

    if profile == HIGHLIGHT_CLIP_PLAN_PROFILE:
        _add_file_check(run_dir / "clip_plan.json", "clip_plan_exists", checks)
        _add_check(checks, "clip_plan_json_object", "pass" if clip_plan is not None else "fail")
        if highlight_plan is not None and clip_plan is not None:
            _add_clip_plan_checks(checks, highlight_plan, clip_plan)
    else:
        _add_check(
            checks,
            "clip_plan_not_generated_for_script",
            "pass" if not (run_dir / "clip_plan.json").exists() else "fail",
        )

    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "status": "fail" if failed else "pass",
        "checks": checks,
        "warnings": [],
        "errors": [_check_error(check) for check in failed],
        "summary": {
            "quality_profile": profile,
            "highlight_plan": _highlight_plan_summary(highlight_plan, profile),
            "clip_plan": _clip_plan_summary(clip_plan),
        },
    }


def build_highlight_review_section(root: str | Path, run_manifest: dict[str, Any] | None) -> dict[str, Any]:
    profile = str(run_manifest.get("quality_profile") if run_manifest else "")
    report = build_highlight_quality_report(root, profile)
    checks = [_review_check(check) for check in report["checks"]]
    return {
        "name": "highlight_artifacts",
        "status": _review_status(checks),
        "checks": checks,
    }


def _add_highlight_plan_checks(checks: list[dict[str, Any]], plan: dict[str, Any]) -> None:
    input_mode = str(plan.get("input_mode") or "")
    highlights = plan.get("highlights")
    highlights_list = highlights if isinstance(highlights, list) else []
    _add_check(checks, "highlight_count_positive", "pass" if highlights_list else "fail", {"count": len(highlights_list)})
    _add_check(
        checks,
        "highlight_input_mode_valid",
        "pass" if input_mode in {"script_only", "timestamped_transcript"} else "fail",
        {"input_mode": input_mode},
    )
    _add_check(checks, "highlight_ids_unique", "pass" if ids_are_unique(highlights_list) else "fail")
    _add_check(checks, "highlight_scores_valid", "pass" if numeric_fields_valid(highlights_list, "score") else "fail")
    _add_check(
        checks,
        "highlight_confidences_valid",
        "pass" if numeric_fields_valid(highlights_list, "confidence") else "fail",
    )
    _add_check(
        checks,
        "ranking_factors_present",
        "pass" if all_have_ranking_factors(highlights_list) else "fail",
    )
    _add_check(
        checks,
        "ranking_final_scores_valid",
        "pass" if final_scores_valid(highlights_list) else "fail",
    )

    if input_mode == "script_only":
        _add_check(
            checks,
            "script_only_without_timestamps",
            "pass" if not any(has_time_range(item) for item in highlights_list) else "fail",
        )
    if input_mode == "timestamped_transcript":
        _add_check(
            checks,
            "timestamped_highlights_have_timestamps",
            "pass" if all(has_valid_time_range(item) for item in highlights_list) else "fail",
        )
        _add_check(
            checks,
            "transcript_source_segment_ids_present",
            "pass" if all(has_source_segment_ids(item) for item in highlights_list) else "fail",
        )


def _add_clip_plan_checks(
    checks: list[dict[str, Any]],
    highlight_plan: dict[str, Any],
    clip_plan: dict[str, Any],
) -> None:
    segments = clip_plan.get("segments")
    segment_list = segments if isinstance(segments, list) else []
    _add_check(checks, "clip_segments_non_empty", "pass" if segment_list else "fail", {"count": len(segment_list)})
    _add_check(
        checks,
        "clip_segments_time_ranges_valid",
        "pass" if all(segment_has_valid_time_range(item) for item in segment_list) else "fail",
    )
    _add_check(
        checks,
        "clip_segments_have_highlight_metadata",
        "pass" if all(segment_has_highlight_id(item) for item in segment_list) else "fail",
    )
    _add_check(
        checks,
        "clip_segments_have_ranking_factors",
        "pass" if all(segment_has_ranking_factors(item) for item in segment_list) else "fail",
    )
    _add_check(
        checks,
        "clip_order_matches_highlights",
        "pass" if clip_order_matches_highlights(highlight_plan, segment_list) else "fail",
    )


def _highlight_plan_summary(plan: dict[str, Any] | None, quality_profile: str) -> dict[str, Any]:
    if plan is None:
        return {
            "artifact_type": "highlight_plan",
            "input_mode": None,
            "highlight_count": 0,
            "clip_plan_expected": quality_profile == HIGHLIGHT_CLIP_PLAN_PROFILE,
        }
    highlights = plan.get("highlights")
    highlight_list = highlights if isinstance(highlights, list) else []
    final_scores = [final_score(item) for item in highlight_list]
    return {
        "artifact_type": "highlight_plan",
        "input_mode": plan.get("input_mode"),
        "highlight_count": len(highlight_list),
        "highlight_types": type_distribution(highlight_list),
        "has_timestamps": bool(highlight_list) and all(has_valid_time_range(item) for item in highlight_list),
        "has_ranking_factors": bool(highlight_list) and all_have_ranking_factors(highlight_list),
        "score_range": range_values(number(item.get("score")) for item in highlight_list if isinstance(item, dict)),
        "final_score_range": range_values(score for score in final_scores if score is not None),
        "clip_plan_expected": quality_profile == HIGHLIGHT_CLIP_PLAN_PROFILE,
    }


def _clip_plan_summary(clip_plan: dict[str, Any] | None) -> dict[str, Any] | None:
    if clip_plan is None:
        return None
    segments = clip_plan.get("segments")
    segment_list = segments if isinstance(segments, list) else []
    return {
        "artifact_type": "clip_plan",
        "segment_count": len(segment_list),
        "has_highlight_metadata": bool(segment_list) and all(segment_has_highlight_id(item) for item in segment_list),
        "has_ranking_factors": bool(segment_list) and all(segment_has_ranking_factors(item) for item in segment_list),
    }


def _review_check(check: dict[str, Any]) -> dict[str, Any]:
    status = check["status"]
    mapped = "passed" if status == "pass" else "warning" if status == "warning" else "failed"
    result = {"id": check["name"], "status": mapped, "message": f"{check['name']} {status}"}
    if "details" in check:
        result["details"] = check["details"]
    return result


def _review_status(checks: list[dict[str, Any]]) -> str:
    if any(check["status"] == "failed" for check in checks):
        return "failed"
    if any(check["status"] == "warning" for check in checks):
        return "warning"
    return "passed"


def _add_file_check(path: Path, name: str, checks: list[dict[str, Any]]) -> None:
    _add_check(checks, name, "pass" if path.is_file() else "fail")


def _add_check(
    checks: list[dict[str, Any]],
    name: str,
    status: str,
    details: dict[str, Any] | None = None,
) -> None:
    check: dict[str, Any] = {"name": name, "status": status}
    if details is not None:
        check["details"] = details
    checks.append(check)


def _read_json_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _check_error(check: dict[str, Any]) -> str:
    return f"{check['name']} failed"
