from __future__ import annotations

import re
from typing import Any
from uuid import uuid4


ALGORITHM_ID = "afs.runtime_feedback_candidate_context_overlay.v0.1"
SCHEMA_VERSION = "runtime-feedback-candidate-context-overlay/v0.1"
INPUT_CONTRACT = "human-promoted runtime feedback candidate decision"
OUTPUT_CONTRACT = "safe context overlay artifact without provider calls, durable memory writes, or Company KB writes"
SUPPORTED_SOURCE_DECISION = "promote_to_context_overlay"
NON_CLAIMS = [
    "not durable memory",
    "not human creative acceptance",
    "not business validation",
    "not provider smoke",
    "not generated media",
]
SAFE_TOKEN_RE = re.compile(r"[^a-zA-Z0-9_.:-]+")


def build_feedback_candidate_context_overlay(
    *,
    project_id: str,
    promotion_decision_artifact_id: str,
    promotion_decision: dict[str, Any],
    overlay_intent: str,
    generated_at: str,
) -> dict[str, Any]:
    if promotion_decision.get("artifact_type") != "agentflow_runtime_feedback_candidate_promotion_decision":
        raise ValueError("source artifact is not a runtime feedback candidate promotion decision")
    if promotion_decision.get("project_id") != project_id:
        raise ValueError("promotion decision project does not match request project")
    decision = promotion_decision.get("decision")
    if not isinstance(decision, dict):
        raise ValueError("promotion decision has no decision object")
    if decision.get("decision") != SUPPORTED_SOURCE_DECISION or decision.get("context_overlay_allowed") is not True:
        raise ValueError("promotion decision does not allow context overlay")

    overlay_id = f"runtime-feedback-context-overlay:{_safe_token(project_id)}:{uuid4().hex[:12]}"
    return {
        "artifact_type": "agentflow_runtime_feedback_candidate_context_overlay",
        "schema_version": SCHEMA_VERSION,
        "algorithm_id": ALGORITHM_ID,
        "overlay_id": overlay_id,
        "project_id": project_id,
        "generated_at": generated_at,
        "source_promotion_decision_id": _safe_token(promotion_decision.get("decision_id")),
        "source_promotion_decision_artifact_id": _safe_token(promotion_decision_artifact_id),
        "source_feedback_id": _safe_token(promotion_decision.get("source_feedback_id")),
        "source_feedback_artifact_id": _safe_token(promotion_decision.get("source_feedback_artifact_id")),
        "candidate_id": _safe_token(promotion_decision.get("candidate_id")),
        "candidate_scope": _safe_token(promotion_decision.get("candidate_scope")),
        "safe_target": _safe_dict(promotion_decision.get("safe_target")),
        "safe_evidence_summary": _safe_summary(promotion_decision.get("safe_evidence_summary")),
        "feedback_taxonomy": _safe_list(promotion_decision.get("feedback_taxonomy"), limit=16),
        "overlay": {
            "overlay_scope": "next_local_context_pass",
            "overlay_intent": _safe_text(overlay_intent),
            "decision_effect": "included_in_next_context_overlay",
            "candidate_included_in_context": True,
            "context_overlay_written": True,
            "context_bundle_written": False,
            "durable_memory_written": False,
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
    "SUPPORTED_SOURCE_DECISION",
    "build_feedback_candidate_context_overlay",
)
