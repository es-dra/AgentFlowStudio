from __future__ import annotations

import json
from pathlib import Path


def test_agentflow_production_asset_reuse_review_example_is_review_only() -> None:
    payload = json.loads(
        Path("examples/agentflow/agentflow_production_asset_reuse_review.example.json").read_text(encoding="utf-8")
    )

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_production_asset_reuse_review"
    assert payload["review_scope"] == "agentflow_production_asset_reuse_dry_run_chain"
    assert payload["runtime_status"] == "not_implemented"
    assert payload["does_not_execute"] is True
    assert payload["writes_long_term_memory"] is False
    assert payload["dry_run_only"] is True
    assert payload["overall_status"] in {"passed", "blocked", "failed"}
    assert payload["source_artifact_types"]["dry_run_plan"] == "agentflow_production_asset_reuse_dry_run_plan"
    assert isinstance(payload["selected_asset_profile_ids"], list)
    assert isinstance(payload["candidate_reuse_actions"], list)
    assert isinstance(payload["next_required_human_decisions"], list)
    assert payload["forbidden_actions"] == [
        "execute_workflow",
        "write_long_term_memory",
        "persist_reusable_asset_profile",
        "call_remote_provider",
    ]
    check_ids = {check["check_id"] for check in payload["checks"]}
    assert {
        "review_artifact_type",
        "validation_artifact_type",
        "gate_artifact_type",
        "dry_run_plan_artifact_type",
        "gate_passed",
        "dry_run_plan_ready",
        "chain_handoff_ids_match",
        "chain_run_ids_match",
    } <= check_ids
