from __future__ import annotations

import copy
import json
from pathlib import Path

from agentflow.memory.narratostudio_reuse_review import review_narratostudio_asset_reuse_dry_run_chain


REVIEW_EXAMPLE = Path("examples/agentflow/narratostudio_asset_feedback_review.example.json")
VALIDATION_EXAMPLE = Path("examples/agentflow/narratostudio_asset_feedback_review_validation.example.json")
GATE_EXAMPLE = Path("examples/agentflow/narratostudio_asset_feedback_review_gate.example.json")
PLAN_EXAMPLE = Path("examples/agentflow/narratostudio_asset_reuse_dry_run_plan.example.json")


def test_narratostudio_asset_reuse_review_surface_accepts_ready_chain() -> None:
    review = _json(REVIEW_EXAMPLE)
    validation = _json(VALIDATION_EXAMPLE)
    gate = _json(GATE_EXAMPLE)
    plan = _json(PLAN_EXAMPLE)
    original_payloads = copy.deepcopy((review, validation, gate, plan))

    chain_review = review_narratostudio_asset_reuse_dry_run_chain(
        review=review,
        validation=validation,
        gate=gate,
        dry_run_plan=plan,
    )

    assert chain_review["schema_version"] == "0.1.0"
    assert chain_review["artifact_type"] == "agentflow_narratostudio_asset_reuse_review"
    assert chain_review["review_scope"] == "narratostudio_asset_reuse_dry_run_chain"
    assert chain_review["runtime_status"] == "not_implemented"
    assert chain_review["does_not_execute"] is True
    assert chain_review["writes_long_term_memory"] is False
    assert chain_review["dry_run_only"] is True
    assert chain_review["overall_status"] == "passed"
    assert chain_review["handoff_id"] == plan["handoff_id"]
    assert chain_review["run_id"] == plan["run_id"]
    assert chain_review["source_artifact_types"] == {
        "review": "agentflow_narratostudio_asset_feedback_review",
        "validation": "agentflow_narratostudio_asset_feedback_review_validation",
        "gate": "agentflow_narratostudio_asset_feedback_review_gate",
        "dry_run_plan": "agentflow_narratostudio_asset_reuse_dry_run_plan",
    }
    assert chain_review["selected_asset_profile_ids"] == plan["selected_asset_profile_ids"]
    assert chain_review["candidate_reuse_actions"] == plan["candidate_reuse_actions"]
    assert chain_review["next_required_human_decisions"] == plan["required_human_decisions"]
    assert chain_review["forbidden_actions"] == [
        "execute_workflow",
        "write_long_term_memory",
        "persist_reusable_asset_profile",
        "call_remote_provider",
    ]
    assert chain_review["blocking_check_ids"] == []
    assert (review, validation, gate, plan) == original_payloads


def test_narratostudio_asset_reuse_review_surface_blocks_failed_gate() -> None:
    gate = _json(GATE_EXAMPLE)
    gate["gate_status"] = "blocked"
    gate["blocking_check_ids"] = ["validation_passed"]
    plan = _json(PLAN_EXAMPLE)
    plan["plan_status"] = "blocked"
    plan["blocking_check_ids"] = ["source_gate_not_passed", "validation_passed"]
    plan["selected_asset_profile_ids"] = []
    plan["candidate_reuse_actions"] = []

    chain_review = review_narratostudio_asset_reuse_dry_run_chain(
        review=_json(REVIEW_EXAMPLE),
        validation=_json(VALIDATION_EXAMPLE),
        gate=gate,
        dry_run_plan=plan,
    )

    assert chain_review["overall_status"] == "blocked"
    assert chain_review["selected_asset_profile_ids"] == []
    assert chain_review["candidate_reuse_actions"] == []
    assert chain_review["blocking_check_ids"] == [
        "gate_passed",
        "dry_run_plan_ready",
        "source_gate_not_passed",
        "validation_passed",
    ]


def test_narratostudio_asset_reuse_review_surface_rejects_mismatched_chain() -> None:
    plan = _json(PLAN_EXAMPLE)
    plan["handoff_id"] = "different_handoff"

    chain_review = review_narratostudio_asset_reuse_dry_run_chain(
        review=_json(REVIEW_EXAMPLE),
        validation=_json(VALIDATION_EXAMPLE),
        gate=_json(GATE_EXAMPLE),
        dry_run_plan=plan,
    )

    assert chain_review["overall_status"] == "failed"
    assert "chain_handoff_ids_match" in chain_review["blocking_check_ids"]
    assert chain_review["selected_asset_profile_ids"] == []


def test_narratostudio_asset_reuse_review_surface_rejects_runtime_or_memory_claims() -> None:
    validation = _json(VALIDATION_EXAMPLE)
    validation["does_not_execute"] = False
    plan = _json(PLAN_EXAMPLE)
    plan["writes_long_term_memory"] = True

    chain_review = review_narratostudio_asset_reuse_dry_run_chain(
        review=_json(REVIEW_EXAMPLE),
        validation=validation,
        gate=_json(GATE_EXAMPLE),
        dry_run_plan=plan,
    )

    assert chain_review["overall_status"] == "failed"
    assert set(chain_review["blocking_check_ids"]) >= {
        "validation_does_not_execute",
        "dry_run_plan_does_not_write_memory",
    }
    assert chain_review["selected_asset_profile_ids"] == []


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
