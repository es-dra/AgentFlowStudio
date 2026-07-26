from __future__ import annotations

from typing import Any

from apps.api.generation_path_contract import video_generation_path_contract, video_generation_path_id


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
        payload = _default_input_source_payload(request)
    fallback_asset_id = (
        getattr(request, "first_frame_image_asset_id", None)
        or getattr(request, "reference_video_artifact_id", None)
        or ""
    )
    payload["source_asset_id"] = str(payload.get("source_asset_id") or fallback_asset_id).strip()
    payload["role"] = str(payload.get("role") or _default_input_role(request)).strip()
    return {key: value for key, value in payload.items() if value not in (None, "", [])}


def video_input_mode(request: Any) -> str:
    path_id = video_generation_path_id(request)
    if path_id == "t2v":
        return "text_only"
    if path_id == "reference_video":
        return "reference_video"
    if path_id in {"director_to_keyframe", "director_to_video"}:
        return "director_setup"
    if path_id == "i2v_first_last":
        return "first_last_frame"
    if getattr(request, "reference_image_asset_ids", None):
        return "reference_images"
    return "first_frame"


def _default_input_source_payload(request: Any) -> dict[str, Any]:
    path_id = video_generation_path_id(request)
    if path_id == "t2v":
        return {
            "source_mode": "text_prompt",
            "source_node_id": getattr(request, "node_id", None),
            "role": "prompt_only",
        }
    if path_id == "reference_video":
        return {
            "source_mode": "reference_video",
            "source_asset_id": getattr(request, "reference_video_artifact_id", ""),
            "source_node_id": getattr(request, "node_id", None),
            "role": "reference_video",
        }
    if path_id in {"director_to_keyframe", "director_to_video"}:
        return {
            "source_mode": "director_setup",
            "source_node_id": getattr(request, "node_id", None),
            "role": "director_setup",
        }
    return {
        "source_mode": "explicit_first_frame_selection",
        "source_asset_id": getattr(request, "first_frame_image_asset_id", ""),
        "source_node_id": getattr(request, "node_id", None),
        "role": "first_frame",
    }


def _default_input_role(request: Any) -> str:
    path_id = video_generation_path_id(request)
    if path_id == "t2v":
        return "prompt_only"
    if path_id == "reference_video":
        return "reference_video"
    if path_id in {"director_to_keyframe", "director_to_video"}:
        return "director_setup"
    return "first_frame"


__all__ = (
    "VIDEO_DURATION_MAX_SECONDS",
    "VIDEO_DURATION_MIN_SECONDS",
    "video_duration_contract",
    "video_generation_path_contract",
    "video_input_mode",
    "video_input_source_contract",
)
