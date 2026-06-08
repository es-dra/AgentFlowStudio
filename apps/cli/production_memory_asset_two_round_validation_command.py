from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_asset_two_round_validation import run_two_round_context_runtime_validation


def asset_two_round_validate_command(
    round_1_dir: Path = typer.Option(
        ...,
        "--round-1",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Round 1 deterministic asset loop output directory.",
    ),
    consistency_review_json_path: Path = typer.Option(
        Path("examples/agentflow/production_memory_asset_consistency_review.example.json"),
        "--consistency-review-json",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to sanitized Round 2 asset consistency review fixture.",
        show_default=False,
    ),
    generated_at: str = typer.Option(
        "2026-06-04T01:00:00+08:00",
        "--generated-at",
        help="ISO timestamp for Round 2 context projection.",
    ),
    reviewed_at: str = typer.Option(
        "2026-06-04T01:30:00+08:00",
        "--reviewed-at",
        help="ISO timestamp for Round 2 consistency review.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/local_internal_test/asset_loop_round_2"),
        "--output",
        "-o",
        help="Ignored runtime directory for Round 2 context runtime validation.",
        show_default=False,
    ),
) -> None:
    """Validate two-round context reuse from a deterministic asset loop package."""
    try:
        report = run_two_round_context_runtime_validation(
            round_1_dir=round_1_dir,
            output_dir=output_dir,
            consistency_review_json_path=consistency_review_json_path,
            generated_at=generated_at,
            reviewed_at=reviewed_at,
        )
    except ValueError as exc:
        typer.echo(f"Two-round context runtime validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Two-round context runtime validation: {report['runtime_verification_status']}")
    typer.echo(f"Improvement assessment: {report['improvement_assessment']}")
    typer.echo("Business validation: not claimed")
    typer.echo("Human acceptance: not claimed")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    typer.echo(f"Wrote: {str(output_dir / 'two_round_context_runtime_report.md').replace(chr(92), '/')}")


__all__ = ("asset_two_round_validate_command",)
