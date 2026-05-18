from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narratocut.harness.quality_profiles import FINISHED_PACKAGE_PROFILE


def package_artifacts_to_inspect() -> list[str]:
    return [
        "finished_package_manifest.json",
        "manifest.json",
        "run_manifest.json",
        "trace.json",
    ]


def build_package_quality_report(root: str | Path) -> dict[str, Any]:
    run_dir = Path(root)
    checks: list[dict[str, Any]] = []
    errors: list[str] = []

    _add_file_check(run_dir / "manifest.json", "manifest_file_exists", checks)
    _add_file_check(run_dir / "run_manifest.json", "run_manifest_file_exists", checks)
    _add_file_check(run_dir / "trace.json", "trace_file_exists", checks)
    package = _check_json_object(run_dir, "finished_package_manifest_exists", "finished_package_manifest.json", checks)
    _add_package_checks(run_dir, package, checks, errors)

    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "status": "fail" if failed else "pass",
        "checks": checks,
        "warnings": [],
        "errors": errors + [_check_error(check) for check in failed if _check_error(check) not in errors],
        "summary": {
            "quality_profile": FINISHED_PACKAGE_PROFILE,
            "package_id": package.get("package_id") if package else None,
            "asset_count": len(package.get("assets", [])) if package else 0,
        },
    }


def build_package_review_section(root: str | Path) -> dict[str, Any]:
    report = build_package_quality_report(root)
    checks = [_review_check(check) for check in report["checks"]]
    return {
        "name": "finished_package_outputs",
        "status": _review_status(checks),
        "checks": checks,
    }


def _add_package_checks(
    root: Path,
    package: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    if package is None:
        return
    status = str(package.get("status") or "")
    _add_check(checks, "finished_package_manifest_status", "pass" if status == "succeeded" else "fail", {"status": status})
    errors.extend(str(error) for error in package.get("errors", []) if error)
    assets = package.get("assets")
    if not isinstance(assets, list) or not assets:
        _add_check(checks, "finished_package_assets_non_empty", "fail", {"count": 0})
        return
    _add_check(checks, "finished_package_assets_non_empty", "pass", {"count": len(assets)})
    for asset in assets:
        if isinstance(asset, dict):
            _add_asset_check(root, asset, checks, errors)


def _add_asset_check(
    root: Path,
    asset: dict[str, Any],
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    role = _safe_check_fragment(str(asset.get("role") or "asset"))
    path = str(asset.get("path") or "")
    exists = _asset_path(root, path).is_file()
    status = "pass" if _is_safe_path(path) and exists else "fail"
    _add_check(
        checks,
        f"finished_package_asset_{role}_exists",
        status,
        {"path": path, "required": bool(asset.get("required"))},
    )
    if status == "fail":
        errors.append(f"finished_package_asset_missing: {role}")


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


def _is_safe_path(ref: str) -> bool:
    return bool(ref) and ".." not in Path(ref).parts


def _asset_path(root: Path, ref: str) -> Path:
    path = Path(ref)
    if path.is_absolute() or path.is_file():
        return path
    return root / path


def _safe_check_fragment(value: str) -> str:
    return "".join(char if char.isalnum() or char == "_" else "_" for char in value)


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
