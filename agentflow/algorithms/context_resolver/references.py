from __future__ import annotations

from typing import Any


def merged_reference_image_refs(
    *,
    request_asset_refs: list[str] | tuple[str, ...],
    context_bundle: dict[str, Any] | None,
) -> list[str]:
    if not context_bundle:
        return _dedupe_refs(request_asset_refs)
    refs = [
        str(item.get("asset_id") or "").strip()
        for item in context_bundle.get("reference_image_channel", [])
        if isinstance(item, dict)
    ]
    refs.extend(str(item or "").strip() for item in request_asset_refs)
    return _dedupe_refs(refs)


def _dedupe_refs(refs: list[str] | tuple[str, ...]) -> list[str]:
    result: list[str] = []
    for ref in refs:
        clean = str(ref or "").strip()
        if clean and clean not in result:
            result.append(clean)
    return result


__all__ = ("merged_reference_image_refs",)
