from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_loop import (
    build_production_memory_loop_run,
    load_production_memory_loop,
    validate_production_memory_loop,
    write_production_memory_loop_run,
)
from agentflow.memory.production_feedback import (
    build_production_memory_feedback_capture,
    write_production_memory_feedback_capture,
)
from agentflow.memory.production_promotion import (
    build_production_memory_promotion_decision,
    build_reviewed_feedback_run,
    load_production_memory_feedback_capture,
    load_production_memory_promotion_decision,
    write_production_memory_promotion_decision,
    write_reviewed_feedback_run,
)


def production_memory_loop_validate_command(
    loop_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to production-memory loop JSON.",
    ),
) -> None:
    """Validate a generic production-memory loop contract without execution."""
    payload = load_production_memory_loop(loop_path)
    validation = validate_production_memory_loop(payload)

    typer.echo(f"Production memory loop validation: {validation['overall_status']}")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    _echo_failed_checks(validation)

    if validation["overall_status"] != "passed":
        raise typer.Exit(code=1)


def production_memory_loop_run_no_provider_command(
    loop_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to production-memory loop JSON.",
        show_default=False,
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/no_provider"),
        "--output",
        "-o",
        help="Directory for no-provider run artifacts.",
        show_default=False,
    ),
) -> None:
    """Build context bundle and readiness artifacts without provider access."""
    payload = load_production_memory_loop(loop_path)
    run = build_production_memory_loop_run(payload)
    written_paths = write_production_memory_loop_run(run, output_dir)
    readiness = run["pass_readiness"]

    typer.echo(f"Production memory loop no-provider run: {'ready' if readiness['ready'] else 'blocked'}")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo(f"Included refs: {len(run['context_bundle']['included_refs'])}")
    typer.echo(f"Blocked refs: {len(run['context_bundle']['blocked_refs'])}")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")
    _echo_failed_checks(run["validation"])
    _echo_failed_checks(readiness)

    if not readiness["ready"]:
        raise typer.Exit(code=1)


def production_memory_loop_draft_feedback_command(
    loop_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to production-memory loop JSON.",
    ),
    target_ref: str = typer.Option(..., "--target-ref", help="Artifact ledger ref receiving feedback."),
    decision: str = typer.Option("note", "--decision", help="Feedback decision: accepted, rejected, needs_revision, or note."),
    summary: str = typer.Option(..., "--summary", help="Bounded operator feedback summary."),
    reviewer_role: str = typer.Option("operator", "--reviewer-role", help="Reviewer role label."),
    created_at: str = typer.Option(..., "--created-at", help="ISO timestamp for the draft feedback packet."),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/feedback_capture"),
        "--output",
        "-o",
        help="Directory for no-provider feedback capture draft artifacts.",
    ),
) -> None:
    """Draft feedback, candidate memory, and a pending promotion decision template."""
    try:
        payload = load_production_memory_loop(loop_path)
        capture = build_production_memory_feedback_capture(
            payload,
            target_ref=target_ref,
            decision=decision,
            summary=summary,
            reviewer_role=reviewer_role,
            created_at=created_at,
        )
        written_paths = write_production_memory_feedback_capture(capture, output_dir)
    except ValueError as exc:
        typer.echo(f"Production memory feedback capture failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo("Production memory feedback capture: draft")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Promotion decision: pending")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")


def production_memory_loop_review_promotion_command(
    capture_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to production_memory_feedback_capture JSON.",
    ),
    decision: str = typer.Option(
        "promoted",
        "--decision",
        help="Reviewed decision: promoted, merged, rejected, expired, or blocked.",
    ),
    rationale: str = typer.Option(..., "--rationale", help="Operator rationale for the promotion decision."),
    reviewer_role: str = typer.Option("operator", "--reviewer-role", help="Reviewer role label."),
    decided_at: str = typer.Option(..., "--decided-at", help="ISO timestamp for the explicit decision."),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/promotion_decision"),
        "--output",
        "-o",
        help="Directory for reviewed promotion decision artifacts.",
    ),
) -> None:
    """Create an explicit promotion decision from a draft feedback capture."""
    try:
        capture = load_production_memory_feedback_capture(capture_path)
        promotion_decision = build_production_memory_promotion_decision(
            capture,
            decision=decision,
            rationale=rationale,
            reviewer_role=reviewer_role,
            decided_at=decided_at,
        )
        written_paths = write_production_memory_promotion_decision(promotion_decision, output_dir)
    except ValueError as exc:
        typer.echo(f"Production memory promotion decision failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Production memory promotion decision: {promotion_decision['decision']}")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")


def production_memory_loop_run_reviewed_feedback_no_provider_command(
    loop_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to agentflow_production_memory_loop JSON.",
    ),
    feedback_capture_path: Path = typer.Option(
        ...,
        "--feedback-capture",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to production_memory_feedback_capture JSON.",
    ),
    promotion_decision_path: Path = typer.Option(
        ...,
        "--promotion-decision",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to reviewed promotion decision JSON.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/reviewed_feedback"),
        "--output",
        "-o",
        help="Directory for reviewed feedback no-provider run artifacts.",
    ),
) -> None:
    """Overlay reviewed feedback and build a no-provider context bundle."""
    try:
        payload = load_production_memory_loop(loop_path)
        capture = load_production_memory_feedback_capture(feedback_capture_path)
        promotion_decision = load_production_memory_promotion_decision(promotion_decision_path)
        derived_loop, run = build_reviewed_feedback_run(payload, capture, promotion_decision)
        written_paths = write_reviewed_feedback_run(derived_loop, run, output_dir)
    except ValueError as exc:
        typer.echo(f"Production memory reviewed feedback run failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    readiness = run["pass_readiness"]
    typer.echo(f"Production memory reviewed feedback run: {'ready' if readiness['ready'] else 'blocked'}")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo(f"Included refs: {len(run['context_bundle']['included_refs'])}")
    typer.echo(f"Blocked refs: {len(run['context_bundle']['blocked_refs'])}")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")
    _echo_failed_checks(run["validation"])
    _echo_failed_checks(readiness)

    if not readiness["ready"]:
        raise typer.Exit(code=1)


def _echo_failed_checks(validation: dict) -> None:
    failed = [check for check in validation.get("checks", []) if check.get("status") == "failed"]
    if not failed:
        return
    typer.echo("Failed checks:")
    for check in failed:
        typer.echo(f"- {check.get('check_id')}: {check.get('message')}")


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


__all__ = (
    "production_memory_loop_draft_feedback_command",
    "production_memory_loop_review_promotion_command",
    "production_memory_loop_run_no_provider_command",
    "production_memory_loop_run_reviewed_feedback_no_provider_command",
    "production_memory_loop_validate_command",
)
