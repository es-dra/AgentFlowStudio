from __future__ import annotations

import re
from typing import Any


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def token_key(value: Any) -> str:
    text = clean_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def has_cjk(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value)


def has_latin(value: str) -> bool:
    return bool(re.search(r"[A-Za-z]", value))


__all__ = ("clean_text", "has_cjk", "has_latin", "token_key")
