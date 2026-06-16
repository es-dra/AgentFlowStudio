from __future__ import annotations

import re
from typing import Any


ATTRIBUTE_GROUPS: dict[str, dict[str, tuple[str, ...]]] = {
    "hair_color": {
        "black": (r"re:\bblack\b(?:\s+[\w'-]+){0,2}\s+hair\b", "黑发", "黑色头发"),
        "brown": (r"re:\bbrown\b(?:\s+[\w'-]+){0,2}\s+hair\b", "棕发", "棕色头发"),
        "blonde": (r"re:\bblonde?\b(?:\s+[\w'-]+){0,2}\s+hair\b", "金发", "金色头发"),
        "red": (r"re:\bred\b(?:\s+[\w'-]+){0,2}\s+hair\b", "红发", "红色头发"),
        "white": (r"re:\bwhite\b(?:\s+[\w'-]+){0,2}\s+hair\b", "白发", "白色头发"),
        "silver": (r"re:\bsilver\b(?:\s+[\w'-]+){0,2}\s+hair\b", "银发", "银色头发"),
        "gray": (r"re:\bgr[ae]y\b(?:\s+[\w'-]+){0,2}\s+hair\b", "灰发", "灰色头发"),
        "blue": (r"re:\bblue\b(?:\s+[\w'-]+){0,2}\s+hair\b", "蓝发", "蓝色头发"),
        "green": (r"re:\bgreen\b(?:\s+[\w'-]+){0,2}\s+hair\b", "绿发", "绿色头发"),
        "purple": (r"re:\bpurple\b(?:\s+[\w'-]+){0,2}\s+hair\b", "紫发", "紫色头发"),
        "pink": (r"re:\bpink\b(?:\s+[\w'-]+){0,2}\s+hair\b", "粉发", "粉色头发"),
    },
    "hair_length": {
        "short": ("short hair", "短发"),
        "long": ("long hair", "长发"),
        "shoulder_length": ("shoulder-length hair", "shoulder length hair", "齐肩发", "及肩发"),
        "bald": ("bald", "光头", "秃头"),
    },
    "hair_texture": {
        "straight": ("straight hair", "直发"),
        "curly": ("curly hair", "卷发"),
        "wavy": ("wavy hair", "波浪发", "微卷发"),
        "braided": ("braid", "braided hair", "辫子", "麻花辫"),
        "ponytail": ("ponytail", "马尾", "马尾辫"),
        "bun": ("hair bun", "丸子头", "发髻"),
    },
    "eye_color": {
        "black": ("black eyes", "黑色眼睛", "黑瞳"),
        "brown": ("brown eyes", "棕色眼睛", "褐色眼睛"),
        "blue": ("blue eyes", "蓝色眼睛", "蓝瞳"),
        "green": ("green eyes", "绿色眼睛", "绿瞳"),
        "gray": ("gray eyes", "grey eyes", "灰色眼睛"),
        "amber": ("amber eyes", "琥珀色眼睛"),
    },
    "outfit_color": {
        "black": ("black coat", "black dress", "black suit", "black jacket", "black shirt", "黑色外套", "黑色风衣", "黑衣"),
        "white": ("white coat", "white dress", "white suit", "white jacket", "white shirt", "白色外套", "白衣"),
        "red": ("red coat", "red dress", "red suit", "red jacket", "red shirt", "红色外套", "红色风衣", "红衣"),
        "blue": ("blue coat", "blue dress", "blue suit", "blue jacket", "blue shirt", "蓝色外套", "蓝衣"),
        "green": ("green coat", "green dress", "green suit", "green jacket", "green shirt", "绿色外套"),
        "yellow": ("yellow coat", "yellow dress", "yellow jacket", "黄色外套"),
        "purple": ("purple coat", "purple dress", "purple jacket", "紫色外套"),
        "gray": ("gray coat", "grey coat", "gray suit", "灰色外套", "灰色西装"),
    },
    "build": {
        "slim": ("slim build", "slender", "瘦削", "纤细"),
        "muscular": ("muscular", "肌肉发达", "健壮"),
        "heavy": ("heavyset", "stocky", "魁梧", "壮硕"),
        "petite": ("petite", "娇小"),
    },
    "facial_mark": {
        "scar": ("scar", "疤痕", "刀疤"),
        "mole": ("mole", "痣"),
        "freckles": ("freckles", "雀斑"),
        "tattoo": ("tattoo", "纹身", "刺青"),
        "clean_face": ("clean face", "no marks", "面部无痕", "无疤"),
    },
}

_ASCII_TERM = re.compile(r"^[\x00-\x7f]+$")


def attribute_values_in_text(text: str) -> dict[str, set[str]]:
    folded = str(text or "").casefold()
    found: dict[str, set[str]] = {}
    for attribute, values in ATTRIBUTE_GROUPS.items():
        for value, terms in values.items():
            for term in terms:
                if _term_in_text(term, folded):
                    found.setdefault(attribute, set()).add(value)
                    break
    return found


def find_lock_conflicts(lock_text: str, prompt_text: str) -> list[dict[str, Any]]:
    lock_values = attribute_values_in_text(lock_text)
    prompt_values = attribute_values_in_text(prompt_text)
    conflicts: list[dict[str, Any]] = []
    for attribute, locked in sorted(lock_values.items()):
        asserted = prompt_values.get(attribute) or set()
        for lock_value in sorted(locked):
            for prompt_value in sorted(asserted):
                if prompt_value != lock_value:
                    conflicts.append(
                        {
                            "attribute": attribute,
                            "lock_value": lock_value,
                            "prompt_value": prompt_value,
                        }
                    )
    return conflicts


def _term_in_text(term: str, folded_text: str) -> bool:
    if term.startswith("re:"):
        return re.search(term[3:], folded_text, flags=re.IGNORECASE) is not None
    folded_term = term.casefold()
    if _ASCII_TERM.match(folded_term):
        return re.search(rf"\b{re.escape(folded_term)}\b", folded_text) is not None
    return folded_term in folded_text


__all__ = ("ATTRIBUTE_GROUPS", "attribute_values_in_text", "find_lock_conflicts")
