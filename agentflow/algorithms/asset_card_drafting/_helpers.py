from __future__ import annotations

import re
from typing import Any


def animal_label_from_prompt(prompt_text: str) -> str:
    text = clean_text(prompt_text).casefold()
    if "黑色" in prompt_text and "狸花猫" in prompt_text:
        return "黑色狸花猫"
    if "狸花猫" in prompt_text or "tabby" in text:
        return "狸花猫"
    if "猫" in prompt_text or "cat" in text or "kitten" in text or "feline" in text:
        return "猫主体资产"
    if "狗" in prompt_text or "犬" in prompt_text or "dog" in text or "puppy" in text:
        return "狗主体资产"
    return "动物主体资产"


def is_animal_subject_text(prompt_text: str) -> bool:
    text = clean_text(prompt_text).casefold()
    animal_terms = (
        "猫", "狸花猫", "黑猫", "白猫", "橘猫", "宠物", "动物", "狗", "犬",
        "cat", "tabby", "kitten", "feline", "dog", "puppy", "animal", "pet",
    )
    human_terms = (
        "人物", "人像", "真人", "人类", "女孩", "男孩", "女人", "男人", "女性", "男性",
        "头发", "发型", "校服", "服装", "person", "human", "girl", "boy", "woman",
        "man", "hair", "wardrobe", "uniform",
    )
    return any(term.casefold() in text for term in animal_terms) and not any(
        term.casefold() in text for term in human_terms
    )


def sentence_or_default(prompt_text: str, fallback: str) -> str:
    text = clean_text(prompt_text)
    if not text:
        return fallback
    first = re.split(r"[。.!?！？]\s*", text)[0]
    return first[:160] or fallback


def camera_motion(prompt_text: str) -> str:
    lowered = prompt_text.lower()
    if "push" in lowered or "推进" in lowered:
        return "slow push in"
    if "pan" in lowered or "摇" in lowered:
        return "pan"
    return "camera motion pending confirmation"


def prop_category(prompt_text: str) -> str:
    text = clean_text(prompt_text).casefold()
    if "compass" in text or "罗盘" in prompt_text:
        return "compass prop"
    if "key" in text or "钥匙" in prompt_text:
        return "key prop"
    if "photo" in text or "照片" in prompt_text:
        return "photo prop"
    return "prop category pending confirmation"


def missing_fields(card: dict[str, Any]) -> list[str]:
    return [key for key, value in card.items() if "待人工确认" in str(value) or "pending confirmation" in str(value)]


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())[:2000]
