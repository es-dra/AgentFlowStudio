from __future__ import annotations

import hashlib
import json
import re
from typing import Any


ALIAS_LINK_PROPOSAL_SCHEMA_VERSION = "afs.alias_link_proposal.v0.1"

_LINKABLE_TITLES = ("师傅", "老师", "医生", "老板", "教授", "警官", "主任", "经理")
_SCENE_SPLIT = re.compile(r"(?m)^[ \t]*第[一二三四五六七八九十百零\d]+场\b")
_EXPLICIT_AKA = re.compile(
    r"(?P<name>[\u4e00-\u9fff]{2,4})\s*[（(]\s*(?:外号|又名|也叫|小名)\s*[「『\"“]?"
    r"(?P<aka>[\u4e00-\u9fff]{1,4})[」』\"”]?\s*[）)]"
)
_TITLE_FORM = re.compile(
    rf"(?<![\u4e00-\u9fff])(?P<form>(?P<surname>[\u4e00-\u9fff])(?:{'|'.join(_LINKABLE_TITLES)}))"
)
_LAO_X = re.compile(r"(?<![\u4e00-\u9fff])老(?P<root>[\u4e00-\u9fff])(?![\u4e00-\u9fff])")
_OFFSTAGE_BEFORE_TITLE = re.compile(r"(?:远处[^。\n]{0,16})?(?:有人)?喊[：:]\s*$")


def build_alias_link_proposals(source_text: str, characters: list[Any]) -> list[dict[str, Any]]:
    """Build non-authoritative alias link proposals for analysis-candidates.

    These proposals never mutate character assets, never call merge_alias, and never
    write Production Graph state. They are source-backed hints for human review.
    """
    anchors = _anchors(characters)
    if not anchors:
        return []

    spans = _scene_spans(source_text)
    proposals: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def add(anchor: str, alias: str, method: str, confidence: float, evidence_spans: list[dict[str, Any]]) -> None:
        if anchor == alias or anchor not in anchors or not alias.strip():
            return
        key = (anchor, alias, method)
        if key in seen:
            return
        seen.add(key)
        proposal_identity = {
            "schema_version": ALIAS_LINK_PROPOSAL_SCHEMA_VERSION,
            "target_display_name": anchor,
            "alias": alias,
            "method": method,
        }
        proposals.append(
            {
                "proposal_id": f"aliasprop_{_sha256_json(proposal_identity)[:20]}",
                "schema_version": ALIAS_LINK_PROPOSAL_SCHEMA_VERSION,
                "relation_type": "alias_identity_link",
                "status": "candidate",
                "authority": "non_authoritative_proposal",
                "target_display_name": anchor,
                "alias": alias,
                "confidence": confidence,
                "evidence_spans": evidence_spans[:12],
                "extraction_method": method,
                "review_action": "use_core_asset_command_merge_alias",
                "provider_dispatch_count": 0,
                "remote_dispatch_count": 0,
            }
        )

    for match in _EXPLICIT_AKA.finditer(source_text):
        name = match.group("name")
        aka = match.group("aka")
        if name in anchors:
            add(name, aka, "explicit_aka_label", 0.95, [_span(source_text, match.start("aka"), match.end("aka"))])

    for match in _TITLE_FORM.finditer(source_text):
        form = match.group("form")
        surname = match.group("surname")
        if form in anchors or _is_offstage(source_text, match.start("form")):
            continue
        scene_index = _scene_index_for(match.start("form"), spans)
        candidates = [
            name
            for name in anchors
            if name.startswith(surname) and name != form and _surface_appears_in_scene(source_text, name, scene_index, spans)
        ]
        if len(candidates) == 1:
            add(
                candidates[0],
                form,
                "surname_title_same_scene",
                0.9,
                [_span(source_text, match.start("form"), match.end("form"))],
            )

    for match in _LAO_X.finditer(source_text):
        form = f"老{match.group('root')}"
        candidates = [name for name in anchors if name.startswith(match.group("root")) and name != form]
        if len(candidates) == 1:
            add(candidates[0], form, "lao_x_unique_anchor", 0.8, [_span(source_text, match.start(), match.end())])

    for anchor in sorted(anchors):
        suffix = _safe_given_name_suffix(anchor)
        if not suffix:
            continue
        candidates = [name for name in anchors if name.endswith(suffix)]
        if len(candidates) != 1:
            continue
        for match in _standalone_surface_matches(source_text, suffix):
            scene_index = _scene_index_for(match.start(), spans)
            if not _surface_appears_in_scene(source_text, anchor, scene_index, spans):
                continue
            add(anchor, suffix, "given_name_suffix_same_scene_unique_anchor", 0.72, [_span(source_text, match.start(), match.end())])

    return sorted(proposals, key=lambda item: (item["target_display_name"], item["alias"], item["extraction_method"]))


def _anchors(characters: list[Any]) -> set[str]:
    anchors: set[str] = set()
    for item in characters:
        value = getattr(item, "value", "")
        text = str(value or "").strip()
        if text:
            anchors.add(text)
    return anchors


def _safe_given_name_suffix(anchor: str) -> str:
    if not re.fullmatch(r"[\u4e00-\u9fff]{3,4}", anchor):
        return ""
    suffix = anchor[1:]
    return suffix if 2 <= len(suffix) <= 3 else ""


def _standalone_surface_matches(source_text: str, surface: str) -> list[re.Match[str]]:
    pattern = re.compile(rf"(?<![\u4e00-\u9fff]){re.escape(surface)}(?![\u4e00-\u9fff])")
    return [match for match in pattern.finditer(source_text)]


def _scene_spans(source_text: str) -> list[tuple[int, int]]:
    starts = [match.start() for match in _SCENE_SPLIT.finditer(source_text)]
    if not starts:
        return [(0, len(source_text))]
    if starts[0] > 0:
        starts = [0, *starts]
    return [
        (start, starts[index + 1] if index + 1 < len(starts) else len(source_text))
        for index, start in enumerate(starts)
    ]


def _scene_index_for(offset: int, spans: list[tuple[int, int]]) -> int:
    for index, (start, end) in enumerate(spans):
        if start <= offset < end:
            return index
    return max(0, len(spans) - 1)


def _surface_appears_in_scene(source_text: str, surface: str, scene_index: int, spans: list[tuple[int, int]]) -> bool:
    if scene_index < 0 or scene_index >= len(spans):
        return False
    start, end = spans[scene_index]
    return surface in source_text[start:end]


def _is_offstage(source_text: str, offset: int) -> bool:
    before = source_text[max(0, offset - 80) : offset]
    return bool(_OFFSTAGE_BEFORE_TITLE.search(before))


def _span(source_text: str, start: int, end: int) -> dict[str, Any]:
    return {"start": start, "end": end, "quote": source_text[start:end]}


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


__all__ = (
    "ALIAS_LINK_PROPOSAL_SCHEMA_VERSION",
    "build_alias_link_proposals",
)
