from __future__ import annotations

from typing import Any

from agentflow.memory.production_acceptance_feedback_candidate_overlay import (
    build_acceptance_feedback_candidate_reviewed_run,
)
from agentflow.memory.production_operator_feedback_candidate_overlay import (
    build_operator_feedback_candidate_reviewed_run,
)


def build_operator_feedback_candidate_promotion(
    loop: dict[str, Any],
    packet: dict[str, Any] | None,
    decision: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if packet is None and decision is None:
        return None
    _require_pair(
        packet,
        decision,
        packet_name="operator_feedback_candidate_packet",
        decision_name="operator_feedback_candidate_promotion_decision",
    )
    _validate_candidate_project(loop, packet, decision, "operator_feedback_candidate")
    derived_loop, run, overlay = build_operator_feedback_candidate_reviewed_run(loop, packet, decision)
    return {"decision": decision, "derived_loop": derived_loop, "run": run, "overlay": overlay}


def build_acceptance_feedback_candidate_promotion(
    loop: dict[str, Any],
    packet: dict[str, Any] | None,
    decision: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if packet is None and decision is None:
        return None
    _require_pair(
        packet,
        decision,
        packet_name="acceptance_feedback_candidate_packet",
        decision_name="acceptance_feedback_candidate_promotion_decision",
    )
    _validate_candidate_project(loop, packet, decision, "acceptance_feedback_candidate")
    derived_loop, run, overlay = build_acceptance_feedback_candidate_reviewed_run(loop, packet, decision)
    return {"decision": decision, "derived_loop": derived_loop, "run": run, "overlay": overlay}


def _require_pair(
    packet: dict[str, Any] | None,
    decision: dict[str, Any] | None,
    *,
    packet_name: str,
    decision_name: str,
) -> None:
    if packet is None:
        raise ValueError(f"{decision_name} requires {packet_name}")
    if decision is None:
        raise ValueError(f"{packet_name} requires {decision_name}")


def _validate_candidate_project(
    loop: dict[str, Any],
    packet: dict[str, Any],
    decision: dict[str, Any],
    prefix: str,
) -> None:
    project_input = loop.get("project_input")
    project_id = project_input.get("project_id") if isinstance(project_input, dict) else None
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError(f"{prefix} overlay requires loop project_input.project_id")
    if packet.get("source_project_id") != project_id:
        raise ValueError(f"{prefix}_packet source_project_id must match loop project_id")
    if decision.get("source_project_id") != packet.get("source_project_id"):
        raise ValueError(f"{prefix}_promotion_decision source_project_id must match packet")


__all__ = (
    "build_acceptance_feedback_candidate_promotion",
    "build_operator_feedback_candidate_promotion",
)
