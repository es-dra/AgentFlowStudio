from __future__ import annotations

from typing import Any

from agentflow.harness.constants import (
    AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS,
    AGENTFLOW_VALIDATION_SCHEMA_VERSION,
    FAILED,
    PASSED,
)
from agentflow.memory.promotion import PROMOTION_DECISION_STATUSES, memory_promotion_review_checks

SCHEMA_VERSION = AGENTFLOW_VALIDATION_SCHEMA_VERSION
FORBIDDEN_ASSET_MEMORY_FRAGMENTS = AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS


def validate_asset_memory_contract_set(
    *,
    intermediate_asset: dict[str, Any],
    reusable_asset_profile: dict[str, Any],
    asset_reuse_decision: dict[str, Any],
    memory_candidate: dict[str, Any],
    memory_promotion_decision: dict[str, Any],
) -> dict[str, Any]:
    """Validate asset/memory contract artifacts without executing runtime behavior."""
    checks = [
        _check(
            "schema_version_0_1_0",
            _all_schema_version_0_1_0(
                intermediate_asset,
                reusable_asset_profile,
                asset_reuse_decision,
                memory_candidate,
                memory_promotion_decision,
            ),
            "all asset and memory artifacts use schema_version 0.1.0",
        ),
        _check(
            "intermediate_asset_type",
            intermediate_asset.get("artifact_type") == "agentflow_intermediate_asset",
            "intermediate asset artifact_type is agentflow_intermediate_asset",
        ),
        _check(
            "reusable_profile_type",
            reusable_asset_profile.get("artifact_type") == "agentflow_reusable_asset_profile",
            "reusable asset profile artifact_type is agentflow_reusable_asset_profile",
        ),
        _check(
            "asset_reuse_decision_type",
            asset_reuse_decision.get("artifact_type") == "agentflow_asset_reuse_decision",
            "asset reuse decision artifact_type is agentflow_asset_reuse_decision",
        ),
        _check(
            "memory_candidate_type",
            memory_candidate.get("artifact_type") == "agentflow_memory_candidate",
            "memory candidate artifact_type is agentflow_memory_candidate",
        ),
        _check(
            "promotion_decision_type",
            memory_promotion_decision.get("artifact_type") == "agentflow_memory_promotion_decision",
            "memory promotion decision artifact_type is agentflow_memory_promotion_decision",
        ),
        _check(
            "intermediate_asset_candidate_only",
            intermediate_asset.get("reuse_status") == "candidate",
            "intermediate asset remains a candidate",
        ),
        _check(
            "intermediate_asset_has_sources",
            _non_empty_string_list(intermediate_asset.get("source_artifact_refs")),
            "intermediate asset declares source artifact references",
        ),
        _check(
            "intermediate_asset_has_evidence",
            _non_empty_string_list(intermediate_asset.get("evidence_refs")),
            "intermediate asset declares evidence references",
        ),
        _check(
            "memory_candidate_candidate_only",
            memory_candidate.get("promotion_status") == "candidate",
            "memory candidate is candidate-only",
        ),
        _check(
            "memory_candidate_uses_raw_feedback_source",
            memory_candidate.get("source_of_truth") == "feedback.jsonl",
            "memory candidate keeps feedback.jsonl as source of truth",
        ),
        *memory_promotion_review_checks(
            memory_candidate=memory_candidate,
            memory_promotion_decision=memory_promotion_decision,
        ),
        _check(
            "reusable_profile_links_intermediate_asset",
            _contains_value(
                reusable_asset_profile.get("source_intermediate_asset_ids"),
                intermediate_asset.get("asset_id"),
            ),
            "reusable asset profile links the source intermediate asset",
        ),
        _check(
            "reusable_profile_has_promotion_ref",
            _non_empty_str(reusable_asset_profile.get("promotion_decision_ref")),
            "reusable asset profile references a promotion decision",
        ),
        _check(
            "reusable_profile_links_promotion_decision",
            reusable_asset_profile.get("promotion_decision_ref")
            == f"agentflow_memory_promotion_decision:{memory_promotion_decision.get('decision_id')}",
            "reusable asset profile references the provided promotion decision",
        ),
        _check(
            "reusable_profile_has_policy",
            isinstance(reusable_asset_profile.get("reuse_policy"), dict)
            and bool(reusable_asset_profile.get("reuse_policy")),
            "reusable asset profile declares a reuse policy",
        ),
        _check(
            "asset_reuse_decision_selects_profile",
            _contains_value(
                asset_reuse_decision.get("selected_asset_profile_ids"),
                reusable_asset_profile.get("asset_profile_id"),
            ),
            "asset reuse decision selects the reusable asset profile",
        ),
        _check(
            "asset_reuse_decision_has_reason",
            _non_empty_str(asset_reuse_decision.get("reason")),
            "asset reuse decision declares a reason",
        ),
        _check(
            "asset_reuse_decision_only",
            asset_reuse_decision.get("does_not_execute") is True,
            "asset reuse decision does not execute tasks or workflows",
        ),
        _check(
            "no_private_paths_or_secrets",
            _contains_no_forbidden_fragments(
                intermediate_asset,
                reusable_asset_profile,
                asset_reuse_decision,
                memory_candidate,
                memory_promotion_decision,
            ),
            "asset and memory artifacts do not include private paths, generated media, run outputs, or secrets",
        ),
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "agentflow_asset_memory_validation",
        "validation_scope": "asset_memory_contract_set",
        "runtime_status": "not_implemented",
        "does_not_execute": True,
        "writes_long_term_memory": False,
        "intermediate_asset_id": intermediate_asset.get("asset_id"),
        "asset_profile_id": reusable_asset_profile.get("asset_profile_id"),
        "asset_reuse_decision_id": asset_reuse_decision.get("decision_id"),
        "memory_candidate_id": memory_candidate.get("candidate_id"),
        "memory_promotion_decision_id": memory_promotion_decision.get("decision_id"),
        "overall_status": FAILED if any(check["status"] == FAILED for check in checks) else PASSED,
        "checks": checks,
    }


def _all_schema_version_0_1_0(*payloads: dict[str, Any]) -> bool:
    return all(payload.get("schema_version") == SCHEMA_VERSION for payload in payloads)


def _non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _non_empty_string_list(values: Any) -> bool:
    return isinstance(values, list) and bool(values) and all(_non_empty_str(value) for value in values)


def _contains_value(values: Any, expected: Any) -> bool:
    return _non_empty_str(expected) and isinstance(values, list) and expected in values


def _contains_no_forbidden_fragments(*payloads: Any) -> bool:
    raw_text = " ".join(str(payload).lower() for payload in payloads)
    return not any(fragment.lower() in raw_text for fragment in FORBIDDEN_ASSET_MEMORY_FRAGMENTS)


def _check(check_id: str, passed: bool, message: str) -> dict[str, str]:
    return {"check_id": check_id, "status": PASSED if passed else FAILED, "message": message}


__all__ = (
    "FORBIDDEN_ASSET_MEMORY_FRAGMENTS",
    "PROMOTION_DECISION_STATUSES",
    "SCHEMA_VERSION",
    "validate_asset_memory_contract_set",
)
