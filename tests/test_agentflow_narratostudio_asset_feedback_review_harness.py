from __future__ import annotations

import copy
import json
from pathlib import Path

from agentflow.harness.narratostudio_review import validate_narratostudio_asset_feedback_review


REVIEW_EXAMPLE = Path("examples/agentflow/narratostudio_asset_feedback_review.example.json")


def test_narratostudio_asset_feedback_review_harness_accepts_current_example() -> None:
    review = _review_example()
    original = copy.deepcopy(review)

    validation = validate_narratostudio_asset_feedback_review(review)

    assert validation["schema_version"] == "0.1.0"
    assert validation["artifact_type"] == "agentflow_narratostudio_asset_feedback_review_validation"
    assert validation["validation_scope"] == "narratostudio_asset_feedback_review"
    assert validation["runtime_status"] == "not_implemented"
    assert validation["does_not_execute"] is True
    assert validation["writes_long_term_memory"] is False
    assert validation["overall_status"] == "passed"
    assert validation["handoff_id"] == review["handoff_id"]
    assert validation["run_id"] == review["run_id"]
    assert all(check["status"] == "passed" for check in validation["checks"])
    assert review == original


def test_narratostudio_asset_feedback_review_harness_rejects_runtime_claims() -> None:
    review = _review_example()
    review["does_not_execute"] = False
    review["writes_long_term_memory"] = True

    validation = validate_narratostudio_asset_feedback_review(review)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {
        "review_does_not_execute",
        "review_does_not_write_memory",
    }


def test_narratostudio_asset_feedback_review_harness_requires_step_consistency() -> None:
    review = _review_example()
    review["source_validation"]["overall_status"] = "failed"
    review["asset_memory_step_status"] = "passed"

    validation = validate_narratostudio_asset_feedback_review(review)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"failed_source_skips_asset_memory_step"}


def test_narratostudio_asset_feedback_review_harness_rejects_private_paths() -> None:
    review = _review_example()
    review["asset_memory_validation"]["intermediate_asset_id"] = "D:\\private\\clip.mp4?api_key=abc123"

    validation = validate_narratostudio_asset_feedback_review(review)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"no_private_paths_or_secrets"}


def _review_example() -> dict:
    return json.loads(REVIEW_EXAMPLE.read_text(encoding="utf-8"))


def _failed_check_ids(validation: dict) -> set[str]:
    return {check["check_id"] for check in validation["checks"] if check["status"] == "failed"}
