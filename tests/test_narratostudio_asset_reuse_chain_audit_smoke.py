from __future__ import annotations

import json
from pathlib import Path

from agentflow.memory.narratostudio_reuse_audit import audit_narratostudio_asset_reuse_chain_fixture
from agentflow.memory.narratostudio_reuse_chain import build_narratostudio_asset_reuse_dry_run_chain


SOURCE_DIR = Path("examples/agentflow")
REVIEW_EXAMPLE = SOURCE_DIR / "narratostudio_asset_feedback_review.example.json"
EXPECTED_CHAIN_KEYS = {
    "review",
    "validation",
    "gate",
    "dry_run_plan",
    "reuse_review",
}
EXPECTED_ARTIFACT_TYPES = {
    "review": "agentflow_narratostudio_asset_feedback_review",
    "validation": "agentflow_narratostudio_asset_feedback_review_validation",
    "gate": "agentflow_narratostudio_asset_feedback_review_gate",
    "dry_run_plan": "agentflow_narratostudio_asset_reuse_dry_run_plan",
    "reuse_review": "agentflow_narratostudio_asset_reuse_review",
}


def test_narratostudio_asset_reuse_chain_audit_accepts_ready_fixture_chain() -> None:
    chain = build_narratostudio_asset_reuse_dry_run_chain(review=_json(REVIEW_EXAMPLE))

    audit = audit_narratostudio_asset_reuse_chain_fixture(chain)

    assert audit["audit_status"] == "passed"
    assert audit["chain_keys"] == sorted(EXPECTED_CHAIN_KEYS)
    assert audit["source_artifact_types"] == EXPECTED_ARTIFACT_TYPES
    assert audit["source_statuses"] == {
        "review": "passed",
        "validation": "passed",
        "gate": "passed",
        "dry_run_plan": "ready",
        "reuse_review": "passed",
    }
    assert audit["does_not_define_contract_artifact_type"] is True
    assert audit["checks"]
    assert not audit["blocking_check_ids"]


def test_narratostudio_asset_reuse_chain_audit_keeps_blocked_fixture_chain_valid() -> None:
    review = _json(REVIEW_EXAMPLE)
    review["overall_status"] = "failed"
    chain = build_narratostudio_asset_reuse_dry_run_chain(review=review)

    audit = audit_narratostudio_asset_reuse_chain_fixture(chain)

    assert audit["audit_status"] == "passed"
    assert audit["source_statuses"] == {
        "review": "failed",
        "validation": "failed",
        "gate": "blocked",
        "dry_run_plan": "blocked",
        "reuse_review": "blocked",
    }
    assert not audit["blocking_check_ids"]


def test_narratostudio_asset_reuse_chain_audit_rejects_runtime_claims() -> None:
    chain = build_narratostudio_asset_reuse_dry_run_chain(review=_json(REVIEW_EXAMPLE))
    chain["dry_run_plan"]["does_not_execute"] = False

    audit = audit_narratostudio_asset_reuse_chain_fixture(chain)

    assert audit["audit_status"] == "failed"
    assert "dry_run_plan_does_not_execute" in audit["blocking_check_ids"]


def test_narratostudio_asset_reuse_chain_audit_rejects_unexpected_contract_surface() -> None:
    chain = build_narratostudio_asset_reuse_dry_run_chain(review=_json(REVIEW_EXAMPLE))
    chain["new_contract"] = {
        "artifact_type": "agentflow_unreviewed_runtime_contract",
        "runtime_status": "implemented",
    }

    audit = audit_narratostudio_asset_reuse_chain_fixture(chain)

    assert audit["audit_status"] == "failed"
    assert "chain_keys_expected" in audit["blocking_check_ids"]
    assert audit["does_not_define_contract_artifact_type"] is False


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
