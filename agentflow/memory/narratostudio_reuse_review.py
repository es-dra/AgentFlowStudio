from __future__ import annotations

from typing import Any

from agentflow.harness.constants import AGENTFLOW_VALIDATION_SCHEMA_VERSION, FAILED, PASSED

SCHEMA_VERSION = AGENTFLOW_VALIDATION_SCHEMA_VERSION
BLOCKED = "blocked"
EXPECTED_ARTIFACT_TYPES = {
    "review": "agentflow_narratostudio_asset_feedback_review",
    "validation": "agentflow_narratostudio_asset_feedback_review_validation",
    "gate": "agentflow_narratostudio_asset_feedback_review_gate",
    "dry_run_plan": "agentflow_narratostudio_asset_reuse_dry_run_plan",
}
FORBIDDEN_ACTIONS = [
    "execute_workflow",
    "write_long_term_memory",
    "persist_reusable_asset_profile",
    "call_remote_provider",
]


def review_narratostudio_asset_reuse_dry_run_chain(
    *,
    review: dict[str, Any],
    validation: dict[str, Any],
    gate: dict[str, Any],
    dry_run_plan: dict[str, Any],
) -> dict[str, Any]:
    """Review an existing NarratoStudio asset-reuse dry-run chain without side effects."""
    checks = [
        *_artifact_type_checks(review=review, validation=validation, gate=gate, dry_run_plan=dry_run_plan),
        *_status_checks(review=review, validation=validation, gate=gate, dry_run_plan=dry_run_plan),
        *_boundary_checks(review=review, validation=validation, gate=gate, dry_run_plan=dry_run_plan),
        *_chain_consistency_checks(review=review, validation=validation, gate=gate, dry_run_plan=dry_run_plan),
    ]
    blocking_check_ids = _blocking_check_ids(checks, gate, dry_run_plan)
    overall_status = _overall_status(blocking_check_ids, gate, dry_run_plan)
    is_passed = overall_status == PASSED
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "agentflow_narratostudio_asset_reuse_review",
        "review_scope": "narratostudio_asset_reuse_dry_run_chain",
        "runtime_status": "not_implemented",
        "does_not_execute": True,
        "writes_long_term_memory": False,
        "dry_run_only": True,
        "handoff_id": dry_run_plan.get("handoff_id") or gate.get("handoff_id") or validation.get("handoff_id"),
        "run_id": dry_run_plan.get("run_id") or gate.get("run_id") or validation.get("run_id"),
        "overall_status": overall_status,
        "source_artifact_types": {
            key: payload.get("artifact_type")
            for key, payload in {
                "review": review,
                "validation": validation,
                "gate": gate,
                "dry_run_plan": dry_run_plan,
            }.items()
        },
        "source_statuses": {
            "review": review.get("overall_status"),
            "validation": validation.get("overall_status"),
            "gate": gate.get("gate_status"),
            "dry_run_plan": dry_run_plan.get("plan_status"),
        },
        "selected_asset_profile_ids": dry_run_plan.get("selected_asset_profile_ids", []) if is_passed else [],
        "candidate_reuse_actions": dry_run_plan.get("candidate_reuse_actions", []) if is_passed else [],
        "next_required_human_decisions": dry_run_plan.get("required_human_decisions", []) if is_passed else [],
        "required_pre_execution_reviews": dry_run_plan.get("required_pre_execution_reviews", []),
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "blocking_check_ids": blocking_check_ids,
        "checks": checks,
    }


def _artifact_type_checks(
    *,
    review: dict[str, Any],
    validation: dict[str, Any],
    gate: dict[str, Any],
    dry_run_plan: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        _check(
            "review_artifact_type",
            review.get("artifact_type") == EXPECTED_ARTIFACT_TYPES["review"],
            "source review artifact_type is agentflow_narratostudio_asset_feedback_review",
        ),
        _check(
            "validation_artifact_type",
            validation.get("artifact_type") == EXPECTED_ARTIFACT_TYPES["validation"],
            "source validation artifact_type is agentflow_narratostudio_asset_feedback_review_validation",
        ),
        _check(
            "gate_artifact_type",
            gate.get("artifact_type") == EXPECTED_ARTIFACT_TYPES["gate"],
            "source gate artifact_type is agentflow_narratostudio_asset_feedback_review_gate",
        ),
        _check(
            "dry_run_plan_artifact_type",
            dry_run_plan.get("artifact_type") == EXPECTED_ARTIFACT_TYPES["dry_run_plan"],
            "source dry-run plan artifact_type is agentflow_narratostudio_asset_reuse_dry_run_plan",
        ),
    ]


def _status_checks(
    *,
    review: dict[str, Any],
    validation: dict[str, Any],
    gate: dict[str, Any],
    dry_run_plan: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        _check("review_passed", review.get("overall_status") == PASSED, "source review passed"),
        _check("validation_passed", validation.get("overall_status") == PASSED, "source validation passed"),
        _check("gate_passed", gate.get("gate_status") == PASSED, "source gate passed"),
        _check("dry_run_plan_ready", dry_run_plan.get("plan_status") == "ready", "source dry-run plan is ready"),
    ]


def _boundary_checks(
    *,
    review: dict[str, Any],
    validation: dict[str, Any],
    gate: dict[str, Any],
    dry_run_plan: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        _side_effect_check("review", review),
        _side_effect_check("validation", validation),
        _side_effect_check("gate", gate),
        _side_effect_check("dry_run_plan", dry_run_plan),
        _memory_write_check("review", review),
        _memory_write_check("validation", validation),
        _memory_write_check("gate", gate),
        _memory_write_check("dry_run_plan", dry_run_plan),
        _check(
            "dry_run_plan_dry_run_only",
            dry_run_plan.get("dry_run_only") is True,
            "dry-run plan declares dry_run_only",
        ),
    ]


def _chain_consistency_checks(
    *,
    review: dict[str, Any],
    validation: dict[str, Any],
    gate: dict[str, Any],
    dry_run_plan: dict[str, Any],
) -> list[dict[str, str]]:
    handoff_ids = [
        value
        for value in (review.get("handoff_id"), validation.get("handoff_id"), gate.get("handoff_id"), dry_run_plan.get("handoff_id"))
        if isinstance(value, str) and value
    ]
    run_ids = [
        value
        for value in (review.get("run_id"), validation.get("run_id"), gate.get("run_id"), dry_run_plan.get("run_id"))
        if isinstance(value, str) and value
    ]
    return [
        _check(
            "chain_handoff_ids_match",
            bool(handoff_ids) and len(set(handoff_ids)) == 1,
            "review, validation, gate, and dry-run plan refer to the same handoff_id",
        ),
        _check(
            "chain_run_ids_match",
            bool(run_ids) and len(set(run_ids)) == 1,
            "review, validation, gate, and dry-run plan refer to the same run_id",
        ),
        _check(
            "gate_uses_validation",
            gate.get("source_validation_artifact_type") == validation.get("artifact_type"),
            "gate references the provided validation artifact type",
        ),
        _check(
            "dry_run_plan_uses_review_and_gate",
            dry_run_plan.get("source_review_artifact_type") == review.get("artifact_type")
            and dry_run_plan.get("source_gate_artifact_type") == gate.get("artifact_type"),
            "dry-run plan references the provided review and gate artifact types",
        ),
    ]


def _side_effect_check(label: str, payload: dict[str, Any]) -> dict[str, str]:
    return _check(
        f"{label}_does_not_execute",
        payload.get("does_not_execute") is True,
        f"{label} artifact does not execute workflows or tasks",
    )


def _memory_write_check(label: str, payload: dict[str, Any]) -> dict[str, str]:
    return _check(
        f"{label}_does_not_write_memory",
        payload.get("writes_long_term_memory") is False,
        f"{label} artifact does not write long-term memory",
    )


def _blocking_check_ids(
    checks: list[dict[str, str]],
    gate: dict[str, Any],
    dry_run_plan: dict[str, Any],
) -> list[str]:
    check_failures = [check["check_id"] for check in checks if check["status"] == FAILED]
    upstream_failures = _string_list(dry_run_plan.get("blocking_check_ids")) + _string_list(gate.get("blocking_check_ids"))
    return _dedupe([*check_failures, *upstream_failures])


def _overall_status(blocking_check_ids: list[str], gate: dict[str, Any], dry_run_plan: dict[str, Any]) -> str:
    if not blocking_check_ids:
        return PASSED
    if gate.get("gate_status") == BLOCKED or dry_run_plan.get("plan_status") == BLOCKED:
        return BLOCKED
    return FAILED


def _string_list(values: Any) -> list[str]:
    return [value for value in values if isinstance(value, str) and value] if isinstance(values, list) else []


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _check(check_id: str, passed: bool, message: str) -> dict[str, str]:
    return {"check_id": check_id, "status": PASSED if passed else FAILED, "message": message}


__all__ = (
    "BLOCKED",
    "EXPECTED_ARTIFACT_TYPES",
    "FORBIDDEN_ACTIONS",
    "SCHEMA_VERSION",
    "review_narratostudio_asset_reuse_dry_run_chain",
)
