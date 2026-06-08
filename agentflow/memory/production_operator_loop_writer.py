from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.memory.company_kb_feedback import write_company_kb_feedback_candidate_packet
from agentflow.memory.production_acceptance_feedback_candidate_overlay import (
    write_acceptance_feedback_candidate_reviewed_run,
)
from agentflow.memory.production_acceptance_feedback_candidate_promotion import (
    write_acceptance_feedback_candidate_promotion_decision,
)
from agentflow.memory.production_loop import write_production_memory_loop_run
from agentflow.memory.production_next_context import write_next_context_handoff
from agentflow.memory.production_next_pass_promotion import write_next_pass_promotion_decision, write_next_pass_reviewed_feedback_run
from agentflow.memory.production_next_pass_result import write_next_pass_result_scaffold
from agentflow.memory.production_next_pass_review import write_next_pass_review
from agentflow.memory.production_next_task import write_next_task_packet
from agentflow.memory.production_operator_feedback_candidate_overlay import write_operator_feedback_candidate_reviewed_run
from agentflow.memory.production_operator_feedback_candidate_promotion import (
    write_operator_feedback_candidate_promotion_decision,
)
from agentflow.memory.production_operator_handoff import build_operator_handoff_packet, write_operator_handoff_packet
from agentflow.memory.production_operator_manifest_check import check_operator_manifest, write_operator_manifest_check
from agentflow.memory.production_operator_outputs import operator_output_artifacts
from agentflow.memory.production_operator_post_check_outputs import (
    validate_post_check_output_options,
    write_post_check_outputs,
)
from agentflow.memory.production_operator_run_package import build_operator_run_package, write_operator_run_package
from agentflow.memory.production_operator_run_package_check import (
    check_operator_run_package,
    write_operator_run_package_check_report,
)
from agentflow.memory.production_session import write_production_memory_session_report
from agentflow.harness.json_io import write_json


def write_production_memory_operator_loop_run(
    result: dict[str, Any],
    output_dir: str | Path,
    *,
    write_manifest_check: bool = False,
    write_handoff_packet: bool = False,
    write_run_package: bool = False,
    write_run_package_check: bool = False,
    write_next_operator_start_packet: bool = False,
    write_next_operator_start_event: bool = False,
    next_operator_start_event_decision: str | None = None,
    next_operator_start_event_summary: str | None = None,
    next_operator_start_event_operator_role: str = "next_operator",
    write_next_operator_action_result: bool = False,
    next_operator_action_result_decision: str | None = None,
    next_operator_action_result_summary: str | None = None,
    next_operator_action_result_refs: list[str] | None = None,
    next_operator_action_result_operator_role: str = "next_operator",
) -> list[Path]:
    validate_post_check_output_options(
        write_run_package=write_run_package,
        write_run_package_check=write_run_package_check,
        write_next_operator_start_packet=write_next_operator_start_packet,
        write_next_operator_start_event=write_next_operator_start_event,
        write_next_operator_action_result=write_next_operator_action_result,
        next_operator_start_event_decision=next_operator_start_event_decision,
        next_operator_start_event_summary=next_operator_start_event_summary,
        next_operator_action_result_decision=next_operator_action_result_decision,
        next_operator_action_result_summary=next_operator_action_result_summary,
        next_operator_action_result_refs=next_operator_action_result_refs,
    )
    output_root = Path(output_dir)
    include_result = "next_pass_result" in result
    include_review = "next_pass_review" in result
    include_promotion = "next_pass_promotion_overlay" in result
    include_operator_feedback_candidate_promotion = "operator_feedback_candidate_promotion_overlay" in result
    include_acceptance_feedback_candidate_promotion = "acceptance_feedback_candidate_promotion_overlay" in result
    written_paths: list[Path] = []
    written_paths.extend(write_production_memory_loop_run(result["run"], output_root / "run"))
    written_paths.extend(write_next_context_handoff(result["next_context_handoff"], output_root / "next_context_handoff"))
    written_paths.extend(write_next_task_packet(result["next_task_packet"], output_root / "next_task_packet"))
    if include_result:
        written_paths.extend(write_next_pass_result_scaffold(result["next_pass_result"], output_root / "next_pass_result"))
    if include_review:
        written_paths.extend(write_next_pass_review(result["next_pass_review"], output_root / "next_pass_review"))
    if include_promotion:
        written_paths.extend(
            write_next_pass_promotion_decision(
                result["next_pass_promotion_decision"],
                output_root / "next_pass_promotion_decision",
            )
        )
        written_paths.extend(
            write_next_pass_reviewed_feedback_run(
                result["next_pass_reviewed_feedback_loop"],
                result["next_pass_reviewed_feedback_run"],
                result["next_pass_promotion_overlay"],
                output_root / "next_pass_reviewed_feedback",
            )
        )
    if include_operator_feedback_candidate_promotion:
        written_paths.extend(
            write_operator_feedback_candidate_promotion_decision(
                result["operator_feedback_candidate_promotion_decision"],
                output_root / "operator_feedback_candidate_promotion_decision",
            )
        )
        written_paths.extend(
            write_operator_feedback_candidate_reviewed_run(
                result["operator_feedback_candidate_reviewed_feedback_loop"],
                result["operator_feedback_candidate_reviewed_feedback_run"],
                result["operator_feedback_candidate_promotion_overlay"],
                output_root / "operator_feedback_candidate_reviewed_feedback",
            )
        )
    if include_acceptance_feedback_candidate_promotion:
        written_paths.extend(
            write_acceptance_feedback_candidate_promotion_decision(
                result["acceptance_feedback_candidate_promotion_decision"],
                output_root / "acceptance_feedback_candidate_promotion_decision",
            )
        )
        written_paths.extend(
            write_acceptance_feedback_candidate_reviewed_run(
                result["acceptance_feedback_candidate_reviewed_feedback_loop"],
                result["acceptance_feedback_candidate_reviewed_feedback_run"],
                result["acceptance_feedback_candidate_promotion_overlay"],
                output_root / "acceptance_feedback_candidate_reviewed_feedback",
            )
        )
    written_paths.extend(write_production_memory_session_report(result["session_report"], output_root / "session_report"))
    written_paths.extend(
        write_company_kb_feedback_candidate_packet(
            result["company_kb_feedback_candidate_packet"],
            output_root / "company_kb_candidates",
        )
    )
    manifest = {
        **result["manifest"],
        "output_artifacts": operator_output_artifacts(
            include_next_pass_result=include_result,
            include_next_pass_review=include_review,
            include_next_pass_promotion=include_promotion,
            include_operator_feedback_candidate_promotion=include_operator_feedback_candidate_promotion,
            include_acceptance_feedback_candidate_promotion=include_acceptance_feedback_candidate_promotion,
        ),
    }
    manifest_path = write_json(output_root / "production_memory_operator_loop_run.json", manifest)
    written_paths.append(manifest_path)
    result["manifest"] = manifest
    if write_run_package:
        write_handoff_packet = True
    if write_manifest_check or write_handoff_packet:
        check = check_operator_manifest(manifest_path)
        result["operator_manifest_check"] = check
        written_paths.append(
            write_operator_manifest_check(
                check,
                output_root / "operator_manifest_check" / "operator_manifest_check.json",
            )
        )
    if write_handoff_packet:
        packet = build_operator_handoff_packet(
            result["manifest"],
            manifest_check=result["operator_manifest_check"],
            generated_at=str(result["manifest"].get("generated_at", "")),
        )
        result["operator_handoff_packet"] = packet
        written_paths.extend(write_operator_handoff_packet(packet, output_root / "operator_handoff"))
    if write_run_package:
        package = build_operator_run_package(
            result["manifest"],
            manifest_check=result["operator_manifest_check"],
            handoff_packet=result["operator_handoff_packet"],
            generated_at=str(result["manifest"].get("generated_at", "")),
        )
        result["operator_run_package"] = package
        written_paths.extend(write_operator_run_package(package, output_root / "operator_run_package"))
    if write_run_package_check:
        check = check_operator_run_package(output_root / "operator_run_package" / "operator_run_package.json")
        result["operator_run_package_check"] = check
        written_paths.extend(write_operator_run_package_check_report(check, output_root / "operator_run_package_check"))
    written_paths.extend(
        write_post_check_outputs(
            result,
            output_root,
            write_next_operator_start_packet=write_next_operator_start_packet,
            write_next_operator_start_event=write_next_operator_start_event,
            write_next_operator_action_result=write_next_operator_action_result,
            next_operator_start_event_decision=next_operator_start_event_decision,
            next_operator_start_event_summary=next_operator_start_event_summary,
            next_operator_start_event_operator_role=next_operator_start_event_operator_role,
            next_operator_action_result_decision=next_operator_action_result_decision,
            next_operator_action_result_summary=next_operator_action_result_summary,
            next_operator_action_result_refs=next_operator_action_result_refs,
            next_operator_action_result_operator_role=next_operator_action_result_operator_role,
        )
    )
    return written_paths


__all__ = ("write_production_memory_operator_loop_run",)
