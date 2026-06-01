from __future__ import annotations

import json
from pathlib import Path

import typer

from agentflow.memory.production_next_pass_review import build_next_pass_review, write_next_pass_review


def production_memory_loop_review_next_pass_command(
    packet_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to next_task_packet JSON.",
    ),
    result_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to next-pass result JSON.",
    ),
    reviewed_at: str = typer.Option(..., "--reviewed-at", help="ISO timestamp for this review."),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/next_pass_review"),
        "--output",
        "-o",
        help="Directory for next-pass review artifacts.",
    ),
) -> None:
    """Review a supplied next-pass result against a no-provider task packet."""
    try:
        packet = _load_json_object(packet_path, "next task packet")
        result = _load_json_object(result_path, "next pass result")
        review = build_next_pass_review(packet, result, reviewed_at=reviewed_at)
        written_paths = write_next_pass_review(review, output_dir)
    except ValueError as exc:
        typer.echo(f"Production memory next pass review failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Production memory next pass review: {review['review_status']}")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    typer.echo(f"Used allowed refs: {len(review['used_allowed_refs'])}")
    typer.echo(f"Blocked or unknown refs: {len(review['blocked_or_unknown_refs'])}")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")

    if review["review_status"] != "ready_for_operator_review":
        raise typer.Exit(code=1)


def _load_json_object(path: Path, label: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


__all__ = ("production_memory_loop_review_next_pass_command",)
