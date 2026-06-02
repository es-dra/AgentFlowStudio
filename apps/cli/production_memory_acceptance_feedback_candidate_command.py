from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_acceptance_feedback_candidate import (
    build_acceptance_feedback_candidate_packet,
    load_acceptance_feedback_event,
    write_acceptance_feedback_candidate_packet,
)


def production_memory_loop_draft_acceptance_feedback_candidate_command(
    event_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to production-memory acceptance feedback event JSON.",
    ),
    generated_at: str = typer.Option(..., "--generated-at", help="ISO timestamp for the candidate packet."),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/acceptance_feedback_candidate"),
        "--output",
        "-o",
        help="Directory for candidate-only acceptance feedback artifacts.",
    ),
) -> None:
    """Draft a candidate-only memory packet from human acceptance feedback evidence."""
    try:
        event = load_acceptance_feedback_event(event_path)
        packet = build_acceptance_feedback_candidate_packet(event, generated_at=generated_at)
        written_paths = write_acceptance_feedback_candidate_packet(packet, output_dir)
    except ValueError as exc:
        typer.echo(f"Production memory acceptance feedback candidate failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Production memory acceptance feedback candidate: {packet['candidate_generation_status']}")
    typer.echo(f"Source human acceptance: {packet['source_acceptance_decision']}")
    typer.echo("Business validation: not validated")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    typer.echo(f"Promotion decision: {packet['promotion_decision_template']['decision']}")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


__all__ = ("production_memory_loop_draft_acceptance_feedback_candidate_command",)
