from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.memory.production_acceptance_feedback import ACCEPTANCE_FEEDBACK_EVENT_KIND
from agentflow.memory.production_loop import SCHEMA_VERSION
from narratocut.utils import write_json

ACCEPTANCE_FEEDBACK_CANDIDATE_PACKET_KIND = "agentflow_production_memory_acceptance_feedback_candidate_packet"
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


def load_acceptance_feedback_event(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("acceptance feedback event must be a JSON object")
    return payload


def build_acceptance_feedback_candidate_packet(
    event: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    """Draft a candidate-only memory packet from explicit human acceptance feedback."""
    _validate_event(event)
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise ValueError("generated_at is required")

    feedback_id = str(event["feedback_id"])
    candidate = _memory_candidate(event, generated_at)
    promotion_template = _promotion_decision_template(candidate["candidate_id"], feedback_id, generated_at)
    packet = {
        "kind": ACCEPTANCE_FEEDBACK_CANDIDATE_PACKET_KIND,
        "artifact_type": ACCEPTANCE_FEEDBACK_CANDIDATE_PACKET_KIND,
        "schema_version": event.get("schema_version", SCHEMA_VERSION),
        "packet_id": _safe_id("acceptance-feedback-candidate", feedback_id, generated_at),
        "generated_at": generated_at,
        "candidate_generation_status": "candidate_only",
        "source_acceptance_feedback_event_id": feedback_id,
        "source_operator_loop_id": event.get("source_operator_loop_id", "unknown"),
        "source_project_id": event.get("source_project_id", "unknown"),
        "source_package_path": event.get("source_package_path", "unknown"),
        "source_check_status": event.get("source_check_status", "unknown"),
        "source_ready_for_handoff": event.get("source_ready_for_handoff") is True,
        "source_acceptance_decision": event.get("acceptance_decision", "unknown"),
        "source_human_acceptance_recorded": event.get("human_acceptance_recorded") is True,
        "business_validation": event.get("business_validation", "not_validated"),
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "feedback_is_memory": False,
        "candidate_is_promoted_memory": False,
        "memory_candidate": candidate,
        "promotion_decision_template": promotion_template,
        "claim_boundaries": _claim_boundaries(event),
        "non_claims": _non_claims(),
    }
    _reject_unsafe(packet, allow_source_refs=True)
    return packet


def write_acceptance_feedback_candidate_packet(packet: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "acceptance_feedback_candidate_packet.json", packet)
    candidate_path = write_json(output_root / "memory_candidate.json", packet["memory_candidate"])
    template_path = write_json(output_root / "promotion_decision_template.json", packet["promotion_decision_template"])
    md_path = output_root / "acceptance_feedback_candidate_packet.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_acceptance_feedback_candidate_markdown(packet), encoding="utf-8")
    return [json_path, candidate_path, template_path, md_path]


def render_acceptance_feedback_candidate_markdown(packet: dict[str, Any]) -> str:
    candidate = _dict(packet.get("memory_candidate"))
    template = _dict(packet.get("promotion_decision_template"))
    boundaries = _dict(packet.get("claim_boundaries"))
    return "\n".join(
        [
            "# Production Memory Acceptance Feedback Candidate Packet",
            "",
            f"Status: {packet.get('candidate_generation_status', 'unknown')}",
            f"Source human acceptance: {packet.get('source_acceptance_decision', 'unknown')}",
            f"Candidate: {candidate.get('candidate_id', 'unknown')}",
            f"Candidate status: {candidate.get('status', 'unknown')}",
            f"Promotion decision: {template.get('decision', 'unknown')}",
            "Provider calls: not started",
            "Writes long-term memory: false",
            "Writes Company KB: false",
            f"Business validation: {boundaries.get('business_validation', 'not_validated')}",
            "",
            "## Candidate Statement",
            str(candidate.get("statement", "")),
            "",
        ]
    )


def _validate_event(event: dict[str, Any]) -> None:
    if event.get("kind") != ACCEPTANCE_FEEDBACK_EVENT_KIND:
        raise ValueError(f"acceptance feedback candidate requires kind {ACCEPTANCE_FEEDBACK_EVENT_KIND}")
    if not isinstance(event.get("feedback_id"), str) or not event["feedback_id"].strip():
        raise ValueError("acceptance feedback candidate requires feedback_id")
    if event.get("status") != "human_recorded":
        raise ValueError("acceptance feedback candidate requires human_recorded feedback")
    if event.get("provider_mode") != "no-provider":
        raise ValueError("acceptance feedback candidate requires no-provider feedback")
    if event.get("provider_calls_started") is not False:
        raise ValueError("acceptance feedback candidate requires provider_calls_started false")
    if event.get("writes_long_term_memory") is not False:
        raise ValueError("acceptance feedback candidate requires writes_long_term_memory false")
    if event.get("writes_company_kb") is not False:
        raise ValueError("acceptance feedback candidate requires writes_company_kb false")
    if event.get("feedback_is_memory") is not False:
        raise ValueError("acceptance feedback candidate requires feedback_is_memory false")
    if event.get("creates_memory_candidate") is not False:
        raise ValueError("acceptance feedback candidate requires original event to create no memory candidate")
    if event.get("creates_promotion_decision") is not False:
        raise ValueError("acceptance feedback candidate requires original event to create no promotion decision")
    if event.get("business_validation") != "not_validated":
        raise ValueError("acceptance feedback candidate requires business_validation not_validated")
    _reject_unsafe(event, allow_source_refs=True)


def _memory_candidate(event: dict[str, Any], generated_at: str) -> dict[str, Any]:
    feedback_id = str(event["feedback_id"])
    decision = str(event.get("acceptance_decision", "unknown"))
    status = "candidate" if decision == "accepted" else "blocked"
    return {
        "candidate_id": _safe_id("memory-candidate-acceptance-feedback", feedback_id, generated_at),
        "status": status,
        "scope": "project",
        "source_feedback_ids": [feedback_id],
        "source_operator_loop_id": event.get("source_operator_loop_id", "unknown"),
        "source_acceptance_decision": decision,
        "target_ref": f"operator-run-package:{event.get('source_operator_loop_id', 'unknown')}",
        "target_status": event.get("source_check_status", "unknown"),
        "target_artifact_type": "agentflow_production_memory_operator_run_package",
        "statement": event.get("summary", ""),
        "candidate_is_promoted_memory": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def _promotion_decision_template(candidate_id: str, feedback_id: str, generated_at: str) -> dict[str, Any]:
    return {
        "decision_id": _safe_id("promotion-template-acceptance-feedback", candidate_id, generated_at),
        "candidate_id": candidate_id,
        "source_feedback_ids": [feedback_id],
        "decision": "pending",
        "review_mode": "explicit_operator_decision_required",
        "template_only": True,
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def _claim_boundaries(event: dict[str, Any]) -> dict[str, str]:
    source = _dict(event.get("claim_boundaries"))
    return {
        "human_acceptance": source.get("human_acceptance", event.get("acceptance_decision", "unknown")),
        "business_validation": "not_validated",
        "provider_success": "not_claimed",
        "durable_memory_runtime": "not_implemented",
        "company_kb_promotion": "not_performed",
        "memory_promotion": "not_performed",
    }


def _non_claims() -> list[str]:
    return [
        "not new human acceptance",
        "not business validation",
        "not promoted memory",
        "not durable memory",
        "not Company KB promotion",
        "not provider success",
    ]


def _safe_id(*parts: str) -> str:
    raw = ":".join(parts)
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
        raise ValueError("production memory acceptance feedback candidate contains unsafe path, media reference, provider URL, or secret")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


__all__ = (
    "ACCEPTANCE_FEEDBACK_CANDIDATE_PACKET_KIND",
    "build_acceptance_feedback_candidate_packet",
    "load_acceptance_feedback_event",
    "render_acceptance_feedback_candidate_markdown",
    "write_acceptance_feedback_candidate_packet",
)
