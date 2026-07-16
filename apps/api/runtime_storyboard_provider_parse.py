from __future__ import annotations

import json
import re
from typing import Any

from apps.api.runtime_asset_extraction import normalize_asset_refs_with_diagnostics, principal_asset_refs_with_diagnostics
from apps.api.runtime_storyboard_grounding import (
    grounding_status_for_unsupported,
    storyboard_source_span,
    unsupported_additions_for_description,
)
from apps.api.runtime_storyboard_asset_coverage import reconcile_storyboard_asset_coverage
from apps.api.runtime_storyboard_local import structured_shot
from apps.api.runtime_storyboard_provider_latin_guard import (
    validate_localized_display_fields as _validate_localized_display_fields,
    validate_raw_display_field_english as _validate_raw_display_field_english,
)
from apps.api.runtime_storyboard_provider_localization import (
    localized_camera_motion as _localized_camera_motion,
    localized_light_atmosphere as _localized_light_atmosphere,
    localized_shot_size as _localized_shot_size,
    localized_sound as _localized_sound,
    localize_display_text as _localize_display_text,
)
from apps.api.runtime_storyboard_provider_text import clean_text as _clean


def shots_from_provider_text(text: str, *, source_script_text: str = "") -> list[dict[str, Any]]:
    payload = _json_from_text(text)
    raw_shots = payload.get("shots")
    if not isinstance(raw_shots, list):
        raise ValueError("provider storyboard response missing shots")
    _validate_raw_display_field_english(raw_shots, source_script_text)
    shots = [
        _normalize_provider_shot(item, index + 1, source_script_text=source_script_text)
        for index, item in enumerate(raw_shots)
    ]
    shots = [item for item in shots if item]
    if not shots:
        raise ValueError("provider storyboard response has no usable shots")
    shots = reconcile_storyboard_asset_coverage(shots)
    _validate_provider_shots(shots, source_script_text)
    _validate_localized_display_fields(shots, source_script_text)
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


def _normalize_provider_shot(item: Any, index: int, *, source_script_text: str = "") -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    description = _localize_display_text(_clean(item.get("description") or item.get("source_text") or ""))
    source_span = _provider_source_span(item.get("source_span"), description, source_script_text, index)
    fallback = structured_shot(source_span["text"] or description, index, full_source=source_script_text or description)
    asset_refs = item.get("asset_refs")
    gate_context = "\n".join(part for part in (source_span["text"], description) if part)
    if isinstance(asset_refs, list) and asset_refs:
        refs, dropped_refs = normalize_asset_refs_with_diagnostics(
            asset_refs,
            context=gate_context,
            include_inferred=True,
        )
        refs, dropped_refs = principal_asset_refs_with_diagnostics(refs, dropped_refs)
    else:
        refs = fallback["asset_refs"]
        dropped_refs = list(fallback.get("dropped_asset_ref_diagnostics") or [])
    unsupported = unsupported_additions_for_description(description, source_span["text"])
    return {
        **fallback,
        "shot_id": str(item.get("shot_id") or fallback["shot_id"]),
        "index": int(item.get("index") or index),
        "duration": str(item.get("duration") or fallback["duration"]),
        "description": description or fallback["description"],
        "shot_size": _localized_shot_size(item.get("shot_size"), fallback["shot_size"]),
        "light_atmosphere": _localized_light_atmosphere(
            item.get("light_atmosphere"),
            fallback["light_atmosphere"],
        ),
        "camera_motion": _localized_camera_motion(item.get("camera_motion"), fallback["camera_motion"]),
        "dialogue": _localize_display_text(item.get("dialogue") or fallback["dialogue"]),
        "sound": _localized_sound(item.get("sound"), fallback["sound"]),
        "asset_refs": refs,
        "dropped_asset_ref_diagnostics": dropped_refs,
        "source_text": _localize_display_text(_clean(item.get("source_text") or description)),
        "source_span": source_span,
        "grounding_status": grounding_status_for_unsupported(unsupported),
        "unsupported_additions": unsupported,
        "planning_agent": {
            **fallback.get("planning_agent", {}),
            "agent_id": "storyboard_provider_structured",
            "mode": "llm_structured_json_normalized",
            "evidence_policy": "source_span_required",
        },
    }


def _provider_source_span(raw: Any, description: str, source_script_text: str, index: int) -> dict[str, Any]:
    if isinstance(raw, dict):
        text = _clean(raw.get("text") or raw.get("source_text") or "")
        if text:
            span = storyboard_source_span(text, source_script_text or text, index)
            if raw.get("span_id"):
                span["span_id"] = str(raw.get("span_id"))
            return span
    return _closest_source_span(description, source_script_text, index)


def _closest_source_span(description: str, source_script_text: str, index: int) -> dict[str, Any]:
    source = _clean(source_script_text)
    if not source:
        return storyboard_source_span(description, description, index)
    sentences = [part.strip() for part in re.split(r"(?<=[。！？!?；;])\s*", source) if part.strip()]
    if not sentences:
        return storyboard_source_span(source, source, index)
    best = max(sentences, key=lambda sentence: _overlap_score(description, sentence))
    return storyboard_source_span(best, source, index)


def _overlap_score(left: str, right: str) -> int:
    left_chars = {char for char in str(left or "") if "\u4e00" <= char <= "\u9fff" or char.isalnum()}
    right_chars = {char for char in str(right or "") if "\u4e00" <= char <= "\u9fff" or char.isalnum()}
    return len(left_chars.intersection(right_chars))


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


__all__ = ("shots_from_provider_text",)
