from __future__ import annotations

from typing import Any

from agentflow.memory.company_kb_feedback import COMPANY_KB_FEEDBACK_PACKET_KIND
from agentflow.memory.production_loop import CONTEXT_BUNDLE_KIND, PASS_READINESS_KIND, RUN_KIND
from agentflow.memory.production_next_context import NEXT_CONTEXT_HANDOFF_KIND
from agentflow.memory.production_next_pass import NEXT_PASS_BUNDLE_KIND
from agentflow.memory.production_next_pass_promotion import (
    NEXT_PASS_PROMOTION_DECISION_KIND,
    NEXT_PASS_PROMOTION_OVERLAY_KIND,
)
from agentflow.memory.production_next_pass_result import NEXT_PASS_RESULT_KIND
from agentflow.memory.production_next_pass_review import NEXT_PASS_REVIEW_KIND
from agentflow.memory.production_next_task import NEXT_TASK_PACKET_KIND
from agentflow.memory.production_session import SESSION_REPORT_KIND

OPERATOR_LOOP_KIND = "agentflow_production_memory_operator_loop_run"
OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND = (
    "agentflow_production_memory_operator_feedback_candidate_promotion_decision"
)
OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_OVERLAY_KIND = (
    "agentflow_production_memory_operator_feedback_candidate_promotion_overlay"
)
ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND = (
    "agentflow_production_memory_acceptance_feedback_candidate_promotion_decision"
)
ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_OVERLAY_KIND = (
    "agentflow_production_memory_acceptance_feedback_candidate_promotion_overlay"
)


def operator_output_artifacts(
    *,
    include_next_pass_result: bool = False,
    include_next_pass_review: bool = False,
    include_next_pass_promotion: bool = False,
    include_operator_feedback_candidate_promotion: bool = False,
    include_acceptance_feedback_candidate_promotion: bool = False,
) -> list[dict[str, Any]]:
    artifacts = [
        _artifact(RUN_KIND, "run/production_memory_loop_run.json"),
        _artifact(CONTEXT_BUNDLE_KIND, "run/context_bundle.json"),
        _artifact(PASS_READINESS_KIND, "run/pass_readiness.json"),
        _artifact(NEXT_PASS_BUNDLE_KIND, "run/next_pass_bundle.json"),
        _artifact(NEXT_CONTEXT_HANDOFF_KIND, "next_context_handoff/next_context_handoff.json"),
        _artifact("markdown_report", "next_context_handoff/next_context_handoff.md"),
        _artifact(NEXT_TASK_PACKET_KIND, "next_task_packet/next_task_packet.json"),
        _artifact("markdown_report", "next_task_packet/next_task_packet.md"),
    ]
    if include_next_pass_result:
        artifacts.extend(
            [
                _artifact(NEXT_PASS_RESULT_KIND, "next_pass_result/next_pass_result.json"),
                _artifact("markdown_report", "next_pass_result/next_pass_result.md"),
            ]
        )
    if include_next_pass_review:
        artifacts.extend(
            [
                _artifact(NEXT_PASS_REVIEW_KIND, "next_pass_review/next_pass_review.json"),
                _artifact("markdown_report", "next_pass_review/next_pass_review.md"),
            ]
        )
    if include_next_pass_promotion:
        artifacts.extend(
            [
                _artifact(NEXT_PASS_PROMOTION_DECISION_KIND, "next_pass_promotion_decision/next_pass_promotion_decision.json"),
                _artifact("agentflow_production_memory_loop", "next_pass_reviewed_feedback/derived_production_memory_loop.json"),
                _artifact(RUN_KIND, "next_pass_reviewed_feedback/production_memory_loop_run.json"),
                _artifact(CONTEXT_BUNDLE_KIND, "next_pass_reviewed_feedback/context_bundle.json"),
                _artifact(PASS_READINESS_KIND, "next_pass_reviewed_feedback/pass_readiness.json"),
                _artifact(NEXT_PASS_BUNDLE_KIND, "next_pass_reviewed_feedback/next_pass_bundle.json"),
                _artifact(NEXT_PASS_PROMOTION_OVERLAY_KIND, "next_pass_reviewed_feedback/next_pass_promotion_overlay.json"),
            ]
        )
    if include_operator_feedback_candidate_promotion:
        artifacts.extend(
            [
                _artifact(
                    OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND,
                    "operator_feedback_candidate_promotion_decision/operator_feedback_candidate_promotion_decision.json",
                ),
                _artifact(
                    "markdown_report",
                    "operator_feedback_candidate_promotion_decision/operator_feedback_candidate_promotion_decision.md",
                ),
                _artifact(
                    "agentflow_production_memory_loop",
                    "operator_feedback_candidate_reviewed_feedback/derived_production_memory_loop.json",
                ),
                _artifact(RUN_KIND, "operator_feedback_candidate_reviewed_feedback/production_memory_loop_run.json"),
                _artifact(CONTEXT_BUNDLE_KIND, "operator_feedback_candidate_reviewed_feedback/context_bundle.json"),
                _artifact(PASS_READINESS_KIND, "operator_feedback_candidate_reviewed_feedback/pass_readiness.json"),
                _artifact(NEXT_PASS_BUNDLE_KIND, "operator_feedback_candidate_reviewed_feedback/next_pass_bundle.json"),
                _artifact(
                    OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_OVERLAY_KIND,
                    "operator_feedback_candidate_reviewed_feedback/operator_feedback_candidate_promotion_overlay.json",
                ),
            ]
        )
    if include_acceptance_feedback_candidate_promotion:
        artifacts.extend(
            [
                _artifact(
                    ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND,
                    "acceptance_feedback_candidate_promotion_decision/acceptance_feedback_candidate_promotion_decision.json",
                ),
                _artifact(
                    "markdown_report",
                    "acceptance_feedback_candidate_promotion_decision/acceptance_feedback_candidate_promotion_decision.md",
                ),
                _artifact(
                    "agentflow_production_memory_loop",
                    "acceptance_feedback_candidate_reviewed_feedback/derived_production_memory_loop.json",
                ),
                _artifact(RUN_KIND, "acceptance_feedback_candidate_reviewed_feedback/production_memory_loop_run.json"),
                _artifact(CONTEXT_BUNDLE_KIND, "acceptance_feedback_candidate_reviewed_feedback/context_bundle.json"),
                _artifact(PASS_READINESS_KIND, "acceptance_feedback_candidate_reviewed_feedback/pass_readiness.json"),
                _artifact(NEXT_PASS_BUNDLE_KIND, "acceptance_feedback_candidate_reviewed_feedback/next_pass_bundle.json"),
                _artifact(
                    ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_OVERLAY_KIND,
                    "acceptance_feedback_candidate_reviewed_feedback/acceptance_feedback_candidate_promotion_overlay.json",
                ),
            ]
        )
    artifacts.extend(
        [
            _artifact(SESSION_REPORT_KIND, "session_report/production_memory_session_report.json"),
            _artifact("markdown_report", "session_report/production_memory_session_report.md"),
            _artifact(COMPANY_KB_FEEDBACK_PACKET_KIND, "company_kb_candidates/company_kb_feedback_candidate_packet.json"),
            _artifact("markdown_report", "company_kb_candidates/company_kb_feedback_candidate_packet.md"),
            _artifact(OPERATOR_LOOP_KIND, "production_memory_operator_loop_run.json"),
        ]
    )
    return artifacts


def _artifact(artifact_type: str, path: str) -> dict[str, Any]:
    return {"artifact_type": artifact_type, "path": path, "required": True}


__all__ = ("OPERATOR_LOOP_KIND", "operator_output_artifacts")
