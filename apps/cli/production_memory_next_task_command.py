from __future__ import annotations

import json
from pathlib import Path

import typer

from agentflow.memory.production_next_task import build_next_task_packet, write_next_task_packet


def production_memory_loop_next_task_packet_command(
    handoff_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to next_context_handoff JSON.",
    ),
    generated_at: str = typer.Option(..., "--generated-at", help="ISO timestamp for the next task packet."),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/next_task_packet"),
        "--output",
        "-o",
        help="Directory for next task packet artifacts.",
    ),
) -> None:
    """Write a no-provider next-task packet from a next-context handoff."""
    try:
        handoff = _load_handoff(handoff_path)
        packet = build_next_task_packet(handoff, generated_at=generated_at)
        written_paths = write_next_task_packet(packet, output_dir)
    except ValueError as exc:
        typer.echo(f"Production memory next task packet failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Production memory next task packet: {packet['packet_status']}")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    typer.echo(f"Allowed refs: {len(packet['allowed_context_refs'])}")
    typer.echo(f"Blocked refs: {len(packet['blocked_refs'])}")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")

    if packet["packet_status"] != "ready":
        raise typer.Exit(code=1)


def _load_handoff(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("next context handoff must be a JSON object")
    return payload


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


__all__ = ("production_memory_loop_next_task_packet_command",)
