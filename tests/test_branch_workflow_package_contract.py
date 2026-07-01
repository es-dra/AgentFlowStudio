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


def test_branch_workflow_exposes_review_status_and_residual_risk_envelope() -> None:
    from agentflow.algorithms.branch_workflow_package import load_branch_workflow_package_fixture

    report = load_branch_workflow_package_fixture(FIXTURE_PATH)

    assert report["review_status"] == {
        "review_state": "structure_verified_pending_review",
        "blockers": ["branch_specific_assets_unconfirmed"],
        "open_question_count": 2,
        "open_question_refs": [
            "review_question:branch-specific-assets-confirmation",
            "review_question:pb3-residual-boundary-final-schema",
        ],
        "unresolved_open_question_refs": [
            "review_question:branch-specific-assets-confirmation",
            "review_question:pb3-residual-boundary-final-schema",
        ],
    }
    assert report["residual_boundary"] == {
        "boundary_ref": "residual_boundary:t54-pb3-review-envelope",
        "residual_risk_state": "open_residual_review_only",
        "allowed_stage": "review_ready",
        "blocked_stages": ["accepted_for_generation_planning"],
        "source_residual_refs": [
            "pb3_local_package_commit_8296afa31b639224bcb3e7c1f8dea70000ea00b4_review_pending_local_package",
            "pb3_spec_evaluator_pass_with_residual_risk_implementation_dispatch_candidate",
            "pb3_stage0_stage1_evaluator_pass_with_residual_risk_stage_review_ready",
            "stage1_evaluator_system_error_residual",
        ],
        "claim_boundary": "review_ready_with_residual_risk_not_schema_or_product_acceptance",
        "implementation_ready_evidence_allowed": False,
        "protected_non_claim_refs": [
            "final_schema_acceptance",
            "product_readiness",
            "provider_smoke",
            "generated_media_quality",
            "human_creative_acceptance",
            "business_validation",
        ],
    }
    assert report["readiness"]["residual_blocked_stages"] == ["accepted_for_generation_planning"]
    assert report["readiness"]["unresolved_open_question_refs"] == [
        "review_question:branch-specific-assets-confirmation",
        "review_question:pb3-residual-boundary-final-schema",
    ]


def test_branch_workflow_requires_structured_review_questions_and_residual_boundary() -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    payload["branch_workflow_package"]["review_status"]["open_questions"] = ["branch_specific_assets_unconfirmed"]

    with pytest.raises(ValueError, match="open question"):
        validate_branch_workflow_package_fixture(payload)

    payload = load_json_fixture(FIXTURE_PATH)
    payload["branch_workflow_package"]["review_status"]["residual_boundary"] = (
        "pass_with_residual_risk_not_schema_or_product_acceptance"
    )

    with pytest.raises(ValueError, match="residual_boundary"):
        validate_branch_workflow_package_fixture(payload)


def test_branch_workflow_rejects_open_question_as_implementation_ready_evidence() -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    question = payload["branch_workflow_package"]["review_status"]["open_questions"][0]
    question["implementation_ready_evidence_allowed"] = True

    with pytest.raises(ValueError, match="open question cannot be implementation-ready evidence"):
        validate_branch_workflow_package_fixture(payload)


@pytest.mark.parametrize(
    ("field", "mutation"),
    (
        ("target_refs", "missing"),
        ("target_refs", "empty"),
        ("evidence_refs", "missing"),
        ("evidence_refs", "empty"),
    ),
)
def test_branch_workflow_requires_open_question_target_and_evidence_refs(field: str, mutation: str) -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    question = payload["branch_workflow_package"]["review_status"]["open_questions"][0]
    if mutation == "missing":
        question.pop(field)
    else:
        question[field] = []

    with pytest.raises(ValueError, match=f"{field} must be a non-empty list"):
        validate_branch_workflow_package_fixture(payload)


def test_branch_workflow_rejects_generation_planning_claim_with_unresolved_residual() -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    payload["branch_workflow_package"]["review_status"]["review_state"] = "accepted_for_generation_planning"

    with pytest.raises(ValueError, match="unresolved residual cannot be accepted-for-generation planning"):
        validate_branch_workflow_package_fixture(payload)


def test_branch_workflow_keeps_unresolved_residuals_out_of_generation_planning_readiness() -> None:
    from agentflow.algorithms.branch_workflow_package import load_json_fixture, validate_branch_workflow_package_fixture

    payload = load_json_fixture(FIXTURE_PATH)
    _add_branch_confirmation_evidence_without_residual_closure(payload)

    report = validate_branch_workflow_package_fixture(payload)

    assert report["readiness"]["implementation_ready_evidence_complete"] is False
    assert report["readiness"]["residual_blocked_stages"] == ["accepted_for_generation_planning"]
    assert report["readiness"]["fixed_asset_confirmation_evidence_complete"] is True
    assert report["readiness"]["residual_question_closure_evidence_complete"] is False


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


def _add_branch_confirmation_evidence_without_residual_closure(payload: dict) -> None:
    branch_sources = {
        "asset_need:ally-trust-reveal": (
            "fixed_asset:ally-trust-reveal-v1",
            "evidence:fixed-asset-confirmation-ally-trust-v1",
        ),
        "asset_need:shadow-cover-hide": (
            "fixed_asset:shadow-cover-hide-v1",
            "evidence:fixed-asset-confirmation-shadow-cover-v1",
        ),
    }
    package = payload["branch_workflow_package"]
    for asset_need in package["asset_needs"]:
        source = branch_sources.get(asset_need["asset_need_ref"])
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
        *branch_sources.keys(),
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
    confirmation = package["fixed_asset_confirmation_evidence"]
    confirmation["local_confirmation_evidence_refs"].extend(source[1] for source in branch_sources.values())
    for asset_ref, (source_ref, evidence_ref) in branch_sources.items():
        suffix = asset_ref.removeprefix("asset_need:")
        confirmation["asset_confirmation_records"].append(
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
                "protected_non_claim_refs": [
                    "provider_smoke",
                    "generated_media_quality",
                    "human_creative_acceptance",
                    "business_validation",
                    "final_schema_acceptance",
                    "product_readiness",
                ],
            }
        )
