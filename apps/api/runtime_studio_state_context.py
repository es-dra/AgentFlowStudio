from __future__ import annotations

import re
from typing import Any

from apps.api.runtime_store import safe_id


LOCAL_PATH_PATTERN = re.compile(r"([a-zA-Z]:\\|/Users/|/home/|data/processed/runs)")
SAFE_PROMPT_POLICY_ID_PATTERN = re.compile(r"[^a-zA-Z0-9_.:-]+")


def sanitize_context_bundle(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for key in ("schema_version", "resolver_version", "mode", "subject_reference_asset_id"):
        text = _text(value.get(key), "", 120)
        if text:
            result[key] = safe_id(text) if key.endswith("_id") else text
    for key in ("included_assets", "excluded_assets", "available_project_assets"):
        items = _bundle_asset_list(value.get(key))
        if items:
            result[key] = items
    warnings = _bundle_warning_list(value.get("warnings"))
    if warnings:
        result["warnings"] = warnings
    overrides = _bundle_override_list(value.get("temporary_lock_overrides"))
    if overrides:
        result["temporary_lock_overrides"] = overrides
    budget = _bundle_budget(value.get("budget"))
    if budget:
        result["budget"] = budget
    overlays = _bundle_feedback_overlay_list(value.get("feedback_context_overlays"))
    if overlays:
        result["feedback_context_overlays"] = overlays
    trace = value.get("trace_summary") if isinstance(value.get("trace_summary"), dict) else {}
    policy = _bundle_feedback_overlay_prompt_policy(
        value.get("feedback_context_overlay_prompt_policy")
        or trace.get("feedback_context_overlay_prompt_policy")
    )
    if policy:
        result["feedback_context_overlay_prompt_policy"] = policy
    return result


def _bundle_asset_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    for item in value[:80]:
        if not isinstance(item, dict):
            continue
        asset: dict[str, Any] = {}
        for key in ("asset_id", "visual_asset_id", "source_node_id", "feature_card_hash"):
            text = _text(item.get(key), "", 160)
            if text:
                asset[key] = safe_id(text) if key.endswith("_id") or key == "source_node_id" else text
        for key in ("asset_type", "label", "signature", "status", "reason", "channel", "connected_state"):
            text = _text(item.get(key), "", 1000 if key in {"signature", "reason"} else 160)
            if text:
                asset[key] = text
        for key in ("hop_count", "hop_distance"):
            if key in item:
                asset[key] = _number(item.get(key), 0)
        if "lock_count" in item:
            asset["lock_count"] = int(_number(item.get("lock_count"), 0))
        if item.get("subject_reference") is not None:
            asset["subject_reference"] = bool(item.get("subject_reference"))
        if asset:
            result.append(asset)
    return result


def _bundle_warning_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    allowed = {
        "warning_id",
        "asset_id",
        "label",
        "lock_text",
        "attribute",
        "lock_value",
        "prompt_value",
        "reason",
    }
    for item in value[:80]:
        if not isinstance(item, dict):
            continue
        warning: dict[str, Any] = {}
        for key in allowed:
            text = _text(item.get(key), "", 500)
            if text:
                warning[key] = safe_id(text) if key.endswith("_id") else text
        if warning:
            result.append(warning)
    return result


def _bundle_override_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    for item in value[:40]:
        if not isinstance(item, dict):
            continue
        override: dict[str, Any] = {}
        asset_id = _text(item.get("asset_id"), "", 160)
        if asset_id:
            override["asset_id"] = safe_id(asset_id)
        for key in ("lock_text", "reason"):
            text = _text(item.get(key), "", 500)
            if text:
                override[key] = text
        if override:
            result.append(override)
    return result


def _bundle_budget(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for key in ("limit", "total_limit", "used", "total_used"):
        if key in value:
            result[key] = _number(value.get(key), 0)
    if "enforcement_applied" in value:
        result["enforcement_applied"] = bool(value.get("enforcement_applied"))
    segments = value.get("segments")
    if isinstance(segments, dict):
        safe_segments: dict[str, Any] = {}
        for name, segment in list(segments.items())[:20]:
            if not isinstance(segment, dict):
                continue
            safe_segment: dict[str, Any] = {}
            for key in ("allocated", "used"):
                if key in segment:
                    safe_segment[key] = _number(segment.get(key), 0)
            if "truncated" in segment:
                safe_segment["truncated"] = bool(segment.get("truncated"))
            if safe_segment:
                safe_segments[safe_id(str(name))[:80]] = safe_segment
        if safe_segments:
            result["segments"] = safe_segments
    return result


def _bundle_feedback_overlay_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    for item in value[:5]:
        if not isinstance(item, dict):
            continue
        overlay: dict[str, Any] = {}
        for key in (
            "overlay_id",
            "source_feedback_id",
            "source_promotion_decision_id",
            "candidate_id",
            "candidate_scope",
            "overlay_scope",
            "overlay_intent",
            "decision_effect",
        ):
            text = _text(item.get(key), "", 600 if key == "overlay_intent" else 180)
            if text:
                overlay[key] = text
        safe_target = _safe_text_dict(item.get("safe_target"), max_items=12, max_length=180)
        if safe_target:
            overlay["safe_target"] = safe_target
        evidence = _safe_evidence_summary(item.get("safe_evidence_summary"))
        if evidence:
            overlay["safe_evidence_summary"] = evidence
        for key in (
            "context_overlay_consumed",
            "candidate_feedback_included_in_context",
            "provider_calls_started",
            "writes_long_term_memory",
            "writes_company_kb",
        ):
            if key in item:
                overlay[key] = bool(item.get(key))
        artifact_ref = _safe_artifact_ref(item.get("artifact_ref"))
        if artifact_ref:
            overlay["artifact_ref"] = artifact_ref
        if overlay.get("overlay_id"):
            result.append(overlay)
    return result


def _safe_text_dict(value: Any, *, max_items: int, max_length: int) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key, item in list(value.items())[:max_items]:
        safe_key = safe_id(_text(key, "", 80))[:80]
        safe_value = _text(item, "", max_length)
        if safe_key and safe_value:
            result[safe_key] = safe_value
    return result


def _safe_evidence_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for key in ("rating_count", "decision_count"):
        if key in value:
            result[key] = int(max(0, min(1000, _number(value.get(key), 0))))
    if "has_note" in value:
        result["has_note"] = bool(value.get("has_note"))
    policy = _text(value.get("raw_evidence_policy"), "", 120)
    if policy:
        result["raw_evidence_policy"] = policy
    return result


def _safe_artifact_ref(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key in ("artifact_id", "artifact_type", "role", "filename"):
        text = _text(value.get(key), "", 180)
        if text:
            result[key] = text
    return result


def _bundle_feedback_overlay_prompt_policy(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for key in ("schema_version", "policy_id", "default_action", "overlay_text_channel"):
        text = _text(value.get(key), "", 160)
        if text:
            result[key] = safe_id(text) if key == "policy_id" else text
    for key in ("provider_prompt_includes_context_overlays", "requires_explicit_prompt_policy_gate"):
        if key in value:
            result[key] = bool(value.get(key))
    if "context_overlay_count" in value:
        result["context_overlay_count"] = int(max(0, min(1000, _number(value.get("context_overlay_count"), 0))))
    for key in ("selected_overlay_ids", "rejected_overlay_ids"):
        ids = _safe_id_list(value.get(key))
        if ids:
            result[key] = ids
    gate = _bundle_prompt_provider_gate(value.get("prompt_provider_gate"))
    if gate:
        result["prompt_provider_gate"] = gate
    return result


def _bundle_prompt_provider_gate(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for key in ("gate_id", "status", "gate_record_ref"):
        text = _text(value.get(key), "", 160)
        if text:
            result[key] = safe_id(text) if key == "gate_id" else text
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


def _safe_id_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value[:20]:
        text = SAFE_PROMPT_POLICY_ID_PATTERN.sub("_", _text(item, "", 180).strip())
        if text and text not in result:
            result.append(text)
    return result


def _text(value: Any, fallback: str, max_length: int) -> str:
    text = str(value if value is not None else fallback)
    if LOCAL_PATH_PATTERN.search(text):
        raise ValueError("studio state contains local path or runtime artifact path")
    return text[:max_length]


def _number(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


__all__ = ("sanitize_context_bundle",)
