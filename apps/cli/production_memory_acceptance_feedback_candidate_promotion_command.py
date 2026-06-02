from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_acceptance_feedback_candidate_promotion import (
    build_acceptance_feedback_candidate_promotion_decision,
    load_acceptance_feedback_candidate_packet,
    write_acceptance_feedback_candidate_promotion_decision,
)


def production_memory_loop_review_acceptance_feedback_candidate_command(
    packet_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to acceptance_feedback_candidate_packet JSON.",
    ),
    decision: str = typer.Option(
        "promoted",
        "--decision",
        help="Reviewed decision: promoted, merged, rejected, expired, or blocked.",
    ),
    rationale: str = typer.Option(..., "--rationale", help="Operator rationale for the candidate decision."),
    reviewer_role: str = typer.Option("operator", "--reviewer-role", help="Reviewer role label."),
    decided_at: str = typer.Option(..., "--decided-at", help="ISO timestamp for the explicit decision."),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/acceptance_feedback_candidate_promotion"),
        "--output",
        "-o",
        help="Directory for acceptance feedback candidate decision artifacts.",
    ),
) -> None:
    """Create an explicit decision for an acceptance feedback memory candidate."""
    try:
        packet = load_acceptance_feedback_candidate_packet(packet_path)
        promotion_decision = build_acceptance_feedback_candidate_promotion_decision(
            packet,
            decision=decision,
            rationale=rationale,
            reviewer_role=reviewer_role,
            decided_at=decided_at,
        )
        written_paths = write_acceptance_feedback_candidate_promotion_decision(promotion_decision, output_dir)
    except ValueError as exc:
        typer.echo(f"Production memory acceptance feedback candidate decision failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    reuse = "allowed" if promotion_decision["candidate_reuse_allowed"] else "blocked"
    typer.echo(f"Production memory acceptance feedback candidate decision: {promotion_decision['decision']}")
    typer.echo(f"Candidate reuse: {reuse}")
    typer.echo(f"Source human acceptance: {promotion_decision['source_acceptance_decision']}")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


__all__ = ("production_memory_loop_review_acceptance_feedback_candidate_command",)
