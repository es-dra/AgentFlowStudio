from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_asset_profile_promotion import (
    build_asset_profile_promotion_review,
    load_asset_profile_update_candidate,
    load_asset_profiles,
    write_asset_profile_promotion_review,
)


def production_memory_loop_review_asset_profile_update_candidate_command(
    asset_profiles_path: Path = typer.Option(
        ...,
        "--asset-profiles",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to asset_profiles.json from the asset test package.",
    ),
    update_candidate_path: Path = typer.Option(
        ...,
        "--asset-profile-update-candidate",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to agentflow_production_memory_asset_profile_update_candidate JSON.",
    ),
    decision: str = typer.Option(
        ...,
        "--decision",
        help="Reviewed decision: promoted, merged, rejected, expired, or blocked.",
    ),
    rationale: str = typer.Option(..., "--rationale", help="Operator rationale for the profile decision."),
    reviewer_role: str = typer.Option("operator", "--reviewer-role", help="Reviewer role label."),
    decided_at: str = typer.Option(..., "--decided-at", help="ISO timestamp for the explicit decision."),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/asset_profile_promotion"),
        "--output",
        "-o",
        help="Directory for asset profile promotion decision and version artifacts.",
    ),
) -> None:
    """Review a structured asset profile update candidate and optionally apply a local profile version."""
    try:
        asset_profiles = load_asset_profiles(asset_profiles_path)
        candidate = load_asset_profile_update_candidate(update_candidate_path)
        decision_payload, version = build_asset_profile_promotion_review(
            asset_profiles=asset_profiles,
            update_candidate=candidate,
            decision=decision,
            rationale=rationale,
            reviewer_role=reviewer_role,
            decided_at=decided_at,
        )
        written_paths = write_asset_profile_promotion_review(decision_payload, version, output_dir)
    except ValueError as exc:
        typer.echo(f"Asset profile promotion review failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Asset profile promotion decision: {decision_payload['decision']}")
    typer.echo(f"Profile version: {'applied' if version is not None else 'not applied'}")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    for path in written_paths:
        typer.echo(f"Wrote: {str(path).replace(chr(92), '/')}")


__all__ = ("production_memory_loop_review_asset_profile_update_candidate_command",)
