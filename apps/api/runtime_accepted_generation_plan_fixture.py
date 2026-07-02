from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.algorithms.branch_workflow_package import (
    load_json_fixture,
    validate_branch_workflow_package_fixture,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
BRANCH_WORKFLOW_FIXTURE_REF = "tests/fixtures/branch_workflow_package/branch_workflow_package_fixture.json"
BRANCH_WORKFLOW_FIXTURE_PATH = REPO_ROOT / BRANCH_WORKFLOW_FIXTURE_REF
DEFAULT_FIXTURE_MODE = "default_unconfirmed"
CONFIRMED_FIXTURE_MODE = "confirmed_local_fixture"


def validated_generation_plan_report(fixture_mode: str) -> dict[str, Any]:
    payload = load_json_fixture(BRANCH_WORKFLOW_FIXTURE_PATH)
    if fixture_mode == CONFIRMED_FIXTURE_MODE:
        _make_confirmed_local_fixture(payload)
    return validate_branch_workflow_package_fixture(payload, source_root=REPO_ROOT)


def _make_confirmed_local_fixture(payload: dict[str, Any]) -> None:
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


def _add_branch_asset_confirmation(payload: dict[str, Any]) -> None:
    sources = {
        "asset_need:ally-trust-reveal": ("fixed_asset:ally-trust-reveal-v1", "evidence:fixed-asset-confirmation-ally-trust-v1"),
        "asset_need:shadow-cover-hide": ("fixed_asset:shadow-cover-hide-v1", "evidence:fixed-asset-confirmation-shadow-cover-v1"),
    }
    package = payload["branch_workflow_package"]
    for asset_need in package["asset_needs"]:
        source = sources.get(asset_need["asset_need_ref"])
        if not source:
            continue
        asset_need["source_asset_ref"] = source[0]
        asset_need["confirmation_state"] = "fixed_asset_available"
        asset_need["implementation_ready_evidence_allowed"] = True
    requirement = _evidence_requirement(payload, "evidence_req:implementation-ready-assets")
    requirement["evidence_state"] = "fixed_asset_available"
    requirement["implementation_ready_evidence_refs"] = ["asset_need:map-shared", "fixed_asset:map-v1", *sources.keys()]
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


def _add_residual_closure_evidence(payload: dict[str, Any]) -> None:
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


def _residual_closure(ref: str, question_ref: str, residual_ref: str, target_refs: list[str], evidence_refs: list[str]) -> dict[str, Any]:
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


def _evidence_requirement(payload: dict[str, Any], ref: str) -> dict[str, Any]:
    for item in payload["branch_workflow_package"]["evidence_requirements"]:
        if item["evidence_requirement_ref"] == ref:
            return item
    raise ValueError(f"fixture evidence requirement not found: {ref}")


def _protected_non_claim_refs() -> list[str]:
    return sorted(
        {
            "provider_smoke",
            "generated_media_quality",
            "human_creative_acceptance",
            "business_validation",
            "final_schema_acceptance",
            "product_readiness",
        }
    )


__all__ = (
    "BRANCH_WORKFLOW_FIXTURE_REF",
    "CONFIRMED_FIXTURE_MODE",
    "DEFAULT_FIXTURE_MODE",
    "validated_generation_plan_report",
)
