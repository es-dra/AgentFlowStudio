from __future__ import annotations

from typing import Any

from agentflow.harness.constants import FAILED, PASSED
from agentflow.memory.production_next_pass_promotion import (
    NEXT_PASS_PROMOTION_DECISION_KIND,
    NEXT_PASS_PROMOTION_OVERLAY_KIND,
)
from agentflow.memory.production_next_pass_result import NEXT_PASS_RESULT_KIND
from agentflow.memory.production_next_pass_review import NEXT_PASS_REVIEW_KIND


def next_pass_result_ready(next_pass_result: dict[str, Any] | None) -> bool:
    if next_pass_result is None:
        return True
    return (
        next_pass_result.get("result_status") == "scaffolded_for_operator_completion"
        and next_pass_result.get("provider_calls_started") is False
        and next_pass_result.get("writes_long_term_memory") is False
        and next_pass_result.get("writes_company_kb") is False
    )


def next_pass_review_ready(next_pass_review: dict[str, Any] | None) -> bool:
    return next_pass_review is None or next_pass_review.get("review_status") == "ready_for_operator_review"


def next_pass_promotion_ready(next_pass_promotion: dict[str, Any] | None) -> bool:
    if next_pass_promotion is None:
        return True
    overlay = next_pass_promotion["overlay"]
    return (
        overlay.get("run_readiness") == PASSED
        and overlay.get("provider_calls_started") is False
        and overlay.get("writes_long_term_memory") is False
        and overlay.get("writes_company_kb") is False
    )


def next_pass_nodes(
    next_pass_result: dict[str, Any] | None,
    next_pass_review: dict[str, Any] | None,
    next_pass_promotion: dict[str, Any] | None,
) -> list[dict[str, str]]:
    nodes: list[dict[str, str]] = []
    if next_pass_result is not None:
        nodes.append(
            _node(
                "next_pass_result",
                next_pass_result.get("result_status", "unknown"),
                "operator completion scaffold",
                NEXT_PASS_RESULT_KIND,
            )
        )
    if next_pass_review is not None:
        nodes.append(
            _node(
                "next_pass_review",
                next_pass_review.get("review_status", "unknown"),
                "explicit next-pass result review",
                NEXT_PASS_REVIEW_KIND,
            )
        )
    if next_pass_promotion is not None:
        decision = next_pass_promotion["decision"]
        overlay = next_pass_promotion["overlay"]
        nodes.extend(
            [
                _node(
                    "next_pass_promotion_decision",
                    decision.get("decision", "unknown"),
                    decision.get("decision_id", "unknown"),
                    NEXT_PASS_PROMOTION_DECISION_KIND,
                ),
                _node(
                    "next_pass_promotion_overlay",
                    overlay.get("decision_effect", "unknown"),
                    overlay.get("context_bundle_id", "unknown"),
                    NEXT_PASS_PROMOTION_OVERLAY_KIND,
                ),
            ]
        )
    return nodes


def next_pass_promotion_controls(next_pass_promotion: dict[str, Any]) -> list[dict[str, str]]:
    overlay = next_pass_promotion["overlay"]
    return [
        _control("next_pass_promotion_decision_explicit", next_pass_promotion["decision"].get("template_only") is False),
        _control("next_pass_promotion_no_provider_mode", overlay.get("provider_mode") == "no-provider"),
        _control("next_pass_promotion_long_term_memory_write_disabled", overlay.get("writes_long_term_memory") is False),
        _control("next_pass_promotion_company_kb_write_disabled", overlay.get("writes_company_kb") is False),
    ]


def next_pass_result_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "result_id": result.get("result_id", "unknown"),
        "result_status": result.get("result_status", "unknown"),
        "provider_mode": result.get("provider_mode", "unknown"),
        "provider_calls_started": result.get("provider_calls_started") is True,
        "writes_long_term_memory": result.get("writes_long_term_memory") is True,
        "writes_company_kb": result.get("writes_company_kb") is True,
        "output_artifact_count": len(result.get("output_artifacts", [])),
        "feedback_event_count": len(result.get("feedback_events", [])),
    }


def next_pass_review_summary(review: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_id": review.get("review_id", "unknown"),
        "review_status": review.get("review_status", "unknown"),
        "used_allowed_ref_count": len(review.get("used_allowed_refs", [])),
        "blocked_or_unknown_ref_count": len(review.get("blocked_or_unknown_refs", [])),
        "feedback_candidate_count": len(review.get("feedback_candidates", [])),
    }


def next_pass_promotion_summary(promotion: dict[str, Any]) -> dict[str, Any]:
    decision = promotion["decision"]
    overlay = promotion["overlay"]
    return {
        "decision_id": decision.get("decision_id", "unknown"),
        "candidate_id": decision.get("candidate_id", "unknown"),
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
    "next_pass_nodes",
    "next_pass_promotion_controls",
    "next_pass_promotion_ready",
    "next_pass_promotion_summary",
    "next_pass_result_ready",
    "next_pass_result_summary",
    "next_pass_review_ready",
    "next_pass_review_summary",
)
