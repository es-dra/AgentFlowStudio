from __future__ import annotations

from typing import Any

from agentflow.harness.constants import FAILED, PASSED
from agentflow.memory.production_operator_feedback_candidate_overlay import (
    OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_OVERLAY_KIND,
)
from agentflow.memory.production_operator_feedback_candidate_promotion import (
    OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND,
)


def operator_feedback_candidate_promotion_ready(promotion: dict[str, Any] | None) -> bool:
    if promotion is None:
        return True
    overlay = promotion["overlay"]
    return (
        overlay.get("run_readiness") == PASSED
        and overlay.get("provider_calls_started") is False
        and overlay.get("writes_long_term_memory") is False
        and overlay.get("writes_company_kb") is False
    )


def operator_feedback_candidate_promotion_nodes(promotion: dict[str, Any]) -> list[dict[str, str]]:
    decision = promotion["decision"]
    overlay = promotion["overlay"]
    return [
        _node(
            "operator_feedback_candidate_promotion_decision",
            decision.get("decision", "unknown"),
            decision.get("decision_id", "unknown"),
            OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND,
        ),
        _node(
            "operator_feedback_candidate_promotion_overlay",
            overlay.get("decision_effect", "unknown"),
            overlay.get("context_bundle_id", "unknown"),
            OPERATOR_FEEDBACK_CANDIDATE_PROMOTION_OVERLAY_KIND,
        ),
    ]


def operator_feedback_candidate_promotion_controls(promotion: dict[str, Any]) -> list[dict[str, str]]:
    decision = promotion["decision"]
    overlay = promotion["overlay"]
    return [
        _control("operator_feedback_candidate_promotion_decision_explicit", decision.get("template_only") is False),
        _control("operator_feedback_candidate_promotion_no_provider_mode", overlay.get("provider_mode") == "no-provider"),
        _control(
            "operator_feedback_candidate_promotion_long_term_memory_write_disabled",
            overlay.get("writes_long_term_memory") is False,
        ),
        _control(
            "operator_feedback_candidate_promotion_company_kb_write_disabled",
            overlay.get("writes_company_kb") is False,
        ),
    ]


def operator_feedback_candidate_promotion_summary(promotion: dict[str, Any]) -> dict[str, Any]:
    decision = promotion["decision"]
    overlay = promotion["overlay"]
    return {
        "decision_id": decision.get("decision_id", "unknown"),
        "candidate_id": decision.get("candidate_id", "unknown"),
        "source_feedback_event_id": decision.get("source_feedback_event_id", "unknown"),
        "decision": decision.get("decision", "unknown"),
        "decision_effect": overlay.get("decision_effect", "unknown"),
        "candidate_included_in_context": overlay.get("candidate_included_in_context") is True,
        "candidate_blocked_from_context": overlay.get("candidate_blocked_from_context") is True,
        "context_bundle_id": overlay.get("context_bundle_id", "unknown"),
    }


def _node(node_id: str, status: str, detail: Any, artifact_type: str) -> dict[str, str]:
    return {
        "node_id": node_id,
        "status": str(status),
        "detail": str(detail),
        "artifact_type": artifact_type,
    }


def _control(control_id: str, passed: bool) -> dict[str, str]:
    return {"control_id": control_id, "status": PASSED if passed else FAILED}


__all__ = (
    "operator_feedback_candidate_promotion_controls",
    "operator_feedback_candidate_promotion_nodes",
    "operator_feedback_candidate_promotion_ready",
    "operator_feedback_candidate_promotion_summary",
)
