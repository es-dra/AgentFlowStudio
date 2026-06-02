from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow_studio.slicing_sop import probe_video_metadata, resolve_media_tool_paths


FINAL_VIDEO_QUALITY_PROFILE = "final_video"
FINAL_DURATION_TOLERANCE_SEC = 1.0
KNOWN_FFMPEG_WARNING_PATTERNS = [
    ("non_monotonic_dts", "Non-monotonic DTS"),
    ("dts_out_of_order", "DTS out of order"),
    ("invalid_non_monotonic_dts", "non monotonically increasing dts"),
]


def build_final_video_quality_report(root: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    _add_file_check(root / "manifest.json", "manifest_file_exists", checks)
    _add_file_check(root / "run_manifest.json", "run_manifest_file_exists", checks)
    _add_file_check(root / "trace.json", "trace_file_exists", checks)
    assembly_plan = _check_json_object(root, "assembly_plan_exists", "assembly_plan.json", checks)
    final_manifest = _check_json_object(root, "final_video_manifest_exists", "final_video_manifest.json", checks)
    _add_final_manifest_status_check(final_manifest, checks, errors)
    _add_final_video_file_checks(root, final_manifest, checks, warnings, errors)
    _add_ffmpeg_warning_checks(final_manifest, checks, warnings)
    _add_final_stream_check(root, final_manifest, checks, errors)
    _add_final_duration_check(root, assembly_plan, final_manifest, checks, warnings, errors)

    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "status": "fail" if failed else "pass",
        "checks": checks,
        "warnings": warnings,
        "errors": errors + [_check_error(check) for check in failed if _check_error(check) not in errors],
        "summary": {
            "quality_profile": FINAL_VIDEO_QUALITY_PROFILE,
            "final_video": final_manifest.get("final_video") if final_manifest else None,
            "input_clip_count": final_manifest.get("input_clip_count") if final_manifest else 0,
        },
    }


def final_video_artifacts_to_inspect() -> list[str]:
    return [
        "assembly_plan.json",
        "concat_list.txt",
        "final_video_manifest.json",
        "final_video.mp4",
        "manifest.json",
        "run_manifest.json",
        "trace.json",
    ]


def _add_final_manifest_status_check(
    final_manifest: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    if final_manifest is None:
        return
    status = str(final_manifest.get("status") or "")
    _add_check(checks, "final_video_manifest_status", "pass" if status == "succeeded" else "fail", {"status": status})
    errors.extend(str(error) for error in final_manifest.get("errors", []) if error)


def _add_final_video_file_checks(
    root: Path,
    final_manifest: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    warnings: list[str],
    errors: list[str],
) -> None:
    if final_manifest is None:
        return
    ref = str(final_manifest.get("final_video") or "")
    path = root / ref
    if not ref or not path.is_file():
        _add_check(checks, "final_video_file_exists", "fail", {"path": ref})
        errors.append(f"final_video_missing: {ref}")
        return
    if path.stat().st_size <= 0:
        _add_check(checks, "final_video_file_size_positive", "fail", {"path": ref})
        errors.append(f"final_video_empty: {ref}")
        return
    _add_check(checks, "final_video_file_exists", "pass", {"path": ref})


def _add_ffmpeg_warning_checks(
    final_manifest: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    warnings: list[str],
) -> None:
    if final_manifest is None:
        return
    classified = _classify_ffmpeg_warnings(str(final_manifest.get("stderr") or ""))
    if not classified:
        _add_check(checks, "final_video_ffmpeg_warnings", "pass", {"warnings": []})
        return
    for item in classified:
        warnings.append(f"final_video_ffmpeg_warning: {item['code']}")
    _add_check(checks, "final_video_ffmpeg_warnings", "warning", {"warnings": classified})


def _add_final_stream_check(
    root: Path,
    final_manifest: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    if final_manifest is None:
        return
    ref = str(final_manifest.get("final_video") or "")
    if not ref or not (root / ref).is_file():
        return
    manifest_warnings = [str(item) for item in final_manifest.get("warnings", []) if item]
    if "video_stream_missing" in manifest_warnings:
        _add_check(checks, "final_video_stream_present", "fail", {"path": ref, "errors": manifest_warnings})
        errors.append(f"final_video_stream_missing: {ref}")
        return
    paths = resolve_media_tool_paths()
    metadata = probe_video_metadata(root / ref, ffprobe_executable=paths.ffprobe)
    if metadata.probe_status == "succeeded":
        _add_check(checks, "final_video_stream_present", "pass", {"path": ref})
        return
    if "video_stream_missing" in metadata.errors:
        _add_check(checks, "final_video_stream_present", "fail", {"path": ref, "errors": metadata.errors})
        errors.append(f"final_video_stream_missing: {ref}")


def _add_final_duration_check(
    root: Path,
    assembly_plan: dict[str, Any] | None,
    final_manifest: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    warnings: list[str],
    errors: list[str],
) -> None:
    if assembly_plan is None or final_manifest is None:
        return
    ref = str(final_manifest.get("final_video") or "")
    expected = _optional_float(assembly_plan.get("target_duration_sec"))
    if not ref or expected is None or not (root / ref).is_file():
        return
    paths = resolve_media_tool_paths()
    metadata = probe_video_metadata(root / ref, ffprobe_executable=paths.ffprobe)
    if metadata.probe_status != "succeeded":
        warning = f"final_video_duration_probe_failed: {ref}"
        warnings.append(warning)
        _add_check(checks, "final_video_duration_probe", "warning", {"path": ref, "errors": metadata.errors})
        return
    actual = metadata.duration_sec
    if actual is None:
        warning = f"final_video_duration_missing: {ref}"
        warnings.append(warning)
        _add_check(checks, "final_video_duration_probe", "warning", {"path": ref})
        return
    delta = abs(actual - expected)
    status = "pass" if delta <= FINAL_DURATION_TOLERANCE_SEC else "fail"
    _add_check(
        checks,
        "final_video_duration_tolerance",
        status,
        {
            "path": ref,
            "expected_sec": expected,
            "actual_sec": actual,
            "tolerance_sec": FINAL_DURATION_TOLERANCE_SEC,
        },
    )
    if status == "fail":
        errors.append(f"final_video_duration_out_of_tolerance: {ref}")


def _classify_ffmpeg_warnings(stderr: str) -> list[dict[str, str]]:
    classified: list[dict[str, str]] = []
    lowered = stderr.lower()
    for code, pattern in KNOWN_FFMPEG_WARNING_PATTERNS:
        if pattern.lower() in lowered:
            classified.append(
                {
                    "code": code,
                    "severity": "warning",
                    "source": "ffmpeg_stderr",
                    "message": pattern,
                }
            )
    return classified


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


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _check_error(check: dict[str, Any]) -> str:
    return f"{check['name']} failed"
