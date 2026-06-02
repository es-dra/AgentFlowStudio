from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import FAILED, PASSED

ACCEPTANCE_CONTEXT_ACTION = "run_next_ai_task_with_acceptance_feedback_context"
ACCEPTANCE_PROMOTION_REQUIRED_CONTROL = "acceptance_feedback_candidate_promotion_required_for_context_action"
ACCEPTANCE_PROMOTION_MATCHES_HANDOFF_CONTROL = "acceptance_feedback_candidate_promotion_matches_handoff"
ACCEPTANCE_PROMOTION_INCLUDED_CONTROL = "acceptance_feedback_candidate_promotion_included_for_context_action"
SUMMARY_KEYS = (
    "decision_id",
    "candidate_id",
    "source_acceptance_feedback_event_id",
    "source_acceptance_decision",
    "decision",
    "decision_effect",
    "candidate_included_in_context",
    "candidate_blocked_from_context",
    "context_bundle_id",
)


def check_acceptance_feedback_candidate_promotion(
    package: dict[str, Any],
    artifact_root: Path,
) -> dict[str, Any]:
    package_summary = _dict(package.get("acceptance_feedback_candidate_promotion"))
    handoff_summary = _handoff_acceptance_feedback_candidate_promotion(artifact_root)
    action = str(_dict(package.get("next_operator_action")).get("action", "unknown"))
    requires_acceptance_context = action == ACCEPTANCE_CONTEXT_ACTION
    handoff_matches_package = _summaries_match(package_summary, handoff_summary)
    reasons: list[str] = []

    if (requires_acceptance_context or handoff_summary) and not package_summary:
        reasons.append("missing package acceptance feedback candidate promotion summary")
    if (requires_acceptance_context or package_summary) and not handoff_summary:
        reasons.append("missing handoff acceptance feedback candidate promotion summary")
    if package_summary and handoff_summary and not handoff_matches_package:
        reasons.append("acceptance feedback candidate promotion summary differs from handoff")
    if requires_acceptance_context and package_summary:
        if package_summary.get("candidate_included_in_context") is not True:
            reasons.append("acceptance feedback candidate promotion is not included in context")
        if package_summary.get("decision_effect") != "included_in_context":
            reasons.append("acceptance feedback candidate promotion does not include context effect")
        if package_summary.get("candidate_blocked_from_context") is True:
            reasons.append("acceptance feedback candidate promotion is blocked from context")

    status = "not_applicable"
    if reasons:
        status = FAILED
    elif requires_acceptance_context or package_summary or handoff_summary:
        status = PASSED

    return {
        "status": status,
        "requires_acceptance_context": requires_acceptance_context,
        "package_summary_present": bool(package_summary),
        "handoff_summary_present": bool(handoff_summary),
        "handoff_matches_package": handoff_matches_package,
        "decision": str(package_summary.get("decision", "unknown")),
        "decision_effect": str(package_summary.get("decision_effect", "unknown")),
        "candidate_id": str(package_summary.get("candidate_id", "unknown")),
        "context_bundle_id": str(package_summary.get("context_bundle_id", "unknown")),
        "candidate_included_in_context": package_summary.get("candidate_included_in_context") is True,
        "candidate_blocked_from_context": package_summary.get("candidate_blocked_from_context") is True,
        "reasons": reasons,
    }


def acceptance_feedback_candidate_promotion_failed_controls(
    acceptance_check: dict[str, Any],
) -> list[dict[str, str]]:
    if acceptance_check.get("status") != FAILED:
        return []

    reasons = set(_list(acceptance_check.get("reasons")))
    controls: list[dict[str, str]] = []
    if (
        "missing package acceptance feedback candidate promotion summary" in reasons
        and acceptance_check.get("requires_acceptance_context") is True
    ):
        controls.append(_failed_control(ACCEPTANCE_PROMOTION_REQUIRED_CONTROL))
    if (
        "missing package acceptance feedback candidate promotion summary" in reasons
        and acceptance_check.get("handoff_summary_present") is True
    ):
        controls.append(_failed_control(ACCEPTANCE_PROMOTION_MATCHES_HANDOFF_CONTROL))
    if (
        "missing handoff acceptance feedback candidate promotion summary" in reasons
        or "acceptance feedback candidate promotion summary differs from handoff" in reasons
    ):
        controls.append(_failed_control(ACCEPTANCE_PROMOTION_MATCHES_HANDOFF_CONTROL))
    if (
        "acceptance feedback candidate promotion is not included in context" in reasons
        or "acceptance feedback candidate promotion does not include context effect" in reasons
        or "acceptance feedback candidate promotion is blocked from context" in reasons
    ):
        controls.append(_failed_control(ACCEPTANCE_PROMOTION_INCLUDED_CONTROL))
    return controls


def _handoff_acceptance_feedback_candidate_promotion(artifact_root: Path) -> dict[str, Any]:
    handoff_path = artifact_root / "operator_handoff" / "operator_handoff_packet.json"
    if not handoff_path.exists():
        return {}
    try:
        payload = json.loads(handoff_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return _dict(_dict(payload).get("acceptance_feedback_candidate_promotion"))


def _summaries_match(package_summary: dict[str, Any], handoff_summary: dict[str, Any]) -> bool:
    if not package_summary and not handoff_summary:
        return True
    if not package_summary or not handoff_summary:
        return False
    return all(package_summary.get(key) == handoff_summary.get(key) for key in SUMMARY_KEYS)


def _failed_control(control_id: str) -> dict[str, str]:
    return {"control_id": control_id, "status": FAILED}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "ACCEPTANCE_CONTEXT_ACTION",
    "ACCEPTANCE_PROMOTION_INCLUDED_CONTROL",
    "ACCEPTANCE_PROMOTION_MATCHES_HANDOFF_CONTROL",
    "ACCEPTANCE_PROMOTION_REQUIRED_CONTROL",
    "acceptance_feedback_candidate_promotion_failed_controls",
    "check_acceptance_feedback_candidate_promotion",
)
