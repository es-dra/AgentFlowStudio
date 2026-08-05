from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

from apps.api.runtime_script_alias_proposals import build_alias_link_proposals


DETERMINISTIC_EXTRACTION_SCHEMA_VERSION = "afs.deterministic_script_extraction.v0.1"
ALIAS_LINK_PROPOSALS_ENV = "AFS_ENABLE_ALIAS_LINK_PROPOSALS"


@dataclass(frozen=True)
class ExtractedFact:
    value: str
    start: int
    end: int
    confidence: float
    method: str

    def evidence_span(self, source_text: str) -> dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "quote": source_text[self.start : self.end],
        }


_GENERIC_PEOPLE = frozenset(
    {
        "女人",
        "男人",
        "女孩",
        "男孩",
        "老人",
        "孩子",
        "小孩",
        "陌生人",
        "来电者",
        "对方",
        "路人",
        "乘客",
        "观众",
        "职员",
    }
)
_ALLOWED_ROLE_NAMES = frozenset(
    {
        "母亲",
        "父亲",
        "妈妈",
        "爸爸",
        "奶奶",
        "爷爷",
        "外婆",
        "外公",
        "姐姐",
        "哥哥",
        "弟弟",
        "妹妹",
        "儿子",
        "女儿",
        "老师",
        "医生",
        "警察",
    }
)
_NON_NAME_WORDS = frozenset(
    {
        "标题",
        "时间",
        "地点",
        "场景",
        "人物",
        "角色",
        "第一场",
        "第二场",
        "第三场",
        "第四场",
        "第五场",
    }
)
_BAD_NAME_START = frozenset("从在到把被让向往和与对用比这那有不也都很就才再还只将一")
_BAD_NAME_END = frozenset(
    "没从不道的了着过在是和与把被让给向往到用对比很也都就才又再还已会能要想"
    "说问看走跑递开发现决定进入握住停下坐站拿翻举望听喊叫哭笑抖"
)
_BIO_ROLE_MARKERS = ("她的朋友", "他的朋友", "朋友", "邮局职员", "职员", "老师", "医生", "警察")

_VAGUE_SCENES = frozenset(
    {
        "房间",
        "一个房间",
        "昏暗的房间",
        "某处",
        "某个地方",
        "室内",
        "室外",
    }
)
_SCENE_JUNK = frozenset(
    {
        "颤抖",
        "灯上",
        "柜台前",
        "柜台上",
        "礁石上",
        "远处",
        "从远处",
        "身边",
        "书桌前",
    }
)

_CHARACTER_LABEL = re.compile(
    r"(?im)^[ \t]*(?:人物|角色|characters|cast)[ \t]*[:：][ \t]*(?P<values>[^\r\n。；;]+)"
)
_SCENE_LABEL = re.compile(
    r"(?im)^[ \t]*(?:地点|场景|locations?|scenes?)[ \t]*[:：][ \t]*(?P<values>[^\r\n。；;]+)"
)
_SPEAKER_CUE = re.compile(
    r"(?m)^[ \t]*(?P<name>[\u4e00-\u9fff]{2,4}|[A-Z][a-z]{1,18})[ \t]*\r?$"
)
_BIO_INTRO = re.compile(
    r"(?m)^[ \t]*(?P<lead>[\u4e00-\u9fff]{2,12})[（(][^）)\r\n]{2,100}[）)]"
)
_INDUSTRY_HEADING = re.compile(
    r"(?im)^[ \t]*(?:第[一二三四五六七八九十百零\d]+场[ \t]*[-—–][ \t]*)?"
    r"(?:内景|外景|INT\.?|EXT\.?)"
    r"[ \t]*[-—–][ \t]*(?P<location>[^\r\n—–-]+?)"
    r"[ \t]*[-—–][ \t]*[^\r\n]+$"
)


def build_deterministic_analysis_candidate(
    *,
    project_id: str,
    revision_id: str,
    source_digest: str,
    source_text: str,
    candidate_schema_version: str,
) -> dict[str, Any]:
    characters = extract_characters(source_text)
    scenes = extract_scenes(source_text)
    alias_link_proposals = (
        build_alias_link_proposals(source_text, characters)
        if _alias_link_proposals_enabled()
        else []
    )
    missing_slots: list[str] = []
    notes: list[str] = []
    if not characters:
        missing_slots.append("named_characters")
        notes.append("named characters missing: no source-backed proper name found")
    if not scenes:
        missing_slots.append("main_scenes")
        notes.append("main scenes missing: no specific labeled location or industry heading found")
    return {
        "project_id": project_id,
        "revision_id": revision_id,
        "source_digest": source_digest,
        "schema_version": candidate_schema_version,
        "named_characters": [
            {
                "display_name": item.value,
                "aliases": [],
                "pronoun_links": [],
                "evidence_spans": [item.evidence_span(source_text)],
                "confidence": item.confidence,
                "status": "candidate",
                "evidence_status": "extracted_from_text",
                "extraction_method": item.method,
            }
            for item in characters
        ],
        "main_scenes": [
            {
                "name": item.value,
                "evidence_spans": [item.evidence_span(source_text)],
                "confidence": item.confidence,
                "status": "candidate",
                "evidence_status": "extracted_from_text",
                "extraction_method": item.method,
            }
            for item in scenes
        ],
        "missing_slots": missing_slots,
        "extraction_notes": notes,
        "alias_link_proposals": alias_link_proposals,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _alias_link_proposals_enabled() -> bool:
    return str(os.getenv(ALIAS_LINK_PROPOSALS_ENV, "")).strip().lower() in {"1", "true", "yes", "on"}


def extract_characters(source_text: str) -> list[ExtractedFact]:
    facts: list[ExtractedFact] = []
    for match in _CHARACTER_LABEL.finditer(source_text):
        facts.extend(
            _facts_from_labeled_values(
                source_text,
                match.group("values"),
                match.start("values"),
                confidence=0.98,
                method="labeled_character_field",
                validator=_is_person_name,
            )
        )
    for match in _SPEAKER_CUE.finditer(source_text):
        name = match.group("name").strip()
        next_line = _next_nonempty_line(source_text, match.end())
        if not next_line or _looks_like_heading(next_line) or not _is_person_name(name):
            continue
        facts.append(
            ExtractedFact(
                value=name,
                start=match.start("name"),
                end=match.end("name"),
                confidence=0.9,
                method="dialogue_speaker_cue",
            )
        )
    for match in _BIO_INTRO.finditer(source_text):
        lead = match.group("lead").strip()
        name = _name_from_bio_lead(lead)
        if not _is_person_name(name):
            continue
        relative = lead.rfind(name)
        start = match.start("lead") + relative
        facts.append(
            ExtractedFact(
                value=name,
                start=start,
                end=start + len(name),
                confidence=0.92,
                method="character_bio_intro",
            )
        )
    return _dedupe(facts)


def extract_scenes(source_text: str) -> list[ExtractedFact]:
    facts: list[ExtractedFact] = []
    for match in _SCENE_LABEL.finditer(source_text):
        facts.extend(
            _facts_from_labeled_values(
                source_text,
                match.group("values"),
                match.start("values"),
                confidence=0.98,
                method="labeled_scene_field",
                validator=_is_specific_scene,
            )
        )
    for match in _INDUSTRY_HEADING.finditer(source_text):
        raw = match.group("location")
        location = raw.strip()
        if not _is_specific_scene(location):
            continue
        left_trim = len(raw) - len(raw.lstrip())
        start = match.start("location") + left_trim
        facts.append(
            ExtractedFact(
                value=location,
                start=start,
                end=start + len(location),
                confidence=0.98,
                method="industry_scene_heading",
            )
        )
    return _dedupe(facts)


def _facts_from_labeled_values(
    source_text: str,
    raw_values: str,
    source_start: int,
    *,
    confidence: float,
    method: str,
    validator,
) -> list[ExtractedFact]:
    del source_text
    facts: list[ExtractedFact] = []
    for segment in re.finditer(r"[^、,，/;；]+", raw_values):
        raw = segment.group(0)
        without_bio = re.sub(r"[（(][^）)]*[）)]", "", raw).strip()
        if not validator(without_bio):
            continue
        relative = raw.find(without_bio)
        start = source_start + segment.start() + relative
        facts.append(
            ExtractedFact(
                value=without_bio,
                start=start,
                end=start + len(without_bio),
                confidence=confidence,
                method=method,
            )
        )
    return facts


def _dedupe(facts: list[ExtractedFact]) -> list[ExtractedFact]:
    best: dict[str, ExtractedFact] = {}
    order: list[str] = []
    for fact in facts:
        existing = best.get(fact.value)
        if existing is None:
            best[fact.value] = fact
            order.append(fact.value)
        elif fact.confidence > existing.confidence:
            best[fact.value] = fact
    return [best[value] for value in order]


def _next_nonempty_line(source_text: str, offset: int) -> str:
    for line in source_text[offset:].splitlines():
        value = line.strip()
        if value:
            return value
    return ""


def _looks_like_heading(value: str) -> bool:
    return bool(
        re.match(r"^第[一二三四五六七八九十百零\d]+场", value)
        or re.match(r"^(?:内景|外景|INT\.?|EXT\.?)\b", value, re.I)
        or re.match(r"^(?:时间|地点|场景|人物|角色)[ \t]*[:：]", value)
    )


def _name_from_bio_lead(lead: str) -> str:
    for marker in _BIO_ROLE_MARKERS:
        index = lead.rfind(marker)
        if index >= 0:
            suffix = lead[index + len(marker) :].strip()
            if suffix:
                return suffix
    return lead


def _is_person_name(value: str) -> bool:
    name = value.strip()
    if name in _GENERIC_PEOPLE or name in _NON_NAME_WORDS or not name:
        return False
    if name in _ALLOWED_ROLE_NAMES:
        return True
    if re.fullmatch(r"[\u4e00-\u9fff]{2,4}", name):
        if name[0] in _BAD_NAME_START or name[-1] in _BAD_NAME_END:
            return False
        if any(fragment in name for fragment in ("苏晴没", "道他", "可能", "一个", "一名", "一位")):
            return False
        return True
    return bool(re.fullmatch(r"[A-Z][a-z]{1,18}", name))


def _is_specific_scene(value: str) -> bool:
    scene = value.strip()
    if not scene or scene in _VAGUE_SCENES or scene in _SCENE_JUNK:
        return False
    if re.fullmatch(r"(?:一[个間]|某个)?(?:昏暗的|黑暗的|狭小的)?房间", scene):
        return False
    if len(scene) > 80 or not re.fullmatch(r"[\u4e00-\u9fffA-Za-z0-9·的中之\- ]{2,80}", scene):
        return False
    return True


__all__ = (
    "ALIAS_LINK_PROPOSALS_ENV",
    "DETERMINISTIC_EXTRACTION_SCHEMA_VERSION",
    "ExtractedFact",
    "build_deterministic_analysis_candidate",
    "extract_characters",
    "extract_scenes",
)
