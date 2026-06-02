from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_acceptance_feedback import (
    build_production_memory_acceptance_feedback_event,
    load_operator_run_package_check,
    write_production_memory_acceptance_feedback_event,
)


def production_memory_loop_record_acceptance_feedback_command(
    package_check_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to operator_run_package_check.json.",
    ),
    decision: str = typer.Option(..., "--decision", help="Human decision: accepted, rejected, or needs_revision."),
    summary: str = typer.Option(..., "--summary", help="Bounded human acceptance feedback summary."),
    reviewer_role: str = typer.Option("operator", "--reviewer-role", help="Reviewer role label."),
    reviewed_at: str = typer.Option(..., "--reviewed-at", help="ISO timestamp for the human feedback event."),
    acceptance_scope: str = typer.Option(
        "operator_run_package",
        "--acceptance-scope",
        help="Human feedback scope label.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/acceptance_feedback"),
        "--output",
        "-o",
        help="Directory for no-provider human acceptance feedback artifacts.",
    ),
) -> None:
    """Record human-supplied acceptance feedback without memory or Company KB writes."""
    try:
        package_check = load_operator_run_package_check(package_check_path)
        event = build_production_memory_acceptance_feedback_event(
            package_check,
            decision=decision,
            summary=summary,
            reviewer_role=reviewer_role,
            reviewed_at=reviewed_at,
            acceptance_scope=acceptance_scope,
        )
        written_paths = write_production_memory_acceptance_feedback_event(event, output_dir)
    except ValueError as exc:
        typer.echo(f"Production memory acceptance feedback failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Production memory acceptance feedback: {event['acceptance_decision']}")
    typer.echo(f"Human acceptance: {event['claim_boundaries']['human_acceptance']}")
    typer.echo("Business validation: not validated")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    for path in written_paths:
        typer.echo(f"Wrote: {str(path).replace(chr(92), '/')}")


__all__ = ("production_memory_loop_record_acceptance_feedback_command",)
