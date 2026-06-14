from __future__ import annotations

from typing import Any


def reference_image_size_blocks(
    images: list[dict[str, Any]],
    *,
    min_edge_px: int,
    capability: str,
    required_gate: str,
) -> list[dict[str, str]]:
    if min_edge_px <= 0:
        return []
    blocks: list[dict[str, str]] = []
    for item in images:
        public = item.get("public") if isinstance(item.get("public"), dict) else item
        width = _safe_int(public.get("width"))
        height = _safe_int(public.get("height"))
        if width >= min_edge_px and height >= min_edge_px:
            continue
        blocks.append(
            {
                "block_id": f"remote_{capability}_reference_image_too_small",
                "reason": (
                    f"Reference image is too small for remote {capability} provider: "
                    f"minimum {min_edge_px}px on each edge; got {width}x{height}. "
                    "Upload a larger reference image."
                ),
                "required_gate": required_gate,
            }
        )
    return blocks


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


__all__ = ("reference_image_size_blocks",)
