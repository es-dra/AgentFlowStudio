from __future__ import annotations

import re
from typing import Any

from apps.api.runtime_models import PromptOptimizationRequest


ZH_SUBJECT_PATTERN = re.compile(r"(一个|一位|这位|那个)?(男孩|女孩|男人|女人|少年|少女|老人|侦探|创始人|导演|艺术家|角色[A-Z]?)")
ZH_SCENE_PATTERN = re.compile(r"在([^，。；、]{1,24}?(?:房间|街道|街|室内|办公室|走廊|天台|餐厅|教室|片场|车内|广场|城市|森林|海边|门口|桌边|观测站|工作室))(?:里|中|内)?")
EN_CHARACTER_PATTERN = re.compile(
    r"\b(?:a|an|the)?\s*([a-zA-Z-]+(?:\s+[a-zA-Z-]+){0,2}\s+(?:detective|founder|director|artist|creator|lead|hero))\b",
    re.I,
)


def extract_prompt_slots(request: PromptOptimizationRequest) -> dict[str, str]:
    prompt = request.prompt_text.strip()
    slots = {
        "language": "zh" if _contains_zh(prompt + request.style) else "en",
        "intent": _intent(request),
        "subject": _subject(request),
        "scene": _scene(prompt),
        "action": _action(prompt),
        "emotion": _emotion(prompt + " " + request.style),
        "lighting": _lighting(prompt + " " + request.style),
        "camera": _camera(prompt + " " + request.style),
        "motion": _motion(prompt + " " + request.style),
        "style": _style(request.style),
        "preference": _preference(request.style),
        "negative": "provider_gate_closed",
        "platform": request.target_platform,
    }
    if request.asset_refs:
        slots["asset_refs"] = ",".join(request.asset_refs)
    if request.director_setup:
        slots["director_setup"] = _director_setup_summary(request.director_setup.model_dump(mode="json"))
    return slots


def _contains_zh(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value)


def _intent(request: PromptOptimizationRequest) -> str:
    return f"{request.node_type} node for {request.generation_target} generation"


def _subject(request: PromptOptimizationRequest) -> str:
    if request.director_setup:
        for item in request.director_setup.characters:
            label = _clean(str(item.get("label") or item.get("name") or ""))
            if label:
                return label
    zh_match = ZH_SUBJECT_PATTERN.search(request.prompt_text)
    if zh_match:
        return f"{zh_match.group(1) or ''}{zh_match.group(2)}"
    en_match = EN_CHARACTER_PATTERN.search(request.prompt_text)
    if en_match:
        return _title(en_match.group(1))
    for keyword in ("detective", "founder", "director", "artist", "creator", "lead", "hero"):
        if keyword in request.prompt_text.lower():
            return _title(keyword)
    return "Primary character"


def _scene(prompt: str) -> str:
    zh_match = ZH_SCENE_PATTERN.search(prompt)
    if zh_match:
        return _clean(zh_match.group(1).rstrip("里中内"))
    patterns = [
        r"\b(rainy neon street)\b",
        r"\b(abandoned observatory)(?:\s+at\s+blue\s+hour)?\b",
        r"\b(neon street)\b",
        r"\b(observatory)\b",
        r"\b(studio)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt, re.I)
        if match:
            return _title(match.group(1))
    return "Primary scene"


def _action(prompt: str) -> str:
    text = re.split(r"[。；.!?]", prompt, maxsplit=1)[0]
    return _clean(text) or "visible action from the node prompt"


def _emotion(value: str) -> str:
    for keyword in ("情绪低落", "孤独", "紧张", "克制", "真实", "愤怒", "惊讶", "恐惧", "温暖", "melancholy", "tense", "calm"):
        if keyword.lower() in value.lower():
            return keyword
    return "emotion implied by the prompt"


def _lighting(value: str) -> str:
    for keyword in ("低照度室内光线", "昏暗", "冷光", "暖光", "窗外冷光", "台灯暖光", "low key", "soft light", "neon"):
        if keyword.lower() in value.lower():
            return keyword
    return "motivated cinematic light"


def _camera(value: str) -> str:
    for keyword in ("镜头缓慢推进", "缓慢推进", "低角度", "手持", "固定机位", "dolly", "push in", "tracking", "handheld"):
        if keyword.lower() in value.lower():
            return keyword
    return "camera movement aligned with the beat"


def _motion(value: str) -> str:
    for keyword in ("缓慢推进", "走向", "抬头", "轻微呼吸", "甩镜", "sweeping", "pull back", "push in", "tracking"):
        if keyword.lower() in value.lower():
            return keyword
    return "subtle subject and camera motion"


def _style(value: str) -> str:
    cleaned = _clean(value)
    return cleaned or "cinematic"


def _preference(value: str) -> str:
    match = re.search(r"用户偏好[:：]([^；;]+)", value)
    if match:
        return _clean(match.group(1))
    english = re.search(r"user\s+preference\s*:\s*([^;]+)", value, re.I)
    if english:
        return _clean(english.group(1))
    return ""


def _director_setup_summary(setup: dict[str, Any]) -> str:
    parts = []
    for key in ("characters", "lights", "cameras"):
        labels = [str(item.get("label") or item.get("name") or "item") for item in setup.get(key, []) if isinstance(item, dict)]
        if labels:
            parts.append(f"{key}=" + ",".join(labels))
    return "; ".join(parts) or "top_down_2d"


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" .,:;，。；")


def _title(value: str) -> str:
    cleaned = _clean(value)
    return cleaned[:1].upper() + cleaned[1:] if cleaned else cleaned


__all__ = ("extract_prompt_slots",)
