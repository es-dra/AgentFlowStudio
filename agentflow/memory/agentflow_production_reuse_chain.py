from __future__ import annotations

import copy
from typing import Any

from agentflow.harness.agentflow_production_review import (
    gate_agentflow_production_asset_feedback_review,
    validate_agentflow_production_asset_feedback_review,
)
from agentflow.memory.agentflow_production_reuse import plan_agentflow_production_asset_reuse_dry_run
from agentflow.memory.agentflow_production_reuse_review import review_agentflow_production_asset_reuse_dry_run_chain


def build_agentflow_production_asset_reuse_dry_run_chain(
    *,
    review: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build the existing AgentFlow Production asset-reuse review chain in memory."""
    source_review = copy.deepcopy(review)
    validation = validate_agentflow_production_asset_feedback_review(source_review)
    gate = gate_agentflow_production_asset_feedback_review(validation)
    dry_run_plan = plan_agentflow_production_asset_reuse_dry_run(review=source_review, gate=gate)
    reuse_review = review_agentflow_production_asset_reuse_dry_run_chain(
        review=source_review,
        validation=validation,
        gate=gate,
        dry_run_plan=dry_run_plan,
    )
    return {
        "review": source_review,
        "validation": validation,
        "gate": gate,
        "dry_run_plan": dry_run_plan,
        "reuse_review": reuse_review,
    }


__all__ = ("build_agentflow_production_asset_reuse_dry_run_chain",)
