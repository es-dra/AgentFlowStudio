from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.memory.company_kb_feedback import (
    build_company_kb_feedback_candidate_packet,
    write_company_kb_feedback_candidate_packet,
)
from agentflow.memory.production_loop import build_production_memory_loop_run, write_production_memory_loop_run
from agentflow.memory.production_next_context import build_next_context_handoff, write_next_context_handoff
from agentflow.memory.production_next_pass_promotion import (
    build_next_pass_reviewed_feedback_run,
    write_next_pass_promotion_decision,
    write_next_pass_reviewed_feedback_run,
)
from agentflow.memory.production_next_pass_result import build_next_pass_result_scaffold, write_next_pass_result_scaffold
from agentflow.memory.production_next_pass_review import build_next_pass_review, write_next_pass_review
from agentflow.memory.production_next_task import build_next_task_packet, write_next_task_packet
from agentflow.memory.production_operator_feedback_candidate_overlay import (
    build_operator_feedback_candidate_reviewed_run,
    write_operator_feedback_candidate_reviewed_run,
)
from agentflow.memory.production_operator_feedback_candidate_promotion import (
    write_operator_feedback_candidate_promotion_decision,
)
from agentflow.memory.production_operator_handoff import build_operator_handoff_packet, write_operator_handoff_packet
from agentflow.memory.production_operator_manifest import build_operator_manifest
from agentflow.memory.production_operator_manifest_check import check_operator_manifest, write_operator_manifest_check
from agentflow.memory.production_operator_outputs import OPERATOR_LOOP_KIND, operator_output_artifacts
from agentflow.memory.production_session import (
    build_production_memory_session_report,
    write_production_memory_session_report,
)
from narratocut.utils import write_json


def build_production_memory_operator_loop_run(
    loop: dict[str, Any],
    *,
    generated_at: str,
    source_kb_status: str = "restructuring_or_unknown",
    draft_next_pass_result: bool = False,
    next_pass_result: dict[str, Any] | None = None,
    next_pass_promotion_decision: dict[str, Any] | None = None,
    operator_feedback_candidate_packet: dict[str, Any] | None = None,
    operator_feedback_candidate_promotion_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an auditable no-provider operator loop from source loop to feedback packet."""
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise ValueError("generated_at is required")
    if draft_next_pass_result and next_pass_result is not None:
        raise ValueError("draft_next_pass_result cannot be combined with next_pass_result")
    if next_pass_promotion_decision is not None and next_pass_result is None:
        raise ValueError("next_pass_promotion_decision requires next_pass_result")
    if operator_feedback_candidate_packet is not None and operator_feedback_candidate_promotion_decision is None:
        raise ValueError("operator_feedback_candidate_packet requires operator_feedback_candidate_promotion_decision")
    if operator_feedback_candidate_promotion_decision is not None and operator_feedback_candidate_packet is None:
        raise ValueError("operator_feedback_candidate_promotion_decision requires operator_feedback_candidate_packet")

    run = build_production_memory_loop_run(loop)
    handoff = build_next_context_handoff(run, generated_at=generated_at)
    next_task_packet = build_next_task_packet(handoff, generated_at=generated_at)
    next_pass_result_scaffold = (
        build_next_pass_result_scaffold(next_task_packet, generated_at=generated_at) if draft_next_pass_result else None
    )
    next_pass_review = (
        build_next_pass_review(next_task_packet, next_pass_result, reviewed_at=generated_at)
        if next_pass_result is not None
        else None
    )
    next_pass_promotion = _build_next_pass_promotion(loop, next_pass_review, next_pass_promotion_decision)
    operator_feedback_candidate_promotion = _build_operator_feedback_candidate_promotion(
        loop,
        operator_feedback_candidate_packet,
        operator_feedback_candidate_promotion_decision,
    )
    report = build_production_memory_session_report(run, generated_at=generated_at)
    packet = build_company_kb_feedback_candidate_packet(
        report,
        generated_at=generated_at,
        source_kb_status=source_kb_status,
    )
    manifest = build_operator_manifest(
        loop,
        run,
        handoff,
        next_task_packet,
        next_pass_result_scaffold,
        next_pass_review,
        next_pass_promotion,
        operator_feedback_candidate_promotion,
        report,
        packet,
        generated_at=generated_at,
    )
    result = {
        "manifest": manifest,
        "run": run,
        "next_context_handoff": handoff,
        "next_task_packet": next_task_packet,
        "session_report": report,
        "company_kb_feedback_candidate_packet": packet,
    }
    if next_pass_result_scaffold is not None:
        result["next_pass_result"] = next_pass_result_scaffold
    if next_pass_review is not None:
        result["next_pass_review"] = next_pass_review
    if next_pass_promotion is not None:
        result.update(
            {
                "next_pass_promotion_decision": next_pass_promotion["decision"],
                "next_pass_reviewed_feedback_loop": next_pass_promotion["derived_loop"],
                "next_pass_reviewed_feedback_run": next_pass_promotion["run"],
                "next_pass_promotion_overlay": next_pass_promotion["overlay"],
            }
        )
    if operator_feedback_candidate_promotion is not None:
        result.update(
            {
                "operator_feedback_candidate_promotion_decision": operator_feedback_candidate_promotion["decision"],
                "operator_feedback_candidate_reviewed_feedback_loop": operator_feedback_candidate_promotion["derived_loop"],
                "operator_feedback_candidate_reviewed_feedback_run": operator_feedback_candidate_promotion["run"],
                "operator_feedback_candidate_promotion_overlay": operator_feedback_candidate_promotion["overlay"],
            }
        )
    return result


def write_production_memory_operator_loop_run(
    result: dict[str, Any],
    output_dir: str | Path,
    *,
    write_manifest_check: bool = False,
    write_handoff_packet: bool = False,
) -> list[Path]:
    output_root = Path(output_dir)
    include_result = "next_pass_result" in result
    include_review = "next_pass_review" in result
    include_promotion = "next_pass_promotion_overlay" in result
    include_operator_feedback_candidate_promotion = "operator_feedback_candidate_promotion_overlay" in result
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
        ),
    }
    manifest_path = write_json(output_root / "production_memory_operator_loop_run.json", manifest)
    written_paths.append(manifest_path)
    result["manifest"] = manifest
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
    return written_paths


def _build_next_pass_promotion(
    loop: dict[str, Any],
    next_pass_review: dict[str, Any] | None,
    decision: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if decision is None:
        return None
    if next_pass_review is None:
        raise ValueError("next_pass_promotion_decision requires next_pass_result")
    derived_loop, run, overlay = build_next_pass_reviewed_feedback_run(loop, next_pass_review, decision)
    return {"decision": decision, "derived_loop": derived_loop, "run": run, "overlay": overlay}


def _build_operator_feedback_candidate_promotion(
    loop: dict[str, Any],
    packet: dict[str, Any] | None,
    decision: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if packet is None and decision is None:
        return None
    if packet is None:
        raise ValueError("operator_feedback_candidate_promotion_decision requires operator_feedback_candidate_packet")
    if decision is None:
        raise ValueError("operator_feedback_candidate_packet requires operator_feedback_candidate_promotion_decision")
    _validate_operator_feedback_candidate_project(loop, packet, decision)
    derived_loop, run, overlay = build_operator_feedback_candidate_reviewed_run(loop, packet, decision)
    return {"decision": decision, "derived_loop": derived_loop, "run": run, "overlay": overlay}


def _validate_operator_feedback_candidate_project(
    loop: dict[str, Any],
    packet: dict[str, Any],
    decision: dict[str, Any],
) -> None:
    project_input = loop.get("project_input")
    project_id = project_input.get("project_id") if isinstance(project_input, dict) else None
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("operator feedback candidate overlay requires loop project_input.project_id")
    if packet.get("source_project_id") != project_id:
        raise ValueError("operator_feedback_candidate_packet source_project_id must match loop project_id")
    if decision.get("source_project_id") != packet.get("source_project_id"):
        raise ValueError("operator_feedback_candidate_promotion_decision source_project_id must match packet")


__all__ = (
    "OPERATOR_LOOP_KIND",
    "build_production_memory_operator_loop_run",
    "write_production_memory_operator_loop_run",
)
