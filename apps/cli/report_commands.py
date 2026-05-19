from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from narratocut.harness import inspect_run, review_run, write_review_report
from narratocut.package_sop import PACKAGE_REPORT, write_package_report


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


def package_report_output(run_dir: Path, report_name: str = PACKAGE_REPORT) -> tuple[Path, list[str]]:
    report_path = write_package_report(run_dir, report_name)
    return report_path, [
        f"Package report: {_display_ref(report_path)}",
    ]


def package_report_command(
    run_dir: Path = typer.Option(
        ...,
        "--run-dir",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Workflow run directory to summarize.",
    ),
    report_name: str = typer.Option(
        PACKAGE_REPORT,
        "--report-name",
        help="Markdown report filename to write inside the run directory.",
    ),
) -> None:
    """Write or refresh package_report.md for a workflow run."""
    _, lines = package_report_output(run_dir, report_name)
    for line in lines:
        typer.echo(line)


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")
