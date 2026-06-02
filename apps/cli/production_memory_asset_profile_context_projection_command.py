from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_asset_profile_context_projection import (
    build_asset_profile_context_projection,
    load_asset_profile_version,
    write_asset_profile_context_projection,
)


def production_memory_loop_asset_profile_context_projection_command(
    asset_profile_version_paths: list[Path] = typer.Option(
        ...,
        "--asset-profile-version",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to asset profile version JSON. May be repeated.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/asset_profile_context_projection"),
        "--output",
        "-o",
        help="Directory for no-provider asset profile context projection artifacts.",
        show_default=False,
    ),
    generated_at: str = typer.Option(
        "2026-06-03T00:00:00+08:00",
        "--generated-at",
        help="ISO timestamp for the asset profile context projection.",
    ),
) -> None:
    """Project promoted asset profile versions into the next no-provider context."""
    try:
        versions = [load_asset_profile_version(path) for path in asset_profile_version_paths]
        projection = build_asset_profile_context_projection(
            asset_profile_versions=versions,
            generated_at=generated_at,
        )
        written_paths = write_asset_profile_context_projection(projection, output_dir)
    except ValueError as exc:
        typer.echo(f"Asset profile context projection failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Asset profile context projection: {projection['projection_status']}")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    typer.echo(f"Included refs: {len(projection['included_refs'])}")
    typer.echo(f"Blocked refs: {len(projection['blocked_refs'])}")
    for path in written_paths:
        typer.echo(f"Wrote: {str(path).replace(chr(92), '/')}")


__all__ = ("production_memory_loop_asset_profile_context_projection_command",)
