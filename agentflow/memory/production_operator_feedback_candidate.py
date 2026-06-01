from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow.memory.production_operator_feedback import OPERATOR_FEEDBACK_EVENT_KIND
from narratocut.utils import write_json

OPERATOR_FEEDBACK_CANDIDATE_PACKET_KIND = "agentflow_production_memory_operator_feedback_candidate_packet"
UNSAFE_EXTRA_FRAGMENTS = (
    "http://",
    "https://",
    "file://",
    "data:image/",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
)


def load_operator_feedback_event(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("operator feedback event must be a JSON object")
    return payload


def build_operator_feedback_candidate_packet(
    event: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    """Draft a candidate-only memory packet from an operator feedback event."""
    _validate_event(event)
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise ValueError("generated_at is required")

    feedback_id = str(event["feedback_id"])
    candidate = _memory_candidate(event, generated_at)
    promotion_template = _promotion_decision_template(candidate["candidate_id"], feedback_id, generated_at)
    packet = {
        "kind": OPERATOR_FEEDBACK_CANDIDATE_PACKET_KIND,
        "artifact_type": OPERATOR_FEEDBACK_CANDIDATE_PACKET_KIND,
        "schema_version": event.get("schema_version", SCHEMA_VERSION),
        "packet_id": _safe_id("operator-feedback-candidate", feedback_id, generated_at),
        "generated_at": generated_at,
        "candidate_generation_status": "candidate_only",
        "source_feedback_event_id": feedback_id,
        "source_operator_loop_id": event.get("source_operator_loop_id", "unknown"),
        "source_project_id": event.get("source_project_id", "unknown"),
        "source_target_node_id": event.get("target_node_id", "unknown"),
        "source_target_node_status": event.get("target_node_status", "unknown"),
        "source_target_artifact_type": event.get("target_artifact_type", "operator_loop_node"),
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "feedback_is_memory": False,
        "candidate_is_promoted_memory": False,
        "memory_candidate": candidate,
        "promotion_decision_template": promotion_template,
        "claim_boundaries": _claim_boundaries(),
        "non_claims": _non_claims(),
    }
    _reject_unsafe(packet)
    return packet


def write_operator_feedback_candidate_packet(packet: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "operator_feedback_candidate_packet.json", packet)
    candidate_path = write_json(output_root / "memory_candidate.json", packet["memory_candidate"])
    template_path = write_json(output_root / "promotion_decision_template.json", packet["promotion_decision_template"])
    md_path = output_root / "operator_feedback_candidate_packet.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_operator_feedback_candidate_markdown(packet), encoding="utf-8")
    return [json_path, candidate_path, template_path, md_path]


def render_operator_feedback_candidate_markdown(packet: dict[str, Any]) -> str:
    candidate = _dict(packet.get("memory_candidate"))
    template = _dict(packet.get("promotion_decision_template"))
    boundaries = _dict(packet.get("claim_boundaries"))
    return "\n".join(
        [
            "# Production Memory Operator Feedback Candidate Packet",
            "",
            f"Status: {packet.get('candidate_generation_status', 'unknown')}",
            f"Candidate: {candidate.get('candidate_id', 'unknown')}",
            f"Candidate status: {candidate.get('status', 'unknown')}",
            f"Promotion decision: {template.get('decision', 'unknown')}",
            "Provider calls: not started",
            "Writes long-term memory: false",
            "Writes Company KB: false",
            f"Human acceptance: {boundaries.get('human_acceptance', 'not_claimed')}",
            "",
            "## Candidate Statement",
            str(candidate.get("statement", "")),
            "",
        ]
    )


def _validate_event(event: dict[str, Any]) -> None:
    if event.get("kind") != OPERATOR_FEEDBACK_EVENT_KIND:
        raise ValueError(f"operator feedback candidate requires kind {OPERATOR_FEEDBACK_EVENT_KIND}")
    if not isinstance(event.get("feedback_id"), str) or not event["feedback_id"].strip():
        raise ValueError("operator feedback candidate requires feedback_id")
    if event.get("status") != "evidence_only":
        raise ValueError("operator feedback candidate requires evidence_only feedback")
    if event.get("provider_mode") != "no-provider":
        raise ValueError("operator feedback candidate requires no-provider feedback")
    if event.get("provider_calls_started") is not False:
        raise ValueError("operator feedback candidate requires provider_calls_started false")
    if event.get("writes_long_term_memory") is not False:
        raise ValueError("operator feedback candidate requires writes_long_term_memory false")
    if event.get("writes_company_kb") is not False:
        raise ValueError("operator feedback candidate requires writes_company_kb false")
    if event.get("feedback_is_memory") is not False:
        raise ValueError("operator feedback candidate requires feedback_is_memory false")
    if event.get("creates_memory_candidate") is not False:
        raise ValueError("operator feedback candidate requires original event to create no memory candidate")
    if event.get("creates_promotion_decision") is not False:
        raise ValueError("operator feedback candidate requires original event to create no promotion decision")
    _reject_unsafe(event)


def _memory_candidate(event: dict[str, Any], generated_at: str) -> dict[str, Any]:
    feedback_id = str(event["feedback_id"])
    decision = str(event.get("decision", "note"))
    status = "candidate" if decision == "accepted" else "blocked"
    return {
        "candidate_id": _safe_id("memory-candidate-operator-feedback", feedback_id, generated_at),
        "status": status,
        "scope": "project",
        "source_feedback_ids": [feedback_id],
        "source_operator_loop_id": event.get("source_operator_loop_id", "unknown"),
        "target_ref": f"operator-node:{event.get('target_node_id', 'unknown')}",
        "target_status": event.get("target_node_status", "unknown"),
        "target_artifact_type": event.get("target_artifact_type", "operator_loop_node"),
        "statement": event.get("summary", ""),
        "candidate_is_promoted_memory": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def _promotion_decision_template(candidate_id: str, feedback_id: str, generated_at: str) -> dict[str, Any]:
    return {
        "decision_id": _safe_id("promotion-template-operator-feedback", candidate_id, generated_at),
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


def _claim_boundaries() -> dict[str, str]:
    return {
        "human_acceptance": "not_claimed",
        "business_validation": "not_validated",
        "provider_success": "not_attempted",
        "durable_memory_runtime": "not_implemented",
        "company_kb_promotion": "not_performed",
    }


def _non_claims() -> list[str]:
    return [
        "operator feedback remains evidence",
        "not promoted memory",
        "not human acceptance",
        "not business validation",
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


def _reject_unsafe(value: Any) -> None:
    raw = json.dumps(value, ensure_ascii=False).lower()
    fragments = AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS + UNSAFE_EXTRA_FRAGMENTS
    if any(fragment.lower() in raw for fragment in fragments):
        raise ValueError("production memory operator feedback candidate contains unsafe path, media reference, provider URL, or secret")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


__all__ = (
    "OPERATOR_FEEDBACK_CANDIDATE_PACKET_KIND",
    "build_operator_feedback_candidate_packet",
    "load_operator_feedback_event",
    "render_operator_feedback_candidate_markdown",
    "write_operator_feedback_candidate_packet",
)
