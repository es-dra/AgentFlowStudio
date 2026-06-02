from __future__ import annotations

import json
from pathlib import Path

import typer

from agentflow.memory.production_next_pass_result import (
    build_next_pass_result_scaffold,
    write_next_pass_result_scaffold,
)


def production_memory_loop_draft_next_pass_result_no_provider_command(
    packet_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to next_task_packet JSON.",
    ),
    generated_at: str = typer.Option(..., "--generated-at", help="ISO timestamp for this result scaffold."),
    output_ref: str = typer.Option(
        "next-pass:artifact:scaffold-001",
        "--output-ref",
        help="Ref id for the scaffolded next-pass output artifact.",
    ),
    title: str = typer.Option(
        "Next pass operator scaffold",
        "--title",
        help="Title for the scaffolded next-pass output artifact.",
    ),
    summary: str = typer.Option(
        "No-provider scaffold for an operator-supplied next pass result.",
        "--summary",
        help="Bounded summary for the scaffolded next-pass output artifact.",
    ),
    used_context_refs: list[str] | None = typer.Option(
        None,
        "--used-context-ref",
        help="Allowed context ref used by this scaffold. Repeat to select a subset; omit to include all allowed refs.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/next_pass_result"),
        "--output",
        "-o",
        help="Directory for next-pass result scaffold artifacts.",
    ),
) -> None:
    """Draft a no-provider next-pass result envelope from a ready task packet."""
    try:
        packet = _load_json_object(packet_path, "next task packet")
        result = build_next_pass_result_scaffold(
            packet,
            generated_at=generated_at,
            output_ref=output_ref,
            title=title,
            summary=summary,
            used_context_refs=used_context_refs,
        )
        written_paths = write_next_pass_result_scaffold(result, output_dir)
    except ValueError as exc:
        typer.echo(f"Production memory next pass result scaffold failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Production memory next pass result scaffold: {result['result_status']}")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    typer.echo(f"Used context refs: {len(result['output_artifacts'][0]['used_context_refs'])}")
    typer.echo("Feedback events: 0")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")


def _load_json_object(path: Path, label: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


__all__ = ("production_memory_loop_draft_next_pass_result_no_provider_command",)
