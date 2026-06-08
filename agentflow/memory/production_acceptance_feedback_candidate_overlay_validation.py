from __future__ import annotations

import json
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.memory.production_acceptance_feedback_candidate import ACCEPTANCE_FEEDBACK_CANDIDATE_PACKET_KIND
from agentflow.memory.production_acceptance_feedback_candidate_promotion import (
    ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND,
    ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_DECISIONS,
    REUSE_ALLOWED_DECISIONS,
)
from agentflow.memory.production_loop import KIND, SCHEMA_VERSION

UNSAFE_EXTRA_FRAGMENTS = (
    "http://",
    "https://",
    "file://",
    "data:image/",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".mp4",
    ".mov",
)
ALLOWED_SOURCE_REF_FRAGMENTS = ("data/processed/runs",)


def validate_loop(payload: dict[str, Any]) -> None:
    if payload.get("kind") != KIND:
        raise ValueError(f"acceptance feedback candidate overlay requires kind {KIND}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"acceptance feedback candidate overlay requires schema_version {SCHEMA_VERSION}")
    for section in ("artifact_ledger", "feedback_events", "memory_candidates", "promotion_decisions"):
        if not isinstance(payload.get(section), list):
            raise ValueError(f"{section} must be a list")


def validate_packet(packet: dict[str, Any]) -> None:
    if packet.get("kind") != ACCEPTANCE_FEEDBACK_CANDIDATE_PACKET_KIND:
        raise ValueError(f"acceptance feedback candidate overlay requires kind {ACCEPTANCE_FEEDBACK_CANDIDATE_PACKET_KIND}")
    if packet.get("candidate_generation_status") != "candidate_only":
        raise ValueError("acceptance feedback candidate overlay requires candidate_only packet")
    if packet.get("provider_calls_started") is not False:
        raise ValueError("acceptance feedback candidate overlay requires provider_calls_started false")
    if packet.get("writes_long_term_memory") is not False or packet.get("writes_company_kb") is not False:
        raise ValueError("acceptance feedback candidate overlay requires no memory or Company KB writes")
    candidate = dict_value(packet.get("memory_candidate"))
    if not isinstance(candidate.get("candidate_id"), str) or not candidate["candidate_id"].strip():
        raise ValueError("acceptance feedback candidate overlay requires memory_candidate.candidate_id")
    reject_unsafe(packet, allow_source_refs=True)


def validate_promotion_decision(packet: dict[str, Any], decision: dict[str, Any]) -> None:
    candidate = dict_value(packet.get("memory_candidate"))
    template = dict_value(packet.get("promotion_decision_template"))
    if decision.get("kind") != ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND:
        raise ValueError("explicit acceptance feedback candidate promotion decision is required")
    if decision.get("source_packet_id") != packet.get("packet_id"):
        raise ValueError("acceptance feedback candidate decision source_packet_id must match packet")
    if decision.get("source_acceptance_feedback_event_id") != packet.get("source_acceptance_feedback_event_id"):
        raise ValueError("acceptance feedback candidate decision source_acceptance_feedback_event_id must match packet")
    if decision.get("source_promotion_decision_template_id") != template.get("decision_id"):
        raise ValueError("acceptance feedback candidate decision must preserve source pending template id")
    if decision.get("candidate_id") != candidate.get("candidate_id"):
        raise ValueError("acceptance feedback candidate decision candidate_id must match packet")
    if decision.get("decision") not in ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_DECISIONS:
        raise ValueError("acceptance feedback candidate decision must be reviewed")
    if decision.get("review_mode") != "explicit_operator_decision" or decision.get("template_only") is not False:
        raise ValueError("explicit acceptance feedback candidate promotion decision is required")
    if decision.get("provider_calls_started") is not False:
        raise ValueError("acceptance feedback candidate decision must not start provider calls")
    if decision.get("writes_long_term_memory") is not False or decision.get("writes_company_kb") is not False:
        raise ValueError("acceptance feedback candidate decision must not write memory or Company KB")
    if decision.get("decision") in REUSE_ALLOWED_DECISIONS and candidate.get("status") != "candidate":
        raise ValueError("only candidate acceptance feedback can be promoted or merged")
    reject_unsafe(decision, allow_source_refs=True)


def reject_unsafe(value: Any, *, allow_source_refs: bool = False) -> None:
    raw = json.dumps(value, ensure_ascii=False).lower()
    fragments = AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS + UNSAFE_EXTRA_FRAGMENTS
    if allow_source_refs:
        fragments = tuple(fragment for fragment in fragments if fragment not in ALLOWED_SOURCE_REF_FRAGMENTS)
    if any(fragment.lower() in raw for fragment in fragments):
        raise ValueError(
            "production memory acceptance feedback candidate overlay contains unsafe path, media reference, "
            "provider URL, or secret"
        )


def dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
