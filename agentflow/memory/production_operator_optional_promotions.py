from __future__ import annotations

from typing import Any

from agentflow.memory.production_next_pass_promotion import build_next_pass_reviewed_feedback_run
from agentflow.memory.production_operator_candidate_promotions import build_operator_feedback_candidate_promotion


def build_optional_next_pass_promotion(
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


def build_optional_operator_feedback_candidate_promotion(
    loop: dict[str, Any],
    packet: dict[str, Any] | None,
    decision: dict[str, Any] | None,
) -> dict[str, Any] | None:
    return build_operator_feedback_candidate_promotion(loop, packet, decision)


__all__ = (
    "build_optional_next_pass_promotion",
    "build_optional_operator_feedback_candidate_promotion",
)
