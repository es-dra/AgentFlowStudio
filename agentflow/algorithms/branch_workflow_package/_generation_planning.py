from __future__ import annotations

from typing import Any

from . import (
    BRANCH_ASSET_SCOPES,
    IMPLEMENTATION_READY_ASSET_STATES,
    PROTECTED_NON_CLAIMS,
    SHARED_ASSET_SCOPES,
    UNCONFIRMED_ASSET_STATES,
)


GENERATION_PLANNING_STAGE = "accepted_for_generation_planning"
GENERATION_PLANNING_ACCEPTED_STATES = {
    "accepted_for_generation_planning",
    "generation_planning_accepted",
}
LOCAL_EVIDENCE_ORIGINS = {"repo_local_fixture"}
CANDIDATE_CLAIM_LEVEL = "deterministic_structure_evidence_only"


def build_generation_planning_candidate(
    package: dict[str, Any],
    assets: dict[str, dict[str, Any]],
    evidence_requirements: list[Any],
    readiness: dict[str, Any],
    review_status: dict[str, Any],
    non_claims: dict[str, Any],
    fixed_asset_confirmation_evidence: dict[str, Any],
) -> dict[str, Any]:
    evidence_requirement_refs = _validate_local_evidence_origins(evidence_requirements)
    checks = _eligibility_checks(readiness, review_status, non_claims, fixed_asset_confirmation_evidence)
    blocked_reasons = _blocked_reasons(checks)
    return {
        "candidate_kind": "generation_planning_candidate",
        "candidate_ref": f"generation_planning_candidate:{package['package_id']}",
        "candidate_state": (
            "generation_planning_candidate_structure_evidence"
            if not blocked_reasons
            else "blocked_pending_generation_planning_prerequisites"
        ),
        "claim_level": CANDIDATE_CLAIM_LEVEL,
        "eligible": not blocked_reasons,
        "evidence_origin": "repo_local_fixture",
        "evidence_requirement_refs": evidence_requirement_refs,
        "fixed_asset_confirmation_evidence_ref": fixed_asset_confirmation_evidence["evidence_ref"],
        "provider_calls_started": False,
        "generated_media": False,
        "product_readiness": False,
        "checks": checks,
        "asset_policy": _asset_policy(assets),
        "blocked_reasons": blocked_reasons,
        "protected_non_claim_refs": sorted(PROTECTED_NON_CLAIMS),
    }


def _validate_local_evidence_origins(evidence_requirements: list[Any]) -> list[str]:
    refs: list[str] = []
    for item in evidence_requirements:
        if not isinstance(item, dict):
            raise ValueError("generation planning evidence requirement must be an object")
        ref = str(item.get("evidence_requirement_ref") or "")
        origin = str(item.get("evidence_origin") or "")
        if origin not in LOCAL_EVIDENCE_ORIGINS:
            raise ValueError(f"generation planning evidence must be repo-local deterministic fixture: {ref}")
        refs.append(ref)
    return refs


def _eligibility_checks(
    readiness: dict[str, Any],
    review_status: dict[str, Any],
    non_claims: dict[str, Any],
    fixed_asset_confirmation_evidence: dict[str, Any],
) -> dict[str, bool]:
    residual_boundary = review_status["residual_boundary"]
    residual_blocked_stages = set(readiness.get("residual_blocked_stages") or [])
    unresolved_questions = list(readiness.get("unresolved_open_question_refs") or [])
    confirmation_checks = fixed_asset_confirmation_evidence["checks"]
    return {
        "local_fixture_evidence_only": True,
        "implementation_ready_evidence_complete": bool(readiness["implementation_ready_evidence_complete"]),
        "fixed_asset_confirmation_evidence_complete": bool(
            confirmation_checks["branch_specific_asset_confirmation_complete"]
        ),
        "review_accepted_for_generation_planning": str(review_status["review_state"])
        in GENERATION_PLANNING_ACCEPTED_STATES,
        "no_unresolved_open_questions": not unresolved_questions,
        "residual_question_closure_evidence_complete": bool(
            confirmation_checks["residual_question_closure_evidence_complete"]
        ),
        "residual_allows_generation_planning": (
            GENERATION_PLANNING_STAGE not in residual_blocked_stages
            and residual_boundary["allowed_stage"] == GENERATION_PLANNING_STAGE
        ),
        "protected_non_claims_preserved": all(non_claims.get(claim) is False for claim in PROTECTED_NON_CLAIMS),
    }


def _blocked_reasons(checks: dict[str, bool]) -> list[str]:
    reasons: list[str] = []
    if not checks["implementation_ready_evidence_complete"]:
        reasons.append("implementation_ready_evidence_incomplete")
    if not checks["fixed_asset_confirmation_evidence_complete"]:
        reasons.append("fixed_asset_confirmation_evidence_missing")
    if not checks["review_accepted_for_generation_planning"]:
        reasons.append("review_status_not_accepted_for_generation_planning")
    if not checks["no_unresolved_open_questions"]:
        reasons.append("unresolved_open_questions_block_generation_planning")
    if not checks["residual_question_closure_evidence_complete"]:
        reasons.append("residual_question_closure_evidence_missing")
    if not checks["residual_allows_generation_planning"]:
        reasons.append("residual_boundary_blocks_generation_planning")
    if not checks["protected_non_claims_preserved"]:
        reasons.append("protected_non_claims_not_preserved")
    return reasons


def _asset_policy(assets: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    return {
        "shared_confirmed_refs": _confirmed_refs(assets, SHARED_ASSET_SCOPES),
        "branch_specific_confirmed_refs": _confirmed_refs(assets, BRANCH_ASSET_SCOPES),
        "excluded_unconfirmed_candidate_refs": sorted(
            ref for ref, item in assets.items() if item["confirmation_state"] in UNCONFIRMED_ASSET_STATES
        ),
    }


def _confirmed_refs(assets: dict[str, dict[str, Any]], scopes: set[str]) -> list[str]:
    refs: list[str] = []
    for ref, item in assets.items():
        if item["scope"] not in scopes or item["confirmation_state"] not in IMPLEMENTATION_READY_ASSET_STATES:
            continue
        refs.append(ref)
        source_ref = str(item.get("source_asset_ref") or "")
        if source_ref.startswith("fixed_asset:"):
            refs.append(source_ref)
    return sorted(set(refs))
