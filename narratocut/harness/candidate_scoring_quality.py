from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narratocut.harness.quality_profiles import CANDIDATE_SCORING_PROFILE


def build_candidate_scoring_quality_report(root: str | Path) -> dict[str, Any]:
    run_dir = Path(root)
    ocr_transcript = _read_json_object(run_dir / "ocr_transcript.json")
    ocr_manifest = _read_json_object(run_dir / "ocr_transcript_manifest.json")
    candidates = _read_json_object(run_dir / "candidate_windows.json")
    score_report = _read_json_object(run_dir / "highlight_score_report.json")
    highlight_plan = _read_json_object(run_dir / "highlight_plan.json")

    checks: list[dict[str, Any]] = []
    for filename in [
        "manifest.json",
        "run_manifest.json",
        "trace.json",
        "ocr_transcript.json",
        "ocr_transcript_manifest.json",
        "candidate_windows.json",
        "highlight_score_report.json",
        "highlight_plan.json",
    ]:
        _add_file_check(run_dir / filename, f"{Path(filename).stem}_exists", checks)

    _add_check(checks, "ocr_transcript_channel", "pass" if _channel(ocr_transcript) == "ocr_subtitle" else "fail")
    _add_check(checks, "ocr_manifest_succeeded", "pass" if _status(ocr_manifest) == "succeeded" else "fail")
    _add_check(checks, "candidate_count_positive", "pass" if _count(candidates, "candidates") > 0 else "fail")
    _add_check(checks, "score_report_succeeded", "pass" if _status(score_report) == "succeeded" else "fail")
    _add_check(checks, "score_report_selected_positive", "pass" if _selected_count(score_report) > 0 else "fail")
    _add_check(checks, "selected_candidates_have_scores", "pass" if _selected_have_scores(score_report) else "fail")
    _add_check(checks, "highlight_plan_has_candidate_ids", "pass" if _highlights_have_candidate_ids(highlight_plan) else "fail")

    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "status": "fail" if failed else "pass",
        "checks": checks,
        "warnings": [],
        "errors": [_check_error(check) for check in failed],
        "summary": {
            "quality_profile": CANDIDATE_SCORING_PROFILE,
            "ocr_segments": _count(ocr_transcript, "segments"),
            "candidate_count": _count(candidates, "candidates"),
            "selected_count": _selected_count(score_report),
        },
    }


def build_candidate_scoring_review_section(root: str | Path) -> dict[str, Any]:
    report = build_candidate_scoring_quality_report(root)
    checks = [_review_check(check) for check in report["checks"]]
    return {
        "name": "candidate_scoring",
        "status": _review_status(checks),
        "checks": checks,
    }


def _read_json_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _channel(payload: dict[str, Any] | None) -> str | None:
    metadata = payload.get("metadata") if payload else None
    if isinstance(metadata, dict) and isinstance(metadata.get("content_channel"), str):
        return metadata["content_channel"]
    return None


def _status(payload: dict[str, Any] | None) -> str | None:
    return str(payload.get("status")) if payload and payload.get("status") is not None else None


def _count(payload: dict[str, Any] | None, key: str) -> int:
    value = payload.get(key) if payload else None
    return len(value) if isinstance(value, list) else 0


def _selected_count(payload: dict[str, Any] | None) -> int:
    value = payload.get("selected_count") if payload else None
    return int(value) if isinstance(value, int) and value >= 0 else 0


def _selected_have_scores(payload: dict[str, Any] | None) -> bool:
    candidates = payload.get("candidates") if payload else None
    if not isinstance(candidates, list):
        return False
    selected = [item for item in candidates if isinstance(item, dict) and item.get("decision") == "selected"]
    return bool(selected) and all(isinstance(item.get("score_breakdown"), dict) for item in selected)


def _highlights_have_candidate_ids(payload: dict[str, Any] | None) -> bool:
    highlights = payload.get("highlights") if payload else None
    if not isinstance(highlights, list) or not highlights:
        return False
    for item in highlights:
        metadata = item.get("metadata") if isinstance(item, dict) else None
        if not isinstance(metadata, dict) or not metadata.get("candidate_id"):
            return False
    return True


def _review_check(check: dict[str, Any]) -> dict[str, Any]:
    mapped = "passed" if check["status"] == "pass" else "warning" if check["status"] == "warning" else "failed"
    result = {"id": check["name"], "status": mapped, "message": f"{check['name']} {check['status']}"}
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


def _add_check(checks: list[dict[str, Any]], name: str, status: str) -> None:
    checks.append({"name": name, "status": status})


def _check_error(check: dict[str, Any]) -> str:
    return f"{check['name']} failed"
