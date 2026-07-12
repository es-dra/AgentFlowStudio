from __future__ import annotations

from typing import Any

from agentflow.algorithms.interactive_manga_branch_package._helpers import (
    dict_items,
    require_resolved_refs,
    required_dict,
    required_text,
)

from . import PACKAGE_STAGES, PROTECTED_NON_CLAIMS


OPEN_QUESTION_STATES = {"open", "unresolved", "residual_open", "pending_owner_review"}
CLOSED_QUESTION_STATES = {"closed", "resolved", "superseded"}
REVIEW_ACCEPTED_STATES = {
    "accepted",
    "accepted_for_generation_planning",
    "generation_planning_accepted",
}


def validate_review_status(
    review_status: dict[str, Any],
    refs: set[str],
    residual_refs: set[str],
    *,
    package_stage: str,
) -> dict[str, Any]:
    review_state = required_text(review_status, "review_state")
    blockers = review_status.get("blockers")
    if not isinstance(blockers, list):
        raise ValueError("review_status.blockers must be a list")
    open_questions = _validate_open_questions(review_status, refs, residual_refs)
    residual_boundary = _validate_residual_boundary(
        required_dict(review_status, "residual_boundary"),
        residual_refs,
    )
    unresolved_refs = [
        item["question_ref"]
        for item in open_questions
        if item["question_state"] in OPEN_QUESTION_STATES
    ]
    blocked_stages = set(residual_boundary["blocked_stages"])
    for item in open_questions:
        if item["question_state"] in OPEN_QUESTION_STATES:
            blocked_stages.update(item["blocked_stages"])
    if unresolved_refs and review_state in REVIEW_ACCEPTED_STATES:
        raise ValueError("unresolved residual cannot be accepted-for-generation planning")
    if package_stage in blocked_stages:
        raise ValueError(f"package stage blocked by unresolved residual: {package_stage}")
    return {
        "review_state": review_state,
        "blockers": list(blockers),
        "open_questions": open_questions,
        "open_question_refs": [item["question_ref"] for item in open_questions],
        "unresolved_open_question_refs": unresolved_refs,
        "residual_boundary": residual_boundary,
        "residual_blocked_stages": sorted(blocked_stages),
    }


def _validate_open_questions(
    review_status: dict[str, Any],
    refs: set[str],
    residual_refs: set[str],
) -> list[dict[str, Any]]:
    items = review_status.get("open_questions")
    if not isinstance(items, list):
        raise ValueError("review_status.open_questions must be a list")
    questions: list[dict[str, Any]] = []
    for item in dict_items(items, "open question"):
        question_ref = required_text(item, "question_ref")
        question_state = required_text(item, "question_state")
        if question_state not in OPEN_QUESTION_STATES | CLOSED_QUESTION_STATES:
            raise ValueError(f"unknown open question state: {question_ref}")
        residual_ref = required_text(item, "residual_ref")
        if residual_ref not in residual_refs:
            raise ValueError(f"open question residual ref is not declared: {question_ref}")
        if item.get("implementation_ready_evidence_allowed") is not False:
            raise ValueError(f"open question cannot be implementation-ready evidence: {question_ref}")
        blocked_stages = _required_stage_list(item, "blocked_stages", question_ref)
        _required_resolved_ref_list(item, "target_refs", refs, question_ref)
        _required_resolved_ref_list(item, "evidence_refs", refs, question_ref)
        for field in ("owner", "next_action", "close_condition"):
            required_text(item, field)
        questions.append(
            {
                "question_ref": question_ref,
                "question_state": question_state,
                "residual_ref": residual_ref,
                "blocked_stages": blocked_stages,
            }
        )
    return questions


def _validate_residual_boundary(
    item: dict[str, Any],
    residual_refs: set[str],
) -> dict[str, Any]:
    boundary_ref = required_text(item, "boundary_ref")
    residual_ref = required_text(item, "residual_ref")
    if residual_ref not in residual_refs:
        raise ValueError(f"residual_boundary residual ref is not declared: {boundary_ref}")
    if item.get("implementation_ready_evidence_allowed") is not False:
        raise ValueError(f"residual_boundary cannot be implementation-ready evidence: {boundary_ref}")
    allowed_stage = required_text(item, "allowed_stage")
    if allowed_stage not in PACKAGE_STAGES:
        raise ValueError(f"unknown residual boundary allowed stage: {boundary_ref}")
    blocked_stages = _required_stage_list(item, "blocked_stages", boundary_ref)
    source_residual_refs = item.get("source_residual_refs")
    if not isinstance(source_residual_refs, list) or not source_residual_refs:
        raise ValueError(f"residual_boundary source_residual_refs must be a non-empty list: {boundary_ref}")
    undeclared = sorted(str(ref) for ref in source_residual_refs if str(ref) not in residual_refs)
    if undeclared:
        raise ValueError(f"residual_boundary source residual ref is not declared: {', '.join(undeclared)}")
    protected = item.get("protected_non_claim_refs")
    if not isinstance(protected, list) or not protected:
        raise ValueError(f"residual_boundary protected_non_claim_refs must be a non-empty list: {boundary_ref}")
    unknown_claims = sorted(str(claim) for claim in protected if str(claim) not in PROTECTED_NON_CLAIMS)
    if unknown_claims:
        raise ValueError(f"residual_boundary unknown protected non-claim: {', '.join(unknown_claims)}")
    return {
        "boundary_ref": boundary_ref,
        "residual_risk_state": required_text(item, "residual_risk_state"),
        "allowed_stage": allowed_stage,
        "blocked_stages": blocked_stages,
        "source_residual_refs": [str(ref) for ref in source_residual_refs],
        "claim_boundary": required_text(item, "claim_boundary"),
        "implementation_ready_evidence_allowed": False,
        "protected_non_claim_refs": [str(claim) for claim in protected],
    }


def _required_resolved_ref_list(item: dict[str, Any], field: str, refs: set[str], owner: str) -> None:
    values = item.get(field)
    if not isinstance(values, list) or not values:
        raise ValueError(f"{field} must be a non-empty list: {owner}")
    require_resolved_refs(values, refs, owner=owner, field=field)


def _required_stage_list(item: dict[str, Any], field: str, owner: str) -> list[str]:
    values = item.get(field)
    if not isinstance(values, list) or not values:
        raise ValueError(f"{field} must be a non-empty list: {owner}")
    stages = [str(value) for value in values]
    unknown = sorted(stage for stage in stages if stage not in PACKAGE_STAGES)
    if unknown:
        raise ValueError(f"unknown package stage in {owner}.{field}: {', '.join(unknown)}")
    return stages
