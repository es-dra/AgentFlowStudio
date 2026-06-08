from __future__ import annotations

import json
from pathlib import Path

import typer

from agentflow.memory.production_acceptance_feedback_candidate_overlay import (
    load_acceptance_feedback_candidate_promotion_decision,
)
from agentflow.memory.production_acceptance_feedback_candidate_promotion import (
    load_acceptance_feedback_candidate_packet,
)
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


def run_production_memory_loop_operator_no_provider(
    *,
    loop_path: Path,
    generated_at: str,
    source_kb_status: str,
    draft_next_pass_result: bool,
    next_pass_result_path: Path | None,
    next_pass_promotion_decision_path: Path | None,
    operator_feedback_candidate_packet_path: Path | None,
    operator_feedback_candidate_promotion_decision_path: Path | None,
    acceptance_feedback_candidate_packet_path: Path | None,
    acceptance_feedback_candidate_promotion_decision_path: Path | None,
    write_manifest_check: bool,
    write_handoff_packet: bool,
    write_run_package: bool,
    write_run_package_check: bool,
    write_next_operator_start_packet: bool,
    write_next_operator_start_event: bool,
    next_operator_start_decision: str | None,
    next_operator_start_summary: str | None,
    next_operator_start_role: str,
    write_next_operator_action_result: bool,
    next_operator_action_decision: str | None,
    next_operator_action_summary: str | None,
    next_operator_action_result_refs: list[str] | None,
    next_operator_action_role: str,
    output_dir: Path,
) -> None:
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
        acceptance_feedback_candidate_packet = (
            load_acceptance_feedback_candidate_packet(acceptance_feedback_candidate_packet_path)
            if acceptance_feedback_candidate_packet_path
            else None
        )
        acceptance_feedback_candidate_promotion_decision = (
            load_acceptance_feedback_candidate_promotion_decision(
                acceptance_feedback_candidate_promotion_decision_path
            )
            if acceptance_feedback_candidate_promotion_decision_path
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
            acceptance_feedback_candidate_packet=acceptance_feedback_candidate_packet,
            acceptance_feedback_candidate_promotion_decision=acceptance_feedback_candidate_promotion_decision,
        )
        written_paths = write_production_memory_operator_loop_run(
            result,
            output_dir,
            write_manifest_check=write_manifest_check,
            write_handoff_packet=write_handoff_packet,
            write_run_package=write_run_package,
            write_run_package_check=write_run_package_check,
            write_next_operator_start_packet=write_next_operator_start_packet,
            write_next_operator_start_event=write_next_operator_start_event,
            next_operator_start_event_decision=next_operator_start_decision,
            next_operator_start_event_summary=next_operator_start_summary,
            next_operator_start_event_operator_role=next_operator_start_role,
            write_next_operator_action_result=write_next_operator_action_result,
            next_operator_action_result_decision=next_operator_action_decision,
            next_operator_action_result_summary=next_operator_action_summary,
            next_operator_action_result_refs=next_operator_action_result_refs,
            next_operator_action_result_operator_role=next_operator_action_role,
        )
    except ValueError as exc:
        typer.echo(f"Production memory operator loop failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    _print_operator_loop_result(result, written_paths)

    manifest = result["manifest"]
    if manifest["chain_status"] != "ready":
        raise typer.Exit(code=1)
    if "operator_run_package" in result and result["operator_run_package"]["package_status"] != "ready":
        raise typer.Exit(code=1)
    if "operator_run_package_check" in result and result["operator_run_package_check"]["check_status"] != "passed":
        raise typer.Exit(code=1)
    if "next_operator_start_packet" in result and result["next_operator_start_packet"]["start_packet_status"] != "ready":
        raise typer.Exit(code=1)
    if "next_operator_start_event" in result and result["next_operator_start_event"]["provider_calls_started"] is not False:
        raise typer.Exit(code=1)
    if "next_operator_action_result" in result and result["next_operator_action_result"]["provider_calls_started"] is not False:
        raise typer.Exit(code=1)


def _print_operator_loop_result(result: dict, written_paths: list[Path]) -> None:
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
    if "acceptance_feedback_candidate_promotion" in manifest:
        typer.echo(
            "Acceptance feedback candidate promotion: "
            f"{manifest['acceptance_feedback_candidate_promotion']['decision_effect']}"
        )
    if "operator_manifest_check" in result:
        typer.echo(f"Operator manifest check: {result['operator_manifest_check']['check_status']}")
    if "operator_handoff_packet" in result:
        typer.echo(f"Operator handoff packet: {result['operator_handoff_packet']['handoff_status']}")
    if "operator_run_package" in result:
        typer.echo(f"Operator run package: {result['operator_run_package']['package_status']}")
    if "operator_run_package_check" in result:
        typer.echo(f"Operator run package check: {result['operator_run_package_check']['check_status']}")
    if "next_operator_start_packet" in result:
        typer.echo(f"Next operator start packet: {result['next_operator_start_packet']['start_packet_status']}")
    if "next_operator_start_event" in result:
        typer.echo(f"Next operator start event: {result['next_operator_start_event']['event_status']}")
    if "next_operator_action_result" in result:
        typer.echo(f"Next operator action result: {result['next_operator_action_result']['result_status']}")
    typer.echo(f"Company KB candidates: {manifest['company_kb_feedback']['promotion_status']}")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


def _load_json_object(path: Path, label: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


__all__ = ("run_production_memory_loop_operator_no_provider",)
