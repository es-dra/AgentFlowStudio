from __future__ import annotations

import re
from typing import Any


UNREQUESTED_SET_PIECES = (
    "木椅",
    "椅子",
    "凳子",
    "屋檐",
    "飞檐",
    "篮子",
    "chair",
    "stool",
    "eaves",
)


def storyboard_source_span(source: str, full_source: str, index: int) -> dict[str, Any]:
    clean_source = clean_text(source)
    clean_full = clean_text(full_source) or clean_source
    start = clean_full.find(clean_source) if clean_source else -1
    end = start + len(clean_source) if start >= 0 else -1
    grounded = bool(clean_source and (start >= 0 or clean_full == clean_source))
    return {
        "span_id": f"script_span_{index:02d}",
        "text": clean_source[:500],
        "start": start,
        "end": end,
        "grounding_status": "source_grounded" if grounded else "missing_source_text" if not clean_source else "source_span_not_found",
    }


def unsupported_additions_for_description(description: str, source_text: str) -> list[str]:
    desc = str(description or "")
    source = str(source_text or "")
    additions: list[str] = []
    for term in UNREQUESTED_SET_PIECES:
        if term in desc and term not in source:
            additions.append(term)
    return additions


def grounding_status_for_unsupported(unsupported: list[str]) -> str:
    return "needs_review_unsupported_addition" if unsupported else "source_grounded"


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


__all__ = (
    "clean_text",
    "grounding_status_for_unsupported",
    "storyboard_source_span",
    "unsupported_additions_for_description",
)
