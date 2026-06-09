from __future__ import annotations

from typing import Any

from apps.api.runtime_workbench_support import list_value


def build_asset_library(manifest: dict[str, Any]) -> dict[str, Any]:
    items = [_asset_item(item) for item in list_value(manifest.get("source_assets")) if isinstance(item, dict)]
    items = [item for item in items if item["asset_id"]]
    counts = _counts(items)
    return {
        "status": "ready" if items else "needs_assets",
        "title": "素材库",
        "summary": _summary(counts),
        "counts": counts,
        "items": items,
        "next_actions": _next_actions(counts),
        "safe_ref_policy": "仅使用安全素材摘要；不暴露私有素材路径或媒体字节",
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
        return "先添加需求、脚本或视觉参考摘要，再进入制作检查。"
    return f"已附加 {counts['total']} 条安全素材摘要。"


def _next_actions(counts: dict[str, int]) -> list[str]:
    actions = []
    if not counts["brief"]:
        actions.append("添加项目需求或任务摘要。")
    if not counts["reference"]:
        actions.append("添加已确认的视觉或风格参考摘要。")
    if not counts["script"]:
        actions.append("如有脚本、大纲或场景来源，补充对应摘要。")
    return actions or ["素材库已可用于分镜规划和审片。"]


def _usage(asset_type: str) -> str:
    labels = {
        "brief": "项目设置",
        "reference": "视觉参考",
        "script": "场景规划",
    }
    return labels.get(asset_type.lower(), "辅助上下文")


__all__ = ("build_asset_library",)
