from __future__ import annotations

import copy
import json
from pathlib import Path

from agentflow.memory.narratostudio_reuse import plan_narratostudio_asset_reuse_dry_run


REVIEW_EXAMPLE = Path("examples/agentflow/narratostudio_asset_feedback_review.example.json")
GATE_EXAMPLE = Path("examples/agentflow/narratostudio_asset_feedback_review_gate.example.json")


def test_narratostudio_asset_reuse_dry_run_planner_accepts_passed_gate() -> None:
    review = _json(REVIEW_EXAMPLE)
    gate = _json(GATE_EXAMPLE)
    original_review = copy.deepcopy(review)
    original_gate = copy.deepcopy(gate)

    plan = plan_narratostudio_asset_reuse_dry_run(review=review, gate=gate)

    assert plan["schema_version"] == "0.1.0"
    assert plan["artifact_type"] == "agentflow_narratostudio_asset_reuse_dry_run_plan"
    assert plan["plan_scope"] == "narratostudio_asset_reuse_dry_run"
    assert plan["runtime_status"] == "not_implemented"
    assert plan["does_not_execute"] is True
    assert plan["writes_long_term_memory"] is False
    assert plan["dry_run_only"] is True
    assert plan["plan_status"] == "ready"
    assert plan["source_gate_status"] == "passed"
    assert plan["handoff_id"] == gate["handoff_id"]
    assert plan["run_id"] == gate["run_id"]
    assert plan["selected_asset_profile_ids"] == ["af_reusable_asset_profile_001"]
    assert plan["candidate_reuse_actions"] == [
        {
            "action_id": "review_reusable_asset_profile:af_reusable_asset_profile_001",
            "action_type": "review_reusable_asset_profile",
            "asset_profile_id": "af_reusable_asset_profile_001",
            "does_not_execute": True,
            "requires_human_review": True,
        }
    ]
    assert "human_review_reusable_asset_candidate" in plan["required_pre_execution_reviews"]
    assert review == original_review
    assert gate == original_gate


def test_narratostudio_asset_reuse_dry_run_planner_blocks_failed_gate() -> None:
    review = _json(REVIEW_EXAMPLE)
    gate = _json(GATE_EXAMPLE)
    gate["gate_status"] = "blocked"
    gate["blocking_check_ids"] = ["failed_source_skips_asset_memory_step"]
    gate["next_allowed_actions"] = ["repair_source_artifacts_before_reuse"]

    plan = plan_narratostudio_asset_reuse_dry_run(review=review, gate=gate)

    assert plan["plan_status"] == "blocked"
    assert plan["selected_asset_profile_ids"] == []
    assert plan["candidate_reuse_actions"] == []
    assert plan["blocking_check_ids"] == [
        "source_gate_not_passed",
        "failed_source_skips_asset_memory_step",
    ]
    assert plan["required_pre_execution_reviews"] == ["repair_source_artifacts_before_reuse"]


def test_narratostudio_asset_reuse_dry_run_planner_rejects_runtime_or_memory_claims() -> None:
    review = _json(REVIEW_EXAMPLE)
    gate = _json(GATE_EXAMPLE)
    gate["does_not_execute"] = False
    gate["writes_long_term_memory"] = True

    plan = plan_narratostudio_asset_reuse_dry_run(review=review, gate=gate)

    assert plan["plan_status"] == "blocked"
    assert set(plan["blocking_check_ids"]) >= {
        "source_gate_executes",
        "source_gate_writes_memory",
    }
    assert plan["selected_asset_profile_ids"] == []
    assert plan["candidate_reuse_actions"] == []


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
