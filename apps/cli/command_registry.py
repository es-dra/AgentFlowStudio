from __future__ import annotations

from pathlib import Path

import typer

from apps.cli.auth_invite_commands import auth_invites_app
from apps.cli.media_commands import ffmpeg_check_command
from apps.cli.memory_review_command import memory_evidence_reuse_review_command
from apps.cli.production_memory_command_registry import register_production_memory_commands
from apps.cli.real_slicing_commands import slice_real_command
from apps.cli.runtime_backup_commands import runtime_backup_app
from apps.cli.runtime_service_command import runtime_service_command, runtime_service_openapi_export_command
from apps.reporting.run_reports import inspect_run_output, review_run_output


def register_commands(app: typer.Typer) -> None:
    register_product_commands(app)


def register_product_commands(app: typer.Typer) -> None:
    app.command(name="slice-real")(slice_real_command)
    app.command(name="ffmpeg-check")(ffmpeg_check_command)
    app.command(name="inspect-run")(inspect_run_command)
    app.command(name="review-run")(review_run_command)
    app.command(name="memory-evidence-reuse-review")(memory_evidence_reuse_review_command)
    register_production_memory_commands(app)
    app.command(name="runtime-service")(runtime_service_command)
    app.command(name="runtime-service-openapi-export")(runtime_service_openapi_export_command)
    app.add_typer(runtime_backup_app, name="runtime-backup")
    app.add_typer(auth_invites_app, name="auth-invites")


def inspect_run_command(
    run_dir: Path = typer.Option(
        ...,
        "--run-dir",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Workflow run directory to inspect.",
    ),
) -> None:
    """Inspect a workflow run directory and write quality_report.json."""
    inspection, lines = inspect_run_output(run_dir)
    for line in lines:
        typer.echo(line)
    if inspection["status"] != "pass":
        raise typer.Exit(code=1)


def review_run_command(
    run_dir: Path = typer.Option(
        ...,
        "--run-dir",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Workflow run directory to review.",
    ),
) -> None:
    """Write an agent-readable review_report.json for a workflow run."""
    report, lines = review_run_output(run_dir)
    for line in lines:
        typer.echo(line)
    if report["status"] == "failed":
        raise typer.Exit(code=1)
