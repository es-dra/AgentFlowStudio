from __future__ import annotations

from pathlib import Path

import pytest


FIXTURE_PATH = Path("tests/fixtures/branch_workflow_package/branch_workflow_package_fixture.json")


def test_branch_workflow_generation_plan_packet_is_blocked_by_default() -> None:
    from agentflow.algorithms.branch_workflow_package import load_branch_workflow_package_fixture

    report = load_branch_workflow_package_fixture(FIXTURE_PATH)
    packet = report["accepted_generation_plan_packet"]

    assert packet["packet_kind"] == "accepted_generation_plan_packet"
    assert packet["packet_state"] == "blocked_pending_generation_plan_prerequisites"
    assert packet["accepted"] is False
    assert packet["evidence_origin"] == "repo_local_fixture"
    assert packet["review_state"] == "structure_verified_pending_review"
    assert packet["fixed_asset_refs"] == ["fixed_asset:map-v1"]
    assert packet["residual_closure_refs"] == []
    assert packet["provider_calls_started"] is False
    assert packet["generated_media"] is False
    assert packet["product_readiness"] is False
    assert packet["generation_request_plan"]["request_state"] == "blocked_provider_closed_plan"
    assert packet["generation_request_plan"]["provider_gate"] == "closed"
    assert packet["blocked_reasons"] == report["generation_planning_candidate"]["blocked_reasons"]


def test_branch_workflow_can_assemble_accepted_generation_plan_packet_from_local_fixture() -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    _make_generation_planning_ready(payload)

    report = validate_branch_workflow_package_fixture(payload)
    packet = report["accepted_generation_plan_packet"]

    assert packet["packet_state"] == "accepted_local_generation_plan_packet"
    assert packet["accepted"] is True
    assert packet["claim_level"] == "deterministic_structure_evidence_only"
    assert packet["review_state"] == "accepted_for_generation_planning"
    assert packet["generation_planning_candidate_ref"] == "generation_planning_candidate:branch_pkg_map_choice_demo"
    assert packet["fixed_asset_confirmation_evidence_ref"] == "fixed_asset_confirmation_evidence:branch-workflow-package-v0"
    assert packet["fixed_asset_refs"] == [
        "fixed_asset:ally-trust-reveal-v1",
        "fixed_asset:map-v1",
        "fixed_asset:shadow-cover-hide-v1",
    ]
    assert packet["residual_closure_refs"] == [
        "residual_closure:branch-specific-assets-confirmed",
        "residual_closure:pb3-boundary-owner-accepted",
    ]
    assert packet["evidence_refs"] == [
        "evidence:fixed-asset-confirmation-ally-trust-v1",
        "evidence:fixed-asset-confirmation-map-v1",
        "evidence:fixed-asset-confirmation-shadow-cover-v1",
        "evidence:human-gate-map-v1",
        "evidence:residual-closure-branch-assets",
        "evidence:residual-closure-pb3-boundary",
    ]
    assert packet["generation_request_plan"] == {
        "request_plan_ref": "generation_request_plan:branch_pkg_map_choice_demo",
        "request_kind": "branch_keyframe_generation_plan",
        "request_state": "accepted_provider_closed_plan",
        "target_branch_path_refs": ["branch_path:hide", "branch_path:reveal"],
        "target_branch_shot_refs": [
            "branch_shot:hide-001",
            "branch_shot:hide-002",
            "branch_shot:reveal-001",
            "branch_shot:reveal-002",
        ],
        "fixed_asset_refs": [
            "fixed_asset:ally-trust-reveal-v1",
            "fixed_asset:map-v1",
            "fixed_asset:shadow-cover-hide-v1",
        ],
        "continuity_constraint_refs": [
            "continuity:ally-costume-shared",
            "continuity:map-design-shared",
            "continuity:trust-state-divergence",
        ],
        "production_graph_artifact_refs": ["artifact_production_graph_snapshot_demo"],
        "evidence_requirement_refs": [
            "evidence_req:handoff-non-claims",
            "evidence_req:implementation-ready-assets",
            "evidence_req:workflow-structure",
        ],
        "provider_gate": "closed",
        "provider_calls_started": False,
        "generated_media": False,
        "graph_node_writes_required": False,
    }
    assert packet["non_claim_boundary"]["protected_non_claims_preserved"] is True
    assert packet["non_claim_boundary"]["runtime_openapi_studio_ready"] is False
    assert packet["non_claim_boundary"]["human_or_business_acceptance"] is False
    assert packet["blocked_reasons"] == []


def test_branch_workflow_rejects_fake_external_confirmation_for_generation_plan_packet() -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    _make_generation_planning_ready(payload)
    record = payload["branch_workflow_package"]["fixed_asset_confirmation_evidence"]["asset_confirmation_records"][1]
    record["evidence_origin"] = "external_confirmation_claim"

    with pytest.raises(ValueError, match="fixed asset confirmation evidence must be repo-local"):
        validate_branch_workflow_package_fixture(payload)


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
    sources = {
        "asset_need:ally-trust-reveal": ("fixed_asset:ally-trust-reveal-v1", "evidence:fixed-asset-confirmation-ally-trust-v1"),
        "asset_need:shadow-cover-hide": ("fixed_asset:shadow-cover-hide-v1", "evidence:fixed-asset-confirmation-shadow-cover-v1"),
    }
    package = payload["branch_workflow_package"]
    for asset_need in package["asset_needs"]:
        source = sources.get(asset_need["asset_need_ref"])
        if source is None:
            continue
        asset_need["source_asset_ref"] = source[0]
        asset_need["confirmation_state"] = "fixed_asset_available"
        asset_need["implementation_ready_evidence_allowed"] = True
    requirement = _evidence_requirement(payload, "evidence_req:implementation-ready-assets")
    requirement["evidence_state"] = "fixed_asset_available"
    requirement["implementation_ready_evidence_refs"] = [
        "asset_need:map-shared",
        "fixed_asset:map-v1",
        *sources.keys(),
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
    evidence = package["fixed_asset_confirmation_evidence"]
    evidence["local_confirmation_evidence_refs"].extend(
        [
            "evidence:fixed-asset-confirmation-ally-trust-v1",
            "evidence:fixed-asset-confirmation-shadow-cover-v1",
            "evidence:residual-closure-branch-assets",
            "evidence:residual-closure-pb3-boundary",
        ]
    )
    for asset_ref, (source_ref, evidence_ref) in sources.items():
        suffix = asset_ref.removeprefix("asset_need:")
        evidence["asset_confirmation_records"].append(
            {
                "confirmation_ref": f"asset_confirmation:{suffix}-v1",
                "evidence_origin": "repo_local_fixture",
                "asset_need_ref": asset_ref,
                "source_asset_ref": source_ref,
                "target_refs": [asset_ref],
                "confirmation_source_refs": [evidence_ref],
                "owner_decision_ref": f"owner_decision:{suffix}-fixed",
                "reviewer_decision_ref": f"reviewer_decision:{suffix}-fixed",
                "decision_state": "confirmed_for_generation_planning",
                "close_condition_ref": f"close_condition:{suffix}-fixed-non-claim-preserving",
                "close_condition": "non_claim_preserving_owner_decision_recorded",
                "implementation_ready_evidence_allowed": True,
                "provider_prompt_inclusion_allowed": False,
                "graph_node_writes_required": False,
                "protected_non_claim_refs": _protected_non_claim_refs(),
            }
        )


def _add_residual_closure_evidence(payload: dict) -> None:
    payload["branch_workflow_package"]["fixed_asset_confirmation_evidence"]["residual_question_closures"] = [
        _residual_closure(
            "residual_closure:branch-specific-assets-confirmed",
            "review_question:branch-specific-assets-confirmation",
            "pb3_spec_evaluator_pass_with_residual_risk_implementation_dispatch_candidate",
            ["asset_need:ally-trust-reveal", "asset_need:shadow-cover-hide"],
            ["evidence:fixed-asset-confirmation-ally-trust-v1", "evidence:fixed-asset-confirmation-shadow-cover-v1"],
        ),
        _residual_closure(
            "residual_closure:pb3-boundary-owner-accepted",
            "review_question:pb3-residual-boundary-final-schema",
            "pb3_stage0_stage1_evaluator_pass_with_residual_risk_stage_review_ready",
            ["branch_package:map-choice-demo"],
            ["evidence:residual-closure-pb3-boundary"],
        ),
    ]


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


def _evidence_requirement(payload: dict, ref: str) -> dict:
    for item in payload["branch_workflow_package"]["evidence_requirements"]:
        if item["evidence_requirement_ref"] == ref:
            return item
    raise AssertionError(ref)


def _protected_non_claim_refs() -> list[str]:
    return [
        "provider_smoke",
        "generated_media_quality",
        "human_creative_acceptance",
        "business_validation",
        "final_schema_acceptance",
        "product_readiness",
    ]
