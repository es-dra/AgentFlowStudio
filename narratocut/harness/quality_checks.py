from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narratocut.harness.highlight_artifacts import build_highlight_quality_report, is_highlight_quality_profile
from narratocut.harness.video_artifacts import build_video_quality_report, is_video_quality_profile
from narratocut.slicing_sop import probe_video_metadata, resolve_media_tool_paths


CLIP_DURATION_TOLERANCE_SEC = 0.75


def build_quality_report(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir)
    run_manifest = _read_json(root / "run_manifest.json")
    if isinstance(run_manifest, dict):
        quality_profile = run_manifest.get("quality_profile")
        if quality_profile == "real_video":
            return _build_real_video_quality_report(root)
        if is_video_quality_profile(quality_profile):
            return build_video_quality_report(root, quality_profile)
        if is_highlight_quality_profile(quality_profile):
            return build_highlight_quality_report(root, quality_profile)

    checks: list[dict[str, Any]] = []

    hooks = _check_json_array(root, "hooks_file_exists", "hooks_non_empty", "hooks.json", checks)
    scripts = _check_json_array(root, "scripts_file_exists", "scripts_non_empty", "scripts.json", checks)
    clip_plans = _check_json_array(
        root,
        "clip_plans_file_exists",
        "clip_plans_non_empty",
        "clip_plans.json",
        checks,
    )
    _add_file_check(root / "manifest.json", "manifest_file_exists", checks)
    _add_file_check(root / "run_manifest.json", "run_manifest_file_exists", checks)
    _add_file_check(root / "trace.json", "trace_file_exists", checks)
    slice_manifest = _check_json_object(
        root,
        "slice_manifest_exists",
        "slice_manifest.json",
        checks,
    )
    clips_dir = root / "clips"
    _add_check(checks, "clips_dir_exists", "pass" if clips_dir.is_dir() else "fail")
    _add_mock_clip_count_check(clips_dir, slice_manifest, checks)

    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "status": "fail" if failed else "pass",
        "checks": checks,
        "warnings": [],
        "errors": [_check_error(check) for check in failed],
        "summary": {
            "hooks": len(hooks) if hooks is not None else 0,
            "scripts": len(scripts) if scripts is not None else 0,
            "clip_plans": len(clip_plans) if clip_plans is not None else 0,
        },
    }


def _build_real_video_quality_report(root: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    _add_file_check(root / "manifest.json", "manifest_file_exists", checks)
    _add_file_check(root / "run_manifest.json", "run_manifest_file_exists", checks)
    _add_file_check(root / "trace.json", "trace_file_exists", checks)

    metadata = _check_json_object(root, "video_metadata_exists", "video_metadata.json", checks)
    validation = _check_json_object(
        root,
        "clip_plan_validation_exists",
        "clip_plan_validation.json",
        checks,
    )
    real_manifest = _check_json_object(
        root,
        "real_slice_manifest_exists",
        "real_slice_manifest.json",
        checks,
    )

    _add_video_metadata_status_check(metadata, checks, errors)
    _add_validation_status_check(validation, checks, warnings, errors)
    _add_real_slice_manifest_status_check(real_manifest, checks, errors)
    _add_real_clip_file_checks(root, real_manifest, checks, warnings, errors)

    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "status": "fail" if failed else "pass",
        "checks": checks,
        "warnings": warnings,
        "errors": errors + [_check_error(check) for check in failed if _check_error(check) not in errors],
        "summary": {
            "quality_profile": "real_video",
            "clips": _real_clip_count(real_manifest),
        },
    }


def _check_json_array(
    root: Path,
    exists_check: str,
    non_empty_check: str,
    filename: str,
    checks: list[dict[str, Any]],
) -> list[Any] | None:
    path = root / filename
    if not _add_file_check(path, exists_check, checks):
        _add_check(checks, non_empty_check, "fail", {"count": 0})
        return None

    payload = _read_json(path)
    if not isinstance(payload, list):
        _add_check(checks, non_empty_check, "fail", {"reason": "not_json_array"})
        return None

    status = "pass" if payload else "fail"
    _add_check(checks, non_empty_check, status, {"count": len(payload)})
    return payload


def _check_json_object(
    root: Path,
    exists_check: str,
    filename: str,
    checks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    path = root / filename
    if not _add_file_check(path, exists_check, checks):
        return None

    payload = _read_json(path)
    if isinstance(payload, dict):
        return payload

    _add_check(checks, f"{exists_check}_valid_json_object", "fail")
    return None


def _add_mock_clip_count_check(
    clips_dir: Path,
    slice_manifest: dict[str, Any] | None,
    checks: list[dict[str, Any]],
) -> None:
    clip_count = len(list(clips_dir.glob("*.txt"))) if clips_dir.is_dir() else 0
    manifest_count = 0
    if slice_manifest is not None:
        manifest_count = int(slice_manifest.get("clip_count") or len(slice_manifest.get("items", [])))
    status = "pass" if clip_count == manifest_count and manifest_count > 0 else "fail"
    _add_check(
        checks,
        "mock_clips_count_matches_manifest",
        status,
        {"clips": clip_count, "manifest_items": manifest_count},
    )


def _add_video_metadata_status_check(
    metadata: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    if metadata is None:
        return
    status = metadata.get("probe_status")
    if status == "succeeded":
        _add_check(checks, "video_metadata_status", "pass", {"probe_status": status})
        return
    details = {"probe_status": status, "errors": metadata.get("errors", [])}
    _add_check(checks, "video_metadata_status", "fail", details)
    errors.extend(str(error) for error in metadata.get("errors", []) if error)


def _add_validation_status_check(
    validation: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    warnings: list[str],
    errors: list[str],
) -> None:
    if validation is None:
        return
    status = str(validation.get("status") or "")
    if status in {"passed", "passed_with_warnings"}:
        check_status = "warning" if status == "passed_with_warnings" else "pass"
        _add_check(checks, "clip_plan_validation_status", check_status, {"status": status})
    else:
        _add_check(checks, "clip_plan_validation_status", "fail", {"status": status})
    for issue in validation.get("warnings", []) if isinstance(validation.get("warnings"), list) else []:
        if isinstance(issue, dict) and issue.get("code"):
            warnings.append(str(issue["code"]))
    for issue in validation.get("hard_errors", []) if isinstance(validation.get("hard_errors"), list) else []:
        if isinstance(issue, dict) and issue.get("code"):
            errors.append(str(issue["code"]))


def _add_real_slice_manifest_status_check(
    real_manifest: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    if real_manifest is None:
        return
    status = str(real_manifest.get("status") or "")
    check_status = "pass" if status in {"succeeded", "passed"} else "fail"
    _add_check(
        checks,
        "real_slice_manifest_status",
        check_status,
        {"status": status, "reason": real_manifest.get("reason")},
    )
    if check_status == "fail":
        if real_manifest.get("reason"):
            errors.append(str(real_manifest["reason"]))
        errors.extend(str(error) for error in real_manifest.get("errors", []) if error)


def _add_real_clip_file_checks(
    root: Path,
    real_manifest: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    warnings: list[str],
    errors: list[str],
) -> None:
    if real_manifest is None:
        return
    clips = real_manifest.get("clips")
    if not isinstance(clips, list):
        _add_check(checks, "real_clips_declared", "fail")
        return
    succeeded = [clip for clip in clips if isinstance(clip, dict) and clip.get("status") in {"succeeded", "passed"}]
    if not succeeded and real_manifest.get("status") not in {"succeeded", "passed"}:
        _add_check(checks, "real_clips_written", "fail", {"clips": 0})
        return
    for clip in succeeded:
        ref = str(clip.get("path") or "")
        path = root / ref
        if not path.is_file():
            _add_check(checks, "real_clip_file_exists", "fail", {"path": ref})
            errors.append(f"real_clip_missing: {ref}")
            return
        if path.stat().st_size <= 0:
            _add_check(checks, "real_clip_file_size_positive", "fail", {"path": ref})
            errors.append(f"real_clip_empty: {ref}")
            return
    _add_check(checks, "real_clips_written", "pass", {"clips": len(succeeded)})
    _add_real_clip_duration_checks(root, succeeded, checks, warnings, errors)


def _add_real_clip_duration_checks(
    root: Path,
    clips: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    warnings: list[str],
    errors: list[str],
) -> None:
    paths = resolve_media_tool_paths()
    for clip in clips:
        ref = str(clip.get("path") or "")
        expected = _optional_float(clip.get("duration_sec"))
        if not ref or expected is None:
            continue

        metadata = probe_video_metadata(root / ref, ffprobe_executable=paths.ffprobe)
        if metadata.probe_status != "succeeded":
            if any(str(error).startswith("ffprobe_unavailable") for error in metadata.errors):
                return
            warning = f"clip_duration_probe_failed: {ref}"
            warnings.append(warning)
            _add_check(
                checks,
                "real_clip_duration_probe",
                "warning",
                {"path": ref, "errors": metadata.errors},
            )
            continue

        actual = metadata.duration_sec
        if actual is None:
            warning = f"clip_duration_missing: {ref}"
            warnings.append(warning)
            _add_check(checks, "real_clip_duration_probe", "warning", {"path": ref})
            continue

        delta = abs(actual - expected)
        status = "pass" if delta <= CLIP_DURATION_TOLERANCE_SEC else "fail"
        _add_check(
            checks,
            "real_clip_duration_tolerance",
            status,
            {
                "path": ref,
                "expected_sec": expected,
                "actual_sec": actual,
                "tolerance_sec": CLIP_DURATION_TOLERANCE_SEC,
            },
        )
        if status == "fail":
            errors.append(f"clip_duration_out_of_tolerance: {ref}")


def _real_clip_count(real_manifest: dict[str, Any] | None) -> int:
    if real_manifest is None:
        return 0
    clips = real_manifest.get("clips")
    return len(clips) if isinstance(clips, list) else 0


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


def _read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _check_error(check: dict[str, Any]) -> str:
    return f"{check['name']} failed"
