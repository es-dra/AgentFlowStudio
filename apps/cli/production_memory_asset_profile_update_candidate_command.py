from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_asset_profile_update_candidate import (
    build_asset_profile_update_candidate,
    load_asset_feedback_event,
    write_asset_profile_update_candidate,
)


def production_memory_loop_draft_asset_profile_update_candidate_command(
    asset_feedback_event_path: Path = typer.Option(
        ...,
        "--asset-feedback-event",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to asset feedback event JSON.",
    ),
    generated_at: str = typer.Option(
        "2026-06-02T00:10:00+08:00",
        "--generated-at",
        help="ISO timestamp for the asset profile update candidate.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/asset_profile_update_candidate"),
        "--output",
        "-o",
        help="Directory for no-provider asset profile update candidate artifacts.",
        show_default=False,
    ),
) -> None:
    """Draft a candidate-only structured profile patch from asset feedback evidence."""
    try:
        event = load_asset_feedback_event(asset_feedback_event_path)
        candidate = build_asset_profile_update_candidate(event, generated_at=generated_at)
        written_paths = write_asset_profile_update_candidate(candidate, output_dir)
    except ValueError as exc:
        typer.echo(f"Asset profile update candidate failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Asset profile update candidate: {candidate['candidate_generation_status']}")
    typer.echo("Provider calls: not started")
    typer.echo("Creates promotion decision: false")
    typer.echo("Applies profile version: false")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    for path in written_paths:
        typer.echo(f"Wrote: {str(path).replace(chr(92), '/')}")


__all__ = ("production_memory_loop_draft_asset_profile_update_candidate_command",)
