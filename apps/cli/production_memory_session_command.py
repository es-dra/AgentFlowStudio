from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.company_kb_feedback import (
    build_company_kb_feedback_candidate_packet,
    load_company_kb_feedback_source_report,
    write_company_kb_feedback_candidate_packet,
)
from agentflow.memory.production_promotion import (
    load_production_memory_feedback_capture,
    load_production_memory_promotion_decision,
)
from agentflow.memory.production_session import (
    build_production_memory_session_report,
    load_production_memory_run,
    write_production_memory_session_report,
)


def production_memory_loop_session_report_command(
    run_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to production_memory_loop_run JSON.",
    ),
    feedback_capture_path: Path | None = typer.Option(
        None,
        "--feedback-capture",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Optional production memory feedback capture JSON.",
    ),
    promotion_decision_path: Path | None = typer.Option(
        None,
        "--promotion-decision",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Optional reviewed promotion decision JSON.",
    ),
    generated_at: str = typer.Option(..., "--generated-at", help="ISO timestamp for the session report."),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/session_report"),
        "--output",
        "-o",
        help="Directory for production-memory session report artifacts.",
    ),
) -> None:
    """Write a read-only operator session report from a production-memory run."""
    try:
        run = load_production_memory_run(run_path)
        feedback_capture = load_production_memory_feedback_capture(feedback_capture_path) if feedback_capture_path else None
        promotion_decision = (
            load_production_memory_promotion_decision(promotion_decision_path) if promotion_decision_path else None
        )
        report = build_production_memory_session_report(
            run,
            feedback_capture=feedback_capture,
            promotion_decision=promotion_decision,
            generated_at=generated_at,
        )
        written_paths = write_production_memory_session_report(report, output_dir)
    except ValueError as exc:
        typer.echo(f"Production memory session report failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Production memory session report: {report['session_status']}")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo(f"Included refs: {report['context_summary']['included_ref_count']}")
    typer.echo(f"Blocked refs: {report['context_summary']['blocked_ref_count']}")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")


def production_memory_loop_company_kb_candidates_command(
    report_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to production_memory_session_report JSON.",
    ),
    generated_at: str = typer.Option(..., "--generated-at", help="ISO timestamp for the candidate packet."),
    source_kb_status: str = typer.Option(
        "restructuring_or_unknown",
        "--source-kb-status",
        help="Current source Company KB state label; recorded as metadata only.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/company_kb_candidates"),
        "--output",
        "-o",
        help="Directory for candidate-only Company KB feedback artifacts.",
    ),
) -> None:
    """Write candidate-only Company KB feedback from a production-memory session report."""
    try:
        report = load_company_kb_feedback_source_report(report_path)
        packet = build_company_kb_feedback_candidate_packet(
            report,
            generated_at=generated_at,
            source_kb_status=source_kb_status,
        )
        written_paths = write_company_kb_feedback_candidate_packet(packet, output_dir)
    except ValueError as exc:
        typer.echo(f"Company KB feedback candidates failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Company KB feedback candidates: {packet['promotion_status']}")
    typer.echo("Writes Company KB: false")
    typer.echo("Writes long-term memory: false")
    typer.echo("Requires human review: true")
    typer.echo(f"Candidate items: {len(packet['candidate_items'])}")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


__all__ = (
    "production_memory_loop_company_kb_candidates_command",
    "production_memory_loop_session_report_command",
)
