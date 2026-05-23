from __future__ import annotations

import copy
import json
from pathlib import Path

from agentflow.harness.narratostudio_review import gate_narratostudio_asset_feedback_review


VALIDATION_EXAMPLE = Path("examples/agentflow/narratostudio_asset_feedback_review_validation.example.json")


def test_narratostudio_asset_feedback_review_gate_passes_valid_review_validation() -> None:
    validation = _validation_example()
    original = copy.deepcopy(validation)

    gate = gate_narratostudio_asset_feedback_review(validation)

    assert gate["schema_version"] == "0.1.0"
    assert gate["artifact_type"] == "agentflow_narratostudio_asset_feedback_review_gate"
    assert gate["gate_scope"] == "narratostudio_asset_feedback_review"
    assert gate["runtime_status"] == "not_implemented"
    assert gate["does_not_execute"] is True
    assert gate["writes_long_term_memory"] is False
    assert gate["gate_status"] == "passed"
    assert gate["source_validation_artifact_type"] == "agentflow_narratostudio_asset_feedback_review_validation"
    assert gate["source_validation_status"] == "passed"
    assert gate["handoff_id"] == validation["handoff_id"]
    assert gate["run_id"] == validation["run_id"]
    assert gate["blocking_check_ids"] == []
    assert gate["next_allowed_actions"] == [
        "human_review_reusable_asset_candidate",
        "prepare_asset_reuse_dry_run",
    ]
    assert validation == original


def test_narratostudio_asset_feedback_review_gate_blocks_failed_review_validation() -> None:
    validation = _validation_example()
    validation["overall_status"] = "failed"
    validation["checks"][0]["status"] = "failed"

    gate = gate_narratostudio_asset_feedback_review(validation)

    assert gate["gate_status"] == "blocked"
    assert gate["source_validation_status"] == "failed"
    assert gate["blocking_check_ids"] == [validation["checks"][0]["check_id"]]
    assert gate["next_allowed_actions"] == ["repair_source_artifacts_before_reuse"]


def test_narratostudio_asset_feedback_review_gate_rejects_runtime_or_write_claims() -> None:
    validation = _validation_example()
    validation["does_not_execute"] = False
    validation["writes_long_term_memory"] = True

    gate = gate_narratostudio_asset_feedback_review(validation)

    assert gate["gate_status"] == "blocked"
    assert set(gate["blocking_check_ids"]) >= {
        "validation_does_not_execute",
        "validation_does_not_write_memory",
    }
    assert gate["next_allowed_actions"] == ["repair_source_artifacts_before_reuse"]


def _validation_example() -> dict:
    return json.loads(VALIDATION_EXAMPLE.read_text(encoding="utf-8"))
