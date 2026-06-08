from __future__ import annotations

from typing import Any

from agentflow.harness.constants import AGENTFLOW_VALIDATION_SCHEMA_VERSION, FAILED, PASSED
from agentflow.memory.promotion_checks import (
    DURABLE_MEMORY_CLAIM_FIELDS,
    EVIDENCE_REUSE_REQUIRED_RUNTIME_REFS,
    PROMOTION_DECISION_STATUSES,
    evidence_reuse_review_checks,
    memory_promotion_review_checks,
)

SCHEMA_VERSION = AGENTFLOW_VALIDATION_SCHEMA_VERSION


def validate_memory_promotion_review(
    *,
    memory_candidate: dict[str, Any],
    memory_promotion_decision: dict[str, Any],
) -> dict[str, Any]:
    """Validate a candidate-to-decision review artifact without durable writes."""
    checks = memory_promotion_review_checks(
        memory_candidate=memory_candidate,
        memory_promotion_decision=memory_promotion_decision,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "agentflow_memory_promotion_review_validation",
        "review_scope": "memory_candidate_promotion_decision",
        "runtime_status": "not_implemented",
        "does_not_execute": True,
        "writes_long_term_memory": False,
        "memory_candidate_id": memory_candidate.get("candidate_id"),
        "memory_promotion_decision_id": memory_promotion_decision.get("decision_id"),
        "decision": memory_promotion_decision.get("decision"),
        "overall_status": FAILED if any(check["status"] == FAILED for check in checks) else PASSED,
        "checks": checks,
    }


def validate_evidence_reuse_review(
    *,
    evidence_reuse_review: dict[str, Any],
    memory_candidate: dict[str, Any],
    memory_promotion_decision: dict[str, Any],
) -> dict[str, Any]:
    """Validate a trace-only evidence reuse review without writing memory."""
    checks = evidence_reuse_review_checks(
        evidence_reuse_review=evidence_reuse_review,
        memory_candidate=memory_candidate,
        memory_promotion_decision=memory_promotion_decision,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "agentflow_memory_evidence_reuse_review_validation",
        "review_scope": evidence_reuse_review.get("review_scope"),
        "runtime_status": "not_implemented",
        "does_not_execute": True,
        "writes_long_term_memory": False,
        "review_id": evidence_reuse_review.get("review_id"),
        "memory_candidate_id": memory_candidate.get("candidate_id"),
        "memory_promotion_decision_id": memory_promotion_decision.get("decision_id"),
        "overall_status": FAILED if any(check["status"] == FAILED for check in checks) else PASSED,
        "checks": checks,
    }


__all__ = (
    "DURABLE_MEMORY_CLAIM_FIELDS",
    "EVIDENCE_REUSE_REQUIRED_RUNTIME_REFS",
    "PROMOTION_DECISION_STATUSES",
    "SCHEMA_VERSION",
    "evidence_reuse_review_checks",
    "memory_promotion_review_checks",
    "validate_evidence_reuse_review",
    "validate_memory_promotion_review",
)
