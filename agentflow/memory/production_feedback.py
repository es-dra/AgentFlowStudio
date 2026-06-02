from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.memory.production_loop import KIND, SCHEMA_VERSION
from narratocut.utils import write_json

FEEDBACK_CAPTURE_KIND = "agentflow_production_memory_feedback_capture"
SUPPORTED_FEEDBACK_DECISIONS = frozenset({"accepted", "rejected", "needs_revision", "note"})
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


def build_production_memory_feedback_capture(
    payload: dict[str, Any],
    *,
    target_ref: str,
    decision: str,
    summary: str,
    reviewer_role: str,
    created_at: str,
) -> dict[str, Any]:
    """Draft feedback, candidate memory, and a pending promotion decision template."""
    _validate_loop(payload)
    _validate_text_inputs(target_ref, decision, summary, reviewer_role, created_at)
    target = _artifact_by_ref(payload, target_ref)
    if target is None:
        raise ValueError(f"target_ref does not exist in artifact_ledger: {target_ref}")

    feedback_id = _safe_id("feedback", target_ref, created_at)
    candidate_id = _safe_id("memory:candidate", target_ref, created_at)
    decision_id = _safe_id("promotion:template", target_ref, created_at)
    feedback_event = _feedback_event(feedback_id, target_ref, decision, summary, reviewer_role, created_at)
    memory_candidate = _memory_candidate(candidate_id, feedback_id, decision, summary, target)
    promotion_template = _promotion_decision_template(decision_id, candidate_id, feedback_id)
    capture = {
        "kind": FEEDBACK_CAPTURE_KIND,
        "artifact_type": FEEDBACK_CAPTURE_KIND,
        "schema_version": SCHEMA_VERSION,
        "source_loop_id": payload.get("loop_id", "unknown"),
        "target_ref": target_ref,
        "provider_mode": "no-provider",
        "execution_status": "draft",
        "does_not_execute": True,
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "feedback_event": feedback_event,
        "memory_candidate": memory_candidate,
        "promotion_decision_template": promotion_template,
        "claim_boundaries": {
            "human_acceptance": "not_reviewed",
            "business_validation": "not_validated",
            "provider_success": "not_attempted",
            "durable_memory_runtime": "not_implemented",
        },
    }
    _reject_unsafe(capture)
    return capture


def write_production_memory_feedback_capture(capture: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    return [
        write_json(output_root / "production_memory_feedback_capture.json", capture),
        write_json(output_root / "feedback_event.json", capture["feedback_event"]),
        write_json(output_root / "memory_candidate.json", capture["memory_candidate"]),
        write_json(output_root / "promotion_decision_template.json", capture["promotion_decision_template"]),
    ]


def _feedback_event(
    feedback_id: str,
    target_ref: str,
    decision: str,
    summary: str,
    reviewer_role: str,
    created_at: str,
) -> dict[str, Any]:
    return {
        "feedback_id": feedback_id,
        "target_ref": target_ref,
        "decision": decision,
        "reviewer_role": reviewer_role,
        "summary": summary,
        "status": "draft",
        "created_at": created_at,
        "writes_long_term_memory": False,
    }


def _memory_candidate(candidate_id: str, feedback_id: str, decision: str, summary: str, target: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "status": "candidate" if decision == "accepted" else "blocked",
        "scope": "project",
        "source_feedback_ids": [feedback_id],
        "statement": summary,
        "target_ref": target.get("ref_id"),
        "target_status": target.get("status", "unknown"),
        "candidate_is_promoted_memory": False,
        "writes_long_term_memory": False,
    }


def _promotion_decision_template(decision_id: str, candidate_id: str, feedback_id: str) -> dict[str, Any]:
    return {
        "decision_id": decision_id,
        "candidate_id": candidate_id,
        "source_feedback_ids": [feedback_id],
        "decision": "pending",
        "review_mode": "explicit_operator_decision_required",
        "template_only": True,
        "writes_long_term_memory": False,
    }


def _validate_loop(payload: dict[str, Any]) -> None:
    if payload.get("kind") != KIND:
        raise ValueError(f"feedback capture requires kind {KIND}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"feedback capture requires schema_version {SCHEMA_VERSION}")


def _validate_text_inputs(target_ref: str, decision: str, summary: str, reviewer_role: str, created_at: str) -> None:
    for label, value in {
        "target_ref": target_ref,
        "summary": summary,
        "reviewer_role": reviewer_role,
        "created_at": created_at,
    }.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is required")
    if decision not in SUPPORTED_FEEDBACK_DECISIONS:
        raise ValueError(f"unsupported feedback decision: {decision}")
    _reject_unsafe({"target_ref": target_ref, "summary": summary, "reviewer_role": reviewer_role})


def _artifact_by_ref(payload: dict[str, Any], target_ref: str) -> dict[str, Any] | None:
    for item in payload.get("artifact_ledger", []):
        if isinstance(item, dict) and item.get("ref_id") == target_ref:
            return item
    return None


def _safe_id(prefix: str, target_ref: str, created_at: str) -> str:
    raw = f"{prefix}:{target_ref}:{created_at}"
    safe = "".join(char.lower() if char.isalnum() else "-" for char in raw).strip("-")
    return safe.replace("--", "-")


def _reject_unsafe(value: Any) -> None:
    raw = json.dumps(value, ensure_ascii=False).lower()
    fragments = AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS + UNSAFE_EXTRA_FRAGMENTS
    if any(fragment.lower() in raw for fragment in fragments):
        raise ValueError("production memory feedback capture contains unsafe path, media reference, provider URL, or secret")


__all__ = (
    "FEEDBACK_CAPTURE_KIND",
    "SUPPORTED_FEEDBACK_DECISIONS",
    "build_production_memory_feedback_capture",
    "write_production_memory_feedback_capture",
)
