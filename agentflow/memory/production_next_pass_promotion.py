from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from agentflow.memory.production_loop import (
    SCHEMA_VERSION,
    build_production_memory_loop_run,
    write_production_memory_loop_run,
)
from agentflow.memory import production_next_pass_promotion_records as records
from narratocut.utils import write_json

NEXT_PASS_PROMOTION_DECISION_KIND = "agentflow_production_memory_next_pass_promotion_decision"
NEXT_PASS_PROMOTION_OVERLAY_KIND = "agentflow_production_memory_next_pass_promotion_overlay"
REVIEWED_NEXT_PASS_DECISIONS = frozenset({"promoted", "merged", "rejected", "expired", "blocked"})


def load_next_pass_review(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("next pass review must be a JSON object")
    return payload


def load_next_pass_promotion_decision(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("next pass promotion decision must be a JSON object")
    return payload


def build_next_pass_promotion_decision(
    review: dict[str, Any],
    *,
    candidate_id: str,
    decision: str,
    rationale: str,
    reviewer_role: str,
    decided_at: str,
) -> dict[str, Any]:
    """Record an explicit operator decision for one next-pass feedback candidate."""
    records.validate_review(review)
    records.validate_review_inputs(
        candidate_id,
        decision,
        rationale,
        reviewer_role,
        decided_at,
        REVIEWED_NEXT_PASS_DECISIONS,
    )
    candidate = records.candidate_by_id(review, candidate_id)
    source_feedback_ids = records.candidate_source_feedback_ids(candidate)

    promotion_decision = {
        "kind": NEXT_PASS_PROMOTION_DECISION_KIND,
        "artifact_type": NEXT_PASS_PROMOTION_DECISION_KIND,
        "schema_version": review.get("schema_version", SCHEMA_VERSION),
        "decision_id": _safe_id("promotion:next-pass-reviewed", candidate_id, decided_at),
        "candidate_id": candidate_id,
        "source_candidate_id": candidate_id,
        "source_feedback_ids": source_feedback_ids,
        "decision": decision,
        "review_mode": "explicit_operator_decision",
        "reviewer_role": reviewer_role,
        "rationale": rationale,
        "decided_at": decided_at,
        "template_only": False,
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "source_review_id": review.get("review_id", "unknown"),
        "source_task_packet_id": review.get("source_task_packet_id", "unknown"),
        "source_result_id": review.get("source_result_id", "unknown"),
        "claim_boundaries": {
            "human_acceptance": "not_reviewed",
            "business_validation": "not_validated",
            "provider_success": "not_attempted",
            "durable_memory_runtime": "not_implemented",
            "company_kb_promotion": "not_performed",
        },
    }
    records.reject_unsafe_next_pass_promotion(promotion_decision)
    return promotion_decision


def build_loop_with_next_pass_reviewed_feedback(
    payload: dict[str, Any],
    review: dict[str, Any],
    promotion_decision: dict[str, Any],
) -> dict[str, Any]:
    """Overlay one reviewed next-pass feedback candidate onto a source loop."""
    records.validate_loop(payload)
    records.validate_review(review)
    records.validate_promotion_decision(
        review,
        promotion_decision,
        kind=NEXT_PASS_PROMOTION_DECISION_KIND,
        supported_decisions=REVIEWED_NEXT_PASS_DECISIONS,
    )

    derived = deepcopy(payload)
    candidate = records.candidate_by_id(review, str(promotion_decision["candidate_id"]))
    feedback_by_id = records.feedback_events_by_id(review)
    output_by_ref = records.output_artifacts_by_ref(review)

    for ref_id in records.feedback_target_refs(candidate, feedback_by_id):
        records.append_unique(derived["artifact_ledger"], records.artifact_record(output_by_ref, ref_id), "ref_id")
    for feedback_id in records.candidate_source_feedback_ids(candidate):
        records.append_unique(derived["feedback_events"], records.feedback_record(feedback_by_id, feedback_id), "feedback_id")
    records.append_unique(derived["memory_candidates"], records.memory_candidate_record(candidate, review), "candidate_id")
    records.append_unique(derived["promotion_decisions"], deepcopy(promotion_decision), "decision_id")

    requested_refs = records.requested_refs(derived)
    candidate_id = str(promotion_decision["candidate_id"])
    if candidate_id not in requested_refs:
        requested_refs.append(candidate_id)

    records.reject_unsafe_next_pass_promotion(derived)
    return derived


def build_next_pass_reviewed_feedback_run(
    payload: dict[str, Any],
    review: dict[str, Any],
    promotion_decision: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    derived_loop = build_loop_with_next_pass_reviewed_feedback(payload, review, promotion_decision)
    run = build_production_memory_loop_run(derived_loop)
    overlay = build_next_pass_promotion_overlay(review, promotion_decision, run)
    return derived_loop, run, overlay


def build_next_pass_promotion_overlay(
    review: dict[str, Any],
    promotion_decision: dict[str, Any],
    run: dict[str, Any],
) -> dict[str, Any]:
    records.validate_review(review)
    records.validate_promotion_decision(
        review,
        promotion_decision,
        kind=NEXT_PASS_PROMOTION_DECISION_KIND,
        supported_decisions=REVIEWED_NEXT_PASS_DECISIONS,
    )
    candidate_id = str(promotion_decision["candidate_id"])
    included_ids = {str(ref.get("ref_id")) for ref in records.value_list(run["context_bundle"].get("included_refs"))}
    blocked_ids = {str(ref.get("ref_id")) for ref in records.value_list(run["context_bundle"].get("blocked_refs"))}
    return {
        "kind": NEXT_PASS_PROMOTION_OVERLAY_KIND,
        "artifact_type": NEXT_PASS_PROMOTION_OVERLAY_KIND,
        "schema_version": review.get("schema_version", SCHEMA_VERSION),
        "source_review_id": review.get("review_id", "unknown"),
        "source_decision_id": promotion_decision.get("decision_id", "unknown"),
        "candidate_id": candidate_id,
        "decision": promotion_decision.get("decision", "unknown"),
        "decision_effect": "included_in_context" if candidate_id in included_ids else "blocked_from_context",
        "candidate_included_in_context": candidate_id in included_ids,
        "candidate_blocked_from_context": candidate_id in blocked_ids,
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "run_readiness": run["pass_readiness"].get("overall_status", "unknown"),
        "context_bundle_id": run["context_bundle"].get("bundle_id", "unknown"),
        "non_claims": [
            "not human acceptance",
            "not business validation",
            "not durable memory",
            "not provider success",
            "not Company KB promotion",
        ],
    }


def write_next_pass_promotion_decision(decision: dict[str, Any], output_dir: str | Path) -> list[Path]:
    return [write_json(Path(output_dir) / "next_pass_promotion_decision.json", decision)]


def write_next_pass_reviewed_feedback_run(
    derived_loop: dict[str, Any],
    run: dict[str, Any],
    overlay: dict[str, Any],
    output_dir: str | Path,
) -> list[Path]:
    output_root = Path(output_dir)
    written_paths = [write_json(output_root / "derived_production_memory_loop.json", derived_loop)]
    written_paths.extend(write_production_memory_loop_run(run, output_root))
    written_paths.append(write_json(output_root / "next_pass_promotion_overlay.json", overlay))
    return written_paths


def _safe_id(prefix: str, target_ref: str, created_at: str) -> str:
    raw = f"{prefix}:{target_ref}:{created_at}"
    safe = "".join(char.lower() if char.isalnum() else "-" for char in raw).strip("-")
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe


__all__ = (
    "NEXT_PASS_PROMOTION_DECISION_KIND",
    "NEXT_PASS_PROMOTION_OVERLAY_KIND",
    "REVIEWED_NEXT_PASS_DECISIONS",
    "build_loop_with_next_pass_reviewed_feedback",
    "build_next_pass_promotion_decision",
    "build_next_pass_promotion_overlay",
    "build_next_pass_reviewed_feedback_run",
    "load_next_pass_promotion_decision",
    "load_next_pass_review",
    "write_next_pass_promotion_decision",
    "write_next_pass_reviewed_feedback_run",
)
