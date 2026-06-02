from __future__ import annotations

import copy
import json
from pathlib import Path

from agentflow.memory.agentflow_production_reuse import plan_agentflow_production_asset_reuse_dry_run


GATE_EXAMPLE = Path("examples/agentflow/agentflow_production_asset_feedback_review_gate.example.json")
REUSABLE_PROFILE_EXAMPLE = Path("examples/agentflow/reusable_asset_profile.example.json")
REUSE_DECISION_EXAMPLE = Path("examples/agentflow/asset_reuse_decision.example.json")


def test_agentflow_production_asset_reuse_dry_run_plan_uses_passed_gate_without_executing() -> None:
    gate = _json(GATE_EXAMPLE)
    reusable_profile = _json(REUSABLE_PROFILE_EXAMPLE)
    reuse_decision = _json(REUSE_DECISION_EXAMPLE)
    original_payloads = copy.deepcopy((gate, reusable_profile, reuse_decision))

    plan = plan_agentflow_production_asset_reuse_dry_run(
        review_gate=gate,
        reusable_asset_profile=reusable_profile,
        asset_reuse_decision=reuse_decision,
    )

    assert plan["schema_version"] == "0.1.0"
    assert plan["artifact_type"] == "agentflow_production_asset_reuse_dry_run_plan"
    assert plan["plan_scope"] == "agentflow_production_asset_reuse_dry_run"
    assert plan["runtime_status"] == "not_implemented"
    assert plan["does_not_execute"] is True
    assert plan["writes_long_term_memory"] is False
    assert plan["plan_status"] == "ready"
    assert plan["source_gate_status"] == "passed"
    assert plan["selected_asset_profile_ids"] == reuse_decision["selected_asset_profile_ids"]
    assert plan["reusable_asset_profile_id"] == reusable_profile["asset_profile_id"]
    assert plan["target_task"] == "agentflow_production_brief_to_production_handoff"
    assert plan["required_human_decisions"] == [
        "confirm_asset_profile_still_applies_to_next_brief",
        "confirm_reuse_policy_before_execution",
    ]
    assert plan["forbidden_actions"] == [
        "execute_workflow",
        "write_long_term_memory",
        "persist_reusable_asset_profile",
        "call_remote_provider",
    ]
    assert plan["blocking_reasons"] == []
    assert (gate, reusable_profile, reuse_decision) == original_payloads


def test_agentflow_production_asset_reuse_dry_run_plan_blocks_when_gate_is_not_passed() -> None:
    gate = _json(GATE_EXAMPLE)
    gate["gate_status"] = "blocked"
    gate["blocking_check_ids"] = ["validation_passed"]

    plan = plan_agentflow_production_asset_reuse_dry_run(
        review_gate=gate,
        reusable_asset_profile=_json(REUSABLE_PROFILE_EXAMPLE),
        asset_reuse_decision=_json(REUSE_DECISION_EXAMPLE),
    )

    assert plan["plan_status"] == "blocked"
    assert plan["blocking_reasons"] == ["source_gate_not_passed", "validation_passed"]
    assert plan["selected_asset_profile_ids"] == []


def test_agentflow_production_asset_reuse_dry_run_plan_blocks_mismatched_profile_selection() -> None:
    reusable_profile = _json(REUSABLE_PROFILE_EXAMPLE)
    reuse_decision = _json(REUSE_DECISION_EXAMPLE)
    reuse_decision["selected_asset_profile_ids"] = ["missing_profile"]

    plan = plan_agentflow_production_asset_reuse_dry_run(
        review_gate=_json(GATE_EXAMPLE),
        reusable_asset_profile=reusable_profile,
        asset_reuse_decision=reuse_decision,
    )

    assert plan["plan_status"] == "blocked"
    assert "asset_reuse_decision_does_not_select_profile" in plan["blocking_reasons"]
    assert plan["selected_asset_profile_ids"] == []


def test_agentflow_production_asset_reuse_dry_run_plan_blocks_unprovided_profile_selection() -> None:
    reusable_profile = _json(REUSABLE_PROFILE_EXAMPLE)
    reuse_decision = _json(REUSE_DECISION_EXAMPLE)
    reuse_decision["selected_asset_profile_ids"] = [
        reusable_profile["asset_profile_id"],
        "unprovided_asset_profile",
    ]

    plan = plan_agentflow_production_asset_reuse_dry_run(
        review_gate=_json(GATE_EXAMPLE),
        reusable_asset_profile=reusable_profile,
        asset_reuse_decision=reuse_decision,
    )

    assert plan["plan_status"] == "blocked"
    assert "asset_reuse_decision_selects_unprovided_profiles" in plan["blocking_reasons"]
    assert plan["selected_asset_profile_ids"] == []


def test_agentflow_production_asset_reuse_dry_run_plan_blocks_missing_profile_id() -> None:
    reusable_profile = _json(REUSABLE_PROFILE_EXAMPLE)
    reusable_profile["asset_profile_id"] = ""

    plan = plan_agentflow_production_asset_reuse_dry_run(
        review_gate=_json(GATE_EXAMPLE),
        reusable_asset_profile=reusable_profile,
        asset_reuse_decision=_json(REUSE_DECISION_EXAMPLE),
    )

    assert plan["plan_status"] == "blocked"
    assert "reusable_profile_id" in plan["blocking_reasons"]
    assert plan["selected_asset_profile_ids"] == []


def test_agentflow_production_asset_reuse_dry_run_plan_rejects_execution_or_memory_write_claims() -> None:
    gate = _json(GATE_EXAMPLE)
    gate["does_not_execute"] = False
    reusable_profile = _json(REUSABLE_PROFILE_EXAMPLE)
    reusable_profile["reuse_policy"]["requires_human_review"] = False
    reuse_decision = _json(REUSE_DECISION_EXAMPLE)
    reuse_decision["does_not_execute"] = False

    plan = plan_agentflow_production_asset_reuse_dry_run(
        review_gate=gate,
        reusable_asset_profile=reusable_profile,
        asset_reuse_decision=reuse_decision,
    )

    assert plan["plan_status"] == "blocked"
    assert set(plan["blocking_reasons"]) >= {
        "source_gate_executes",
        "reuse_policy_missing_human_review",
        "asset_reuse_decision_executes",
    }


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
