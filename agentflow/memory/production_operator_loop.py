from __future__ import annotations

from typing import Any

from agentflow.memory.company_kb_feedback import build_company_kb_feedback_candidate_packet
from agentflow.memory.production_loop import build_production_memory_loop_run
from agentflow.memory.production_next_context import build_next_context_handoff
from agentflow.memory.production_next_pass_result import build_next_pass_result_scaffold
from agentflow.memory.production_next_pass_review import build_next_pass_review
from agentflow.memory.production_next_task import build_next_task_packet
from agentflow.memory.production_operator_candidate_promotions import build_acceptance_feedback_candidate_promotion
from agentflow.memory.production_operator_loop_writer import write_production_memory_operator_loop_run
from agentflow.memory.production_operator_manifest import build_operator_manifest
from agentflow.memory.production_operator_optional_promotions import (
    build_optional_next_pass_promotion,
    build_optional_operator_feedback_candidate_promotion,
)
from agentflow.memory.production_operator_outputs import OPERATOR_LOOP_KIND
from agentflow.memory.production_session import build_production_memory_session_report


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
    acceptance_feedback_candidate_packet: dict[str, Any] | None = None,
    acceptance_feedback_candidate_promotion_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an auditable no-provider operator loop from source loop to feedback packet."""
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise ValueError("generated_at is required")
    if draft_next_pass_result and next_pass_result is not None:
        raise ValueError("draft_next_pass_result cannot be combined with next_pass_result")
    if next_pass_promotion_decision is not None and next_pass_result is None:
        raise ValueError("next_pass_promotion_decision requires next_pass_result")

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
    next_pass_promotion = build_optional_next_pass_promotion(loop, next_pass_review, next_pass_promotion_decision)
    operator_feedback_candidate_promotion = build_optional_operator_feedback_candidate_promotion(
        loop,
        operator_feedback_candidate_packet,
        operator_feedback_candidate_promotion_decision,
    )
    acceptance_feedback_candidate_promotion = build_acceptance_feedback_candidate_promotion(
        loop,
        acceptance_feedback_candidate_packet,
        acceptance_feedback_candidate_promotion_decision,
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
        acceptance_feedback_candidate_promotion,
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
    if acceptance_feedback_candidate_promotion is not None:
        result.update(
            {
                "acceptance_feedback_candidate_promotion_decision": acceptance_feedback_candidate_promotion["decision"],
                "acceptance_feedback_candidate_reviewed_feedback_loop": acceptance_feedback_candidate_promotion["derived_loop"],
                "acceptance_feedback_candidate_reviewed_feedback_run": acceptance_feedback_candidate_promotion["run"],
                "acceptance_feedback_candidate_promotion_overlay": acceptance_feedback_candidate_promotion["overlay"],
            }
        )
    return result


__all__ = ("OPERATOR_LOOP_KIND", "build_production_memory_operator_loop_run", "write_production_memory_operator_loop_run")
