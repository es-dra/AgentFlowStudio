from __future__ import annotations

from typing import Any

from agentflow.harness.constants import (
    AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS,
    AGENTFLOW_VALIDATION_SCHEMA_VERSION,
    FAILED,
    PASSED,
)

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
EVIDENCE_REUSE_REQUIRED_RUNTIME_REFS = frozenset(
    {
        "production_memory_loop:run_manifest",
        "production_memory_loop:quality_report",
        "production_memory_loop:review_report",
        "production_memory_loop:package_report",
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


def evidence_reuse_review_checks(
    *,
    evidence_reuse_review: dict[str, Any],
    memory_candidate: dict[str, Any],
    memory_promotion_decision: dict[str, Any],
) -> list[dict[str, str]]:
    runtime_evidence = evidence_reuse_review.get("runtime_evidence")
    feedback_source = evidence_reuse_review.get("feedback_source")
    context_bundle = evidence_reuse_review.get("context_bundle")
    second_pass_prompt = evidence_reuse_review.get("second_pass_prompt")

    runtime_refs = _string_set(_dict(runtime_evidence).get("artifact_refs"))
    feedback_refs = _string_set(_dict(feedback_source).get("evidence_refs"))
    context_candidate_refs = _string_set(_dict(context_bundle).get("source_memory_candidates"))
    context_decision_refs = _string_set(_dict(context_bundle).get("source_promotion_decisions"))
    context_runtime_refs = _string_set(_dict(context_bundle).get("source_runtime_evidence_refs"))
    prompt_memory_refs = _string_set(_dict(second_pass_prompt).get("memory_refs"))
    prompt_decision_refs = _string_set(_dict(second_pass_prompt).get("promotion_decision_refs"))
    context_bundle_id = _dict(context_bundle).get("bundle_id")

    return [
        *memory_promotion_review_checks(
            memory_candidate=memory_candidate,
            memory_promotion_decision=memory_promotion_decision,
        ),
        _check(
            "evidence_reuse_review_type",
            evidence_reuse_review.get("artifact_type") == "agentflow_memory_evidence_reuse_review",
            "evidence reuse review artifact_type is agentflow_memory_evidence_reuse_review",
        ),
        _check(
            "evidence_reuse_scope_production_memory",
            evidence_reuse_review.get("review_scope") == "production_memory_evidence_reuse",
            "evidence reuse review is scoped to Production Memory",
        ),
        _check(
            "evidence_reuse_review_only",
            evidence_reuse_review.get("runtime_status") == "not_implemented"
            and evidence_reuse_review.get("does_not_execute") is True,
            "evidence reuse review is review-only",
        ),
        _check(
            "evidence_reuse_no_long_term_write",
            evidence_reuse_review.get("writes_long_term_memory") is False,
            "evidence reuse review does not write long-term memory",
        ),
        _check(
            "runtime_evidence_refs_required_reports",
            EVIDENCE_REUSE_REQUIRED_RUNTIME_REFS <= runtime_refs,
            "runtime evidence references run, quality, review, and package reports",
        ),
        _check(
            "feedback_source_refs_runtime_evidence",
            bool(feedback_refs) and feedback_refs <= runtime_refs,
            "feedback source references runtime evidence",
        ),
        _check(
            "memory_candidate_ref_matches",
            evidence_reuse_review.get("memory_candidate_ref") == memory_candidate.get("candidate_id"),
            "evidence reuse review references the memory candidate",
        ),
        _check(
            "promotion_decision_ref_matches",
            evidence_reuse_review.get("promotion_decision_ref") == memory_promotion_decision.get("decision_id"),
            "evidence reuse review references the promotion decision",
        ),
        _check(
            "promotion_decision_allows_context_reuse",
            memory_promotion_decision.get("decision") in {"promoted", "merged"},
            "promotion decision allows downstream context reuse",
        ),
        _check(
            "context_bundle_refs_memory_candidate",
            _contains_value(context_candidate_refs, memory_candidate.get("candidate_id")),
            "context bundle references the memory candidate",
        ),
        _check(
            "context_bundle_refs_promotion_decision",
            _contains_value(context_decision_refs, memory_promotion_decision.get("decision_id")),
            "context bundle references the promotion decision",
        ),
        _check(
            "context_bundle_refs_runtime_evidence",
            EVIDENCE_REUSE_REQUIRED_RUNTIME_REFS <= context_runtime_refs,
            "context bundle references the runtime evidence used for reuse review",
        ),
        _check(
            "context_reuse_no_long_term_write",
            _dict(context_bundle).get("writes_long_term_memory") is False,
            "context bundle does not write long-term memory",
        ),
        _check(
            "second_pass_prompt_refs_context_bundle",
            _dict(second_pass_prompt).get("context_bundle_ref") == context_bundle_id and _non_empty_str(context_bundle_id),
            "second-pass prompt references the context bundle",
        ),
        _check(
            "second_pass_prompt_refs_memory_candidate",
            _contains_value(prompt_memory_refs, memory_candidate.get("candidate_id")),
            "second-pass prompt references the memory candidate",
        ),
        _check(
            "second_pass_prompt_refs_promotion_decision",
            _contains_value(prompt_decision_refs, memory_promotion_decision.get("decision_id")),
            "second-pass prompt references the promotion decision",
        ),
        _check(
            "second_pass_prompt_no_long_term_write",
            _dict(second_pass_prompt).get("writes_long_term_memory") is False,
            "second-pass prompt does not write long-term memory",
        ),
        _check(
            "human_acceptance_labeled",
            evidence_reuse_review.get("human_acceptance") in {"not_reviewed", "accepted", "rejected", "needs_revision"},
            "human acceptance is labeled separately",
        ),
        _check(
            "business_validation_labeled",
            evidence_reuse_review.get("business_validation") in {"not_validated", "validated", "invalidated"},
            "business validation is labeled separately",
        ),
        _check(
            "quality_improvement_not_claimed",
            evidence_reuse_review.get("quality_improvement_claim") in {"not_claimed", "comparison_required"},
            "quality improvement is not claimed without comparison evidence",
        ),
        _check(
            "evidence_reuse_no_private_paths_or_secrets",
            not any(fragment.lower() in str(evidence_reuse_review).lower() for fragment in AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS),
            "evidence reuse review avoids private paths, generated media paths, and secrets",
        ),
    ]


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


def _contains_value(values: set[str], expected: Any) -> bool:
    return _non_empty_str(expected) and expected in values


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_set(items: Any) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {str(item) for item in items if item}


def _check(check_id: str, passed: bool, message: str) -> dict[str, str]:
    return {"check_id": check_id, "status": PASSED if passed else FAILED, "message": message}


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
