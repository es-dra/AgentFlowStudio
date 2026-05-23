from __future__ import annotations

import copy
import json
from pathlib import Path

from agentflow.memory.narratostudio_reuse_chain import build_narratostudio_asset_reuse_dry_run_chain


SOURCE_DIR = Path("examples/agentflow")
REVIEW_EXAMPLE = SOURCE_DIR / "narratostudio_asset_feedback_review.example.json"


def test_narratostudio_asset_reuse_chain_fixture_builder_returns_ready_chain() -> None:
    review = _json(REVIEW_EXAMPLE)
    original_review = copy.deepcopy(review)

    chain = build_narratostudio_asset_reuse_dry_run_chain(review=review)

    assert set(chain) == {
        "review",
        "validation",
        "gate",
        "dry_run_plan",
        "reuse_review",
    }
    assert chain["review"] == review
    assert review == original_review
    assert chain["validation"]["artifact_type"] == "agentflow_narratostudio_asset_feedback_review_validation"
    assert chain["validation"]["overall_status"] == "passed"
    assert chain["gate"]["artifact_type"] == "agentflow_narratostudio_asset_feedback_review_gate"
    assert chain["gate"]["gate_status"] == "passed"
    assert chain["dry_run_plan"]["artifact_type"] == "agentflow_narratostudio_asset_reuse_dry_run_plan"
    assert chain["dry_run_plan"]["plan_status"] == "ready"
    assert chain["reuse_review"]["artifact_type"] == "agentflow_narratostudio_asset_reuse_review"
    assert chain["reuse_review"]["overall_status"] == "passed"
    assert chain["reuse_review"]["selected_asset_profile_ids"] == chain["dry_run_plan"]["selected_asset_profile_ids"]


def test_narratostudio_asset_reuse_chain_fixture_builder_blocks_failed_review() -> None:
    review = _json(REVIEW_EXAMPLE)
    review["overall_status"] = "failed"

    chain = build_narratostudio_asset_reuse_dry_run_chain(review=review)

    assert chain["validation"]["overall_status"] == "failed"
    assert chain["gate"]["gate_status"] == "blocked"
    assert chain["dry_run_plan"]["plan_status"] == "blocked"
    assert chain["reuse_review"]["overall_status"] == "blocked"
    assert chain["reuse_review"]["selected_asset_profile_ids"] == []
    assert "source_gate_not_passed" in chain["reuse_review"]["blocking_check_ids"]


def test_narratostudio_asset_reuse_chain_fixture_builder_does_not_write_or_execute() -> None:
    review = _json(REVIEW_EXAMPLE)

    chain = build_narratostudio_asset_reuse_dry_run_chain(review=review)

    for artifact in chain.values():
        assert artifact["runtime_status"] == "not_implemented"
        assert artifact["does_not_execute"] is True
        assert artifact["writes_long_term_memory"] is False
    assert chain["dry_run_plan"]["dry_run_only"] is True
    assert chain["reuse_review"]["dry_run_only"] is True


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
