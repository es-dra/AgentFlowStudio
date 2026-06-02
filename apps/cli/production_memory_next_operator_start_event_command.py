from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_next_operator_start_event import (
    build_next_operator_start_event_from_packet_path,
    write_next_operator_start_event_report,
)


def production_memory_loop_record_next_operator_start_command(
    packet_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to next_operator_start_packet.json.",
    ),
    decision: str = typer.Option(
        "started",
        "--decision",
        help="Start decision: started, blocked, or deferred.",
    ),
    summary: str = typer.Option(..., "--summary", help="Bounded next-operator start summary."),
    operator_role: str = typer.Option("next_operator", "--operator-role", help="Operator role label."),
    recorded_at: str = typer.Option(..., "--recorded-at", help="ISO timestamp for the start event."),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/next_operator_start_event"),
        "--output",
        "-o",
        help="Directory for next_operator_start_event.json and .md.",
    ),
) -> None:
    """Record whether the next operator started from a checked start packet."""
    try:
        event = build_next_operator_start_event_from_packet_path(
            packet_path,
            decision=decision,
            summary=summary,
            operator_role=operator_role,
            recorded_at=recorded_at,
        )
        written_paths = write_next_operator_start_event_report(event, output_dir)
    except ValueError as exc:
        typer.echo(f"Next operator start event failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Next operator start event: {event['event_status']}")
    typer.echo(f"Start decision: {event['start_decision']}")
    typer.echo(f"Source start packet: {event['source_start_packet_status']}")
    typer.echo("Human acceptance: not claimed")
    typer.echo("Next-pass execution: not claimed")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


__all__ = ("production_memory_loop_record_next_operator_start_command",)
