from __future__ import annotations

import json
import re
from typing import Any

from apps.api.runtime_storyboard_local import normalize_asset_ref, structured_shot


def shots_from_provider_text(text: str, *, source_script_text: str = "") -> list[dict[str, Any]]:
    payload = _json_from_text(text)
    raw_shots = payload.get("shots")
    if not isinstance(raw_shots, list):
        raise ValueError("provider storyboard response missing shots")
    shots = [_normalize_provider_shot(item, index + 1) for index, item in enumerate(raw_shots)]
    shots = [item for item in shots if item]
    if not shots:
        raise ValueError("provider storyboard response has no usable shots")
    _validate_provider_shots(shots, source_script_text)
    return shots


def _json_from_text(text: str) -> dict[str, Any]:
    source = _strip_json_fences(text)
    try:
        payload = json.loads(source)
    except json.JSONDecodeError:
        payload = _first_json_object_with_shots(source)
    if not isinstance(payload, dict):
        raise ValueError("provider storyboard response root is not object")
    return payload


def _strip_json_fences(text: str) -> str:
    source = str(text or "").strip()
    if source.startswith("```"):
        lines = source.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        source = "\n".join(lines).strip()
    return source


def _first_json_object_with_shots(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            payload, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("shots"), list):
            return payload
    raise ValueError("provider storyboard response is not json") from None


def _normalize_provider_shot(item: Any, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    description = _clean(item.get("description") or item.get("source_text") or "")
    fallback = structured_shot(description, index)
    asset_refs = item.get("asset_refs")
    if isinstance(asset_refs, list) and asset_refs:
        refs = [normalize_asset_ref(asset, idx) for idx, asset in enumerate(asset_refs)]
        refs = [ref for ref in refs if ref]
    else:
        refs = fallback["asset_refs"]
    return {
        **fallback,
        "shot_id": str(item.get("shot_id") or fallback["shot_id"]),
        "index": int(item.get("index") or index),
        "duration": str(item.get("duration") or fallback["duration"]),
        "description": description or fallback["description"],
        "shot_size": str(item.get("shot_size") or fallback["shot_size"]),
        "light_atmosphere": str(item.get("light_atmosphere") or fallback["light_atmosphere"]),
        "camera_motion": str(item.get("camera_motion") or fallback["camera_motion"]),
        "dialogue": str(item.get("dialogue") or fallback["dialogue"]),
        "sound": str(item.get("sound") or fallback["sound"]),
        "asset_refs": refs,
        "source_text": _clean(item.get("source_text") or description),
    }


def _validate_provider_shots(shots: list[dict[str, Any]], source_script_text: str) -> None:
    source_len = len("".join(str(source_script_text or "").split()))
    if source_len < 120:
        return
    if source_len >= 260 and len(shots) < 3:
        raise ValueError("provider storyboard response too sparse for source script")
    if len(shots) < 2:
        raise ValueError("provider storyboard response too sparse for source script")

    asset_ref_count = sum(len(item.get("asset_refs") or []) for item in shots)
    if asset_ref_count == 0:
        raise ValueError("provider storyboard response missing asset refs")

    descriptive_len = sum(len(_descriptive_text(item.get("description"))) for item in shots)
    required_len = min(120, max(40, source_len // 5))
    if descriptive_len < required_len:
        raise ValueError("provider storyboard response lacks visual detail")


def _descriptive_text(value: Any) -> str:
    text = re.sub(r"@[\w\u4e00-\u9fff-]+", "", str(value or ""))
    return "".join(char for char in text if not char.isspace() and char not in "，。,.；;：:、")


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


__all__ = ("shots_from_provider_text",)
