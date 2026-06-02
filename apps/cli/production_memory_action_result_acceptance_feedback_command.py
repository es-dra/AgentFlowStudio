from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_action_result_acceptance_feedback import (
    build_production_memory_action_result_acceptance_feedback_event_from_path,
    write_production_memory_acceptance_feedback_event,
)


def production_memory_loop_record_action_result_acceptance_feedback_command(
    action_result_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to next_operator_action_result.json.",
    ),
    decision: str = typer.Option(..., "--decision", help="Human decision: accepted, rejected, or needs_revision."),
    summary: str = typer.Option(..., "--summary", help="Bounded human acceptance feedback summary."),
    reviewer_role: str = typer.Option("operator", "--reviewer-role", help="Reviewer role label."),
    reviewed_at: str = typer.Option(..., "--reviewed-at", help="ISO timestamp for the human feedback event."),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/action_result_acceptance_feedback"),
        "--output",
        "-o",
        help="Directory for no-provider action-result acceptance feedback artifacts.",
    ),
) -> None:
    """Record human acceptance feedback for a next-operator action result."""
    try:
        event = build_production_memory_action_result_acceptance_feedback_event_from_path(
            action_result_path,
            decision=decision,
            summary=summary,
            reviewer_role=reviewer_role,
            reviewed_at=reviewed_at,
        )
        written_paths = write_production_memory_acceptance_feedback_event(event, output_dir)
    except ValueError as exc:
        typer.echo(f"Action-result acceptance feedback failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Production memory action-result acceptance feedback: {event['acceptance_decision']}")
    typer.echo(f"Source action result: {event['source_action_result_status']}")
    typer.echo("Business validation: not validated")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


__all__ = ("production_memory_loop_record_action_result_acceptance_feedback_command",)
