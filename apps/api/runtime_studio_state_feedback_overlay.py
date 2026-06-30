from __future__ import annotations

from typing import Any, Callable

TextSanitizer = Callable[[Any, str, int], str]

VALID_FEEDBACK_OVERLAY_DECISIONS = {
    "include_for_next_context",
    "reject_for_next_context",
}


def sanitize_feedback_overlay_decisions(value: Any, *, text: TextSanitizer) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    for item in value[:20]:
        if not isinstance(item, dict):
            continue
        overlay_id = text(item.get("overlay_id"), "", 180)
        decision = text(item.get("decision"), "", 80)
        if not overlay_id or decision not in VALID_FEEDBACK_OVERLAY_DECISIONS:
            continue
        entry = {
            "overlay_id": overlay_id,
            "decision": decision,
            "provider_calls_started": False,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
        }
        candidate_id = text(item.get("candidate_id"), "", 180)
        if candidate_id:
            entry["candidate_id"] = candidate_id
        reviewed_at = text(item.get("reviewed_at"), "", 80)
        if reviewed_at:
            entry["reviewed_at"] = reviewed_at
        result.append(entry)
    return result


__all__ = ("sanitize_feedback_overlay_decisions",)
