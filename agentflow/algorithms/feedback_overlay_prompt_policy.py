from __future__ import annotations

import re
from typing import Any


SCHEMA_VERSION = "afs_feedback_overlay_prompt_policy.v0.1"
POLICY_ID = "feedback_overlay_context_evidence_only_v0"
DEFAULT_ACTION = "context_evidence_only"
OVERLAY_TEXT_CHANNEL = "disabled_by_default"
PROMPT_GATE_ID = "feedback_overlay_provider_prompt_gate_v0"
PROMPT_GATE_STATUS = "blocked_by_default"

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.:-]+")


def feedback_overlay_prompt_policy(
    *,
    context_bundle: dict[str, Any] | None = None,
    context_overlays: list[dict[str, Any]] | None = None,
    selected_overlay_ids: list[str] | set[str] | tuple[str, ...] | None = None,
    rejected_overlay_ids: list[str] | set[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    overlays = _overlay_list(context_overlays, context_bundle)
    trace = context_bundle.get("trace_summary") if isinstance(context_bundle, dict) else {}
    selected = selected_overlay_ids if selected_overlay_ids is not None else _trace_ids(trace, "feedback_context_overlay_selected_ids")
    rejected = rejected_overlay_ids if rejected_overlay_ids is not None else _trace_ids(trace, "feedback_context_overlay_rejected_ids")
    return {
        "schema_version": SCHEMA_VERSION,
        "policy_id": POLICY_ID,
        "default_action": DEFAULT_ACTION,
        "provider_prompt_includes_context_overlays": False,
        "overlay_text_channel": OVERLAY_TEXT_CHANNEL,
        "requires_explicit_prompt_policy_gate": True,
        "prompt_provider_gate": feedback_overlay_prompt_provider_gate(),
        "context_overlay_count": len(overlays),
        "selected_overlay_ids": _safe_ids(selected),
        "rejected_overlay_ids": _safe_ids(rejected),
    }


def feedback_overlay_prompt_provider_gate() -> dict[str, Any]:
    return {
        "gate_id": PROMPT_GATE_ID,
        "status": PROMPT_GATE_STATUS,
        "provider_prompt_inclusion_allowed": False,
        "requires_human_approval": True,
        "requires_provider_gate": True,
        "requires_prompt_budget_review": True,
        "requires_safety_filter": True,
        "gate_record_ref": "not_approved",
    }


def _overlay_list(
    context_overlays: list[dict[str, Any]] | None,
    context_bundle: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if isinstance(context_overlays, list):
        return [item for item in context_overlays if isinstance(item, dict)]
    values = context_bundle.get("feedback_context_overlays") if isinstance(context_bundle, dict) else []
    return [item for item in values if isinstance(item, dict)] if isinstance(values, list) else []


def _trace_ids(trace: Any, key: str) -> list[str]:
    if not isinstance(trace, dict):
        return []
    values = trace.get(key)
    return values if isinstance(values, list) else []


def _safe_ids(values: list[str] | set[str] | tuple[str, ...] | None) -> list[str]:
    result: list[str] = []
    source = sorted(values) if isinstance(values, set) else values or []
    for value in source:
        text = _SAFE_ID_RE.sub("_", str(value or "").strip())[:180]
        if text and text not in result:
            result.append(text)
    return result


__all__ = (
    "DEFAULT_ACTION",
    "OVERLAY_TEXT_CHANNEL",
    "POLICY_ID",
    "PROMPT_GATE_ID",
    "PROMPT_GATE_STATUS",
    "SCHEMA_VERSION",
    "feedback_overlay_prompt_provider_gate",
    "feedback_overlay_prompt_policy",
)
