from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_next_operator_action_result import (
    build_next_operator_action_result_from_start_event_path,
    write_next_operator_action_result_report,
)


def production_memory_loop_record_next_operator_action_result_command(
    start_event_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to next_operator_start_event.json.",
    ),
    decision: str = typer.Option(
        "completed",
        "--decision",
        help="Action result decision: completed, blocked, or deferred.",
    ),
    summary: str = typer.Option(..., "--summary", help="Bounded next-operator action result summary."),
    result_refs: list[str] = typer.Option(
        [],
        "--result-ref",
        help="Logical or package-local result ref produced by the recorded action. Repeatable.",
    ),
    operator_role: str = typer.Option("next_operator", "--operator-role", help="Operator role label."),
    recorded_at: str = typer.Option(..., "--recorded-at", help="ISO timestamp for the action result."),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/next_operator_action_result"),
        "--output",
        "-o",
        help="Directory for next_operator_action_result.json and .md.",
    ),
) -> None:
    """Record the outcome of the next operator's recorded no-provider action."""
    try:
        result = build_next_operator_action_result_from_start_event_path(
            start_event_path,
            decision=decision,
            summary=summary,
            result_refs=result_refs,
            operator_role=operator_role,
            recorded_at=recorded_at,
        )
        written_paths = write_next_operator_action_result_report(result, output_dir)
    except ValueError as exc:
        typer.echo(f"Next operator action result failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Next operator action result: {result['result_status']}")
    typer.echo(f"Action decision: {result['action_decision']}")
    typer.echo(f"Source start event: {result['source_start_event_status']}")
    typer.echo("Human acceptance: not claimed")
    typer.echo("Next-pass execution: not claimed")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


__all__ = ("production_memory_loop_record_next_operator_action_result_command",)
