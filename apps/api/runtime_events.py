from __future__ import annotations

from typing import Any
from uuid import uuid4

SCHEMA_VERSION = "production-memory-loop/v1"


def runtime_feedback_event(project_id: str, feedback: dict[str, Any], generated_at: str) -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_runtime_feedback_event",
        "schema_version": SCHEMA_VERSION,
        "feedback_id": f"runtime-feedback:{project_id}:{uuid4().hex[:12]}",
        "project_id": project_id,
        "generated_at": generated_at,
        "feedback": feedback,
        "feedback_is_memory": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": ["not durable memory", "not human acceptance", "not business validation"],
    }


def runtime_review_decision_event(
    project_id: str,
    card_id: str,
    decision: str,
    note: str,
    generated_at: str,
    *,
    candidate_id: str | None = None,
    artifact_id: str | None = None,
) -> dict[str, Any]:
    event = {
        "artifact_type": "agentflow_runtime_review_decision",
        "schema_version": SCHEMA_VERSION,
        "review_id": f"runtime-review:{project_id}:{uuid4().hex[:12]}",
        "project_id": project_id,
        "card_id": card_id,
        "decision": decision,
        "note": note,
        "generated_at": generated_at,
        "feedback_is_memory": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": ["not durable memory", "not human acceptance", "not business validation"],
    }
    if candidate_id:
        event["candidate_id"] = candidate_id
    if artifact_id:
        event["artifact_id"] = artifact_id
    return event


__all__ = ("runtime_feedback_event", "runtime_review_decision_event")
