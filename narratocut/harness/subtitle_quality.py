from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narratocut.harness.quality_profiles import SUBTITLE_EXPORT_PROFILE


def subtitle_artifacts_to_inspect() -> list[str]:
    return [
        "subtitles.srt",
        "subtitle_manifest.json",
        "manifest.json",
        "run_manifest.json",
        "trace.json",
    ]


def build_subtitle_quality_report(root: str | Path) -> dict[str, Any]:
    run_dir = Path(root)
    checks: list[dict[str, Any]] = []
    errors: list[str] = []

    _add_file_check(run_dir / "manifest.json", "manifest_file_exists", checks)
    _add_file_check(run_dir / "run_manifest.json", "run_manifest_file_exists", checks)
    _add_file_check(run_dir / "trace.json", "trace_file_exists", checks)
    subtitle_manifest = _check_json_object(run_dir, "subtitle_manifest_exists", "subtitle_manifest.json", checks)
    _add_manifest_checks(run_dir, subtitle_manifest, checks, errors)

    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "status": "fail" if failed else "pass",
        "checks": checks,
        "warnings": [],
        "errors": errors + [_check_error(check) for check in failed if _check_error(check) not in errors],
        "summary": {
            "quality_profile": SUBTITLE_EXPORT_PROFILE,
            "subtitle_path": subtitle_manifest.get("subtitle_path") if subtitle_manifest else None,
            "segment_count": subtitle_manifest.get("segment_count") if subtitle_manifest else 0,
        },
    }


def build_subtitle_review_section(root: str | Path) -> dict[str, Any]:
    report = build_subtitle_quality_report(root)
    checks = [_review_check(check) for check in report["checks"]]
    return {
        "name": "subtitle_outputs",
        "status": _review_status(checks),
        "checks": checks,
    }


def _add_manifest_checks(
    root: Path,
    subtitle_manifest: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    if subtitle_manifest is None:
        return
    status = str(subtitle_manifest.get("status") or "")
    _add_check(checks, "subtitle_manifest_status", "pass" if status == "succeeded" else "fail", {"status": status})
    errors.extend(str(error) for error in subtitle_manifest.get("errors", []) if error)

    subtitle_ref = str(subtitle_manifest.get("subtitle_path") or "subtitles.srt")
    subtitle_path = root / subtitle_ref
    if not subtitle_path.is_file():
        _add_check(checks, "subtitle_file_exists", "fail", {"path": subtitle_ref})
        errors.append(f"subtitle_file_missing: {subtitle_ref}")
        return
    _add_check(checks, "subtitle_file_exists", "pass", {"path": subtitle_ref})
    _add_check(
        checks,
        "subtitle_file_non_empty",
        "pass" if subtitle_path.stat().st_size > 0 else "fail",
        {"path": subtitle_ref},
    )
    _add_cue_checks(subtitle_manifest, checks)


def _add_cue_checks(subtitle_manifest: dict[str, Any], checks: list[dict[str, Any]]) -> None:
    cues = subtitle_manifest.get("cues")
    cue_list = cues if isinstance(cues, list) else []
    segment_count = int(subtitle_manifest.get("segment_count") or 0)
    _add_check(checks, "subtitle_cues_non_empty", "pass" if cue_list else "fail", {"count": len(cue_list)})
    _add_check(
        checks,
        "subtitle_cue_count_matches_manifest",
        "pass" if len(cue_list) == segment_count and segment_count > 0 else "fail",
        {"cues": len(cue_list), "segment_count": segment_count},
    )
    _add_check(
        checks,
        "subtitle_cue_time_ranges_valid",
        "pass" if cue_list and all(_cue_time_range_valid(cue) for cue in cue_list) else "fail",
    )
    _add_check(
        checks,
        "subtitle_cues_monotonic",
        "pass" if cue_list and _cues_monotonic(cue_list) else "fail",
    )
    _add_check(
        checks,
        "subtitle_cue_text_non_empty",
        "pass" if cue_list and all(_text_non_empty(cue.get("text")) for cue in cue_list if isinstance(cue, dict)) else "fail",
    )


def _cue_time_range_valid(cue: object) -> bool:
    if not isinstance(cue, dict):
        return False
    try:
        start = float(cue.get("start_time"))
        end = float(cue.get("end_time"))
    except (TypeError, ValueError):
        return False
    return start >= 0 and end > start and bool(cue.get("start_timestamp")) and bool(cue.get("end_timestamp"))


def _cues_monotonic(cues: list[object]) -> bool:
    previous_end: float | None = None
    for cue in cues:
        if not isinstance(cue, dict):
            return False
        try:
            start = float(cue.get("start_time"))
            end = float(cue.get("end_time"))
        except (TypeError, ValueError):
            return False
        if previous_end is not None and start < previous_end:
            return False
        previous_end = end
    return True


def _text_non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _check_json_object(
    root: Path,
    exists_check: str,
    filename: str,
    checks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    path = root / filename
    if not _add_file_check(path, exists_check, checks):
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        _add_check(checks, f"{exists_check}_valid_json_object", "fail")
        return None
    if isinstance(payload, dict):
        return payload
    _add_check(checks, f"{exists_check}_valid_json_object", "fail")
    return None


def _add_file_check(path: Path, name: str, checks: list[dict[str, Any]]) -> bool:
    exists = path.is_file()
    _add_check(checks, name, "pass" if exists else "fail")
    return exists


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


def _check_error(check: dict[str, Any]) -> str:
    return f"{check['name']} failed"
