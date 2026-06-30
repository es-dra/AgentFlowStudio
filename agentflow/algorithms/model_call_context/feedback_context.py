from __future__ import annotations

from collections.abc import Callable
from typing import Any


TextSanitizer = Callable[[Any], str]
RefListSanitizer = Callable[[list[str]], list[str]]


def bundle_feedback_context_overlays(
    bundle: dict[str, Any],
    *,
    sanitize_text: TextSanitizer,
    safe_ref_list: RefListSanitizer,
) -> list[dict[str, Any]]:
    values = bundle.get("feedback_context_overlays") if isinstance(bundle, dict) else []
    overlays: list[dict[str, Any]] = []
    for item in (values if isinstance(values, list) else []):
        if not isinstance(item, dict):
            continue
        overlay = {
            "overlay_id": sanitize_text(item.get("overlay_id")).strip(),
            "candidate_id": sanitize_text(item.get("candidate_id")).strip(),
            "candidate_scope": sanitize_text(item.get("candidate_scope")).strip(),
            "feedback_taxonomy": safe_ref_list(
                [sanitize_text(taxonomy_id).strip() for taxonomy_id in _safe_list(item.get("feedback_taxonomy"))]
            ),
            "target_binding": _safe_payload(item.get("target_binding"), sanitize_text=sanitize_text),
            "scope_policy": _safe_payload(item.get("scope_policy"), sanitize_text=sanitize_text),
            "conflict_summary": _safe_payload(item.get("conflict_summary"), sanitize_text=sanitize_text),
            "safe_evidence_summary": _safe_evidence_summary(
                item.get("safe_evidence_summary"),
                sanitize_text=sanitize_text,
            ),
            "overlay_scope": sanitize_text(item.get("overlay_scope")).strip(),
            "decision_effect": sanitize_text(item.get("decision_effect")).strip(),
            "context_overlay_consumed": bool(item.get("context_overlay_consumed")),
            "provider_calls_started": False,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
        }
        if overlay["overlay_id"]:
            overlays.append(overlay)
    return overlays


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_evidence_summary(value: Any, *, sanitize_text: TextSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    summary = {
        "rating_count": _bounded_int(value.get("rating_count")),
        "decision_count": _bounded_int(value.get("decision_count")),
        "has_note": bool(value.get("has_note")),
        "raw_evidence_policy": sanitize_text(value.get("raw_evidence_policy")).strip()
        or "raw_evidence_not_memory",
    }
    if "taxonomy_count" in value:
        summary["taxonomy_count"] = _bounded_int(value.get("taxonomy_count"))
    return summary


def _safe_payload(value: Any, *, sanitize_text: TextSanitizer) -> Any:
    if isinstance(value, dict):
        return {
            sanitize_text(key).strip()[:80]: _safe_payload(item, sanitize_text=sanitize_text)
            for key, item in list(value.items())[:24]
            if sanitize_text(key).strip()
        }
    if isinstance(value, list):
        return [_safe_payload(item, sanitize_text=sanitize_text) for item in value[:24]]
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return _bounded_int(value)
    return sanitize_text(value).strip()[:180]


def _bounded_int(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(number, 1000))


__all__ = ("bundle_feedback_context_overlays",)
