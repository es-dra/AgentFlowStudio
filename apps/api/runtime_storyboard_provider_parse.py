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
from apps.api.runtime_storyboard_local import structured_shot


SHOT_SIZE_LABELS = {
    "extreme_close_up": "极近特写",
    "big_close_up": "大特写",
    "close_up": "特写",
    "closeup": "特写",
    "detail_shot": "细节特写",
    "insert_shot": "插入特写",
    "insert": "插入特写",
    "medium_close_up": "中近景",
    "medium_closeup": "中近景",
    "medium_shot": "中景",
    "medium": "中景",
    "medium_wide": "中远景",
    "medium_wide_shot": "中远景",
    "wide": "远景",
    "wide_shot": "远景",
    "long_shot": "远景",
    "full_shot": "全景",
    "full_body": "全身景",
    "establishing_shot": "定场远景",
    "establishing": "定场远景",
    "over_the_shoulder": "过肩镜头",
    "pov": "主观镜头",
    "point_of_view": "主观镜头",
}

CAMERA_MOTION_LABELS = {
    "static": "固定机位",
    "locked_off": "固定机位",
    "fixed": "固定机位",
    "tripod": "三脚架固定",
    "handheld": "手持轻晃",
    "hand_held": "手持轻晃",
    "tracking": "跟拍移动",
    "tracking_shot": "跟拍移动",
    "follow": "跟随拍摄",
    "follow_shot": "跟随拍摄",
    "dolly_in": "缓慢推近",
    "push_in": "缓慢推近",
    "truck_in": "缓慢推近",
    "dolly_out": "缓慢拉远",
    "pull_back": "缓慢拉远",
    "pull_out": "缓慢拉远",
    "pan": "横摇",
    "pan_left": "向左横摇",
    "pan_right": "向右横摇",
    "tilt": "俯仰摇镜",
    "tilt_up": "向上摇镜",
    "tilt_down": "向下摇镜",
    "crane_up": "升镜",
    "crane_down": "降镜",
    "orbit": "环绕运动",
    "arc": "弧线环绕",
    "rack_focus": "焦点转移",
    "shallow_depth_of_field": "浅景深",
    "deep_focus": "深焦",
    "slight_rise": "轻微上升",
    "rise": "上升运动",
    "rising": "上升运动",
    "slow_motion": "慢动作",
    "camera_shake": "镜头震动",
    "shake": "镜头震动",
    "whip_pan": "快速甩镜",
}

FOCUS_TARGET_LABELS = {
    "fingertip": "指尖",
    "fingertips": "指尖",
    "finger": "手指",
    "fingers": "手指",
    "score": "分数",
    "test_paper": "试卷",
    "paper": "试卷",
    "exam_paper": "试卷",
    "eyes": "眼睛",
    "eye": "眼睛",
    "face": "面部",
    "expression": "表情",
    "subject": "主体",
    "background": "背景",
    "sword": "剑",
}

CAMERA_MOTION_LABEL_ORDER = (
    "固定机位",
    "三脚架固定",
    "手持轻晃",
    "跟拍移动",
    "跟随拍摄",
    "缓慢推近",
    "缓慢拉远",
    "轻微上升",
    "上升运动",
    "向上摇镜",
    "向下摇镜",
    "俯仰摇镜",
    "向左横摇",
    "向右横摇",
    "快速甩镜",
    "横摇",
    "升镜",
    "降镜",
    "环绕运动",
    "弧线环绕",
    "浅景深",
    "深焦",
    "焦点转移",
    "慢动作",
    "镜头震动",
)

LIGHT_ATMOSPHERE_RULES = (
    (("high_contrast", "chiaroscuro"), "高反差明暗对照"),
    (("cold", "blue", "green", "key_light", "storm_clouds"), "暴风云层投下冷蓝绿色主光"),
    (("deep_indigo_shadows", "craters", "weapon_grooves"), "深靛色阴影在弹坑与兵器沟槽中堆积"),
    (("deep_indigo_shadows",), "深靛色阴影压低画面暗部"),
    (("mist", "diffusing", "highlights"), "雾气柔化高光"),
    (("rim_light",), "轮廓光勾边"),
    (("backlight",), "逆光勾勒主体"),
    (("low_key",), "低调光压暗环境"),
    (("warm", "key_light"), "暖色主光"),
    (("cold", "key_light"), "冷色主光"),
)

SOUND_RULES = (
    (("thunder", "rumble", "low_frequency"), "低频雷鸣轰隆"),
    (("thunder", "rumble"), "雷鸣轰隆"),
    (("torrential_rain", "metal", "earth"), "暴雨击打金属与泥土"),
    (("torrential_rain",), "暴雨持续倾泻"),
    (("distant", "guttural", "growls", "layered_beneath"), "远处喉音低吼在底层铺陈"),
    (("distant", "guttural", "growls"), "远处喉音低吼"),
    (("low_frequency",), "低频氛围音"),
    (("metal",), "金属受击声"),
    (("earth",), "泥土受雨声"),
)


def shots_from_provider_text(text: str, *, source_script_text: str = "") -> list[dict[str, Any]]:
    payload = _json_from_text(text)
    raw_shots = payload.get("shots")
    if not isinstance(raw_shots, list):
        raise ValueError("provider storyboard response missing shots")
    shots = [
        _normalize_provider_shot(item, index + 1, source_script_text=source_script_text)
        for index, item in enumerate(raw_shots)
    ]
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


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _localized_shot_size(value: Any, fallback: str) -> str:
    text = _clean(value)
    if not text:
        return str(fallback)
    key = _token_key(text)
    if key in SHOT_SIZE_LABELS:
        return SHOT_SIZE_LABELS[key]
    if _has_cjk(text):
        return _localize_display_text(text)
    return str(fallback)


def _localized_camera_motion(value: Any, fallback: str) -> str:
    text = _clean(value)
    if not text:
        return str(fallback)
    if _has_cjk(text) and not _has_latin(text):
        return _localize_display_text(text)
    parts = [part.strip() for part in re.split(r"[,;，；、]+", text) if part.strip()]
    localized: list[str] = []
    for part in parts or [text]:
        for label in _camera_motion_labels_for_part(part):
            if label and label not in localized:
                localized.append(label)
    localized = _compact_camera_motion_labels(localized)
    return "，".join(localized) if localized else str(fallback)


def _camera_motion_labels_for_part(value: str) -> list[str]:
    key = _token_key(value)
    if key in CAMERA_MOTION_LABELS:
        return [CAMERA_MOTION_LABELS[key]]
    labels: list[str] = []
    for token, label in sorted(CAMERA_MOTION_LABELS.items(), key=lambda item: len(item[0]), reverse=True):
        if token in key and label not in labels:
            labels.append(label)
    target = _focus_target_label(key)
    if target:
        labels.append(f"焦点锁定{target}")
    mimic = _mimicked_motion_label(value)
    if mimic:
        labels.append(mimic)
    return labels


def _compact_camera_motion_labels(labels: list[str]) -> list[str]:
    compact = list(labels)
    specific_tilts = {CAMERA_MOTION_LABELS["tilt_up"], CAMERA_MOTION_LABELS["tilt_down"]}
    if any(label in compact for label in specific_tilts):
        compact = [label for label in compact if label != CAMERA_MOTION_LABELS["tilt"]]
    specific_pans = {
        CAMERA_MOTION_LABELS["pan_left"],
        CAMERA_MOTION_LABELS["pan_right"],
        CAMERA_MOTION_LABELS["whip_pan"],
    }
    if any(label in compact for label in specific_pans):
        compact = [label for label in compact if label != CAMERA_MOTION_LABELS["pan"]]
    if CAMERA_MOTION_LABELS["slight_rise"] in compact:
        compact = [label for label in compact if label != CAMERA_MOTION_LABELS["rise"]]
    return sorted(compact, key=_camera_motion_label_order)


def _camera_motion_label_order(label: str) -> tuple[int, int, str]:
    if label.startswith("焦点锁定"):
        return (len(CAMERA_MOTION_LABEL_ORDER), 0, label)
    if label.startswith("模拟"):
        return (len(CAMERA_MOTION_LABEL_ORDER) + 1, 0, label)
    try:
        return (CAMERA_MOTION_LABEL_ORDER.index(label), 0, label)
    except ValueError:
        return (len(CAMERA_MOTION_LABEL_ORDER) + 2, 0, label)


def _mimicked_motion_label(value: str) -> str:
    match = re.search(
        r"mimick(?:ing)?\s*([\u4e00-\u9fffA-Za-z0-9_-]+)?(?:'s|’s)?\s*(jump|leap)",
        value,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    subject = str(match.group(1) or "").strip()
    if subject:
        return f"模拟{subject}跳跃"
    return "模拟跳跃动作"


def _focus_target_label(key: str) -> str:
    match = re.search(r"focus_on_(.+)$", key)
    if not match:
        return ""
    target = re.sub(r"^(?:the_)?", "", match.group(1))
    target = target.replace("_and_", "_")
    labels: list[str] = []
    for token in target.split("_"):
        label = FOCUS_TARGET_LABELS.get(token)
        if label and label not in labels:
            labels.append(label)
    return "和".join(labels)


def _localized_light_atmosphere(value: Any, fallback: str) -> str:
    return _localized_english_field(value, fallback, LIGHT_ATMOSPHERE_RULES)


def _localized_sound(value: Any, fallback: str) -> str:
    return _localized_english_field(value, fallback, SOUND_RULES)


def _localized_english_field(
    value: Any,
    fallback: str,
    rules: tuple[tuple[tuple[str, ...], str], ...],
) -> str:
    text = _localize_display_text(value)
    if not text:
        return str(fallback)
    if not _has_latin(text):
        return text
    key = _token_key(text)
    labels: list[str] = []
    for required_tokens, label in rules:
        if all(token in key for token in required_tokens) and label not in labels:
            labels.append(label)
    if rules is LIGHT_ATMOSPHERE_RULES:
        labels = _compact_light_atmosphere_labels(labels)
    elif rules is SOUND_RULES:
        labels = _compact_sound_labels(labels)
    if labels:
        return "，".join(labels)
    return str(fallback)


def _compact_light_atmosphere_labels(labels: list[str]) -> list[str]:
    compact = list(labels)
    specific_shadow = "深靛色阴影在弹坑与兵器沟槽中堆积"
    generic_shadow = "深靛色阴影压低画面暗部"
    if specific_shadow in compact:
        compact = [label for label in compact if label != generic_shadow]
    specific_key_light = "暴风云层投下冷蓝绿色主光"
    generic_key_light = "冷色主光"
    if specific_key_light in compact:
        compact = [label for label in compact if label != generic_key_light]
    return compact


def _compact_sound_labels(labels: list[str]) -> list[str]:
    compact = list(labels)
    suppressions = {
        "低频雷鸣轰隆": {"雷鸣轰隆", "低频氛围音"},
        "暴雨击打金属与泥土": {"暴雨持续倾泻", "金属受击声", "泥土受雨声"},
        "远处喉音低吼在底层铺陈": {"远处喉音低吼"},
    }
    for specific, generic_labels in suppressions.items():
        if specific in compact:
            compact = [label for label in compact if label not in generic_labels]
    return compact


def _localize_display_text(value: Any) -> str:
    text = _clean(value)
    replacements = {
        "(OS)": "（画外音）",
        "（OS）": "（画外音）",
        "(V.O.)": "（旁白）",
        "（V.O.）": "（旁白）",
        "(VO)": "（旁白）",
        "（VO）": "（旁白）",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _token_key(value: Any) -> str:
    text = _clean(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def _has_cjk(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value)


def _has_latin(value: str) -> bool:
    return bool(re.search(r"[A-Za-z]", value))


__all__ = ("shots_from_provider_text",)
