from __future__ import annotations

from typing import Any

from . import IMPLEMENTATION_READY_ASSET_STATES, PROTECTED_NON_CLAIMS


PACKET_CLAIM_LEVEL = "deterministic_structure_evidence_only"


def build_accepted_generation_plan_packet(
    package: dict[str, Any],
    assets: dict[str, dict[str, Any]],
    graph_artifacts: set[str],
    review_status: dict[str, Any],
    fixed_asset_confirmation_evidence: dict[str, Any],
    generation_planning_candidate: dict[str, Any],
    non_claims: dict[str, Any],
) -> dict[str, Any]:
    fixed_asset_refs = _fixed_asset_refs(assets)
    checks = _checks(review_status, fixed_asset_confirmation_evidence, generation_planning_candidate, non_claims)
    blocked_reasons = _blocked_reasons(generation_planning_candidate, checks)
    accepted = not blocked_reasons
    return {
        "packet_kind": "accepted_generation_plan_packet",
        "packet_ref": f"accepted_generation_plan_packet:{package['package_id']}",
        "packet_state": (
            "accepted_local_generation_plan_packet"
            if accepted
            else "blocked_pending_generation_plan_prerequisites"
        ),
        "accepted": accepted,
        "claim_level": PACKET_CLAIM_LEVEL,
        "evidence_origin": "repo_local_fixture",
        "review_state": review_status["review_state"],
        "generation_planning_candidate_ref": generation_planning_candidate["candidate_ref"],
        "fixed_asset_confirmation_evidence_ref": fixed_asset_confirmation_evidence["evidence_ref"],
        "fixed_asset_refs": fixed_asset_refs,
        "residual_closure_refs": list(fixed_asset_confirmation_evidence["residual_question_closure_refs"]),
        "evidence_refs": _evidence_refs(fixed_asset_confirmation_evidence),
        "owner_decision_refs": list(fixed_asset_confirmation_evidence["owner_decision_refs"]),
        "reviewer_decision_refs": list(fixed_asset_confirmation_evidence["reviewer_decision_refs"]),
        "close_condition_refs": list(fixed_asset_confirmation_evidence["close_condition_refs"]),
        "provider_calls_started": False,
        "generated_media": False,
        "product_readiness": False,
        "checks": checks,
        "generation_request_plan": _generation_request_plan(
            package,
            graph_artifacts,
            fixed_asset_refs,
            generation_planning_candidate["evidence_requirement_refs"],
            accepted,
        ),
        "non_claim_boundary": _non_claim_boundary(non_claims),
        "blocked_reasons": blocked_reasons,
    }


def _checks(
    review_status: dict[str, Any],
    fixed_asset_confirmation_evidence: dict[str, Any],
    generation_planning_candidate: dict[str, Any],
    non_claims: dict[str, Any],
) -> dict[str, bool]:
    candidate_checks = generation_planning_candidate["checks"]
    confirmation_checks = fixed_asset_confirmation_evidence["checks"]
    return {
        "local_fixture_evidence_only": (
            generation_planning_candidate["evidence_origin"] == "repo_local_fixture"
            and fixed_asset_confirmation_evidence["evidence_origin"] == "repo_local_fixture"
        ),
        "generation_planning_candidate_eligible": bool(generation_planning_candidate["eligible"]),
        "fixed_asset_confirmation_evidence_complete": bool(
            candidate_checks["fixed_asset_confirmation_evidence_complete"]
        ),
        "residual_question_closure_evidence_complete": bool(
            candidate_checks["residual_question_closure_evidence_complete"]
        ),
        "review_accepted_for_generation_planning": bool(candidate_checks["review_accepted_for_generation_planning"]),
        "provider_gate_closed": (
            generation_planning_candidate["provider_calls_started"] is False
            and fixed_asset_confirmation_evidence["provider_prompt_inclusion_allowed"] is False
        ),
        "graph_node_writes_closed": fixed_asset_confirmation_evidence["graph_node_writes_required"] is False,
        "protected_non_claims_preserved": bool(
            candidate_checks["protected_non_claims_preserved"]
            and confirmation_checks["protected_non_claims_preserved"]
            and all(non_claims.get(claim) is False for claim in PROTECTED_NON_CLAIMS)
        ),
    }


def _blocked_reasons(
    generation_planning_candidate: dict[str, Any],
    checks: dict[str, bool],
) -> list[str]:
    reasons = list(generation_planning_candidate["blocked_reasons"])
    for check, reason in (
        ("local_fixture_evidence_only", "non_local_generation_plan_evidence"),
        ("provider_gate_closed", "provider_gate_not_closed"),
        ("graph_node_writes_closed", "graph_node_writes_not_closed"),
        ("protected_non_claims_preserved", "protected_non_claims_not_preserved"),
    ):
        if not checks[check] and reason not in reasons:
            reasons.append(reason)
    return reasons


def _generation_request_plan(
    package: dict[str, Any],
    graph_artifacts: set[str],
    fixed_asset_refs: list[str],
    evidence_requirement_refs: list[str],
    accepted: bool,
) -> dict[str, Any]:
    return {
        "request_plan_ref": f"generation_request_plan:{package['package_id']}",
        "request_kind": "branch_keyframe_generation_plan",
        "request_state": "accepted_provider_closed_plan" if accepted else "blocked_provider_closed_plan",
        "target_branch_path_refs": sorted(str(item["branch_path_ref"]) for item in package["branch_paths"]),
        "target_branch_shot_refs": sorted(str(item["branch_shot_ref"]) for item in package["branch_shots"]),
        "fixed_asset_refs": fixed_asset_refs,
        "continuity_constraint_refs": sorted(str(item["constraint_ref"]) for item in package["continuity_constraints"]),
        "production_graph_artifact_refs": sorted(graph_artifacts),
        "evidence_requirement_refs": sorted(str(ref) for ref in evidence_requirement_refs),
        "provider_gate": "closed",
        "provider_calls_started": False,
        "generated_media": False,
        "graph_node_writes_required": False,
    }


def _non_claim_boundary(non_claims: dict[str, Any]) -> dict[str, Any]:
    return {
        "protected_non_claim_refs": sorted(PROTECTED_NON_CLAIMS),
        "protected_non_claims_preserved": all(non_claims.get(claim) is False for claim in PROTECTED_NON_CLAIMS),
        "runtime_openapi_studio_ready": False,
        "provider_or_media_readiness": False,
        "human_or_business_acceptance": False,
        "final_schema_or_product_acceptance": False,
    }


def _fixed_asset_refs(assets: dict[str, dict[str, Any]]) -> list[str]:
    refs = {
        str(asset.get("source_asset_ref"))
        for asset in assets.values()
        if asset["confirmation_state"] in IMPLEMENTATION_READY_ASSET_STATES
        and str(asset.get("source_asset_ref") or "").startswith("fixed_asset:")
    }
    return sorted(refs)


def _evidence_refs(fixed_asset_confirmation_evidence: dict[str, Any]) -> list[str]:
    refs = set(fixed_asset_confirmation_evidence["local_confirmation_evidence_refs"])
    refs.update(fixed_asset_confirmation_evidence["confirmation_source_refs"])
    return sorted(str(ref) for ref in refs)
