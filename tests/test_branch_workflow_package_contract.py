from __future__ import annotations

import copy
from pathlib import Path

import pytest


FIXTURE_PATH = Path("tests/fixtures/branch_workflow_package/branch_workflow_package_fixture.json")


def test_branch_workflow_package_algorithm_is_registered() -> None:
    from agentflow import algorithms
    from agentflow.algorithms import branch_workflow_package

    assert "branch_workflow_package" in algorithms.CORE_AGENT_ALGORITHM_MODULES
    assert branch_workflow_package.ALGORITHM_ID == "afs.branch_workflow_package.v0.1"
    assert branch_workflow_package.INPUT_CONTRACT
    assert branch_workflow_package.OUTPUT_CONTRACT
    assert branch_workflow_package.FAILURE_MODES
    assert branch_workflow_package.EVIDENCE_BOUNDARY


def test_branch_workflow_fixture_loads_as_t53_backed_spec2_contract() -> None:
    from agentflow.algorithms.branch_workflow_package import load_branch_workflow_package_fixture

    report = load_branch_workflow_package_fixture(FIXTURE_PATH)

    assert report["fixture_id"] == "branch_workflow_package_contract_fixture_v0"
    assert report["fixture_claim_level"] == "deterministic_branch_workflow_package_contract_only"
    assert report["source_fixture"] == {
        "fixture_id": "interactive_manga_branch_package_fixture_v0",
        "package_ref": "branch_package:map-choice-demo",
    }
    assert report["summary"] == {
        "choice_point_count": 1,
        "branch_path_count": 2,
        "branch_shot_count": 4,
        "asset_need_count": 3,
        "continuity_constraint_count": 3,
        "evidence_requirement_count": 3,
        "handoff_count": 1,
    }


def test_branch_workflow_preserves_shared_and_branch_specific_asset_policy() -> None:
    from agentflow.algorithms.branch_workflow_package import load_branch_workflow_package_fixture

    report = load_branch_workflow_package_fixture(FIXTURE_PATH)

    assert report["asset_need_scopes"] == {
        "branch_specific": 2,
        "shared_across_package": 1,
    }
    assert report["confirmation_state_counts"] == {
        "candidate": 2,
        "fixed_asset_available": 1,
    }
    assert report["readiness"]["implementation_ready_evidence_complete"] is False
    assert report["readiness"]["implementation_ready_asset_refs"] == [
        "asset_need:map-shared",
        "fixed_asset:map-v1",
    ]
    assert report["readiness"]["excluded_unconfirmed_candidate_refs"] == [
        "asset_need:ally-trust-reveal",
        "asset_need:shadow-cover-hide",
    ]


def test_branch_workflow_checks_evidence_completeness_and_non_claim_boundaries() -> None:
    from agentflow.algorithms.branch_workflow_package import load_branch_workflow_package_fixture

    report = load_branch_workflow_package_fixture(FIXTURE_PATH)

    assert report["readiness"]["review_ready_evidence_complete"] is True
    assert report["readiness"]["blocked_reasons"] == [
        "branch_specific_assets_need_future_confirmation_before_generation"
    ]
    assert report["production_graph_boundary"] == {
        "reference_policy": "reference_only_no_node_write",
        "graph_node_writes_required": False,
        "graph_artifact_refs": ["artifact_production_graph_snapshot_demo"],
    }
    assert report["non_claims"]["provider_smoke"] is False
    assert report["non_claims"]["generated_media_quality"] is False
    assert report["non_claims"]["human_creative_acceptance"] is False
    assert report["non_claims"]["business_validation"] is False
    assert report["non_claims"]["product_readiness"] is False


def test_branch_workflow_carries_pb3_stage_residual_boundaries() -> None:
    from agentflow.algorithms.branch_workflow_package import load_branch_workflow_package_fixture

    report = load_branch_workflow_package_fixture(FIXTURE_PATH)

    assert report["source_boundary_refs"] == [
        "docs/handoff/AFS-T52-SHARED-OBJECT-EVIDENCE-FIXTURE-20260701.md",
        "docs/handoff/AFS-T53-INTERACTIVE-MANGA-BRANCH-PACKAGE-CONTRACT-20260701.md",
        "interactive_manga_branch_package_fixture_v0",
    ]
    assert report["residual_boundaries"] == [
        "pb3_local_package_commit_8296afa31b639224bcb3e7c1f8dea70000ea00b4_review_pending_local_package",
        "pb3_spec_evaluator_pass_with_residual_risk_implementation_dispatch_candidate",
        "pb3_stage0_stage1_evaluator_pass_with_residual_risk_stage_review_ready",
        "stage1_evaluator_system_error_residual",
    ]


def test_branch_workflow_rejects_unconfirmed_candidates_in_implementation_ready_evidence() -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    requirement = _evidence_requirement(payload, "evidence_req:implementation-ready-assets")
    requirement["implementation_ready_evidence_refs"].append("asset_need:ally-trust-reveal")

    with pytest.raises(ValueError, match="unconfirmed candidate"):
        validate_branch_workflow_package_fixture(payload)


def test_branch_workflow_rejects_graph_node_write_claims() -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    payload["branch_workflow_package"]["production_graph_references"][0]["graph_node_writes_required"] = True

    with pytest.raises(ValueError, match="graph node write"):
        validate_branch_workflow_package_fixture(payload)


def test_branch_workflow_rejects_unsafe_payload_markers() -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    unsafe_key = "_".join(["signed", "url"])
    payload["branch_workflow_package"]["evidence_requirements"][0][unsafe_key] = "https://example.invalid/private"

    with pytest.raises(ValueError, match="unsafe marker"):
        validate_branch_workflow_package_fixture(payload)


def test_branch_workflow_preserves_protected_non_claims_fail_closed() -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    mutated = copy.deepcopy(payload)
    mutated["non_claims"]["product_readiness"] = True

    with pytest.raises(ValueError, match="protected non-claim"):
        validate_branch_workflow_package_fixture(mutated)


def _evidence_requirement(payload: dict, ref: str) -> dict:
    for item in payload["branch_workflow_package"]["evidence_requirements"]:
        if item["evidence_requirement_ref"] == ref:
            return item
    raise AssertionError(ref)
