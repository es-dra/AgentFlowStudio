from __future__ import annotations

import re
from typing import Any

from apps.api.runtime_store import safe_id


LOCAL_PATH_PATTERN = re.compile(r"([a-zA-Z]:\\|/Users/|/home/|data/processed/runs)")


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
