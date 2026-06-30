from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

SCHEMA_VERSION = "production-memory-loop/v1"
RUNTIME_FEEDBACK_CANDIDATE_SCHEMA_VERSION = "runtime-feedback-candidate/v0.1"
RUNTIME_FEEDBACK_CANDIDATE_ALGORITHM_ID = "afs.runtime_feedback_candidate_contract.v0.1"
SAFE_TOKEN_RE = re.compile(r"[^a-zA-Z0-9_.:-]+")


def runtime_feedback_event(project_id: str, feedback: dict[str, Any], generated_at: str) -> dict[str, Any]:
    feedback_id = f"runtime-feedback:{project_id}:{uuid4().hex[:12]}"
    return {
        "artifact_type": "agentflow_runtime_feedback_event",
        "schema_version": SCHEMA_VERSION,
        "feedback_id": feedback_id,
        "project_id": project_id,
        "generated_at": generated_at,
        "feedback": feedback,
        "feedback_candidate": build_runtime_feedback_candidate(
            project_id=project_id,
            feedback_id=feedback_id,
            feedback=feedback,
            generated_at=generated_at,
        ),
        "feedback_is_memory": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": [
            "not durable memory",
            "not human acceptance",
            "not business validation",
            "candidate is not promoted without a separate human decision",
        ],
    }


def build_runtime_feedback_candidate(
    *,
    project_id: str,
    feedback_id: str,
    feedback: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    kind = _safe_token(feedback.get("kind")) or "runtime_feedback"
    return {
        "artifact_type": "agentflow_runtime_feedback_candidate",
        "schema_version": RUNTIME_FEEDBACK_CANDIDATE_SCHEMA_VERSION,
        "algorithm_id": RUNTIME_FEEDBACK_CANDIDATE_ALGORITHM_ID,
        "candidate_id": f"runtime-feedback-candidate:{_safe_token(feedback_id)}",
        "source_feedback_id": feedback_id,
        "source_project_id": project_id,
        "generated_at": generated_at,
        "candidate_scope": _candidate_scope(kind),
        "safe_target": _safe_target(feedback),
        "safe_evidence_summary": _safe_evidence_summary(feedback),
        "feedback_taxonomy": _safe_taxonomy(feedback.get("feedback_taxonomy")),
        "promotion_status": "candidate_only",
        "promotion_blocked_by_default": True,
        "requires_human_promotion_decision": True,
        "eligible_for_context_overlay": False,
        "eligible_for_durable_memory": False,
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "safety_boundary": {
            "raw_provider_response_stored": False,
            "external_private_link_stored": False,
            "absolute_path_stored": False,
            "media_bytes_stored": False,
        },
        "non_claims": [
            "not durable memory",
            "not human acceptance",
            "not business validation",
            "not provider smoke",
        ],
    }


def _candidate_scope(kind: str) -> str:
    if kind == "studio_quality_feedback":
        return "quality_feedback_candidate"
    if kind == "studio_asset_graph_feedback":
        return "asset_graph_feedback_candidate"
    return "runtime_feedback_candidate"


def _safe_target(feedback: dict[str, Any]) -> dict[str, str]:
    target: dict[str, str] = {"kind": _safe_token(feedback.get("kind")) or "runtime_feedback"}
    for key in ("node_id", "node_type", "artifact_ref", "video_job_id", "video_revision_job_id", "asset_graph_ref"):
        value = _safe_token(feedback.get(key))
        if value:
            target[key] = value
    return target


def _safe_evidence_summary(feedback: dict[str, Any]) -> dict[str, Any]:
    ratings = feedback.get("ratings") if isinstance(feedback.get("ratings"), dict) else {}
    decisions = feedback.get("decisions") if isinstance(feedback.get("decisions"), list) else []
    return {
        "rating_count": len(ratings),
        "decision_count": len(decisions),
        "has_note": bool(str(feedback.get("drift_notes") or feedback.get("note") or "").strip()),
        "taxonomy_count": len(_safe_taxonomy(feedback.get("feedback_taxonomy"))),
        "raw_evidence_policy": str(feedback.get("raw_evidence_policy") or "raw_evidence_not_memory"),
    }


def _safe_token(value: Any) -> str:
    return SAFE_TOKEN_RE.sub("_", str(value or "")).strip("_")[:180]


def _safe_taxonomy(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value[:16]:
        taxonomy_id = _safe_token(item)
        if taxonomy_id and taxonomy_id not in result:
            result.append(taxonomy_id)
    return result


def runtime_review_decision_event(
    project_id: str,
    card_id: str,
    decision: str,
    note: str,
    generated_at: str,
    *,
    candidate_id: str | None = None,
    artifact_id: str | None = None,
) -> dict[str, Any]:
    event = {
        "artifact_type": "agentflow_runtime_review_decision",
        "schema_version": SCHEMA_VERSION,
        "review_id": f"runtime-review:{project_id}:{uuid4().hex[:12]}",
        "project_id": project_id,
        "card_id": card_id,
        "decision": decision,
        "note": note,
        "generated_at": generated_at,
        "feedback_is_memory": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": ["not durable memory", "not human acceptance", "not business validation"],
    }
    if candidate_id:
        event["candidate_id"] = candidate_id
    if artifact_id:
        event["artifact_id"] = artifact_id
    return event


__all__ = (
    "RUNTIME_FEEDBACK_CANDIDATE_ALGORITHM_ID",
    "RUNTIME_FEEDBACK_CANDIDATE_SCHEMA_VERSION",
    "build_runtime_feedback_candidate",
    "runtime_feedback_event",
    "runtime_review_decision_event",
)
