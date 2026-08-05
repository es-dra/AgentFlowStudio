"""Pure scene-block text matching helpers for Script Core Truth ownership extract.

Structural extract from runtime_script_core_truth.py — no behavior change.
These helpers only inspect source_text spans and member labels/aliases.
"""

from __future__ import annotations

import re
from typing import Any


def scene_evidence_start(scene: dict[str, Any]) -> int:
    starts = [
        int(span.get("start"))
        for span in (scene.get("evidence_spans") or [])
        if isinstance(span, dict) and isinstance(span.get("start"), int)
    ]
    return min(starts) if starts else -1


def scene_content_start(source_text: str, scene: dict[str, Any], scene_end: int) -> int:
    evidence_ends = [
        int(span.get("end"))
        for span in (scene.get("evidence_spans") or [])
        if isinstance(span, dict) and isinstance(span.get("end"), int)
    ]
    if not evidence_ends:
        return scene_end
    heading_evidence_end = max(evidence_ends)
    line_end = source_text.find("\n", heading_evidence_end, scene_end)
    return scene_end if line_end < 0 else line_end + 1


def member_spans_in_scene_block(
    source_text: str,
    start: int,
    end: int,
    member: dict[str, Any],
) -> list[dict[str, Any]]:
    labels = _clean_text_list(
        [
            str(member.get("display_name") or member.get("name") or ""),
            *[str(item) for item in (member.get("aliases") or [])],
        ]
    )
    spans: list[dict[str, Any]] = []
    block = source_text[start:end]
    seen: set[tuple[int, int]] = set()
    for label in labels:
        pattern = re.compile(rf"(?<!\w){re.escape(label)}(?!\w)", re.IGNORECASE)
        for match in pattern.finditer(block):
            absolute_start = start + match.start()
            absolute_end = start + match.end()
            identity = (absolute_start, absolute_end)
            if identity in seen:
                continue
            seen.add(identity)
            spans.append(
                {
                    "start": absolute_start,
                    "end": absolute_end,
                    "quote": source_text[absolute_start:absolute_end],
                }
            )
    return sorted(spans, key=lambda item: (item["start"], item["end"]))[:12]


def _clean_label(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:120]


def _clean_text_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for value in values:
        text = _clean_label(value)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            cleaned.append(text)
    return cleaned[:20]
