from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.memory.production_acceptance_feedback_candidate import (
    ACCEPTANCE_FEEDBACK_CANDIDATE_PACKET_KIND,
)
from agentflow.memory.production_loop import SCHEMA_VERSION
from narratocut.utils import write_json

ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND = (
    "agentflow_production_memory_acceptance_feedback_candidate_promotion_decision"
)
ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_DECISIONS = frozenset(
    {"promoted", "merged", "rejected", "expired", "blocked"}
)
REUSE_ALLOWED_DECISIONS = frozenset({"promoted", "merged"})
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


def load_acceptance_feedback_candidate_packet(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("acceptance feedback candidate packet must be a JSON object")
    return payload


def build_acceptance_feedback_candidate_promotion_decision(
    packet: dict[str, Any],
    *,
    decision: str,
    rationale: str,
    reviewer_role: str,
    decided_at: str,
) -> dict[str, Any]:
    """Record an explicit no-provider decision for one acceptance feedback candidate."""
    _validate_packet(packet)
    _validate_inputs(decision, rationale, reviewer_role, decided_at)
    candidate = _dict(packet.get("memory_candidate"))
    template = _dict(packet.get("promotion_decision_template"))
    candidate_status = str(candidate.get("status", "unknown"))
    if decision in REUSE_ALLOWED_DECISIONS and candidate_status != "candidate":
        raise ValueError("blocked acceptance feedback candidate cannot be promoted or merged")

    candidate_id = str(candidate["candidate_id"])
    reuse_allowed = decision in REUSE_ALLOWED_DECISIONS
    promotion_decision = {
        "kind": ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND,
        "artifact_type": ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND,
        "schema_version": packet.get("schema_version", SCHEMA_VERSION),
        "decision_id": _safe_id("promotion:acceptance-feedback-candidate", candidate_id, decided_at),
        "source_packet_id": packet.get("packet_id", "unknown"),
        "source_acceptance_feedback_event_id": packet.get("source_acceptance_feedback_event_id", "unknown"),
        "source_promotion_decision_template_id": template.get("decision_id", "unknown"),
        "source_operator_loop_id": packet.get("source_operator_loop_id", "unknown"),
        "source_project_id": packet.get("source_project_id", "unknown"),
        "candidate_id": candidate_id,
        "source_candidate_status": candidate_status,
        "source_acceptance_decision": packet.get("source_acceptance_decision", "unknown"),
        "source_human_acceptance_recorded": packet.get("source_human_acceptance_recorded") is True,
        "decision": decision,
        "decision_effect": _decision_effect(decision),
        "review_mode": "explicit_operator_decision",
        "reviewer_role": reviewer_role,
        "rationale": rationale,
        "decided_at": decided_at,
        "template_only": False,
        "candidate_reuse_allowed": reuse_allowed,
        "next_context_eligibility": (
            "eligible_by_explicit_operator_decision" if reuse_allowed else "blocked_by_explicit_operator_decision"
        ),
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "decision_is_durable_memory_write": False,
        "decision_writes_company_kb": False,
        "candidate_is_durable_memory": False,
        "claim_boundaries": _claim_boundaries(packet),
        "non_claims": _non_claims(),
    }
    _reject_unsafe(promotion_decision)
    return promotion_decision


def write_acceptance_feedback_candidate_promotion_decision(
    decision: dict[str, Any],
    output_dir: str | Path,
) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "acceptance_feedback_candidate_promotion_decision.json", decision)
    md_path = output_root / "acceptance_feedback_candidate_promotion_decision.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_acceptance_feedback_candidate_promotion_markdown(decision), encoding="utf-8")
    return [json_path, md_path]


def render_acceptance_feedback_candidate_promotion_markdown(decision: dict[str, Any]) -> str:
    boundaries = _dict(decision.get("claim_boundaries"))
    reuse = "allowed" if decision.get("candidate_reuse_allowed") is True else "blocked"
    return "\n".join(
        [
            "# Production Memory Acceptance Feedback Candidate Promotion Decision",
            "",
            f"Decision: {decision.get('decision', 'unknown')}",
            f"Decision effect: {decision.get('decision_effect', 'unknown')}",
            f"Candidate: {decision.get('candidate_id', 'unknown')}",
            f"Candidate reuse: {reuse}",
            f"Source human acceptance: {decision.get('source_acceptance_decision', 'unknown')}",
            "Provider calls: not started",
            "Writes long-term memory: false",
            "Writes Company KB: false",
            f"Business validation: {boundaries.get('business_validation', 'not_validated')}",
            "",
            "## Rationale",
            str(decision.get("rationale", "")),
            "",
        ]
    )


def _validate_packet(packet: dict[str, Any]) -> None:
    if packet.get("kind") != ACCEPTANCE_FEEDBACK_CANDIDATE_PACKET_KIND:
        raise ValueError(
            f"acceptance feedback candidate promotion requires kind {ACCEPTANCE_FEEDBACK_CANDIDATE_PACKET_KIND}"
        )
    if packet.get("candidate_generation_status") != "candidate_only":
        raise ValueError("acceptance feedback candidate promotion requires candidate_only packet")
    if packet.get("provider_mode") != "no-provider":
        raise ValueError("acceptance feedback candidate promotion requires no-provider packet")
    if packet.get("provider_calls_started") is not False:
        raise ValueError("acceptance feedback candidate promotion requires provider_calls_started false")
    if packet.get("writes_long_term_memory") is not False:
        raise ValueError("acceptance feedback candidate promotion requires writes_long_term_memory false")
    if packet.get("writes_company_kb") is not False:
        raise ValueError("acceptance feedback candidate promotion requires writes_company_kb false")
    if packet.get("feedback_is_memory") is not False:
        raise ValueError("acceptance feedback candidate promotion requires feedback_is_memory false")
    if packet.get("candidate_is_promoted_memory") is not False:
        raise ValueError("acceptance feedback candidate promotion requires unpromoted source candidate")
    candidate = _dict(packet.get("memory_candidate"))
    if not isinstance(candidate.get("candidate_id"), str) or not candidate["candidate_id"].strip():
        raise ValueError("acceptance feedback candidate promotion requires memory_candidate.candidate_id")
    if candidate.get("status") not in {"candidate", "blocked"}:
        raise ValueError("acceptance feedback candidate promotion requires candidate or blocked status")
    template = _dict(packet.get("promotion_decision_template"))
    if template.get("candidate_id") != candidate["candidate_id"]:
        raise ValueError("acceptance feedback candidate promotion requires matching promotion template candidate_id")
    if template.get("decision") != "pending":
        raise ValueError("acceptance feedback candidate promotion requires pending promotion template")
    if template.get("template_only") is not True:
        raise ValueError("acceptance feedback candidate promotion requires template_only promotion template")
    _reject_unsafe(packet, allow_source_refs=True)


def _validate_inputs(decision: str, rationale: str, reviewer_role: str, decided_at: str) -> None:
    for label, value in {
        "rationale": rationale,
        "reviewer_role": reviewer_role,
        "decided_at": decided_at,
    }.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is required")
    if decision not in ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_DECISIONS:
        raise ValueError(f"unsupported acceptance feedback candidate promotion decision: {decision}")
    _reject_unsafe({"decision": decision, "rationale": rationale, "reviewer_role": reviewer_role})


def _decision_effect(decision: str) -> str:
    if decision in REUSE_ALLOWED_DECISIONS:
        return "eligible_for_next_context_overlay"
    return {
        "rejected": "blocked_by_operator_rejection",
        "expired": "blocked_by_expiration",
        "blocked": "blocked_by_operator_block",
    }[decision]


def _claim_boundaries(packet: dict[str, Any]) -> dict[str, str]:
    source = _dict(packet.get("claim_boundaries"))
    return {
        "human_acceptance": source.get("human_acceptance", packet.get("source_acceptance_decision", "unknown")),
        "business_validation": "not_validated",
        "provider_success": "not_claimed",
        "durable_memory_runtime": "not_implemented",
        "company_kb_promotion": "not_performed",
        "memory_promotion": "not_performed",
    }


def _non_claims() -> list[str]:
    return [
        "decision is not new human acceptance",
        "decision is not business validation",
        "decision does not write durable memory",
        "decision does not write Company KB",
        "decision does not prove provider success",
        "decision does not execute a next pass",
    ]


def _safe_id(prefix: str, target_ref: str, created_at: str) -> str:
    raw = f"{prefix}:{target_ref}:{created_at}"
    safe = "".join(char.lower() if char.isalnum() else "-" for char in raw).strip("-")
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe


def _reject_unsafe(value: Any, *, allow_source_refs: bool = False) -> None:
    raw = json.dumps(value, ensure_ascii=False).lower()
    fragments = AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS + UNSAFE_EXTRA_FRAGMENTS
    if allow_source_refs:
        fragments = tuple(fragment for fragment in fragments if fragment not in ALLOWED_SOURCE_REF_FRAGMENTS)
    if any(fragment.lower() in raw for fragment in fragments):
        raise ValueError(
            "production memory acceptance feedback candidate promotion contains unsafe path, media reference, provider URL, or secret"
        )


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


__all__ = (
    "ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_DECISION_KIND",
    "ACCEPTANCE_FEEDBACK_CANDIDATE_PROMOTION_DECISIONS",
    "build_acceptance_feedback_candidate_promotion_decision",
    "load_acceptance_feedback_candidate_packet",
    "render_acceptance_feedback_candidate_promotion_markdown",
    "write_acceptance_feedback_candidate_promotion_decision",
)
