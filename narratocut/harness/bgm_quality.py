from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narratocut.harness.quality_profiles import BGM_MIX_PROFILE
from narratocut.slicing_sop import probe_video_metadata, resolve_media_tool_paths


def bgm_artifacts_to_inspect() -> list[str]:
    return [
        "audio_mix_manifest.json",
        "final_video_with_bgm.mp4",
        "manifest.json",
        "run_manifest.json",
        "trace.json",
    ]


def build_bgm_quality_report(root: str | Path) -> dict[str, Any]:
    run_dir = Path(root)
    checks: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    _add_file_check(run_dir / "manifest.json", "manifest_file_exists", checks)
    _add_file_check(run_dir / "run_manifest.json", "run_manifest_file_exists", checks)
    _add_file_check(run_dir / "trace.json", "trace_file_exists", checks)
    mix_manifest = _check_json_object(run_dir, "audio_mix_manifest_exists", "audio_mix_manifest.json", checks)
    _add_manifest_checks(run_dir, mix_manifest, checks, warnings, errors)

    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "status": "fail" if failed else "pass",
        "checks": checks,
        "warnings": warnings,
        "errors": errors + [_check_error(check) for check in failed if _check_error(check) not in errors],
        "summary": {
            "quality_profile": BGM_MIX_PROFILE,
            "output_video": mix_manifest.get("output_video") if mix_manifest else None,
            "duration_sec": mix_manifest.get("duration_sec") if mix_manifest else None,
        },
    }


def build_bgm_review_section(root: str | Path) -> dict[str, Any]:
    report = build_bgm_quality_report(root)
    checks = [_review_check(check) for check in report["checks"]]
    return {
        "name": "bgm_mix_outputs",
        "status": _review_status(checks),
        "checks": checks,
    }


def _add_manifest_checks(
    root: Path,
    mix_manifest: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    warnings: list[str],
    errors: list[str],
) -> None:
    if mix_manifest is None:
        return
    status = str(mix_manifest.get("status") or "")
    _add_check(checks, "bgm_mix_manifest_status", "pass" if status == "succeeded" else "fail", {"status": status})
    errors.extend(str(error) for error in mix_manifest.get("errors", []) if error)
    _add_ffmpeg_checks(mix_manifest, checks, errors)
    _add_output_video_checks(root, mix_manifest, checks, errors)
    warnings.extend(str(warning) for warning in mix_manifest.get("warnings", []) if warning)


def _add_ffmpeg_checks(
    mix_manifest: dict[str, Any],
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    command = mix_manifest.get("ffmpeg_command")
    returncode = mix_manifest.get("returncode")
    _add_check(checks, "bgm_mix_ffmpeg_command_present", "pass" if isinstance(command, list) and command else "fail")
    _add_check(checks, "bgm_mix_ffmpeg_returncode", "pass" if returncode == 0 else "fail", {"returncode": returncode})
    if returncode not in (0, None):
        errors.append(f"bgm_mix_ffmpeg_failed: {returncode}")


def _add_output_video_checks(
    root: Path,
    mix_manifest: dict[str, Any],
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    ref = str(mix_manifest.get("output_video") or "")
    if not _is_safe_file_ref(ref):
        _add_check(checks, "bgm_mix_output_path_safe", "fail", {"path": ref})
        errors.append(f"bgm_mix_output_path_unsafe: {ref}")
        return
    _add_check(checks, "bgm_mix_output_path_safe", "pass", {"path": ref})
    path = root / ref
    if not ref or not path.is_file():
        _add_check(checks, "bgm_mix_output_file_exists", "fail", {"path": ref})
        errors.append(f"bgm_mix_output_missing: {ref}")
        return
    _add_check(checks, "bgm_mix_output_file_exists", "pass", {"path": ref})
    _add_check(
        checks,
        "bgm_mix_output_file_size_positive",
        "pass" if path.stat().st_size > 0 else "fail",
        {"path": ref},
    )
    paths = resolve_media_tool_paths()
    metadata = probe_video_metadata(path, ffprobe_executable=paths.ffprobe)
    if metadata.probe_status == "succeeded":
        _add_check(checks, "bgm_mix_video_stream_present", "pass", {"path": ref})
        return
    if "video_stream_missing" in metadata.errors:
        _add_check(checks, "bgm_mix_video_stream_present", "fail", {"path": ref, "errors": metadata.errors})
        errors.append(f"bgm_mix_video_stream_missing: {ref}")
    else:
        _add_check(checks, "bgm_mix_video_probe", "warning", {"path": ref, "errors": metadata.errors})


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


def _is_safe_file_ref(ref: str) -> bool:
    path = Path(ref)
    return bool(ref) and not path.is_absolute() and ".." not in path.parts and path.name == ref


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
