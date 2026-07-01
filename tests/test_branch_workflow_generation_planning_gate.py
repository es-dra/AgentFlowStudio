from __future__ import annotations

from pathlib import Path

import pytest


FIXTURE_PATH = Path("tests/fixtures/branch_workflow_package/branch_workflow_package_fixture.json")


def test_branch_workflow_reports_generation_planning_candidate_as_structure_evidence_only() -> None:
    from agentflow.algorithms.branch_workflow_package import load_branch_workflow_package_fixture

    report = load_branch_workflow_package_fixture(FIXTURE_PATH)
    candidate = report["generation_planning_candidate"]

    assert candidate["candidate_kind"] == "generation_planning_candidate"
    assert candidate["candidate_ref"] == "generation_planning_candidate:branch_pkg_map_choice_demo"
    assert candidate["candidate_state"] == "blocked_pending_generation_planning_prerequisites"
    assert candidate["claim_level"] == "deterministic_structure_evidence_only"
    assert candidate["eligible"] is False
    assert candidate["evidence_origin"] == "repo_local_fixture"
    assert candidate["provider_calls_started"] is False
    assert candidate["generated_media"] is False
    assert candidate["product_readiness"] is False
    assert candidate["checks"] == {
        "local_fixture_evidence_only": True,
        "implementation_ready_evidence_complete": False,
        "review_accepted_for_generation_planning": False,
        "no_unresolved_open_questions": False,
        "residual_allows_generation_planning": False,
        "protected_non_claims_preserved": True,
    }
    assert candidate["asset_policy"] == {
        "shared_confirmed_refs": ["asset_need:map-shared", "fixed_asset:map-v1"],
        "branch_specific_confirmed_refs": [],
        "excluded_unconfirmed_candidate_refs": [
            "asset_need:ally-trust-reveal",
            "asset_need:shadow-cover-hide",
        ],
    }
    assert candidate["blocked_reasons"] == [
        "implementation_ready_evidence_incomplete",
        "review_status_not_accepted_for_generation_planning",
        "unresolved_open_questions_block_generation_planning",
        "residual_boundary_blocks_generation_planning",
    ]


def test_branch_workflow_can_emit_generation_planning_candidate_when_local_prerequisites_are_closed() -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    package = payload["branch_workflow_package"]
    package["package_stage"] = "accepted_for_generation_planning"
    review_status = package["review_status"]
    review_status["review_state"] = "accepted_for_generation_planning"
    review_status["blockers"] = []
    for question in review_status["open_questions"]:
        question["question_state"] = "closed"
    residual_boundary = review_status["residual_boundary"]
    residual_boundary["residual_risk_state"] = "owner_accepted_for_generation_planning"
    residual_boundary["allowed_stage"] = "accepted_for_generation_planning"
    residual_boundary["blocked_stages"] = ["archived"]
    for asset_need in package["asset_needs"]:
        asset_need["confirmation_state"] = "fixed_asset_available"
        asset_need["implementation_ready_evidence_allowed"] = True
    requirement = _evidence_requirement(payload, "evidence_req:implementation-ready-assets")
    requirement["evidence_state"] = "fixed_asset_available"
    requirement["implementation_ready_evidence_refs"] = [
        "asset_need:map-shared",
        "fixed_asset:map-v1",
        "asset_need:ally-trust-reveal",
        "asset_need:shadow-cover-hide",
    ]
    requirement["excluded_unconfirmed_candidate_refs"] = []

    report = validate_branch_workflow_package_fixture(payload)
    candidate = report["generation_planning_candidate"]

    assert candidate["candidate_state"] == "generation_planning_candidate_structure_evidence"
    assert candidate["eligible"] is True
    assert candidate["claim_level"] == "deterministic_structure_evidence_only"
    assert candidate["provider_calls_started"] is False
    assert candidate["generated_media"] is False
    assert candidate["product_readiness"] is False
    assert candidate["checks"]["local_fixture_evidence_only"] is True
    assert candidate["checks"]["protected_non_claims_preserved"] is True
    assert candidate["blocked_reasons"] == []
    assert candidate["asset_policy"] == {
        "shared_confirmed_refs": ["asset_need:map-shared", "fixed_asset:map-v1"],
        "branch_specific_confirmed_refs": [
            "asset_need:ally-trust-reveal",
            "asset_need:shadow-cover-hide",
        ],
        "excluded_unconfirmed_candidate_refs": [],
    }


def test_branch_workflow_rejects_generation_planning_non_local_evidence_origin() -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    requirement = _evidence_requirement(payload, "evidence_req:workflow-structure")
    requirement["evidence_origin"] = "provider_response"

    with pytest.raises(ValueError, match="generation planning evidence must be repo-local deterministic fixture"):
        validate_branch_workflow_package_fixture(payload)


def _evidence_requirement(payload: dict, ref: str) -> dict:
    for item in payload["branch_workflow_package"]["evidence_requirements"]:
        if item["evidence_requirement_ref"] == ref:
            return item
    raise AssertionError(ref)
