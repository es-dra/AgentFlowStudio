from __future__ import annotations

from typing import Any

from agentflow.memory.company_kb_feedback import COMPANY_KB_FEEDBACK_PACKET_KIND
from agentflow.memory.production_loop import CONTEXT_BUNDLE_KIND, PASS_READINESS_KIND, RUN_KIND
from agentflow.memory.production_next_context import NEXT_CONTEXT_HANDOFF_KIND
from agentflow.memory.production_next_pass import NEXT_PASS_BUNDLE_KIND
from agentflow.memory.production_next_pass_review import NEXT_PASS_REVIEW_KIND
from agentflow.memory.production_next_task import NEXT_TASK_PACKET_KIND
from agentflow.memory.production_session import SESSION_REPORT_KIND

OPERATOR_LOOP_KIND = "agentflow_production_memory_operator_loop_run"

def operator_output_artifacts(*, include_next_pass_review: bool = False) -> list[dict[str, Any]]:
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
    if include_next_pass_review:
        artifacts.extend(
            [
                _artifact(NEXT_PASS_REVIEW_KIND, "next_pass_review/next_pass_review.json"),
                _artifact("markdown_report", "next_pass_review/next_pass_review.md"),
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


__all__ = ("operator_output_artifacts",)
