from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_operator_feedback import (
    build_production_memory_operator_feedback_event,
    load_production_memory_operator_manifest,
    write_production_memory_operator_feedback_event,
)


def production_memory_loop_capture_operator_feedback_command(
    manifest_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to production_memory_operator_loop_run JSON.",
    ),
    target_node_id: str = typer.Option(..., "--target-node", help="Operator-loop node receiving feedback."),
    decision: str = typer.Option("note", "--decision", help="Feedback decision: accepted, rejected, needs_revision, or note."),
    summary: str = typer.Option(..., "--summary", help="Bounded operator feedback summary."),
    reviewer_role: str = typer.Option("operator", "--reviewer-role", help="Reviewer role label."),
    reviewed_at: str = typer.Option(..., "--reviewed-at", help="ISO timestamp for the operator feedback event."),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/operator_feedback"),
        "--output",
        "-o",
        help="Directory for no-provider operator feedback artifacts.",
    ),
) -> None:
    """Capture operator feedback about one production-memory operator-loop node."""
    try:
        manifest = load_production_memory_operator_manifest(manifest_path)
        event = build_production_memory_operator_feedback_event(
            manifest,
            target_node_id=target_node_id,
            decision=decision,
            summary=summary,
            reviewer_role=reviewer_role,
            reviewed_at=reviewed_at,
        )
        written_paths = write_production_memory_operator_feedback_event(event, output_dir)
    except ValueError as exc:
        typer.echo(f"Production memory operator feedback failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Production memory operator feedback: {event['status']}")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    typer.echo("Human acceptance: not claimed")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


__all__ = ("production_memory_loop_capture_operator_feedback_command",)
