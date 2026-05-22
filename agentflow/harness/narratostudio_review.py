from __future__ import annotations

from typing import Any

from agentflow.harness.constants import (
    AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS,
    AGENTFLOW_VALIDATION_SCHEMA_VERSION,
    FAILED,
    PASSED,
)

SCHEMA_VERSION = AGENTFLOW_VALIDATION_SCHEMA_VERSION
FORBIDDEN_REVIEW_FRAGMENTS = AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS


def validate_narratostudio_asset_feedback_review(review: dict[str, Any]) -> dict[str, Any]:
    """Validate a NarratoStudio asset-feedback review artifact without executing work."""
    source_validation = review.get("source_validation")
    asset_memory_validation = review.get("asset_memory_validation")
    source_status = _overall_status(source_validation)
    asset_memory_status = _overall_status(asset_memory_validation)
    checks = [
        _check(
            "schema_version_0_1_0",
            review.get("schema_version") == SCHEMA_VERSION,
            "review uses schema_version 0.1.0",
        ),
        _check(
            "artifact_type_review",
            review.get("artifact_type") == "agentflow_narratostudio_asset_feedback_review",
            "artifact_type is agentflow_narratostudio_asset_feedback_review",
        ),
        _check(
            "validation_scope_review",
            review.get("validation_scope") == "narratostudio_asset_feedback_loop",
            "validation_scope is narratostudio_asset_feedback_loop",
        ),
        _check(
            "review_not_runtime",
            review.get("runtime_status") == "not_implemented",
            "review does not claim runtime implementation",
        ),
        _check(
            "review_does_not_execute",
            review.get("does_not_execute") is True,
            "review does not execute workflows or tasks",
        ),
        _check(
            "review_does_not_write_memory",
            review.get("writes_long_term_memory") is False,
            "review does not write long-term memory",
        ),
        _check(
            "source_validation_embedded",
            isinstance(source_validation, dict)
            and source_validation.get("artifact_type")
            == "agentflow_narratostudio_asset_feedback_source_validation",
            "review embeds NarratoStudio source validation",
        ),
        _check(
            "asset_memory_validation_embedded",
            isinstance(asset_memory_validation, dict)
            and asset_memory_validation.get("artifact_type") == "agentflow_asset_memory_validation",
            "review embeds AgentFlow asset-memory validation",
        ),
        _check(
            "asset_memory_step_matches_validation",
            review.get("asset_memory_step_status") == asset_memory_status,
            "asset_memory_step_status matches embedded asset-memory validation",
        ),
        _check(
            "failed_source_skips_asset_memory_step",
            source_status == PASSED or review.get("asset_memory_step_status") == "not_run",
            "failed source validation skips asset-memory adaptation",
        ),
        _check(
            "overall_status_matches_steps",
            _review_status_matches_steps(review.get("overall_status"), source_status, asset_memory_status),
            "overall_status matches source and asset-memory validation statuses",
        ),
        _check(
            "no_private_paths_or_secrets",
            _contains_no_forbidden_fragments(review),
            "review artifact does not include private paths, generated media, run outputs, or secrets",
        ),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "agentflow_narratostudio_asset_feedback_review_validation",
        "validation_scope": "narratostudio_asset_feedback_review",
        "runtime_status": "not_implemented",
        "does_not_execute": True,
        "writes_long_term_memory": False,
        "handoff_id": review.get("handoff_id"),
        "run_id": review.get("run_id"),
        "overall_status": FAILED if any(check["status"] == FAILED for check in checks) else PASSED,
        "checks": checks,
    }


def _overall_status(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return None
    return payload.get("overall_status")


def _review_status_matches_steps(overall_status: Any, source_status: Any, asset_memory_status: Any) -> bool:
    if source_status != PASSED:
        return overall_status == FAILED
    return overall_status == asset_memory_status


def _contains_no_forbidden_fragments(payload: Any) -> bool:
    raw_text = str(payload).lower()
    return not any(fragment.lower() in raw_text for fragment in FORBIDDEN_REVIEW_FRAGMENTS)


def _check(check_id: str, passed: bool, message: str) -> dict[str, str]:
    return {"check_id": check_id, "status": PASSED if passed else FAILED, "message": message}


__all__ = (
    "FORBIDDEN_REVIEW_FRAGMENTS",
    "SCHEMA_VERSION",
    "validate_narratostudio_asset_feedback_review",
)
