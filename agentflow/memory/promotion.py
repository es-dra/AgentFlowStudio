from __future__ import annotations

from typing import Any

from agentflow.harness.constants import AGENTFLOW_VALIDATION_SCHEMA_VERSION, FAILED, PASSED

SCHEMA_VERSION = AGENTFLOW_VALIDATION_SCHEMA_VERSION
PROMOTION_DECISION_STATUSES = frozenset({"promoted", "rejected", "merged", "expired"})
DURABLE_MEMORY_CLAIM_FIELDS = frozenset(
    {
        "durable_memory_ref",
        "durable_memory_refs",
        "long_term_memory_ref",
        "long_term_memory_refs",
        "memory_store_ref",
        "memory_store_refs",
        "persisted_memory_id",
        "persisted_memory_ids",
    }
)


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


def memory_promotion_review_checks(
    *,
    memory_candidate: dict[str, Any],
    memory_promotion_decision: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        _check(
            "promotion_decision_links_candidate",
            _non_empty_str(memory_candidate.get("candidate_id"))
            and memory_promotion_decision.get("source_candidate_id") == memory_candidate.get("candidate_id"),
            "promotion decision references the memory candidate",
        ),
        _check(
            "promotion_decision_status_supported",
            memory_promotion_decision.get("decision") in PROMOTION_DECISION_STATUSES,
            "promotion decision uses a supported reviewed decision status",
        ),
        _check(
            "promotion_decision_is_reviewed",
            memory_promotion_decision.get("promotion_mode") == "human_reviewed",
            "promotion decision is human reviewed",
        ),
        _check(
            "promotion_decision_has_evidence_refs",
            _non_empty_string_list(memory_promotion_decision.get("evidence_refs")),
            "promotion decision preserves evidence references",
        ),
        _check(
            "promotion_decision_preserves_candidate_evidence",
            _contains_all_values(
                memory_promotion_decision.get("evidence_refs"),
                memory_candidate.get("evidence_refs"),
            ),
            "promotion decision includes the candidate evidence references",
        ),
        _check(
            "promotion_decision_does_not_write_memory",
            memory_promotion_decision.get("writes_long_term_memory") is False,
            "promotion decision does not write long-term memory",
        ),
        _check(
            "promotion_decision_no_durable_memory_claims",
            not any(field in memory_promotion_decision for field in DURABLE_MEMORY_CLAIM_FIELDS),
            "promotion decision does not claim persisted or durable memory refs",
        ),
    ]


def _non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _non_empty_string_list(values: Any) -> bool:
    return isinstance(values, list) and bool(values) and all(_non_empty_str(value) for value in values)


def _contains_all_values(values: Any, expected_values: Any) -> bool:
    if not _non_empty_string_list(values) or not _non_empty_string_list(expected_values):
        return False
    return set(expected_values) <= set(values)


def _check(check_id: str, passed: bool, message: str) -> dict[str, str]:
    return {"check_id": check_id, "status": PASSED if passed else FAILED, "message": message}


__all__ = (
    "DURABLE_MEMORY_CLAIM_FIELDS",
    "PROMOTION_DECISION_STATUSES",
    "SCHEMA_VERSION",
    "memory_promotion_review_checks",
    "validate_memory_promotion_review",
)
