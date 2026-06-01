from __future__ import annotations

import json
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.memory.production_loop import KIND, SCHEMA_VERSION
from agentflow.memory.production_next_pass_review import NEXT_PASS_REVIEW_KIND


def reject_unsafe_next_pass_promotion(value: Any) -> None:
    raw = json.dumps(value, ensure_ascii=False).lower()
    if any(fragment.lower() in raw for fragment in AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS):
        raise ValueError("production memory next-pass promotion contains unsafe path, generated artifact path, or secret")


def validate_loop(payload: dict[str, Any]) -> None:
    if payload.get("kind") != KIND:
        raise ValueError(f"next-pass promotion overlay requires kind {KIND}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"next-pass promotion overlay requires schema_version {SCHEMA_VERSION}")
    for section in ("artifact_ledger", "feedback_events", "memory_candidates", "promotion_decisions"):
        if not isinstance(payload.get(section), list):
            raise ValueError(f"{section} must be a list")


def validate_review(review: dict[str, Any]) -> None:
    if review.get("kind") != NEXT_PASS_REVIEW_KIND:
        raise ValueError(f"next-pass promotion requires kind {NEXT_PASS_REVIEW_KIND}")
    if review.get("review_status") != "ready_for_operator_review":
        raise ValueError("next-pass promotion requires a ready next-pass review")
    if not isinstance(review.get("feedback_candidates"), list):
        raise ValueError("next-pass review feedback_candidates must be a list")
    if not isinstance(review.get("feedback_events"), list):
        raise ValueError("next-pass review feedback_events must be a list")
    if not isinstance(review.get("output_artifacts"), list):
        raise ValueError("next-pass review output_artifacts must be a list")
    reject_unsafe_next_pass_promotion(review)


def validate_review_inputs(
    candidate_id: str,
    decision: str,
    rationale: str,
    reviewer_role: str,
    decided_at: str,
    supported_decisions: frozenset[str],
) -> None:
    for label, value in {
        "candidate_id": candidate_id,
        "decision": decision,
        "rationale": rationale,
        "reviewer_role": reviewer_role,
        "decided_at": decided_at,
    }.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is required")
    if decision not in supported_decisions:
        raise ValueError(f"unsupported next-pass promotion decision: {decision}")
    reject_unsafe_next_pass_promotion(
        {"candidate_id": candidate_id, "rationale": rationale, "reviewer_role": reviewer_role}
    )


def validate_promotion_decision(
    review: dict[str, Any],
    decision: dict[str, Any],
    *,
    kind: str,
    supported_decisions: frozenset[str],
) -> None:
    if decision.get("kind") != kind:
        raise ValueError("explicit next-pass promotion decision is required")
    candidate = candidate_by_id(review, str(decision.get("candidate_id", "")))
    if decision.get("source_candidate_id") != candidate["candidate_id"]:
        raise ValueError("next-pass promotion source_candidate_id must match candidate_id")
    if decision.get("source_review_id") != review.get("review_id"):
        raise ValueError("next-pass promotion source_review_id must match the review")
    if not set(candidate_source_feedback_ids(candidate)) <= set(string_list(decision.get("source_feedback_ids"))):
        raise ValueError("next-pass promotion must preserve candidate feedback refs")
    if decision.get("decision") not in supported_decisions:
        raise ValueError("next-pass promotion decision must be reviewed")
    if decision.get("review_mode") != "explicit_operator_decision" or decision.get("template_only") is not False:
        raise ValueError("explicit next-pass promotion decision is required")
    if decision.get("provider_calls_started") is not False:
        raise ValueError("next-pass promotion must not start provider calls")
    if decision.get("writes_long_term_memory") is not False or decision.get("writes_company_kb") is not False:
        raise ValueError("next-pass promotion must not write memory or Company KB")
    if candidate.get("status") != "candidate" and decision.get("decision") in {"promoted", "merged"}:
        raise ValueError("only candidate next-pass feedback can be promoted or merged")
    reject_unsafe_next_pass_promotion(decision)


def artifact_record(output_by_ref: dict[str, dict[str, Any]], ref_id: str) -> dict[str, Any]:
    output = output_by_ref.get(ref_id)
    if not output:
        raise ValueError(f"next-pass feedback target_ref missing from output artifacts: {ref_id}")
    return {
        "ref_id": ref_id,
        "title": output.get("title", ref_id),
        "status": output.get("status", "draft"),
        "eligible_for_next_context": False,
        "summary": "Next-pass output captured as feedback evidence only.",
        "source_refs": string_list(output.get("used_context_refs")),
    }


def feedback_record(feedback_by_id: dict[str, dict[str, Any]], feedback_id: str) -> dict[str, Any]:
    feedback = feedback_by_id.get(feedback_id)
    if not feedback:
        raise ValueError(f"next-pass feedback event is missing: {feedback_id}")
    return {
        "feedback_id": feedback_id,
        "target_ref": feedback.get("target_ref", "unknown"),
        "decision": feedback.get("decision", "note"),
        "summary": feedback.get("summary", ""),
        "status": "reviewed",
        "reviewer_role": feedback.get("reviewer_role", "operator"),
        "writes_long_term_memory": False,
    }


def memory_candidate_record(candidate: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate["candidate_id"],
        "status": candidate.get("status", "candidate"),
        "scope": "project",
        "source_feedback_ids": candidate_source_feedback_ids(candidate),
        "statement": candidate.get("summary", ""),
        "target_ref": candidate.get("target_ref", "unknown"),
        "candidate_is_promoted_memory": False,
        "writes_long_term_memory": False,
        "source_next_pass_review_id": review.get("review_id", "unknown"),
        "source_task_packet_id": review.get("source_task_packet_id", "unknown"),
    }


def candidate_by_id(review: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    for candidate in value_list(review.get("feedback_candidates")):
        if isinstance(candidate, dict) and candidate.get("candidate_id") == candidate_id:
            return candidate
    raise ValueError(f"next-pass feedback candidate not found: {candidate_id}")


def candidate_source_feedback_ids(candidate: dict[str, Any]) -> list[str]:
    feedback_ids = string_list(candidate.get("source_feedback_ids"))
    if feedback_ids:
        return feedback_ids
    feedback_id = candidate.get("source_feedback_id")
    return [str(feedback_id)] if feedback_id else []


def feedback_target_refs(candidate: dict[str, Any], feedback_by_id: dict[str, dict[str, Any]]) -> list[str]:
    refs = []
    for feedback_id in candidate_source_feedback_ids(candidate):
        refs.append(str(feedback_by_id.get(feedback_id, {}).get("target_ref", candidate.get("target_ref", "unknown"))))
    return refs


def feedback_events_by_id(review: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(event.get("feedback_id")): event
        for event in value_list(review.get("feedback_events"))
        if isinstance(event, dict) and event.get("feedback_id")
    }


def output_artifacts_by_ref(review: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(artifact.get("ref_id")): artifact
        for artifact in value_list(review.get("output_artifacts"))
        if isinstance(artifact, dict) and artifact.get("ref_id")
    }


def requested_refs(loop: dict[str, Any]) -> list[Any]:
    next_pass_request = loop.setdefault("next_pass_request", {})
    if not isinstance(next_pass_request, dict):
        raise ValueError("next_pass_request must be an object")
    refs = next_pass_request.setdefault("requested_refs", [])
    if not isinstance(refs, list):
        raise ValueError("next_pass_request.requested_refs must be a list")
    return refs


def append_unique(items: list[Any], item: dict[str, Any], id_field: str) -> None:
    item_id = item.get(id_field)
    if not isinstance(item_id, str) or not item_id:
        raise ValueError(f"{id_field} is required")
    existing_ids = {entry.get(id_field) for entry in items if isinstance(entry, dict)}
    if item_id in existing_ids:
        return
    items.append(item)


def value_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []
