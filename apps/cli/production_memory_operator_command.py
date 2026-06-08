from __future__ import annotations

from pathlib import Path

import typer

from apps.cli.production_memory_operator_runner import run_production_memory_loop_operator_no_provider


def production_memory_loop_run_operator_no_provider_command(
    loop_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to agentflow_production_memory_loop JSON.",
    ),
    generated_at: str = typer.Option(..., "--generated-at", help="ISO timestamp for generated loop artifacts."),
    source_kb_status: str = typer.Option(
        "restructuring_or_unknown",
        "--source-kb-status",
        help="Current source Company KB state label; metadata only.",
    ),
    draft_next_pass_result: bool = typer.Option(
        False,
        "--draft-next-pass-result",
        help="Draft a no-provider next-pass result scaffold from the generated next-task packet.",
    ),
    next_pass_result_path: Path | None = typer.Option(
        None,
        "--next-pass-result",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Optional explicit next-pass result JSON to review in the operator loop.",
    ),
    next_pass_promotion_decision_path: Path | None = typer.Option(
        None,
        "--next-pass-promotion-decision",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Optional explicit next-pass promotion decision JSON to include in the operator loop.",
    ),
    operator_feedback_candidate_packet_path: Path | None = typer.Option(
        None,
        "--operator-feedback-candidate-packet",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Optional operator feedback candidate packet JSON to include in the operator loop.",
    ),
    operator_feedback_candidate_promotion_decision_path: Path | None = typer.Option(
        None,
        "--operator-feedback-candidate-promotion-decision",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Optional explicit operator feedback candidate promotion decision JSON.",
    ),
    acceptance_feedback_candidate_packet_path: Path | None = typer.Option(
        None,
        "--acceptance-feedback-candidate-packet",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Optional acceptance feedback candidate packet JSON to include in the operator loop.",
    ),
    acceptance_feedback_candidate_promotion_decision_path: Path | None = typer.Option(
        None,
        "--acceptance-feedback-candidate-promotion-decision",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Optional explicit acceptance feedback candidate promotion decision JSON.",
    ),
    write_manifest_check: bool = typer.Option(
        False,
        "--write-manifest-check",
        help="Write a read-only operator manifest consistency check report after generating artifacts.",
    ),
    write_handoff_packet: bool = typer.Option(
        False,
        "--write-handoff-packet",
        help="Write a no-provider operator handoff packet after the manifest check report.",
    ),
    write_run_package: bool = typer.Option(
        False,
        "--write-run-package",
        help="Write a final no-provider operator run package with manifest check and handoff packet.",
    ),
    write_run_package_check: bool = typer.Option(
        False,
        "--write-run-package-check",
        help="Write a read-only run package consistency check after the final operator run package.",
    ),
    write_next_operator_start_packet: bool = typer.Option(
        False,
        "--write-next-operator-start-packet",
        help="Write a post-check next-operator start packet after the final run package check.",
    ),
    write_next_operator_start_event: bool = typer.Option(
        False,
        "--write-next-operator-start-event",
        help="Write an explicit next-operator start event after the start packet.",
    ),
    next_operator_start_decision: str | None = typer.Option(
        None,
        "--next-operator-start-decision",
        help="Start event decision: started, blocked, or deferred. Required with --write-next-operator-start-event.",
    ),
    next_operator_start_summary: str | None = typer.Option(
        None,
        "--next-operator-start-summary",
        help="Bounded start event summary. Required with --write-next-operator-start-event.",
    ),
    next_operator_start_role: str = typer.Option(
        "next_operator",
        "--next-operator-start-role",
        help="Operator role label for the start event.",
    ),
    write_next_operator_action_result: bool = typer.Option(
        False,
        "--write-next-operator-action-result",
        help="Write an explicit next-operator action result after the start event.",
    ),
    next_operator_action_decision: str | None = typer.Option(
        None,
        "--next-operator-action-decision",
        help="Action result decision: completed, blocked, or deferred.",
    ),
    next_operator_action_summary: str | None = typer.Option(
        None,
        "--next-operator-action-summary",
        help="Bounded action result summary. Required with --write-next-operator-action-result.",
    ),
    next_operator_action_result_refs: list[str] | None = typer.Option(
        None,
        "--next-operator-action-result-ref",
        help="Repeatable explicit result ref for a completed next-operator action.",
    ),
    next_operator_action_role: str = typer.Option(
        "next_operator",
        "--next-operator-action-role",
        help="Operator role label for the action result.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/operator_loop"),
        "--output",
        "-o",
        help="Directory for the full no-provider operator loop artifact chain.",
    ),
) -> None:
    """Run the generic production-memory operator loop without provider access."""
    run_production_memory_loop_operator_no_provider(
        loop_path=loop_path,
        generated_at=generated_at,
        source_kb_status=source_kb_status,
        draft_next_pass_result=draft_next_pass_result,
        next_pass_result_path=next_pass_result_path,
        next_pass_promotion_decision_path=next_pass_promotion_decision_path,
        operator_feedback_candidate_packet_path=operator_feedback_candidate_packet_path,
        operator_feedback_candidate_promotion_decision_path=operator_feedback_candidate_promotion_decision_path,
        acceptance_feedback_candidate_packet_path=acceptance_feedback_candidate_packet_path,
        acceptance_feedback_candidate_promotion_decision_path=acceptance_feedback_candidate_promotion_decision_path,
        write_manifest_check=write_manifest_check,
        write_handoff_packet=write_handoff_packet,
        write_run_package=write_run_package,
        write_run_package_check=write_run_package_check,
        write_next_operator_start_packet=write_next_operator_start_packet,
        write_next_operator_start_event=write_next_operator_start_event,
        next_operator_start_decision=next_operator_start_decision,
        next_operator_start_summary=next_operator_start_summary,
        next_operator_start_role=next_operator_start_role,
        write_next_operator_action_result=write_next_operator_action_result,
        next_operator_action_decision=next_operator_action_decision,
        next_operator_action_summary=next_operator_action_summary,
        next_operator_action_result_refs=next_operator_action_result_refs,
        next_operator_action_role=next_operator_action_role,
        output_dir=output_dir,
    )


__all__ = ("production_memory_loop_run_operator_no_provider_command",)
