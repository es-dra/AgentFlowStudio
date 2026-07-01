from __future__ import annotations

from pathlib import Path

import pytest


FIXTURE_PATH = Path("tests/fixtures/branch_workflow_package/branch_workflow_package_fixture.json")


def test_branch_workflow_reports_fixed_asset_confirmation_evidence_blocked_by_default() -> None:
    from agentflow.algorithms.branch_workflow_package import load_branch_workflow_package_fixture

    report = load_branch_workflow_package_fixture(FIXTURE_PATH)
    evidence = report["fixed_asset_confirmation_evidence"]
    candidate = report["generation_planning_candidate"]

    assert evidence["evidence_kind"] == "fixed_asset_confirmation_evidence"
    assert evidence["evidence_origin"] == "repo_local_fixture"
    assert evidence["confirmed_branch_asset_refs"] == []
    assert evidence["pending_branch_asset_refs"] == [
        "asset_need:ally-trust-reveal",
        "asset_need:shadow-cover-hide",
    ]
    assert evidence["blocked_reasons"] == [
        "branch_specific_asset_confirmation_evidence_missing",
        "residual_question_closure_evidence_missing",
    ]
    assert evidence["provider_prompt_inclusion_allowed"] is False
    assert evidence["graph_node_writes_required"] is False
    assert candidate["eligible"] is False
    assert candidate["checks"]["fixed_asset_confirmation_evidence_complete"] is False
    assert candidate["checks"]["residual_question_closure_evidence_complete"] is False


def test_branch_workflow_asset_confirmation_changes_only_asset_evidence_readiness() -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    _add_branch_asset_confirmation(payload)

    report = validate_branch_workflow_package_fixture(payload)
    evidence = report["fixed_asset_confirmation_evidence"]
    candidate = report["generation_planning_candidate"]

    assert evidence["checks"]["branch_specific_asset_confirmation_complete"] is True
    assert evidence["checks"]["residual_question_closure_evidence_complete"] is False
    assert evidence["confirmed_branch_asset_refs"] == [
        "asset_need:ally-trust-reveal",
        "asset_need:shadow-cover-hide",
    ]
    assert report["readiness"]["implementation_ready_evidence_complete"] is False
    assert report["readiness"]["fixed_asset_confirmation_evidence_complete"] is True
    assert report["readiness"]["residual_question_closure_evidence_complete"] is False
    assert candidate["eligible"] is False
    assert "unresolved_open_questions_block_generation_planning" in candidate["blocked_reasons"]
    assert "residual_question_closure_evidence_missing" in candidate["blocked_reasons"]


def test_branch_workflow_rejects_accepted_generation_planning_without_residual_closure_evidence() -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    _add_branch_asset_confirmation(payload)
    _accept_review_without_closure_records(payload)

    with pytest.raises(ValueError, match="closed residual question requires closure evidence"):
        validate_branch_workflow_package_fixture(payload)


def test_branch_workflow_can_emit_generation_candidate_after_confirmation_and_closure_evidence() -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    _make_generation_planning_ready(payload)

    report = validate_branch_workflow_package_fixture(payload)
    evidence = report["fixed_asset_confirmation_evidence"]
    candidate = report["generation_planning_candidate"]

    assert evidence["eligible_for_generation_planning"] is True
    assert evidence["confirmed_branch_asset_refs"] == [
        "asset_need:ally-trust-reveal",
        "asset_need:shadow-cover-hide",
    ]
    assert evidence["residual_question_closure_refs"] == [
        "residual_closure:branch-specific-assets-confirmed",
        "residual_closure:pb3-boundary-owner-accepted",
    ]
    assert evidence["checks"] == {
        "local_fixture_evidence_only": True,
        "branch_specific_asset_confirmation_complete": True,
        "residual_question_closure_evidence_complete": True,
        "protected_non_claims_preserved": True,
        "provider_prompt_inclusion_closed": True,
        "graph_node_writes_closed": True,
    }
    assert candidate["eligible"] is True
    assert candidate["checks"]["fixed_asset_confirmation_evidence_complete"] is True
    assert candidate["checks"]["residual_question_closure_evidence_complete"] is True
    assert candidate["provider_calls_started"] is False
    assert candidate["generated_media"] is False
    assert candidate["product_readiness"] is False
    assert report["non_claims"]["provider_prompt_inclusion"] is False
    assert report["production_graph_boundary"]["graph_node_writes_required"] is False


def test_branch_workflow_rejects_non_local_confirmation_evidence_origin() -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    evidence = payload["branch_workflow_package"]["fixed_asset_confirmation_evidence"]
    evidence["evidence_origin"] = "provider_response"

    with pytest.raises(ValueError, match="fixed asset confirmation evidence must be repo-local"):
        validate_branch_workflow_package_fixture(payload)


def test_branch_workflow_rejects_branch_asset_ready_without_confirmation_record() -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    _mark_branch_assets_fixed(payload)
    requirement = _evidence_requirement(payload, "evidence_req:implementation-ready-assets")
    requirement["evidence_state"] = "fixed_asset_available"
    requirement["implementation_ready_evidence_refs"] = [
        "asset_need:map-shared",
        "fixed_asset:map-v1",
        "asset_need:ally-trust-reveal",
        "asset_need:shadow-cover-hide",
    ]
    requirement["excluded_unconfirmed_candidate_refs"] = []

    with pytest.raises(ValueError, match="branch-specific fixed asset confirmation evidence is required"):
        validate_branch_workflow_package_fixture(payload)


@pytest.mark.parametrize(
    ("field", "expected"),
    (
        ("target_refs", "target_refs must be a non-empty list"),
        ("evidence_refs", "evidence_refs must be a non-empty list"),
        ("owner_decision_ref", "owner_decision_ref"),
        ("reviewer_decision_ref", "reviewer_decision_ref"),
        ("close_condition_ref", "close_condition_ref"),
    ),
)
def test_branch_workflow_rejects_residual_closure_missing_required_evidence(field: str, expected: str) -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    _make_generation_planning_ready(payload)
    closure = payload["branch_workflow_package"]["fixed_asset_confirmation_evidence"]["residual_question_closures"][0]
    closure.pop(field)

    with pytest.raises(ValueError, match=expected):
        validate_branch_workflow_package_fixture(payload)


@pytest.mark.parametrize(
    ("field", "expected"),
    (
        ("provider_prompt_inclusion_allowed", "provider prompt inclusion"),
        ("graph_node_writes_required", "graph node writes"),
    ),
)
def test_branch_workflow_rejects_confirmation_evidence_that_opens_generation_surfaces(field: str, expected: str) -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    _make_generation_planning_ready(payload)
    record = payload["branch_workflow_package"]["fixed_asset_confirmation_evidence"]["asset_confirmation_records"][1]
    record[field] = True

    with pytest.raises(ValueError, match=expected):
        validate_branch_workflow_package_fixture(payload)


def _make_generation_planning_ready(payload: dict) -> None:
    _add_branch_asset_confirmation(payload)
    _accept_review_without_closure_records(payload)
    evidence = payload["branch_workflow_package"]["fixed_asset_confirmation_evidence"]
    evidence["residual_question_closures"] = [
        {
            "closure_ref": "residual_closure:branch-specific-assets-confirmed",
            "evidence_origin": "repo_local_fixture",
            "question_ref": "review_question:branch-specific-assets-confirmation",
            "residual_ref": "pb3_spec_evaluator_pass_with_residual_risk_implementation_dispatch_candidate",
            "target_refs": [
                "asset_need:ally-trust-reveal",
                "asset_need:shadow-cover-hide",
            ],
            "evidence_refs": [
                "evidence:fixed-asset-confirmation-ally-trust-v1",
                "evidence:fixed-asset-confirmation-shadow-cover-v1",
            ],
            "owner_decision_ref": "owner_decision:branch-assets-confirmed",
            "reviewer_decision_ref": "reviewer_decision:branch-assets-confirmed",
            "decision_state": "closed_for_generation_planning",
            "close_condition_ref": "close_condition:branch-assets-confirmed-non-claim-preserving",
            "close_condition": "non_claim_preserving_owner_decision_recorded",
            "implementation_ready_evidence_allowed": False,
            "provider_prompt_inclusion_allowed": False,
            "graph_node_writes_required": False,
            "protected_non_claim_refs": [
                "provider_smoke",
                "generated_media_quality",
                "human_creative_acceptance",
                "business_validation",
                "final_schema_acceptance",
                "product_readiness",
            ],
        },
        {
            "closure_ref": "residual_closure:pb3-boundary-owner-accepted",
            "evidence_origin": "repo_local_fixture",
            "question_ref": "review_question:pb3-residual-boundary-final-schema",
            "residual_ref": "pb3_stage0_stage1_evaluator_pass_with_residual_risk_stage_review_ready",
            "target_refs": [
                "branch_package:map-choice-demo",
            ],
            "evidence_refs": [
                "evidence:residual-closure-pb3-boundary",
            ],
            "owner_decision_ref": "owner_decision:pb3-boundary-owner-accepted",
            "reviewer_decision_ref": "reviewer_decision:pb3-boundary-owner-accepted",
            "decision_state": "closed_for_generation_planning",
            "close_condition_ref": "close_condition:pb3-boundary-non-claim-preserving",
            "close_condition": "non_claim_preserving_owner_accepted_residual_for_generation_planning_only",
            "implementation_ready_evidence_allowed": False,
            "provider_prompt_inclusion_allowed": False,
            "graph_node_writes_required": False,
            "protected_non_claim_refs": [
                "provider_smoke",
                "generated_media_quality",
                "human_creative_acceptance",
                "business_validation",
                "final_schema_acceptance",
                "product_readiness",
            ],
        },
    ]


def _accept_review_without_closure_records(payload: dict) -> None:
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


def _add_branch_asset_confirmation(payload: dict) -> None:
    _mark_branch_assets_fixed(payload)
    requirement = _evidence_requirement(payload, "evidence_req:implementation-ready-assets")
    requirement["evidence_state"] = "fixed_asset_available"
    requirement["implementation_ready_evidence_refs"] = [
        "asset_need:map-shared",
        "fixed_asset:map-v1",
        "asset_need:ally-trust-reveal",
        "asset_need:shadow-cover-hide",
    ]
    requirement["excluded_unconfirmed_candidate_refs"] = []
    mapped = requirement["mapped_refs"]
    mapped["asset_refs"] = [
        "asset_need:map-shared",
        "fixed_asset:map-v1",
        "asset_need:ally-trust-reveal",
        "fixed_asset:ally-trust-reveal-v1",
        "asset_need:shadow-cover-hide",
        "fixed_asset:shadow-cover-hide-v1",
    ]
    mapped["candidate_asset_refs"] = []
    mapped["evidence_refs"] = [
        "evidence:fixed-asset-confirmation-ally-trust-v1",
        "evidence:fixed-asset-confirmation-shadow-cover-v1",
        "evidence:branch-structure-check",
    ]
    evidence = payload["branch_workflow_package"]["fixed_asset_confirmation_evidence"]
    evidence["local_confirmation_evidence_refs"].extend(
        [
            "evidence:fixed-asset-confirmation-ally-trust-v1",
            "evidence:fixed-asset-confirmation-shadow-cover-v1",
            "evidence:residual-closure-pb3-boundary",
            "evidence:residual-closure-branch-assets",
        ]
    )
    evidence["asset_confirmation_records"].extend(
        [
            {
                "confirmation_ref": "asset_confirmation:ally-trust-reveal-v1",
                "evidence_origin": "repo_local_fixture",
                "asset_need_ref": "asset_need:ally-trust-reveal",
                "source_asset_ref": "fixed_asset:ally-trust-reveal-v1",
                "target_refs": ["asset_need:ally-trust-reveal"],
                "confirmation_source_refs": ["evidence:fixed-asset-confirmation-ally-trust-v1"],
                "owner_decision_ref": "owner_decision:ally-trust-reveal-fixed",
                "reviewer_decision_ref": "reviewer_decision:ally-trust-reveal-fixed",
                "decision_state": "confirmed_for_generation_planning",
                "close_condition_ref": "close_condition:ally-trust-reveal-fixed-non-claim-preserving",
                "close_condition": "non_claim_preserving_owner_decision_recorded",
                "implementation_ready_evidence_allowed": True,
                "provider_prompt_inclusion_allowed": False,
                "graph_node_writes_required": False,
                "protected_non_claim_refs": [
                    "provider_smoke",
                    "generated_media_quality",
                    "human_creative_acceptance",
                    "business_validation",
                    "final_schema_acceptance",
                    "product_readiness",
                ],
            },
            {
                "confirmation_ref": "asset_confirmation:shadow-cover-hide-v1",
                "evidence_origin": "repo_local_fixture",
                "asset_need_ref": "asset_need:shadow-cover-hide",
                "source_asset_ref": "fixed_asset:shadow-cover-hide-v1",
                "target_refs": ["asset_need:shadow-cover-hide"],
                "confirmation_source_refs": ["evidence:fixed-asset-confirmation-shadow-cover-v1"],
                "owner_decision_ref": "owner_decision:shadow-cover-hide-fixed",
                "reviewer_decision_ref": "reviewer_decision:shadow-cover-hide-fixed",
                "decision_state": "confirmed_for_generation_planning",
                "close_condition_ref": "close_condition:shadow-cover-hide-fixed-non-claim-preserving",
                "close_condition": "non_claim_preserving_owner_decision_recorded",
                "implementation_ready_evidence_allowed": True,
                "provider_prompt_inclusion_allowed": False,
                "graph_node_writes_required": False,
                "protected_non_claim_refs": [
                    "provider_smoke",
                    "generated_media_quality",
                    "human_creative_acceptance",
                    "business_validation",
                    "final_schema_acceptance",
                    "product_readiness",
                ],
            },
        ]
    )


def _mark_branch_assets_fixed(payload: dict) -> None:
    source_refs = {
        "asset_need:ally-trust-reveal": "fixed_asset:ally-trust-reveal-v1",
        "asset_need:shadow-cover-hide": "fixed_asset:shadow-cover-hide-v1",
    }
    for asset_need in payload["branch_workflow_package"]["asset_needs"]:
        asset_ref = asset_need["asset_need_ref"]
        if asset_ref not in source_refs:
            continue
        asset_need["source_asset_ref"] = source_refs[asset_ref]
        asset_need["confirmation_state"] = "fixed_asset_available"
        asset_need["implementation_ready_evidence_allowed"] = True


def _evidence_requirement(payload: dict, ref: str) -> dict:
    for item in payload["branch_workflow_package"]["evidence_requirements"]:
        if item["evidence_requirement_ref"] == ref:
            return item
    raise AssertionError(ref)
