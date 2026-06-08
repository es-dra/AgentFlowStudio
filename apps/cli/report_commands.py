from __future__ import annotations

from pathlib import Path

import typer

from agentflow_studio.package_sop import PACKAGE_REPORT
from apps.reporting.run_reports import (
    delivery_readiness_output,
    load_report_json,
    package_report_output,
)


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


def delivery_readiness_command(
    run_dirs: list[Path] = typer.Option(
        ...,
        "--run-dir",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Product workflow run directory to include. Repeat for multiple runs.",
    ),
    output_dir: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Directory to write delivery_readiness.json and delivery_readiness.md.",
    ),
) -> None:
    """Write a product delivery readiness summary for one or more runs."""
    paths, lines = delivery_readiness_output(run_dirs, output_dir)
    for line in lines:
        typer.echo(line)
    if load_report_json(paths["json_path"]).get("status") == "fail":
        raise typer.Exit(code=1)
