from __future__ import annotations

import re
from typing import Any
from uuid import uuid4


ALGORITHM_ID = "afs.runtime_feedback_candidate_promotion.v0.1"
SCHEMA_VERSION = "runtime-feedback-candidate-promotion/v0.1"
INPUT_CONTRACT = "safe runtime feedback candidate and explicit operator promotion decision"
OUTPUT_CONTRACT = "promotion decision artifact without provider calls, durable memory writes, or context mutation"
SUPPORTED_DECISIONS = {"promote_to_context_overlay", "reject", "needs_more_evidence"}
NON_CLAIMS = [
    "not durable memory",
    "not human creative acceptance",
    "not business validation",
    "not provider smoke",
    "not context overlay write",
]
SAFE_TOKEN_RE = re.compile(r"[^a-zA-Z0-9_.:-]+")


def build_feedback_candidate_promotion_decision(
    *,
    project_id: str,
    feedback_artifact_id: str,
    feedback_event: dict[str, Any],
    candidate_id: str,
    decision: str,
    rationale: str,
    reviewed_at: str,
) -> dict[str, Any]:
    if decision not in SUPPORTED_DECISIONS:
        raise ValueError("unsupported feedback candidate promotion decision")
    candidate = _candidate_from_event(feedback_event)
    if candidate.get("candidate_id") != candidate_id:
        raise ValueError("feedback candidate id does not match source artifact")
    if feedback_event.get("project_id") != project_id or candidate.get("source_project_id") != project_id:
        raise ValueError("feedback candidate project does not match request project")
    decision_id = f"runtime-feedback-promotion:{_safe_token(project_id)}:{uuid4().hex[:12]}"
    context_allowed = decision == "promote_to_context_overlay"
    return {
        "artifact_type": "agentflow_runtime_feedback_candidate_promotion_decision",
        "schema_version": SCHEMA_VERSION,
        "algorithm_id": ALGORITHM_ID,
        "decision_id": decision_id,
        "project_id": project_id,
        "source_feedback_id": _safe_token(feedback_event.get("feedback_id")),
        "source_feedback_artifact_id": _safe_token(feedback_artifact_id),
        "candidate_id": _safe_token(candidate.get("candidate_id")),
        "candidate_scope": _safe_token(candidate.get("candidate_scope")),
        "safe_target": _safe_dict(candidate.get("safe_target")),
        "target_binding": _safe_payload(candidate.get("target_binding")),
        "scope_policy": _safe_payload(candidate.get("scope_policy")),
        "conflict_summary": _safe_payload(candidate.get("conflict_summary")),
        "safe_evidence_summary": _safe_summary(candidate.get("safe_evidence_summary")),
        "feedback_taxonomy": _safe_list(candidate.get("feedback_taxonomy"), limit=16),
        "decision": {
            "decision": decision,
            "decision_effect": _decision_effect(decision),
            "rationale": _safe_text(rationale),
            "reviewed_at": reviewed_at,
            "context_overlay_allowed": context_allowed,
            "context_overlay_written": False,
            "durable_memory_allowed": False,
            "provider_calls_started": False,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
        },
        "safety_boundary": {
            "raw_provider_response_stored": False,
            "external_private_link_stored": False,
            "absolute_path_stored": False,
            "media_bytes_stored": False,
        },
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "provider_calls_started": False,
        "non_claims": NON_CLAIMS,
    }


def _candidate_from_event(feedback_event: dict[str, Any]) -> dict[str, Any]:
    if feedback_event.get("artifact_type") != "agentflow_runtime_feedback_event":
        raise ValueError("source artifact is not a runtime feedback event")
    candidate = feedback_event.get("feedback_candidate")
    if not isinstance(candidate, dict) or candidate.get("artifact_type") != "agentflow_runtime_feedback_candidate":
        raise ValueError("source feedback event has no runtime feedback candidate")
    return candidate


def _decision_effect(decision: str) -> str:
    if decision == "promote_to_context_overlay":
        return "eligible_for_next_context_overlay"
    if decision == "needs_more_evidence":
        return "blocked_pending_more_evidence"
    return "blocked_from_context_overlay"


def _safe_token(value: Any) -> str:
    return SAFE_TOKEN_RE.sub("_", str(value or "")).strip("_")[:180]


def _safe_text(value: Any) -> str:
    return " ".join(str(value or "").split())[:600]


def _safe_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): _safe_token(item) for key, item in value.items() if _safe_token(item)}


def _safe_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    summary = {
        "rating_count": _bounded_int(value.get("rating_count")),
        "decision_count": _bounded_int(value.get("decision_count")),
        "has_note": bool(value.get("has_note")),
        "raw_evidence_policy": _safe_token(value.get("raw_evidence_policy")) or "raw_evidence_not_memory",
    }
    if "taxonomy_count" in value:
        summary["taxonomy_count"] = _bounded_int(value.get("taxonomy_count"))
    return summary


def _safe_list(value: Any, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value[:limit]:
        text = _safe_token(item)
        if text and text not in result:
            result.append(text)
    return result


def _safe_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            _safe_token(key): _safe_payload(item)
            for key, item in list(value.items())[:24]
            if _safe_token(key)
        }
    if isinstance(value, list):
        return [_safe_payload(item) for item in value[:24]]
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return _bounded_int(value)
    return _safe_token(value)


def _bounded_int(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(number, 1000))


__all__ = (
    "ALGORITHM_ID",
    "INPUT_CONTRACT",
    "NON_CLAIMS",
    "OUTPUT_CONTRACT",
    "SCHEMA_VERSION",
    "SUPPORTED_DECISIONS",
    "build_feedback_candidate_promotion_decision",
)
