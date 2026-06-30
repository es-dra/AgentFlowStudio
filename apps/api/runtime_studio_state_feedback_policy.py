from __future__ import annotations

import re
from typing import Any, Callable


SAFE_PROMPT_POLICY_ID_PATTERN = re.compile(r"[^a-zA-Z0-9_.:-]+")

TextSanitizer = Callable[[Any, str, int], str]
SafeId = Callable[[str], str]


def bundle_feedback_overlay_prompt_policy(
    value: Any,
    *,
    text: TextSanitizer,
    safe_id: SafeId,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for key in ("schema_version", "policy_id", "default_action", "overlay_text_channel"):
        item = text(value.get(key), "", 160)
        if item:
            result[key] = safe_id(item) if key == "policy_id" else item
    for key in ("provider_prompt_includes_context_overlays", "requires_explicit_prompt_policy_gate"):
        if key in value:
            result[key] = bool(value.get(key))
    if "context_overlay_count" in value:
        result["context_overlay_count"] = int(max(0, min(1000, _number(value.get("context_overlay_count"), 0))))
    for key in ("selected_overlay_ids", "rejected_overlay_ids"):
        ids = _safe_id_list(value.get(key), text=text)
        if ids:
            result[key] = ids
    gate = _bundle_prompt_provider_gate(value.get("prompt_provider_gate"), text=text, safe_id=safe_id)
    if gate:
        result["prompt_provider_gate"] = gate
    return result


def _bundle_prompt_provider_gate(
    value: Any,
    *,
    text: TextSanitizer,
    safe_id: SafeId,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for key in ("gate_id", "status", "gate_record_ref"):
        item = text(value.get(key), "", 160)
        if item:
            result[key] = safe_id(item) if key == "gate_id" else item
    for key in (
        "provider_prompt_inclusion_allowed",
        "requires_human_approval",
        "requires_provider_gate",
        "requires_prompt_budget_review",
        "requires_safety_filter",
    ):
        if key in value:
            result[key] = bool(value.get(key))
    return result


def _safe_id_list(value: Any, *, text: TextSanitizer) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value[:20]:
        safe_item = SAFE_PROMPT_POLICY_ID_PATTERN.sub("_", text(item, "", 180).strip())
        if safe_item and safe_item not in result:
            result.append(safe_item)
    return result


def _number(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


__all__ = ("bundle_feedback_overlay_prompt_policy",)
