from __future__ import annotations

from typing import Any, Callable

from apps.api.runtime_store import safe_id


TextSanitizer = Callable[[Any, str, int], str]
PreviewUrlSanitizer = Callable[..., str]


def sanitize_assets(
    value: Any,
    *,
    project_id: str | None = None,
    text: TextSanitizer,
    preview_url: PreviewUrlSanitizer,
) -> list[dict[str, Any]]:
    source = value if isinstance(value, list) else []
    result: list[dict[str, Any]] = []
    for item in source[:300]:
        if not isinstance(item, dict):
            continue
        asset = {
            "id": safe_id(str(item.get("id", f"asset_{len(result) + 1}"))),
            "kind": text(item.get("kind") or item.get("type"), "reference", 60),
            "title": text(item.get("title"), "未命名资产", 120),
            "safe_summary": text(item.get("safe_summary") or item.get("summary"), "", 1000),
            "thumbnail_ref": text(item.get("thumbnail_ref"), "", 160),
            "source_node_id": text(item.get("source_node_id") or item.get("nodeId"), "", 80) or None,
            "status": text(item.get("status"), "ready", 40),
        }
        for key in ("asset_id", "visual_asset_id", "asset_type"):
            value_text = text(item.get(key), "", 120)
            if value_text:
                asset[key] = safe_id(value_text) if key.endswith("_id") else value_text
        signature = text(item.get("signature"), "", 1000)
        if signature:
            asset["signature"] = signature
        feature_card = _text_map(item.get("feature_card"), max_items=24, max_value_length=1000, text=text)
        if feature_card:
            asset["feature_card"] = feature_card
        negative_locks = _text_list(item.get("negative_locks"), max_items=24, max_item_length=500, text=text)
        if negative_locks:
            asset["negative_locks"] = negative_locks
        preview = item.get("preview_url")
        if preview:
            asset["preview_url"] = preview_url(preview, project_id=project_id)
        result.append(asset)
    return result


def _text_map(value: Any, *, max_items: int, max_value_length: int, text: TextSanitizer) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key, item in list(value.items())[:max_items]:
        safe_key = safe_id(str(key))[:80]
        if not safe_key:
            continue
        safe_value = text(item, "", max_value_length)
        if safe_value:
            result[safe_key] = safe_value
    return result


def _text_list(value: Any, *, max_items: int, max_item_length: int, text: TextSanitizer) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in (text(item, "", max_item_length) for item in value[:max_items]) if item]


__all__ = ("sanitize_assets",)
