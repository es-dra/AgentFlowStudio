from __future__ import annotations

import copy
from typing import Any

from agentflow.harness.narratostudio_review import (
    gate_narratostudio_asset_feedback_review,
    validate_narratostudio_asset_feedback_review,
)
from agentflow.memory.narratostudio_reuse import plan_narratostudio_asset_reuse_dry_run
from agentflow.memory.narratostudio_reuse_review import review_narratostudio_asset_reuse_dry_run_chain


def build_narratostudio_asset_reuse_dry_run_chain(
    *,
    review: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build the existing NarratoStudio asset-reuse review chain in memory."""
    source_review = copy.deepcopy(review)
    validation = validate_narratostudio_asset_feedback_review(source_review)
    gate = gate_narratostudio_asset_feedback_review(validation)
    dry_run_plan = plan_narratostudio_asset_reuse_dry_run(review=source_review, gate=gate)
    reuse_review = review_narratostudio_asset_reuse_dry_run_chain(
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


__all__ = ("build_narratostudio_asset_reuse_dry_run_chain",)
