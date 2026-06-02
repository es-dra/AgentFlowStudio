from __future__ import annotations

from typing import Any

from agentflow.harness.constants import AGENTFLOW_VALIDATION_SCHEMA_VERSION, FAILED, PASSED

SCHEMA_VERSION = AGENTFLOW_VALIDATION_SCHEMA_VERSION
PLAN_READY_ACTION = "human_review_reusable_asset_candidate"
PLAN_DRY_RUN_ACTION = "prepare_asset_reuse_dry_run"
PLAN_BLOCKED_ACTION = "repair_source_artifacts_before_reuse"


def plan_agentflow_production_asset_reuse_dry_run(
    *,
    review_gate: dict[str, Any] | None = None,
    reusable_asset_profile: dict[str, Any] | None = None,
    asset_reuse_decision: dict[str, Any] | None = None,
    review: dict[str, Any] | None = None,
    gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a decision-only dry-run plan from existing review and gate artifacts."""
    source_gate = gate or review_gate or {}
    source_review = review or {}
    source_profile = reusable_asset_profile or {}
    source_decision = asset_reuse_decision or {}
    has_contract_inputs = bool(reusable_asset_profile or asset_reuse_decision)
    selected_profile_ids = _selected_profile_ids(
        asset_memory_validation=source_review.get("asset_memory_validation"),
        reusable_asset_profile=source_profile,
        asset_reuse_decision=source_decision,
        has_contract_inputs=has_contract_inputs,
    )
    profile_id = _profile_id(source_profile, selected_profile_ids)
    target_task = source_decision.get("target_task") or "agentflow_production_brief_to_production_handoff"
    checks = _gate_checks(source_gate)
    if has_contract_inputs:
        checks.extend(_contract_input_checks(source_gate, source_profile, source_decision))
    elif review:
        checks.extend(_review_input_checks(source_review, selected_profile_ids))
    else:
        checks.append(
            _check(
                "missing_reuse_sources",
                False,
                "dry-run planner requires review artifacts or explicit reuse contracts",
            )
        )

    blocking_reasons = _blocking_reasons(source_gate, checks)
    plan_status = "ready" if not blocking_reasons else "blocked"
    ready_actions = _ready_actions(selected_profile_ids) if plan_status == "ready" else []
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "agentflow_production_asset_reuse_dry_run_plan",
        "plan_scope": "agentflow_production_asset_reuse_dry_run",
        "runtime_status": "not_implemented",
        "does_not_execute": True,
        "writes_long_term_memory": False,
        "dry_run_only": True,
        "handoff_id": source_gate.get("handoff_id") or source_review.get("handoff_id"),
        "run_id": source_gate.get("run_id") or source_review.get("run_id"),
        "plan_status": plan_status,
        "source_review_artifact_type": source_review.get("artifact_type"),
        "source_review_status": source_review.get("overall_status"),
        "source_gate_artifact_type": source_gate.get("artifact_type"),
        "source_gate_status": source_gate.get("gate_status"),
        "reusable_asset_profile_id": profile_id,
        "target_task": target_task,
        "selected_asset_profile_ids": selected_profile_ids if plan_status == "ready" else [],
        "candidate_reuse_actions": ready_actions,
        "required_human_decisions": _required_human_decisions(plan_status),
        "required_pre_execution_reviews": _required_reviews(source_gate, plan_status),
        "forbidden_actions": _forbidden_actions(),
        "blocking_reasons": blocking_reasons,
        "blocking_check_ids": blocking_reasons,
        "checks": checks,
    }


def _gate_checks(source_gate: dict[str, Any]) -> list[dict[str, str]]:
    return [
        _check(
            "gate_artifact_type",
            source_gate.get("artifact_type") == "agentflow_production_asset_feedback_review_gate",
            "source gate artifact_type is agentflow_production_asset_feedback_review_gate",
        ),
        _check(
            "gate_passed",
            source_gate.get("gate_status") == PASSED,
            "source gate passed",
        ),
        _check(
            "source_gate_executes",
            source_gate.get("does_not_execute") is True,
            "source gate does not execute workflows or tasks",
        ),
        _check(
            "source_gate_writes_memory",
            source_gate.get("writes_long_term_memory") is False,
            "source gate does not write long-term memory",
        ),
    ]


def _contract_input_checks(
    source_gate: dict[str, Any],
    reusable_asset_profile: dict[str, Any],
    asset_reuse_decision: dict[str, Any],
) -> list[dict[str, str]]:
    profile_id = reusable_asset_profile.get("asset_profile_id")
    selected_profile_ids = asset_reuse_decision.get("selected_asset_profile_ids")
    return [
        _check(
            "reusable_profile_type",
            reusable_asset_profile.get("artifact_type") == "agentflow_reusable_asset_profile",
            "source reusable asset profile has the expected artifact_type",
        ),
        _check(
            "reusable_profile_id",
            isinstance(profile_id, str) and bool(profile_id),
            "source reusable asset profile has a non-empty asset_profile_id",
        ),
        _check(
            "reuse_policy_missing_human_review",
            isinstance(reusable_asset_profile.get("reuse_policy"), dict)
            and reusable_asset_profile.get("reuse_policy", {}).get("requires_human_review") is True,
            "reuse policy requires human review before execution",
        ),
        _check(
            "asset_reuse_decision_type",
            asset_reuse_decision.get("artifact_type") == "agentflow_asset_reuse_decision",
            "source asset reuse decision has the expected artifact_type",
        ),
        _check(
            "asset_reuse_decision_does_not_select_profile",
            isinstance(profile_id, str)
            and isinstance(selected_profile_ids, list)
            and profile_id in selected_profile_ids,
            "asset reuse decision selects the provided reusable profile",
        ),
        _check(
            "asset_reuse_decision_selects_unprovided_profiles",
            isinstance(profile_id, str)
            and isinstance(selected_profile_ids, list)
            and selected_profile_ids == [profile_id],
            "asset reuse decision selects only the provided reusable profile",
        ),
        _check(
            "asset_reuse_decision_executes",
            asset_reuse_decision.get("does_not_execute") is True,
            "asset reuse decision does not execute workflows or tasks",
        ),
    ]


def _review_input_checks(source_review: dict[str, Any], selected_profile_ids: list[str]) -> list[dict[str, str]]:
    asset_memory_validation = source_review.get("asset_memory_validation")
    return [
        _check(
            "review_artifact_type",
            source_review.get("artifact_type") == "agentflow_production_asset_feedback_review",
            "source review artifact_type is agentflow_production_asset_feedback_review",
        ),
        _check(
            "review_passed",
            source_review.get("overall_status") == PASSED,
            "source review passed",
        ),
        _check(
            "review_does_not_execute",
            source_review.get("does_not_execute") is True,
            "source review does not execute workflows or tasks",
        ),
        _check(
            "review_does_not_write_memory",
            source_review.get("writes_long_term_memory") is False,
            "source review does not write long-term memory",
        ),
        _check(
            "asset_memory_validation_passed",
            isinstance(asset_memory_validation, dict)
            and asset_memory_validation.get("overall_status") == PASSED,
            "embedded asset-memory validation passed",
        ),
        _check(
            "asset_profile_selected",
            bool(selected_profile_ids),
            "at least one reusable asset profile is available for dry-run review",
        ),
    ]


def _selected_profile_ids(
    *,
    asset_memory_validation: Any,
    reusable_asset_profile: dict[str, Any],
    asset_reuse_decision: dict[str, Any],
    has_contract_inputs: bool,
) -> list[str]:
    if has_contract_inputs:
        values = asset_reuse_decision.get("selected_asset_profile_ids")
        return [value for value in values if isinstance(value, str) and value] if isinstance(values, list) else []
    if not isinstance(asset_memory_validation, dict):
        return []
    profile_id = asset_memory_validation.get("asset_profile_id")
    if not isinstance(profile_id, str) or not profile_id:
        return []
    return [profile_id]


def _profile_id(reusable_asset_profile: dict[str, Any], selected_profile_ids: list[str]) -> str | None:
    profile_id = reusable_asset_profile.get("asset_profile_id")
    if isinstance(profile_id, str) and profile_id:
        return profile_id
    return selected_profile_ids[0] if selected_profile_ids else None


def _ready_actions(selected_profile_ids: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "action_id": f"review_reusable_asset_profile:{profile_id}",
            "action_type": "review_reusable_asset_profile",
            "asset_profile_id": profile_id,
            "does_not_execute": True,
            "requires_human_review": True,
        }
        for profile_id in selected_profile_ids
    ]


def _required_reviews(gate: dict[str, Any], plan_status: str) -> list[str]:
    actions = gate.get("next_allowed_actions")
    if isinstance(actions, list) and all(isinstance(action, str) for action in actions):
        return actions
    return [PLAN_READY_ACTION, PLAN_DRY_RUN_ACTION] if plan_status == "ready" else [PLAN_BLOCKED_ACTION]


def _required_human_decisions(plan_status: str) -> list[str]:
    if plan_status != "ready":
        return []
    return [
        "confirm_asset_profile_still_applies_to_next_brief",
        "confirm_reuse_policy_before_execution",
    ]


def _forbidden_actions() -> list[str]:
    return [
        "execute_workflow",
        "write_long_term_memory",
        "persist_reusable_asset_profile",
        "call_remote_provider",
    ]


def _blocking_reasons(gate: dict[str, Any], checks: list[dict[str, str]]) -> list[str]:
    failed_ids = [check["check_id"] for check in checks if check["status"] == FAILED and check["check_id"] != "gate_passed"]
    gate_blocking_ids = [
        check_id
        for check_id in gate.get("blocking_check_ids", [])
        if isinstance(check_id, str) and check_id
    ]
    if gate.get("gate_status") != PASSED:
        failed_ids = ["source_gate_not_passed", *gate_blocking_ids, *failed_ids]
    return _dedupe(failed_ids)


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
    "PLAN_BLOCKED_ACTION",
    "PLAN_DRY_RUN_ACTION",
    "PLAN_READY_ACTION",
    "SCHEMA_VERSION",
    "plan_agentflow_production_asset_reuse_dry_run",
)
