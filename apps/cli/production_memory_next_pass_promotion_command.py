from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_next_pass_promotion import (
    build_next_pass_promotion_decision,
    build_next_pass_reviewed_feedback_run,
    load_next_pass_promotion_decision,
    load_next_pass_review,
    write_next_pass_promotion_decision,
    write_next_pass_reviewed_feedback_run,
)


def production_memory_loop_review_next_pass_promotion_command(
    review_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to next_pass_review JSON.",
    ),
    candidate_id: str = typer.Option(..., "--candidate-id", help="Next-pass feedback candidate id to review."),
    decision: str = typer.Option(
        "promoted",
        "--decision",
        help="Reviewed decision: promoted, merged, rejected, expired, or blocked.",
    ),
    rationale: str = typer.Option(..., "--rationale", help="Operator rationale for the next-pass promotion decision."),
    reviewer_role: str = typer.Option("operator", "--reviewer-role", help="Reviewer role label."),
    decided_at: str = typer.Option(..., "--decided-at", help="ISO timestamp for the explicit decision."),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/next_pass_promotion_decision"),
        "--output",
        "-o",
        help="Directory for next-pass promotion decision artifacts.",
    ),
) -> None:
    """Create an explicit decision for a next-pass feedback candidate."""
    try:
        review = load_next_pass_review(review_path)
        promotion_decision = build_next_pass_promotion_decision(
            review,
            candidate_id=candidate_id,
            decision=decision,
            rationale=rationale,
            reviewer_role=reviewer_role,
            decided_at=decided_at,
        )
        written_paths = write_next_pass_promotion_decision(promotion_decision, output_dir)
    except ValueError as exc:
        typer.echo(f"Production memory next pass promotion decision failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Production memory next pass promotion decision: {promotion_decision['decision']}")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")


def production_memory_loop_run_next_pass_reviewed_feedback_no_provider_command(
    loop_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to agentflow_production_memory_loop JSON.",
    ),
    review_path: Path = typer.Option(
        ...,
        "--next-pass-review",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to next_pass_review JSON.",
    ),
    promotion_decision_path: Path = typer.Option(
        ...,
        "--promotion-decision",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to reviewed next-pass promotion decision JSON.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/next_pass_reviewed_feedback"),
        "--output",
        "-o",
        help="Directory for next-pass reviewed feedback no-provider run artifacts.",
    ),
) -> None:
    """Overlay reviewed next-pass feedback and build a no-provider context bundle."""
    try:
        payload = load_production_memory_loop(loop_path)
        review = load_next_pass_review(review_path)
        promotion_decision = load_next_pass_promotion_decision(promotion_decision_path)
        derived_loop, run, overlay = build_next_pass_reviewed_feedback_run(payload, review, promotion_decision)
        written_paths = write_next_pass_reviewed_feedback_run(derived_loop, run, overlay, output_dir)
    except ValueError as exc:
        typer.echo(f"Production memory next pass reviewed feedback run failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    readiness = run["pass_readiness"]
    typer.echo(f"Production memory next pass reviewed feedback run: {'ready' if readiness['ready'] else 'blocked'}")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    typer.echo(f"Decision effect: {overlay['decision_effect']}")
    typer.echo(f"Included refs: {len(run['context_bundle']['included_refs'])}")
    typer.echo(f"Blocked refs: {len(run['context_bundle']['blocked_refs'])}")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")

    if not readiness["ready"]:
        raise typer.Exit(code=1)


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


__all__ = (
    "production_memory_loop_review_next_pass_promotion_command",
    "production_memory_loop_run_next_pass_reviewed_feedback_no_provider_command",
)
