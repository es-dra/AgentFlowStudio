from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narratocut.harness.quality_profiles import CANDIDATE_WINDOWS_PROFILE


def candidate_artifacts_to_inspect() -> list[str]:
    return ["candidate_windows.json", "manifest.json", "run_manifest.json", "trace.json"]


def build_candidate_quality_report(root: str | Path) -> dict[str, Any]:
    run_dir = Path(root)
    manifest = _read_json_object(run_dir / "candidate_windows.json")

    checks: list[dict[str, Any]] = []
    _add_file_check(run_dir / "manifest.json", "manifest_file_exists", checks)
    _add_file_check(run_dir / "run_manifest.json", "run_manifest_file_exists", checks)
    _add_file_check(run_dir / "trace.json", "trace_file_exists", checks)
    _add_file_check(run_dir / "candidate_windows.json", "candidate_windows_exists", checks)
    _add_check(checks, "candidate_windows_json_object", "pass" if manifest is not None else "fail")

    if manifest is not None:
        _add_candidate_manifest_checks(checks, manifest)

    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "status": "fail" if failed else "pass",
        "checks": checks,
        "warnings": [],
        "errors": [_check_error(check) for check in failed],
        "summary": {
            "quality_profile": CANDIDATE_WINDOWS_PROFILE,
            "candidate_windows": _candidate_summary(manifest),
        },
    }


def build_candidate_review_section(root: str | Path) -> dict[str, Any]:
    report = build_candidate_quality_report(root)
    checks = [_review_check(check) for check in report["checks"]]
    return {
        "name": "candidate_windows",
        "status": _review_status(checks),
        "checks": checks,
    }


def _add_candidate_manifest_checks(checks: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    candidates = manifest.get("candidates")
    candidate_list = candidates if isinstance(candidates, list) else []
    declared_count = manifest.get("candidate_count")
    min_duration = _number(manifest.get("min_duration_sec"))
    max_duration = _number(manifest.get("max_duration_sec"))

    _add_check(checks, "candidate_windows_status_succeeded", "pass" if manifest.get("status") == "succeeded" else "fail")
    _add_check(checks, "candidate_count_positive", "pass" if candidate_list else "fail", {"count": len(candidate_list)})
    _add_check(
        checks,
        "candidate_count_matches_manifest",
        "pass" if declared_count == len(candidate_list) else "fail",
        {"declared": declared_count, "actual": len(candidate_list)},
    )
    _add_check(
        checks,
        "candidate_content_channel_present",
        "pass" if isinstance(manifest.get("content_channel"), str) and manifest["content_channel"] else "fail",
    )
    _add_check(
        checks,
        "candidate_timestamps_valid",
        "pass" if all(_candidate_has_valid_time_range(candidate) for candidate in candidate_list) else "fail",
    )
    _add_check(
        checks,
        "candidate_segment_ids_present",
        "pass" if all(_candidate_has_segment_ids(candidate) for candidate in candidate_list) else "fail",
    )
    _add_check(
        checks,
        "candidate_duration_bounds",
        "pass" if all(_candidate_within_bounds(candidate, min_duration, max_duration) for candidate in candidate_list) else "fail",
        {"min_duration_sec": min_duration, "max_duration_sec": max_duration},
    )


def _candidate_summary(manifest: dict[str, Any] | None) -> dict[str, Any]:
    if manifest is None:
        return {
            "artifact_type": "candidate_windows",
            "candidate_count": 0,
            "content_channel": None,
        }
    candidates = manifest.get("candidates")
    candidate_list = candidates if isinstance(candidates, list) else []
    return {
        "artifact_type": "candidate_windows",
        "candidate_count": len(candidate_list),
        "content_channel": manifest.get("content_channel"),
        "max_window_size": manifest.get("max_window_size"),
    }


def _candidate_has_valid_time_range(candidate: Any) -> bool:
    if not isinstance(candidate, dict):
        return False
    start = _number(candidate.get("start_sec"))
    end = _number(candidate.get("end_sec"))
    duration = _number(candidate.get("duration_sec"))
    if start is None or end is None or duration is None:
        return False
    return start >= 0 and end > start and duration > 0


def _candidate_has_segment_ids(candidate: Any) -> bool:
    if not isinstance(candidate, dict):
        return False
    segment_ids = candidate.get("segment_ids")
    return isinstance(segment_ids, list) and bool(segment_ids) and all(isinstance(item, str) and item for item in segment_ids)


def _candidate_within_bounds(candidate: Any, min_duration: float | None, max_duration: float | None) -> bool:
    if not isinstance(candidate, dict):
        return False
    duration = _number(candidate.get("duration_sec"))
    if duration is None:
        return False
    if min_duration is not None and duration < min_duration:
        return False
    if max_duration is not None and duration > max_duration:
        return False
    return True


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


def _number(value: Any) -> float | None:
    return value if isinstance(value, int | float) and not isinstance(value, bool) else None


def _check_error(check: dict[str, Any]) -> str:
    return f"{check['name']} failed"
