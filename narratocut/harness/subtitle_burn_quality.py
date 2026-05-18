from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narratocut.harness.quality_profiles import SUBTITLE_BURN_PROFILE
from narratocut.slicing_sop import probe_video_metadata, resolve_media_tool_paths


KNOWN_FFMPEG_WARNING_PATTERNS = [
    ("non_monotonic_dts", "Non-monotonic DTS"),
    ("dts_out_of_order", "DTS out of order"),
    ("invalid_non_monotonic_dts", "non monotonically increasing dts"),
]


def subtitle_burn_artifacts_to_inspect() -> list[str]:
    return [
        "subtitle_burn_manifest.json",
        "final_video_with_subtitles.mp4",
        "manifest.json",
        "run_manifest.json",
        "trace.json",
    ]


def build_subtitle_burn_quality_report(root: str | Path) -> dict[str, Any]:
    run_dir = Path(root)
    checks: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    _add_file_check(run_dir / "manifest.json", "manifest_file_exists", checks)
    _add_file_check(run_dir / "run_manifest.json", "run_manifest_file_exists", checks)
    _add_file_check(run_dir / "trace.json", "trace_file_exists", checks)
    burn_manifest = _check_json_object(run_dir, "subtitle_burn_manifest_exists", "subtitle_burn_manifest.json", checks)
    _add_manifest_checks(run_dir, burn_manifest, checks, warnings, errors)

    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "status": "fail" if failed else "pass",
        "checks": checks,
        "warnings": warnings,
        "errors": errors + [_check_error(check) for check in failed if _check_error(check) not in errors],
        "summary": {
            "quality_profile": SUBTITLE_BURN_PROFILE,
            "output_video": burn_manifest.get("output_video") if burn_manifest else None,
            "duration_sec": burn_manifest.get("duration_sec") if burn_manifest else None,
        },
    }


def build_subtitle_burn_review_section(root: str | Path) -> dict[str, Any]:
    report = build_subtitle_burn_quality_report(root)
    checks = [_review_check(check) for check in report["checks"]]
    return {
        "name": "subtitle_burn_outputs",
        "status": _review_status(checks),
        "checks": checks,
    }


def _add_manifest_checks(
    root: Path,
    burn_manifest: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    warnings: list[str],
    errors: list[str],
) -> None:
    if burn_manifest is None:
        return
    status = str(burn_manifest.get("status") or "")
    _add_check(checks, "subtitle_burn_manifest_status", "pass" if status == "succeeded" else "fail", {"status": status})
    errors.extend(str(error) for error in burn_manifest.get("errors", []) if error)
    _add_ffmpeg_checks(burn_manifest, checks, warnings, errors)
    _add_output_video_checks(root, burn_manifest, checks, errors)


def _add_ffmpeg_checks(
    burn_manifest: dict[str, Any],
    checks: list[dict[str, Any]],
    warnings: list[str],
    errors: list[str],
) -> None:
    command = burn_manifest.get("ffmpeg_command")
    returncode = burn_manifest.get("returncode")
    _add_check(checks, "subtitle_burn_ffmpeg_command_present", "pass" if isinstance(command, list) and command else "fail")
    _add_check(checks, "subtitle_burn_ffmpeg_returncode", "pass" if returncode == 0 else "fail", {"returncode": returncode})
    if returncode not in (0, None):
        errors.append(f"subtitle_burn_ffmpeg_failed: {returncode}")

    classified = _classify_ffmpeg_warnings(str(burn_manifest.get("stderr") or ""))
    if not classified:
        _add_check(checks, "subtitle_burn_ffmpeg_warnings", "pass", {"warnings": []})
        return
    warnings.extend(f"subtitle_burn_ffmpeg_warning: {item['code']}" for item in classified)
    _add_check(checks, "subtitle_burn_ffmpeg_warnings", "warning", {"warnings": classified})


def _add_output_video_checks(
    root: Path,
    burn_manifest: dict[str, Any],
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    ref = str(burn_manifest.get("output_video") or "")
    path = root / ref
    if not ref or not path.is_file():
        _add_check(checks, "subtitle_burn_output_file_exists", "fail", {"path": ref})
        errors.append(f"subtitle_burn_output_missing: {ref}")
        return
    _add_check(checks, "subtitle_burn_output_file_exists", "pass", {"path": ref})
    _add_check(
        checks,
        "subtitle_burn_output_file_size_positive",
        "pass" if path.stat().st_size > 0 else "fail",
        {"path": ref},
    )
    paths = resolve_media_tool_paths()
    metadata = probe_video_metadata(path, ffprobe_executable=paths.ffprobe)
    if metadata.probe_status == "succeeded":
        _add_check(checks, "subtitle_burn_video_stream_present", "pass", {"path": ref})
        return
    if "video_stream_missing" in metadata.errors:
        _add_check(checks, "subtitle_burn_video_stream_present", "fail", {"path": ref, "errors": metadata.errors})
        errors.append(f"subtitle_burn_video_stream_missing: {ref}")
    else:
        _add_check(checks, "subtitle_burn_video_probe", "warning", {"path": ref, "errors": metadata.errors})


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
