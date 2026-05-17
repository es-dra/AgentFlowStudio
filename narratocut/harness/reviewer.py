from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narratocut.utils import write_json


SCHEMA_VERSION = "0.1"
PASSED = "passed"
WARNING = "warning"
FAILED = "failed"


def review_run(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir)
    run_manifest = _load_json_object(root / "run_manifest.json")
    trace = _load_json_object(root / "trace.json")
    quality_report = _load_json_object(root / "quality_report.json")

    sections = [
        _run_contract_section(root, run_manifest, trace, quality_report),
        _workflow_outputs_section(root, run_manifest),
    ]
    summary = _summarize_sections(sections)

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": _run_id(root, run_manifest),
        "status": _status_from_summary(summary),
        "summary": summary,
        "inputs": {
            "run_dir": _display_ref(root),
            "manifest": "run_manifest.json",
            "trace": "trace.json",
            "quality_report": "quality_report.json",
        },
        "sections": sections,
        "recommendations": [],
    }


def write_review_report(
    run_dir: str | Path,
    report: dict[str, Any] | None = None,
) -> Path:
    root = Path(run_dir)
    review_report = report if report is not None else review_run(root)
    return write_json(root / "review_report.json", review_report)


def _run_contract_section(
    root: Path,
    run_manifest: dict[str, Any] | None,
    trace: dict[str, Any] | None,
    quality_report: dict[str, Any] | None,
) -> dict[str, Any]:
    checks = [
        _file_check(root / "run_manifest.json", "manifest_exists", "run_manifest.json exists"),
        _file_check(root / "trace.json", "trace_exists", "trace.json exists"),
        _file_check(
            root / "quality_report.json",
            "quality_report_exists",
            "quality_report.json exists",
        ),
        _trace_steps_check(trace),
        _quality_report_check(quality_report),
    ]
    return _section("run_contract", checks)


def _workflow_outputs_section(
    root: Path,
    run_manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    artifacts = run_manifest.get("artifacts") if run_manifest else None
    if not isinstance(artifacts, dict):
        return _section(
            "workflow_outputs",
            [
                _check(
                    "artifacts_declared",
                    FAILED,
                    "run_manifest.json declares workflow artifacts",
                )
            ],
        )

    checks: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for name, ref in artifacts.items():
        if not isinstance(ref, str) or not ref:
            checks.append(_check(f"artifact_{name}_declared", FAILED, f"{name} artifact is declared"))
            continue

        normalized_ref = _display_ref(ref)
        if normalized_ref in seen_paths:
            continue
        seen_paths.add(normalized_ref)
        checks.append(_artifact_check(root, name, ref))

    return _section("workflow_outputs", checks)


def _file_check(path: Path, check_id: str, message: str) -> dict[str, Any]:
    return _check(check_id, PASSED if path.is_file() else FAILED, message)


def _trace_steps_check(trace: dict[str, Any] | None) -> dict[str, Any]:
    steps = trace.get("steps") if trace else None
    status = PASSED if isinstance(steps, list) and len(steps) > 0 else FAILED
    return _check(
        "trace_steps_non_empty",
        status,
        "trace.json contains at least one workflow step",
        {"count": len(steps) if isinstance(steps, list) else 0},
    )


def _quality_report_check(quality_report: dict[str, Any] | None) -> dict[str, Any]:
    failed_count = 0
    if quality_report:
        checks = quality_report.get("checks")
        if isinstance(checks, list):
            failed_count = sum(1 for check in checks if check.get("status") == "fail")
    status = PASSED if quality_report and quality_report.get("status") == "pass" and failed_count == 0 else FAILED
    return _check(
        "quality_report_passed",
        status,
        "quality_report.json has no failed checks",
        {"failed_checks": failed_count},
    )


def _artifact_check(root: Path, name: str, ref: str) -> dict[str, Any]:
    artifact_path = root / ref.rstrip("/")
    exists = artifact_path.is_dir() if ref.endswith("/") else artifact_path.exists()
    return _check(
        f"artifact_{name}_exists",
        PASSED if exists else FAILED,
        f"{_display_ref(ref)} exists",
        {"path": _display_ref(ref)},
    )


def _section(name: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "name": name,
        "status": _status_from_checks(checks),
        "checks": checks,
    }


def _check(
    check_id: str,
    status: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    check: dict[str, Any] = {"id": check_id, "status": status, "message": message}
    if details is not None:
        check["details"] = details
    return check


def _summarize_sections(sections: list[dict[str, Any]]) -> dict[str, int]:
    checks = [check for section in sections for check in section["checks"]]
    failed = sum(1 for check in checks if check["status"] == FAILED)
    warnings = sum(1 for check in checks if check["status"] == WARNING)
    passed = sum(1 for check in checks if check["status"] == PASSED)
    return {
        "total_checks": len(checks),
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
    }


def _status_from_summary(summary: dict[str, int]) -> str:
    if summary["failed"] > 0:
        return FAILED
    if summary["warnings"] > 0:
        return WARNING
    return PASSED


def _status_from_checks(checks: list[dict[str, Any]]) -> str:
    if any(check["status"] == FAILED for check in checks):
        return FAILED
    if any(check["status"] == WARNING for check in checks):
        return WARNING
    return PASSED


def _run_id(root: Path, run_manifest: dict[str, Any] | None) -> str:
    if run_manifest and run_manifest.get("run_id"):
        return str(run_manifest["run_id"])
    return root.name


def _load_json_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _display_ref(value: str | Path) -> str:
    return str(value).replace("\\", "/")
