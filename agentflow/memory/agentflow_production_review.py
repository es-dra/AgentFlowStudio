from __future__ import annotations

from typing import Any

from agentflow.harness.constants import AGENTFLOW_VALIDATION_SCHEMA_VERSION, FAILED, PASSED
from agentflow.memory.assets import validate_asset_memory_contract_set
from agentflow.memory.agentflow_production_assets import (
    build_agentflow_production_asset_memory_contract_set,
    validate_agentflow_production_asset_feedback_sources,
)

SCHEMA_VERSION = AGENTFLOW_VALIDATION_SCHEMA_VERSION
NOT_RUN = "not_run"


def review_agentflow_production_asset_feedback_loop(
    *,
    production_handoff: dict[str, Any],
    memory_candidates: dict[str, Any],
    feedback_signal_log: dict[str, Any],
    cost_quality_trace: dict[str, Any],
) -> dict[str, Any]:
    """Compose AgentFlow Production source and AgentFlow asset-memory validations."""
    source_validation = validate_agentflow_production_asset_feedback_sources(
        production_handoff=production_handoff,
        memory_candidates=memory_candidates,
        feedback_signal_log=feedback_signal_log,
        cost_quality_trace=cost_quality_trace,
    )
    if source_validation["overall_status"] != PASSED:
        return _review_result(
            source_validation=source_validation,
            asset_memory_validation=_skipped_asset_memory_validation(),
            asset_memory_step_status=NOT_RUN,
            contract_set_keys=[],
            overall_status=FAILED,
        )

    contract_set = build_agentflow_production_asset_memory_contract_set(
        production_handoff=production_handoff,
        memory_candidates=memory_candidates,
        feedback_signal_log=feedback_signal_log,
        cost_quality_trace=cost_quality_trace,
    )
    asset_memory_validation = validate_asset_memory_contract_set(**contract_set)
    return _review_result(
        source_validation=source_validation,
        asset_memory_validation=asset_memory_validation,
        asset_memory_step_status=asset_memory_validation["overall_status"],
        contract_set_keys=sorted(contract_set),
        overall_status=asset_memory_validation["overall_status"],
    )


def _review_result(
    *,
    source_validation: dict[str, Any],
    asset_memory_validation: dict[str, Any],
    asset_memory_step_status: str,
    contract_set_keys: list[str],
    overall_status: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "agentflow_production_asset_feedback_review",
        "validation_scope": "agentflow_production_asset_feedback_loop",
        "runtime_status": "not_implemented",
        "does_not_execute": True,
        "writes_long_term_memory": False,
        "handoff_id": source_validation.get("handoff_id"),
        "run_id": source_validation.get("run_id"),
        "overall_status": overall_status,
        "source_validation": source_validation,
        "asset_memory_step_status": asset_memory_step_status,
        "asset_memory_validation": asset_memory_validation,
        "contract_set_keys": contract_set_keys,
    }


def _skipped_asset_memory_validation() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "agentflow_asset_memory_validation",
        "validation_scope": "asset_memory_contract_set",
        "runtime_status": "not_implemented",
        "does_not_execute": True,
        "writes_long_term_memory": False,
        "overall_status": NOT_RUN,
        "skip_reason": "source_validation_failed",
        "checks": [],
    }


__all__ = (
    "NOT_RUN",
    "SCHEMA_VERSION",
    "review_agentflow_production_asset_feedback_loop",
)
