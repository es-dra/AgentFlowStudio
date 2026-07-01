from __future__ import annotations

from typing import Any


VIDEO_DURATION_MIN_SECONDS = 1
VIDEO_DURATION_MAX_SECONDS = 15


def video_duration_contract(duration_sec: int) -> dict[str, Any]:
    return {
        "duration_seconds": int(duration_sec),
        "min_seconds": VIDEO_DURATION_MIN_SECONDS,
        "max_seconds": VIDEO_DURATION_MAX_SECONDS,
        "unit": "seconds",
        "validation_scope": "afs_request_contract",
    }


def video_input_source_contract(request: Any) -> dict[str, Any]:
    source = getattr(request, "input_source", None)
    if source is not None:
        payload = source.model_dump(mode="json") if hasattr(source, "model_dump") else dict(source)
    else:
        payload = {
            "source_mode": "explicit_first_frame_selection",
            "source_asset_id": getattr(request, "first_frame_image_asset_id", ""),
            "source_node_id": getattr(request, "node_id", None),
            "role": "first_frame",
        }
    payload["source_asset_id"] = str(payload.get("source_asset_id") or getattr(request, "first_frame_image_asset_id", "")).strip()
    payload["role"] = str(payload.get("role") or "first_frame").strip()
    return {key: value for key, value in payload.items() if value not in (None, "", [])}


def video_input_mode(request: Any) -> str:
    return "first_last_frame" if getattr(request, "last_frame_image_asset_id", None) else "first_frame"


__all__ = (
    "VIDEO_DURATION_MAX_SECONDS",
    "VIDEO_DURATION_MIN_SECONDS",
    "video_duration_contract",
    "video_input_mode",
    "video_input_source_contract",
)
