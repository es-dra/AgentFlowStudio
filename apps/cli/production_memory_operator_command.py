from __future__ import annotations

import json
from pathlib import Path

import typer

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_feedback_candidate_overlay import (
    load_operator_feedback_candidate_promotion_decision,
)
from agentflow.memory.production_operator_feedback_candidate_promotion import (
    load_operator_feedback_candidate_packet,
)
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


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
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/operator_loop"),
        "--output",
        "-o",
        help="Directory for the full no-provider operator loop artifact chain.",
    ),
) -> None:
    """Run the generic production-memory operator loop without provider access."""
    try:
        loop = load_production_memory_loop(loop_path)
        next_pass_result = _load_json_object(next_pass_result_path, "next pass result") if next_pass_result_path else None
        next_pass_promotion_decision = (
            _load_json_object(next_pass_promotion_decision_path, "next pass promotion decision")
            if next_pass_promotion_decision_path
            else None
        )
        operator_feedback_candidate_packet = (
            load_operator_feedback_candidate_packet(operator_feedback_candidate_packet_path)
            if operator_feedback_candidate_packet_path
            else None
        )
        operator_feedback_candidate_promotion_decision = (
            load_operator_feedback_candidate_promotion_decision(operator_feedback_candidate_promotion_decision_path)
            if operator_feedback_candidate_promotion_decision_path
            else None
        )
        result = build_production_memory_operator_loop_run(
            loop,
            generated_at=generated_at,
            source_kb_status=source_kb_status,
            draft_next_pass_result=draft_next_pass_result,
            next_pass_result=next_pass_result,
            next_pass_promotion_decision=next_pass_promotion_decision,
            operator_feedback_candidate_packet=operator_feedback_candidate_packet,
            operator_feedback_candidate_promotion_decision=operator_feedback_candidate_promotion_decision,
        )
        written_paths = write_production_memory_operator_loop_run(result, output_dir)
    except ValueError as exc:
        typer.echo(f"Production memory operator loop failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    manifest = result["manifest"]
    typer.echo(f"Production memory operator loop: {manifest['chain_status']}")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    typer.echo(f"Included refs: {manifest['context_summary']['included_ref_count']}")
    typer.echo(f"Blocked refs: {manifest['context_summary']['blocked_ref_count']}")
    if "next_pass_result" in manifest:
        typer.echo(f"Next pass result scaffold: {manifest['next_pass_result']['result_status']}")
    if "next_pass_review" in manifest:
        typer.echo(f"Next pass review: {manifest['next_pass_review']['review_status']}")
    if "next_pass_promotion" in manifest:
        typer.echo(f"Next pass promotion: {manifest['next_pass_promotion']['decision_effect']}")
    if "operator_feedback_candidate_promotion" in manifest:
        typer.echo(
            "Operator feedback candidate promotion: "
            f"{manifest['operator_feedback_candidate_promotion']['decision_effect']}"
        )
    typer.echo(f"Company KB candidates: {manifest['company_kb_feedback']['promotion_status']}")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")

    if manifest["chain_status"] != "ready":
        raise typer.Exit(code=1)


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


def _load_json_object(path: Path, label: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


__all__ = ("production_memory_loop_run_operator_no_provider_command",)
