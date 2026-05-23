from __future__ import annotations

from typing import Any

from agentflow.harness.constants import FAILED, PASSED


EXPECTED_CHAIN_ARTIFACT_TYPES = {
    "review": "agentflow_narratostudio_asset_feedback_review",
    "validation": "agentflow_narratostudio_asset_feedback_review_validation",
    "gate": "agentflow_narratostudio_asset_feedback_review_gate",
    "dry_run_plan": "agentflow_narratostudio_asset_reuse_dry_run_plan",
    "reuse_review": "agentflow_narratostudio_asset_reuse_review",
}
READY_CHAIN_STATUSES = {
    "review": PASSED,
    "validation": PASSED,
    "gate": PASSED,
    "dry_run_plan": "ready",
    "reuse_review": PASSED,
}
BLOCKED_CHAIN_STATUSES = {
    "review": FAILED,
    "validation": FAILED,
    "gate": "blocked",
    "dry_run_plan": "blocked",
    "reuse_review": "blocked",
}


def audit_narratostudio_asset_reuse_chain_fixture(chain: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Audit a fixture-built NarratoStudio asset-reuse chain without creating a contract artifact."""
    source_artifact_types = _source_artifact_types(chain)
    source_statuses = _source_statuses(chain)
    checks = [
        _check(
            "chain_keys_expected",
            set(chain) == set(EXPECTED_CHAIN_ARTIFACT_TYPES),
            "chain contains only the expected fixture artifact keys",
        ),
        *_artifact_type_checks(source_artifact_types),
        *_boundary_checks(chain),
        _check(
            "dry_run_plan_dry_run_only",
            _payload(chain, "dry_run_plan").get("dry_run_only") is True,
            "dry-run plan remains dry_run_only",
        ),
        _check(
            "reuse_review_dry_run_only",
            _payload(chain, "reuse_review").get("dry_run_only") is True,
            "reuse review remains dry_run_only",
        ),
        _check(
            "chain_status_shape",
            source_statuses in (READY_CHAIN_STATUSES, BLOCKED_CHAIN_STATUSES),
            "chain statuses match the ready or blocked fixture shape",
        ),
    ]
    blocking_check_ids = [check["check_id"] for check in checks if check["status"] == FAILED]
    return {
        "audit_scope": "narratostudio_asset_reuse_chain_fixture",
        "audit_status": PASSED if not blocking_check_ids else FAILED,
        "runtime_status": "not_implemented",
        "does_not_execute": True,
        "writes_long_term_memory": False,
        "does_not_define_contract_artifact_type": _does_not_define_contract_artifact_type(chain),
        "chain_keys": sorted(chain),
        "source_artifact_types": source_artifact_types,
        "source_statuses": source_statuses,
        "blocking_check_ids": blocking_check_ids,
        "checks": checks,
    }


def _artifact_type_checks(source_artifact_types: dict[str, Any]) -> list[dict[str, str]]:
    return [
        _check(
            f"{key}_artifact_type",
            source_artifact_types.get(key) == expected_type,
            f"{key} artifact_type is {expected_type}",
        )
        for key, expected_type in EXPECTED_CHAIN_ARTIFACT_TYPES.items()
    ]


def _boundary_checks(chain: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    return [
        check
        for key in EXPECTED_CHAIN_ARTIFACT_TYPES
        for check in (
            _check(
                f"{key}_runtime_not_implemented",
                _payload(chain, key).get("runtime_status") == "not_implemented",
                f"{key} does not claim runtime implementation",
            ),
            _check(
                f"{key}_does_not_execute",
                _payload(chain, key).get("does_not_execute") is True,
                f"{key} does not execute workflows or tasks",
            ),
            _check(
                f"{key}_does_not_write_memory",
                _payload(chain, key).get("writes_long_term_memory") is False,
                f"{key} does not write long-term memory",
            ),
        )
    ]


def _source_artifact_types(chain: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {key: _payload(chain, key).get("artifact_type") for key in EXPECTED_CHAIN_ARTIFACT_TYPES}


def _source_statuses(chain: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "review": _payload(chain, "review").get("overall_status"),
        "validation": _payload(chain, "validation").get("overall_status"),
        "gate": _payload(chain, "gate").get("gate_status"),
        "dry_run_plan": _payload(chain, "dry_run_plan").get("plan_status"),
        "reuse_review": _payload(chain, "reuse_review").get("overall_status"),
    }


def _does_not_define_contract_artifact_type(chain: dict[str, dict[str, Any]]) -> bool:
    if set(chain) != set(EXPECTED_CHAIN_ARTIFACT_TYPES):
        return False
    return all(_payload(chain, key).get("artifact_type") == expected for key, expected in EXPECTED_CHAIN_ARTIFACT_TYPES.items())


def _payload(chain: dict[str, dict[str, Any]], key: str) -> dict[str, Any]:
    payload = chain.get(key)
    return payload if isinstance(payload, dict) else {}


def _check(check_id: str, passed: bool, message: str) -> dict[str, str]:
    return {"check_id": check_id, "status": PASSED if passed else FAILED, "message": message}


__all__ = (
    "BLOCKED_CHAIN_STATUSES",
    "EXPECTED_CHAIN_ARTIFACT_TYPES",
    "READY_CHAIN_STATUSES",
    "audit_narratostudio_asset_reuse_chain_fixture",
)
