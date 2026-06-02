from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from agentflow.memory.production_asset_feedback import (
    build_asset_feedback_event,
    load_asset_feedback_fixture,
    write_asset_feedback_event,
)


def production_memory_loop_record_asset_feedback_command(
    asset_profiles_path: Path = typer.Option(
        ...,
        "--asset-profiles",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to asset_profiles.json from an asset test package.",
    ),
    asset_profile_readiness_path: Path = typer.Option(
        ...,
        "--asset-profile-readiness",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to asset_profile_readiness.json from an asset test package.",
    ),
    feedback_json_path: Path = typer.Option(
        ...,
        "--feedback-json",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to sanitized asset feedback JSON fixture.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/asset_feedback_intake"),
        "--output",
        "-o",
        help="Directory for no-provider asset feedback event artifacts.",
        show_default=False,
    ),
    generated_at: str = typer.Option(
        "2026-06-02T00:00:00+08:00",
        "--generated-at",
        help="ISO timestamp for the asset feedback event.",
    ),
) -> None:
    """Record tester asset feedback as structured evidence without promotion side effects."""
    try:
        asset_profiles = _load_json_object(asset_profiles_path, "asset profiles")
        asset_profile_readiness = _load_json_object(asset_profile_readiness_path, "asset profile readiness")
        fixture = load_asset_feedback_fixture(feedback_json_path)
        event = build_asset_feedback_event(
            asset_profiles=asset_profiles,
            asset_profile_readiness=asset_profile_readiness,
            feedback_fixture=fixture,
            generated_at=generated_at,
        )
        written_paths = write_asset_feedback_event(event, output_dir)
    except ValueError as exc:
        typer.echo(f"Asset feedback intake failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Asset feedback event: {event['parse_status']}")
    typer.echo("Feedback is memory: false")
    typer.echo("Creates promotion decision: false")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    for path in written_paths:
        typer.echo(f"Wrote: {str(path).replace(chr(92), '/')}")


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


__all__ = ("production_memory_loop_record_asset_feedback_command",)
