"""Deterministic discovery of suspected indirect name mentions (prototype only).

Reuses person-name validation from runtime_script_candidate_extraction.
Does NOT write analysis candidates or authority.
"""

from __future__ import annotations

import re
from typing import Any

from apps.api.runtime_script_candidate_extraction import (
    _BIO_INTRO,
    _CHARACTER_LABEL,
    _SPEAKER_CUE,
    _is_person_name,
    _looks_like_heading,
    _name_from_bio_lead,
    _next_nonempty_line,
    extract_characters,
)

# High-precision I1 cues only. Open prose NER is intentionally out of scope.
_QUOTE_NAME = re.compile(r"[「『\"“](?P<name>[\u4e00-\u9fff]{2,4})[」』\"”]")
_MENTION_CUE = re.compile(
    r"(?:"
    r"说起了|谈到了|想起了|提到了|"
    r"收款人是|收款人全是|"
    r"收件人写着|收件人永远写"
    r")(?P<name>[\u4e00-\u9fff]{2,4})"
)
# Keep 你爸/我爸 extremely tight: only when a short name is immediately followed by
# a kinship/plot continuation, not arbitrary four-character prose.
_PARENT_NAME_CUE = re.compile(
    r"(?:你爸|我爸)(?P<name>[\u4e00-\u9fff]{2,3})(?=以前|去世|案|[，。！？\s]|$)"
)


def discover_indirect_mention_candidates(source_text: str) -> list[dict[str, Any]]:
    """Find suspected name mentions that lack label/speaker/bio evidence at that span.

    Returns one record per unique mention name (first supporting span wins),
    sorted by start offset. Prototype-grade: cue/quote gated, not open NER.
    """
    evidenced = _evidenced_name_spans(source_text)
    extracted_names = {item.value for item in extract_characters(source_text)}
    hits: list[dict[str, Any]] = []

    for match in _QUOTE_NAME.finditer(source_text):
        hits.extend(
            _candidate_from_match(
                source_text,
                match,
                method="quoted_name",
                evidenced=evidenced,
            )
        )
    for match in _MENTION_CUE.finditer(source_text):
        hits.extend(
            _candidate_from_match(
                source_text,
                match,
                method="mention_cue",
                evidenced=evidenced,
            )
        )
    for match in _PARENT_NAME_CUE.finditer(source_text):
        hits.extend(
            _candidate_from_match(
                source_text,
                match,
                method="parent_name_cue",
                evidenced=evidenced,
            )
        )

    by_name: dict[str, dict[str, Any]] = {}
    for hit in sorted(hits, key=lambda item: (item["start"], item["end"], item["mention"])):
        name = hit["mention"]
        if name in by_name:
            by_name[name]["occurrence_count"] += 1
            by_name[name]["discovery_methods"] = sorted(
                set(by_name[name]["discovery_methods"]) | {hit["discovery_method"]}
            )
            continue
        by_name[name] = {
            "mention": name,
            "start": hit["start"],
            "end": hit["end"],
            "quote": hit["quote"],
            "discovery_method": hit["discovery_method"],
            "discovery_methods": [hit["discovery_method"]],
            "occurrence_count": 1,
            "already_extracted_as_character": name in extracted_names,
            "source_span": {
                "start": hit["start"],
                "end": hit["end"],
                "quote": hit["quote"],
            },
        }
    return sorted(by_name.values(), key=lambda item: (item["start"], item["mention"]))


def context_window(source_text: str, start: int, end: int, *, radius: int = 220) -> str:
    left = max(0, start - radius)
    right = min(len(source_text), end + radius)
    return source_text[left:right]


def _candidate_from_match(
    source_text: str,
    match: re.Match[str],
    *,
    method: str,
    evidenced: list[tuple[int, int, str]],
) -> list[dict[str, Any]]:
    name = match.group("name").strip()
    if not _is_person_name(name):
        return []
    start = match.start("name")
    end = match.end("name")
    if _overlaps_evidenced(start, end, evidenced):
        return []
    return [
        {
            "mention": name,
            "start": start,
            "end": end,
            "quote": source_text[start:end],
            "discovery_method": method,
        }
    ]


def _evidenced_name_spans(source_text: str) -> list[tuple[int, int, str]]:
    """Spans where deterministic extraction already has label/speaker/bio evidence."""
    spans: list[tuple[int, int, str]] = []
    for match in _CHARACTER_LABEL.finditer(source_text):
        for segment in re.finditer(r"[^、,，/;；]+", match.group("values")):
            raw = segment.group(0)
            without_bio = re.sub(r"[（(][^）)]*[）)]", "", raw).strip()
            if not _is_person_name(without_bio):
                continue
            relative = raw.find(without_bio)
            start = match.start("values") + segment.start() + relative
            spans.append((start, start + len(without_bio), without_bio))
    for match in _SPEAKER_CUE.finditer(source_text):
        name = match.group("name").strip()
        next_line = _next_nonempty_line(source_text, match.end())
        if not next_line or _looks_like_heading(next_line) or not _is_person_name(name):
            continue
        spans.append((match.start("name"), match.end("name"), name))
    for match in _BIO_INTRO.finditer(source_text):
        lead = match.group("lead").strip()
        name = _name_from_bio_lead(lead)
        if not _is_person_name(name):
            continue
        relative = lead.rfind(name)
        start = match.start("lead") + relative
        spans.append((start, start + len(name), name))
    return spans


def _overlaps_evidenced(start: int, end: int, evidenced: list[tuple[int, int, str]]) -> bool:
    for left, right, _name in evidenced:
        if start < right and left < end:
            return True
    return False


__all__ = (
    "context_window",
    "discover_indirect_mention_candidates",
)
