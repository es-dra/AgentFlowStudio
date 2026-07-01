from __future__ import annotations

from typing import Any

from agentflow.algorithms.interactive_manga_branch_package._helpers import (
    dict_items,
    require_resolved_ref,
    require_resolved_refs,
    required_dict,
    required_text,
)

from . import BRANCH_ASSET_SCOPES, IMPLEMENTATION_READY_ASSET_STATES, PROTECTED_NON_CLAIMS
from ._generation_planning import LOCAL_EVIDENCE_ORIGINS
from ._review_status import CLOSED_QUESTION_STATES


ASSET_CONFIRMATION_ACCEPTED_STATES = {
    "confirmed_for_generation_planning",
    "owner_decision_recorded",
}
RESIDUAL_CLOSURE_ACCEPTED_STATES = {
    "closed_for_generation_planning",
    "owner_accepted_for_generation_planning",
}


def validate_fixed_asset_confirmation_evidence(
    package: dict[str, Any],
    assets: dict[str, dict[str, Any]],
    review_status: dict[str, Any],
    refs: set[str],
    non_claims: dict[str, Any],
) -> dict[str, Any]:
    evidence = required_dict(package, "fixed_asset_confirmation_evidence")
    evidence_ref = required_text(evidence, "evidence_ref")
    _require_local_evidence_origin(evidence, evidence_ref)
    _require_generation_surfaces_closed(evidence, evidence_ref)
    local_refs = _required_resolved_ref_list(evidence, "local_confirmation_evidence_refs", refs, evidence_ref)
    records = _validate_asset_confirmation_records(evidence, assets, refs)
    closures = _validate_residual_question_closures(evidence, review_status, refs)

    branch_refs = sorted(ref for ref, asset in assets.items() if asset["scope"] in BRANCH_ASSET_SCOPES)
    confirmed_branch_refs = sorted(ref for ref in records["confirmed_asset_refs"] if ref in branch_refs)
    pending_branch_refs = sorted(set(branch_refs) - set(confirmed_branch_refs))
    _reject_ready_branch_assets_without_confirmation(assets, records["confirmed_asset_refs"])
    _reject_closed_questions_without_closure(review_status, closures["closed_question_refs"])

    checks = {
        "local_fixture_evidence_only": True,
        "branch_specific_asset_confirmation_complete": not pending_branch_refs,
        "residual_question_closure_evidence_complete": (
            not review_status["unresolved_open_question_refs"]
            and not _closed_question_refs_without_closure(review_status, closures["closed_question_refs"])
        ),
        "protected_non_claims_preserved": all(non_claims.get(claim) is False for claim in PROTECTED_NON_CLAIMS),
        "provider_prompt_inclusion_closed": evidence.get("provider_prompt_inclusion_allowed") is False,
        "graph_node_writes_closed": evidence.get("graph_node_writes_required") is False,
    }
    blocked_reasons = _blocked_reasons(checks)
    return {
        "evidence_kind": "fixed_asset_confirmation_evidence",
        "evidence_ref": evidence_ref,
        "evidence_origin": "repo_local_fixture",
        "confirmation_state": required_text(evidence, "confirmation_state"),
        "eligible_for_generation_planning": not blocked_reasons,
        "local_confirmation_evidence_refs": local_refs,
        "confirmed_asset_refs": sorted(records["confirmed_asset_refs"]),
        "confirmed_branch_asset_refs": confirmed_branch_refs,
        "pending_branch_asset_refs": pending_branch_refs,
        "confirmation_source_refs": sorted(records["confirmation_source_refs"]),
        "owner_decision_refs": sorted(records["owner_decision_refs"] | closures["owner_decision_refs"]),
        "reviewer_decision_refs": sorted(records["reviewer_decision_refs"] | closures["reviewer_decision_refs"]),
        "close_condition_refs": sorted(records["close_condition_refs"] | closures["close_condition_refs"]),
        "residual_question_closure_refs": sorted(closures["closure_refs"]),
        "closed_residual_question_refs": sorted(closures["closed_question_refs"]),
        "provider_prompt_inclusion_allowed": False,
        "graph_node_writes_required": False,
        "checks": checks,
        "blocked_reasons": blocked_reasons,
        "readiness": {
            "fixed_asset_confirmation_evidence_complete": checks["branch_specific_asset_confirmation_complete"],
            "residual_question_closure_evidence_complete": checks["residual_question_closure_evidence_complete"],
        },
    }


def _validate_asset_confirmation_records(
    evidence: dict[str, Any],
    assets: dict[str, dict[str, Any]],
    refs: set[str],
) -> dict[str, Any]:
    confirmed_asset_refs: set[str] = set()
    confirmation_source_refs: set[str] = set()
    owner_decision_refs: set[str] = set()
    reviewer_decision_refs: set[str] = set()
    close_condition_refs: set[str] = set()
    for record in dict_items(evidence.get("asset_confirmation_records"), "asset confirmation record"):
        record_ref = required_text(record, "confirmation_ref")
        _require_local_evidence_origin(record, record_ref)
        _require_generation_surfaces_closed(record, record_ref)
        asset_ref = required_text(record, "asset_need_ref")
        asset = assets.get(asset_ref)
        if asset is None:
            raise ValueError(f"asset confirmation target is not declared: {asset_ref}")
        source_asset_ref = required_text(record, "source_asset_ref")
        if not source_asset_ref.startswith("fixed_asset:"):
            raise ValueError(f"asset confirmation source must be a fixed asset: {record_ref}")
        require_resolved_ref(source_asset_ref, refs, owner=record_ref, field="source_asset_ref")
        if str(asset.get("source_asset_ref") or "") != source_asset_ref:
            raise ValueError(f"asset confirmation source mismatch: {record_ref}")
        if asset["confirmation_state"] not in IMPLEMENTATION_READY_ASSET_STATES:
            raise ValueError(f"asset confirmation record requires implementation-ready asset state: {record_ref}")
        if asset.get("implementation_ready_evidence_allowed") is not True:
            raise ValueError(f"asset confirmation record requires implementation-ready evidence policy: {record_ref}")
        if required_text(record, "decision_state") not in ASSET_CONFIRMATION_ACCEPTED_STATES:
            raise ValueError(f"unknown asset confirmation decision state: {record_ref}")
        _required_resolved_ref_list(record, "target_refs", refs, record_ref)
        confirmation_source_refs.update(_required_resolved_ref_list(record, "confirmation_source_refs", refs, record_ref))
        owner_decision_refs.add(required_text(record, "owner_decision_ref"))
        reviewer_decision_refs.add(required_text(record, "reviewer_decision_ref"))
        close_condition_refs.add(_validate_close_condition(record, record_ref))
        _validate_protected_non_claim_refs(record, record_ref)
        confirmed_asset_refs.add(asset_ref)
    return {
        "confirmed_asset_refs": confirmed_asset_refs,
        "confirmation_source_refs": confirmation_source_refs,
        "owner_decision_refs": owner_decision_refs,
        "reviewer_decision_refs": reviewer_decision_refs,
        "close_condition_refs": close_condition_refs,
    }


def _validate_residual_question_closures(
    evidence: dict[str, Any],
    review_status: dict[str, Any],
    refs: set[str],
) -> dict[str, Any]:
    questions = {item["question_ref"]: item for item in review_status["open_questions"]}
    closure_refs: set[str] = set()
    closed_question_refs: set[str] = set()
    owner_decision_refs: set[str] = set()
    reviewer_decision_refs: set[str] = set()
    close_condition_refs: set[str] = set()
    for item in dict_items(evidence.get("residual_question_closures") or [], "residual question closure"):
        closure_ref = required_text(item, "closure_ref")
        _require_local_evidence_origin(item, closure_ref)
        _require_generation_surfaces_closed(item, closure_ref)
        question_ref = required_text(item, "question_ref")
        question = questions.get(question_ref)
        if question is None:
            raise ValueError(f"residual closure question is not declared: {question_ref}")
        if question["question_state"] not in CLOSED_QUESTION_STATES:
            raise ValueError(f"residual closure requires a closed question state: {question_ref}")
        if required_text(item, "residual_ref") != question["residual_ref"]:
            raise ValueError(f"residual closure residual mismatch: {closure_ref}")
        if required_text(item, "decision_state") not in RESIDUAL_CLOSURE_ACCEPTED_STATES:
            raise ValueError(f"unknown residual closure decision state: {closure_ref}")
        _required_resolved_ref_list(item, "target_refs", refs, closure_ref)
        _required_resolved_ref_list(item, "evidence_refs", refs, closure_ref)
        if item.get("implementation_ready_evidence_allowed") is not False:
            raise ValueError(f"residual closure cannot be implementation-ready evidence: {closure_ref}")
        owner_decision_refs.add(required_text(item, "owner_decision_ref"))
        reviewer_decision_refs.add(required_text(item, "reviewer_decision_ref"))
        close_condition_refs.add(_validate_close_condition(item, closure_ref))
        _validate_protected_non_claim_refs(item, closure_ref)
        closure_refs.add(closure_ref)
        closed_question_refs.add(question_ref)
    return {
        "closure_refs": closure_refs,
        "closed_question_refs": closed_question_refs,
        "owner_decision_refs": owner_decision_refs,
        "reviewer_decision_refs": reviewer_decision_refs,
        "close_condition_refs": close_condition_refs,
    }


def _reject_ready_branch_assets_without_confirmation(
    assets: dict[str, dict[str, Any]],
    confirmed_asset_refs: set[str],
) -> None:
    missing = sorted(
        ref
        for ref, asset in assets.items()
        if asset["scope"] in BRANCH_ASSET_SCOPES
        and asset["confirmation_state"] in IMPLEMENTATION_READY_ASSET_STATES
        and ref not in confirmed_asset_refs
    )
    if missing:
        raise ValueError(f"branch-specific fixed asset confirmation evidence is required: {', '.join(missing)}")


def _reject_closed_questions_without_closure(review_status: dict[str, Any], closed_question_refs: set[str]) -> None:
    missing = _closed_question_refs_without_closure(review_status, closed_question_refs)
    if missing:
        raise ValueError(f"closed residual question requires closure evidence: {', '.join(missing)}")


def _closed_question_refs_without_closure(review_status: dict[str, Any], closed_question_refs: set[str]) -> list[str]:
    return sorted(
        item["question_ref"]
        for item in review_status["open_questions"]
        if item["question_state"] in CLOSED_QUESTION_STATES and item["question_ref"] not in closed_question_refs
    )


def _blocked_reasons(checks: dict[str, bool]) -> list[str]:
    reasons: list[str] = []
    if not checks["branch_specific_asset_confirmation_complete"]:
        reasons.append("branch_specific_asset_confirmation_evidence_missing")
    if not checks["residual_question_closure_evidence_complete"]:
        reasons.append("residual_question_closure_evidence_missing")
    if not checks["protected_non_claims_preserved"]:
        reasons.append("protected_non_claims_not_preserved")
    if not checks["provider_prompt_inclusion_closed"]:
        reasons.append("provider_prompt_inclusion_not_closed")
    if not checks["graph_node_writes_closed"]:
        reasons.append("graph_node_writes_not_closed")
    return reasons


def _require_local_evidence_origin(item: dict[str, Any], owner: str) -> None:
    if required_text(item, "evidence_origin") not in LOCAL_EVIDENCE_ORIGINS:
        raise ValueError(f"fixed asset confirmation evidence must be repo-local deterministic fixture: {owner}")


def _require_generation_surfaces_closed(item: dict[str, Any], owner: str) -> None:
    if item.get("provider_prompt_inclusion_allowed") is not False:
        raise ValueError(f"provider prompt inclusion must stay closed for confirmation evidence: {owner}")
    if item.get("graph_node_writes_required") is not False:
        raise ValueError(f"graph node writes must stay closed for confirmation evidence: {owner}")


def _validate_close_condition(item: dict[str, Any], owner: str) -> str:
    close_condition_ref = required_text(item, "close_condition_ref")
    close_condition = required_text(item, "close_condition")
    if "non_claim_preserving" not in close_condition:
        raise ValueError(f"close condition must preserve non-claims: {owner}")
    return close_condition_ref


def _validate_protected_non_claim_refs(item: dict[str, Any], owner: str) -> None:
    values = item.get("protected_non_claim_refs")
    if not isinstance(values, list) or not values:
        raise ValueError(f"protected_non_claim_refs must be a non-empty list: {owner}")
    unknown = sorted(str(value) for value in values if str(value) not in PROTECTED_NON_CLAIMS)
    if unknown:
        raise ValueError(f"unknown protected non-claim in confirmation evidence: {', '.join(unknown)}")


def _required_resolved_ref_list(item: dict[str, Any], field: str, refs: set[str], owner: str) -> list[str]:
    values = item.get(field)
    if not isinstance(values, list) or not values:
        raise ValueError(f"{field} must be a non-empty list: {owner}")
    require_resolved_refs(values, refs, owner=owner, field=field)
    return [str(value) for value in values]
