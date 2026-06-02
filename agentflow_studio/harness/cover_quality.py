from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow_studio.harness.quality_profiles import COVER_EXPORT_PROFILE


def cover_artifacts_to_inspect() -> list[str]:
    return [
        "cover_manifest.json",
        "cover.jpg",
        "manifest.json",
        "run_manifest.json",
        "trace.json",
    ]


def build_cover_quality_report(root: str | Path) -> dict[str, Any]:
    run_dir = Path(root)
    checks: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    _add_file_check(run_dir / "manifest.json", "manifest_file_exists", checks)
    _add_file_check(run_dir / "run_manifest.json", "run_manifest_file_exists", checks)
    _add_file_check(run_dir / "trace.json", "trace_file_exists", checks)
    cover_manifest = _check_json_object(run_dir, "cover_manifest_exists", "cover_manifest.json", checks)
    _add_manifest_checks(run_dir, cover_manifest, checks, warnings, errors)

    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "status": "fail" if failed else "pass",
        "checks": checks,
        "warnings": warnings,
        "errors": errors + [_check_error(check) for check in failed if _check_error(check) not in errors],
        "summary": {
            "quality_profile": COVER_EXPORT_PROFILE,
            "cover_path": cover_manifest.get("cover_path") if cover_manifest else None,
            "cover_time_sec": cover_manifest.get("cover_time_sec") if cover_manifest else None,
        },
    }


def build_cover_review_section(root: str | Path) -> dict[str, Any]:
    report = build_cover_quality_report(root)
    checks = [_review_check(check) for check in report["checks"]]
    return {
        "name": "cover_export_outputs",
        "status": _review_status(checks),
        "checks": checks,
    }


def _add_manifest_checks(
    root: Path,
    cover_manifest: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    warnings: list[str],
    errors: list[str],
) -> None:
    if cover_manifest is None:
        return
    status = str(cover_manifest.get("status") or "")
    _add_check(checks, "cover_manifest_status", "pass" if status == "succeeded" else "fail", {"status": status})
    errors.extend(str(error) for error in cover_manifest.get("errors", []) if error)
    _add_ffmpeg_checks(cover_manifest, checks, errors)
    _add_cover_image_checks(root, cover_manifest, checks, errors)
    warnings.extend(str(warning) for warning in cover_manifest.get("warnings", []) if warning)


def _add_ffmpeg_checks(
    cover_manifest: dict[str, Any],
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    command = cover_manifest.get("ffmpeg_command")
    returncode = cover_manifest.get("returncode")
    _add_check(checks, "cover_ffmpeg_command_present", "pass" if isinstance(command, list) and command else "fail")
    _add_check(checks, "cover_ffmpeg_returncode", "pass" if returncode == 0 else "fail", {"returncode": returncode})
    if returncode not in (0, None):
        errors.append(f"cover_ffmpeg_failed: {returncode}")


def _add_cover_image_checks(
    root: Path,
    cover_manifest: dict[str, Any],
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    ref = str(cover_manifest.get("cover_path") or "")
    if not _is_safe_file_ref(ref):
        _add_check(checks, "cover_image_path_safe", "fail", {"path": ref})
        errors.append(f"cover_image_path_unsafe: {ref}")
        return
    _add_check(checks, "cover_image_path_safe", "pass", {"path": ref})
    path = root / ref
    if not ref or not path.is_file():
        _add_check(checks, "cover_image_file_exists", "fail", {"path": ref})
        errors.append(f"cover_image_missing: {ref}")
        return
    _add_check(checks, "cover_image_file_exists", "pass", {"path": ref})
    _add_check(
        checks,
        "cover_image_file_size_positive",
        "pass" if path.stat().st_size > 0 else "fail",
        {"path": ref},
    )


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
