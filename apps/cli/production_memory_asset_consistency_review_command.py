from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_asset_consistency_review import (
    build_asset_consistency_review,
    load_asset_consistency_review_fixture,
    load_asset_profile_context_projection,
    write_asset_consistency_review,
)


def asset_consistency_review_command(
    asset_profile_context_projection_path: Path = typer.Option(
        ...,
        "--projection",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to context projection JSON.",
    ),
    consistency_review_json_path: Path = typer.Option(
        ...,
        "--review-json",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to sanitized review fixture JSON.",
    ),
    reviewed_at: str = typer.Option(..., "--reviewed-at", help="ISO timestamp for this review."),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/asset_consistency_review"),
        "--output",
        "-o",
        help="Directory for no-provider asset consistency review artifacts.",
        show_default=False,
    ),
) -> None:
    """Review asset consistency observations against projected profile context."""
    _run_asset_consistency_review(
        asset_profile_context_projection_path=asset_profile_context_projection_path,
        consistency_review_json_path=consistency_review_json_path,
        reviewed_at=reviewed_at,
        output_dir=output_dir,
    )


def production_memory_loop_review_asset_consistency_command(
    asset_profile_context_projection_path: Path = typer.Option(
        ...,
        "--asset-profile-context-projection",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to asset_profile_context_projection.json.",
        hidden=True,
    ),
    consistency_review_json_path: Path = typer.Option(
        ...,
        "--consistency-review-json",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to sanitized asset consistency review fixture JSON.",
    ),
    reviewed_at: str = typer.Option(..., "--reviewed-at", help="ISO timestamp for this review."),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/asset_consistency_review"),
        "--output",
        "-o",
        help="Directory for no-provider asset consistency review artifacts.",
        show_default=False,
    ),
) -> None:
    """Review asset consistency observations against projected profile context."""
    _run_asset_consistency_review(
        asset_profile_context_projection_path=asset_profile_context_projection_path,
        consistency_review_json_path=consistency_review_json_path,
        reviewed_at=reviewed_at,
        output_dir=output_dir,
    )


def _run_asset_consistency_review(
    *,
    asset_profile_context_projection_path: Path,
    consistency_review_json_path: Path,
    reviewed_at: str,
    output_dir: Path,
) -> None:
    try:
        projection = load_asset_profile_context_projection(asset_profile_context_projection_path)
        fixture = load_asset_consistency_review_fixture(consistency_review_json_path)
        review = build_asset_consistency_review(
            asset_profile_context_projection=projection,
            consistency_fixture=fixture,
            reviewed_at=reviewed_at,
        )
        written_paths = write_asset_consistency_review(review, output_dir)
    except ValueError as exc:
        typer.echo(f"Asset consistency review failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Asset consistency review: {review['review_status']}")
    typer.echo("Provider calls: not started")
    typer.echo("Creates asset feedback: false")
    typer.echo("Creates profile update candidate: false")
    typer.echo("Creates promotion decision: false")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    typer.echo(f"Findings: {len(review['consistency_findings'])}")
    typer.echo(f"Blocked findings: {len(review['blocked_findings'])}")
    for path in written_paths:
        typer.echo(f"Wrote: {str(path).replace(chr(92), '/')}")

    if review["review_status"] != "ready_for_operator_review":
        raise typer.Exit(code=1)


__all__ = (
    "asset_consistency_review_command",
    "production_memory_loop_review_asset_consistency_command",
)
