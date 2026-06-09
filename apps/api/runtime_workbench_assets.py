from __future__ import annotations

from typing import Any

from apps.api.runtime_workbench_support import list_value


def build_asset_library(manifest: dict[str, Any]) -> dict[str, Any]:
    items = [_asset_item(item) for item in list_value(manifest.get("source_assets")) if isinstance(item, dict)]
    items = [item for item in items if item["asset_id"]]
    counts = _counts(items)
    return {
        "status": "ready" if items else "needs_assets",
        "title": "Reference library",
        "summary": _summary(counts),
        "counts": counts,
        "items": items,
        "next_actions": _next_actions(counts),
        "safe_ref_policy": "safe source summaries only; no private asset locations or media bytes",
    }


def _asset_item(item: dict[str, Any]) -> dict[str, str]:
    asset_type = str(item.get("asset_type") or "reference")
    return {
        "asset_id": str(item.get("asset_id") or ""),
        "asset_type": asset_type,
        "label": str(item.get("label") or item.get("asset_id") or "Asset"),
        "summary": str(item.get("summary") or ""),
        "usage": _usage(asset_type),
        "safety": str(item.get("ref_kind") or "safe_summary"),
    }


def _counts(items: list[dict[str, str]]) -> dict[str, int]:
    counts = {"total": len(items), "brief": 0, "reference": 0, "script": 0, "other": 0}
    for item in items:
        asset_type = item["asset_type"].lower()
        if asset_type in counts and asset_type != "total":
            counts[asset_type] += 1
        else:
            counts["other"] += 1
    return counts


def _summary(counts: dict[str, int]) -> str:
    if not counts["total"]:
        return "Add a brief, script, or visual reference before production checks."
    return f"{counts['total']} safe source summaries are attached."


def _next_actions(counts: dict[str, int]) -> list[str]:
    actions = []
    if not counts["brief"]:
        actions.append("Add a campaign brief or task brief summary.")
    if not counts["reference"]:
        actions.append("Add approved visual or style reference summaries.")
    if not counts["script"]:
        actions.append("Add script, outline, or scene source summaries when available.")
    return actions or ["Reference library is ready for planning and review."]


def _usage(asset_type: str) -> str:
    labels = {
        "brief": "Project setup",
        "reference": "Visual reference",
        "script": "Scene planning",
    }
    return labels.get(asset_type.lower(), "Supporting context")


__all__ = ("build_asset_library",)
