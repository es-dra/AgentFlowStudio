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
        "fixed_asset_confirmation_evidence_complete": False,
        "review_accepted_for_generation_planning": False,
        "no_unresolved_open_questions": False,
        "residual_question_closure_evidence_complete": False,
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
        "fixed_asset_confirmation_evidence_missing",
        "review_status_not_accepted_for_generation_planning",
        "unresolved_open_questions_block_generation_planning",
        "residual_question_closure_evidence_missing",
        "residual_boundary_blocks_generation_planning",
    ]


def test_branch_workflow_can_emit_generation_planning_candidate_when_local_prerequisites_are_closed() -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    _make_generation_planning_ready(payload)

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
    assert candidate["checks"]["fixed_asset_confirmation_evidence_complete"] is True
    assert candidate["checks"]["residual_question_closure_evidence_complete"] is True
    assert candidate["blocked_reasons"] == []
    assert candidate["asset_policy"] == {
        "shared_confirmed_refs": ["asset_need:map-shared", "fixed_asset:map-v1"],
        "branch_specific_confirmed_refs": [
            "asset_need:ally-trust-reveal",
            "asset_need:shadow-cover-hide",
            "fixed_asset:ally-trust-reveal-v1",
            "fixed_asset:shadow-cover-hide-v1",
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


def _make_generation_planning_ready(payload: dict) -> None:
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
    _add_branch_asset_confirmation(payload)
    _add_residual_closure_evidence(payload)


def _add_branch_asset_confirmation(payload: dict) -> None:
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
    requirement = _evidence_requirement(payload, "evidence_req:implementation-ready-assets")
    requirement["evidence_state"] = "fixed_asset_available"
    requirement["implementation_ready_evidence_refs"] = [
        "asset_need:map-shared",
        "fixed_asset:map-v1",
        "asset_need:ally-trust-reveal",
        "asset_need:shadow-cover-hide",
    ]
    requirement["excluded_unconfirmed_candidate_refs"] = []
    requirement["mapped_refs"]["asset_refs"] = [
        "asset_need:map-shared",
        "fixed_asset:map-v1",
        "asset_need:ally-trust-reveal",
        "fixed_asset:ally-trust-reveal-v1",
        "asset_need:shadow-cover-hide",
        "fixed_asset:shadow-cover-hide-v1",
    ]
    requirement["mapped_refs"]["candidate_asset_refs"] = []
    requirement["mapped_refs"]["evidence_refs"] = [
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
        ]
    )
    evidence["asset_confirmation_records"].extend(
        [
            _asset_confirmation_record(
                "asset_confirmation:ally-trust-reveal-v1",
                "asset_need:ally-trust-reveal",
                "fixed_asset:ally-trust-reveal-v1",
                "evidence:fixed-asset-confirmation-ally-trust-v1",
            ),
            _asset_confirmation_record(
                "asset_confirmation:shadow-cover-hide-v1",
                "asset_need:shadow-cover-hide",
                "fixed_asset:shadow-cover-hide-v1",
                "evidence:fixed-asset-confirmation-shadow-cover-v1",
            ),
        ]
    )


def _add_residual_closure_evidence(payload: dict) -> None:
    evidence = payload["branch_workflow_package"]["fixed_asset_confirmation_evidence"]
    evidence["residual_question_closures"] = [
        _residual_closure(
            "residual_closure:branch-specific-assets-confirmed",
            "review_question:branch-specific-assets-confirmation",
            "pb3_spec_evaluator_pass_with_residual_risk_implementation_dispatch_candidate",
            ["asset_need:ally-trust-reveal", "asset_need:shadow-cover-hide"],
            [
                "evidence:fixed-asset-confirmation-ally-trust-v1",
                "evidence:fixed-asset-confirmation-shadow-cover-v1",
            ],
        ),
        _residual_closure(
            "residual_closure:pb3-boundary-owner-accepted",
            "review_question:pb3-residual-boundary-final-schema",
            "pb3_stage0_stage1_evaluator_pass_with_residual_risk_stage_review_ready",
            ["branch_package:map-choice-demo"],
            ["evidence:residual-closure-pb3-boundary"],
        ),
    ]


def _asset_confirmation_record(ref: str, asset_ref: str, source_ref: str, evidence_ref: str) -> dict:
    suffix = ref.removeprefix("asset_confirmation:")
    return {
        "confirmation_ref": ref,
        "evidence_origin": "repo_local_fixture",
        "asset_need_ref": asset_ref,
        "source_asset_ref": source_ref,
        "target_refs": [asset_ref],
        "confirmation_source_refs": [evidence_ref],
        "owner_decision_ref": f"owner_decision:{suffix}",
        "reviewer_decision_ref": f"reviewer_decision:{suffix}",
        "decision_state": "confirmed_for_generation_planning",
        "close_condition_ref": f"close_condition:{suffix}-non-claim-preserving",
        "close_condition": "non_claim_preserving_owner_decision_recorded",
        "implementation_ready_evidence_allowed": True,
        "provider_prompt_inclusion_allowed": False,
        "graph_node_writes_required": False,
        "protected_non_claim_refs": _protected_non_claim_refs(),
    }


def _residual_closure(ref: str, question_ref: str, residual_ref: str, target_refs: list[str], evidence_refs: list[str]) -> dict:
    suffix = ref.removeprefix("residual_closure:")
    return {
        "closure_ref": ref,
        "evidence_origin": "repo_local_fixture",
        "question_ref": question_ref,
        "residual_ref": residual_ref,
        "target_refs": target_refs,
        "evidence_refs": evidence_refs,
        "owner_decision_ref": f"owner_decision:{suffix}",
        "reviewer_decision_ref": f"reviewer_decision:{suffix}",
        "decision_state": "closed_for_generation_planning",
        "close_condition_ref": f"close_condition:{suffix}-non-claim-preserving",
        "close_condition": "non_claim_preserving_owner_decision_recorded",
        "implementation_ready_evidence_allowed": False,
        "provider_prompt_inclusion_allowed": False,
        "graph_node_writes_required": False,
        "protected_non_claim_refs": _protected_non_claim_refs(),
    }


def _protected_non_claim_refs() -> list[str]:
    return [
        "provider_smoke",
        "generated_media_quality",
        "human_creative_acceptance",
        "business_validation",
        "final_schema_acceptance",
        "product_readiness",
    ]
