from __future__ import annotations

from pathlib import Path
from typing import Any

from narratocut.harness import inspect_run, review_run, write_review_report


def inspect_run_output(run_dir: Path) -> tuple[dict[str, Any], list[str]]:
    inspection = inspect_run(run_dir)
    quality = inspection["quality_report"]
    passed = sum(1 for check in quality["checks"] if check["status"] == "pass")
    failed = sum(1 for check in quality["checks"] if check["status"] == "fail")
    warnings = len(quality["warnings"])

    lines = [
        f"Run: {inspection['run_id']}",
        f"Workflow: {inspection['workflow']}",
        f"Status: {inspection['status']}",
        "",
        "Artifacts:",
    ]
    for artifact in inspection["artifacts"]:
        lines.append(f"  {artifact['path']:<24} {artifact['status']}")
    lines.extend(
        [
            "",
            "Quality:",
            f"  {passed} passed",
            f"  {failed} failed",
            f"  {warnings} warnings",
        ]
    )
    return inspection, lines


def review_run_output(run_dir: Path) -> tuple[dict[str, Any], list[str]]:
    report = review_run(run_dir)
    report_path = write_review_report(run_dir, report)
    summary = report["summary"]
    return report, [
        f"Review report: {_display_ref(report_path)}",
        f"Status: {report['status']}",
        "Checks: "
        f"{summary['passed']} passed / "
        f"{summary['failed']} failed / "
        f"{summary['warnings']} warnings",
    ]


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")
