from __future__ import annotations

from typing import Any


def acceptance_feedback_candidate_promotion_prompt(value: Any) -> str:
    summary = _dict(value)
    if not summary:
        return ""
    if summary.get("candidate_included_in_context") is True:
        return "Acceptance feedback candidate promotion is included in the next context. "
    if summary.get("candidate_blocked_from_context") is True:
        return "Acceptance feedback candidate promotion is blocked from the next context. "
    return "Acceptance feedback candidate promotion is present for operator review. "


def acceptance_feedback_candidate_promotion_markdown(value: Any) -> str:
    summary = _dict(value)
    if not summary:
        return "## Acceptance Feedback Candidate Promotion\n\n- none"
    return "\n".join(
        [
            "## Acceptance Feedback Candidate Promotion",
            "",
            f"Decision: {summary.get('decision', 'unknown')}",
            f"Decision effect: {summary.get('decision_effect', 'unknown')}",
            f"Candidate included in context: {_yes_no(summary.get('candidate_included_in_context'))}",
            f"Candidate blocked from context: {_yes_no(summary.get('candidate_blocked_from_context'))}",
            f"Context bundle: {summary.get('context_bundle_id', 'unknown')}",
        ]
    )


def _yes_no(value: Any) -> str:
    return "yes" if value is True else "no"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


__all__ = (
    "acceptance_feedback_candidate_promotion_markdown",
    "acceptance_feedback_candidate_promotion_prompt",
)
