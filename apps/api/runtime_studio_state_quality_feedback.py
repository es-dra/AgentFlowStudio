from __future__ import annotations

from typing import Any, Callable


TextSanitizer = Callable[[Any, str, int], str]


def sanitize_quality_feedback_candidates(value: Any, *, text: TextSanitizer) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        candidate = {
            "feedback_id": text(item.get("feedback_id"), "", 180),
            "feedback_artifact_id": text(item.get("feedback_artifact_id"), "", 180),
            "candidate_id": text(item.get("candidate_id"), "", 180),
            "candidate_scope": text(item.get("candidate_scope"), "", 120),
            "context_overlay_requested": bool(item.get("context_overlay_requested")),
            "promotion_decision_id": text(item.get("promotion_decision_id"), "", 180),
            "promotion_artifact_id": text(item.get("promotion_artifact_id"), "", 180),
            "context_overlay_id": text(item.get("context_overlay_id"), "", 180),
            "context_overlay_artifact_id": text(item.get("context_overlay_artifact_id"), "", 180),
            "status": text(item.get("status"), "", 120),
            "recorded_at": text(item.get("recorded_at"), "", 80),
            "provider_calls_started": False,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
        }
        if candidate["feedback_id"] or candidate["candidate_id"] or candidate["context_overlay_id"]:
            candidates.append(candidate)
        if len(candidates) >= 8:
            break
    return candidates


__all__ = ("sanitize_quality_feedback_candidates",)
