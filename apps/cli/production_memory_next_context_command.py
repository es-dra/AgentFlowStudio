from __future__ import annotations

import json
from pathlib import Path

import typer

from agentflow.memory.production_next_context import (
    build_next_context_handoff,
    write_next_context_handoff,
)


def production_memory_loop_next_context_handoff_command(
    run_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to production_memory_loop_run JSON.",
    ),
    generated_at: str = typer.Option(..., "--generated-at", help="ISO timestamp for the handoff."),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/next_context_handoff"),
        "--output",
        "-o",
        help="Directory for next context handoff artifacts.",
    ),
) -> None:
    """Write a no-provider next-context handoff for the next AI task."""
    try:
        run = _load_run(run_path)
        handoff = build_next_context_handoff(run, generated_at=generated_at)
        written_paths = write_next_context_handoff(handoff, output_dir)
    except ValueError as exc:
        typer.echo(f"Production memory next context handoff failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Production memory next context handoff: {handoff['handoff_status']}")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    typer.echo(f"Included refs: {len(handoff['next_context_refs'])}")
    typer.echo(f"Blocked refs: {len(handoff['blocked_refs'])}")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")

    if handoff["handoff_status"] != "ready":
        raise typer.Exit(code=1)


def _load_run(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("production memory run must be a JSON object")
    return payload


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


__all__ = ("production_memory_loop_next_context_handoff_command",)
