from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_asset_test_run_harness import run_real_asset_test_harness


def asset_test_run_harness_command(
    loop_path: Path = typer.Option(
        Path("examples/agentflow/production_memory_loop.example.json"),
        "--loop",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to production-memory loop JSON.",
        show_default=False,
    ),
    asset_profile_seed_path: Path = typer.Option(
        ...,
        "--asset-profile-seed",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to asset profile seed JSON.",
    ),
    feedback_json_path: Path = typer.Option(
        Path("examples/agentflow/production_memory_asset_feedback.example.json"),
        "--feedback-json",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to sanitized asset feedback JSON fixture.",
        show_default=False,
    ),
    consistency_review_json_path: Path = typer.Option(
        Path("examples/agentflow/production_memory_asset_consistency_review.example.json"),
        "--consistency-review-json",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to sanitized asset consistency review JSON fixture.",
        show_default=False,
    ),
    project_materials_path: Path | None = typer.Option(
        None,
        "--project-materials",
        help="Explicit local ignored project materials path. The path is not persisted.",
    ),
    character_reference_image_path: Path | None = typer.Option(
        None,
        "--character-reference-image",
        help="Explicit local ignored character reference image path. The path is not persisted.",
    ),
    promotion_decision: str = typer.Option(
        ...,
        "--promotion-decision",
        help="Explicit operator decision: promoted, merged, rejected, expired, or blocked.",
    ),
    promotion_rationale: str = typer.Option(
        ...,
        "--promotion-rationale",
        help="Operator rationale for the explicit profile decision.",
    ),
    reviewer_role: str = typer.Option("operator", "--reviewer-role", help="Reviewer role label."),
    generated_at: str = typer.Option(
        "2026-06-04T00:00:00+08:00",
        "--generated-at",
        help="ISO timestamp for package, feedback, and candidate artifacts.",
    ),
    decided_at: str = typer.Option(
        ...,
        "--decided-at",
        help="ISO timestamp for the explicit promotion decision.",
    ),
    reviewed_at: str = typer.Option(
        ...,
        "--reviewed-at",
        help="ISO timestamp for the consistency review.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/local_internal_test/asset_loop_round_1"),
        "--output",
        "-o",
        help="Ignored runtime directory for the deterministic asset loop package.",
        show_default=False,
    ),
) -> None:
    """Run a local deterministic asset loop package for tester review."""
    try:
        report = run_real_asset_test_harness(
            loop_path=loop_path,
            asset_profile_seed_path=asset_profile_seed_path,
            feedback_json_path=feedback_json_path,
            consistency_review_json_path=consistency_review_json_path,
            output_dir=output_dir,
            promotion_decision=promotion_decision,
            promotion_rationale=promotion_rationale,
            generated_at=generated_at,
            decided_at=decided_at,
            reviewed_at=reviewed_at,
            project_materials_path=project_materials_path,
            character_reference_image_path=character_reference_image_path,
            reviewer_role=reviewer_role,
        )
    except ValueError as exc:
        typer.echo(f"Real asset test run harness failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Real asset test run harness: {report['run_status']}")
    typer.echo(f"Blocks: {len(report['blocks'])}")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    typer.echo(f"Wrote: {str(output_dir / 'real_asset_test_report.md').replace(chr(92), '/')}")
    typer.echo(f"Wrote: {str(output_dir / 'review_screen_selected_files.json').replace(chr(92), '/')}")


__all__ = ("asset_test_run_harness_command",)
