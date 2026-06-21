from __future__ import annotations

import re
from typing import Any


SECTION_HEADER_LABELS = (
    "意图",
    "角色",
    "角色/主体",
    "人物",
    "人物/主体",
    "主体",
    "场景",
    "场景/美术",
    "镜头",
    "镜头/构图",
    "灯光",
    "运动",
    "运动/时间推进",
    "连续性",
    "负面",
    "负面约束",
    "Intent",
    "Character",
    "Subject",
    "Scene",
    "Camera",
    "Lighting",
    "Motion",
    "Continuity",
    "Negative",
    "Negative Constraints",
)

_SECTION_HEADER_RE = re.compile(
    r"^\s*(?:" + "|".join(re.escape(label) for label in sorted(SECTION_HEADER_LABELS, key=len, reverse=True)) + r")\s*[：:]\s*",
    flags=re.IGNORECASE,
)


def strip_user_prompt_section_headers(value: str) -> str:
    """Return provider-facing text without human display section labels."""
    lines: list[str] = []
    for raw_line in str(value or "").splitlines():
        line = _SECTION_HEADER_RE.sub("", raw_line.strip()).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def plain_prompt_from_sections(sections: list[dict[str, Any]]) -> str:
    """Build the hidden provider-facing prompt from section text only."""
    lines: list[str] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        text = str(section.get("text") or "").strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


__all__ = ("plain_prompt_from_sections", "strip_user_prompt_section_headers")
