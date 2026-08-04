"""Improved Character + Scene + ScriptProfile + ScriptFormatProfile + Beat extraction.

Promoted from docs/internal-notes/draft_improved_extraction_20260802.py.

Character/Scene results remain a feature-flagged shadow beside M6's legacy
extractors. ScriptProfile facets are consumed only by the candidate confirmation
refresh path, as are explicit Beat boundaries. Both require
AFS_USE_IMPROVED_EXTRACTION and AFS_USE_CANDIDATE_CONFIRMATION_LOOP. Raw
extraction never writes Production Graph.

Hard rules
----------
1. Labeled 人物：/地点： beats everything (high-confidence extracted_from_text).
2. Industry heading 第N场 - 内景 - <地点> - <时间> is structured extract, not junk regex.
3. Verb-prefix name grab (「苏晴没说话」→「苏晴没」) is intentionally NOT used.
4. 「在柜台前」direction fragments are rejected as scene names.
5. Generic roles (女人/男人…) without a proper name → missing, not a fake name.
6. ScriptProfile accepts explicit metadata label lines only; never infer from plot.
7. Beat boundaries accept explicit numbered labels only, scoped to an owning Scene.
8. Beat facets (conflict/turn/info_release/emotion_shift) accept explicit labels
   only inside a Beat range; emotion_shift requires from+to+change together.
9. ScriptFormatProfile only projects existing structured Scene signals and
   conservative text-cleaning diagnostics; it does not infer story content.
10. Scene cast appearance accepts speaker cues / in-scene 人物： labels only
    inside a uniquely resolved Scene range; never cross-scene inference.
11. Scene props accept explicit prop labels or a conservative physical-object
    vocabulary with a same-clause possession/manipulation/state signal. They
    never infer set dressing from the location or plot.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


SCHEMA_VERSION = "afs.script_understanding.improved_extraction.v0.1"


class ExtractStatus(str, Enum):
    EXTRACTED_FROM_TEXT = "extracted_from_text"
    MODEL_INFERRED = "model_inferred"
    MISSING = "missing"


@dataclass(frozen=True)
class ExtractedItem:
    text: str
    status: ExtractStatus
    confidence: float
    method: str
    evidence: str = ""


ScriptProfileFacetName = Literal[
    "theme",
    "genre",
    "audience",
    "narrative_goals",
    "style_requirements",
]


@dataclass(frozen=True)
class ScriptProfileFacetExtraction:
    """One labeled-only ScriptProfile facet for the shared candidate ledger."""

    facet: ScriptProfileFacetName
    field_path: str
    item: ExtractedItem
    uncertainty_note: str | None = None


ScriptFormatStyle = Literal["labeled", "industry_heading", "mixed", "unclear"]


@dataclass(frozen=True)
class ScriptCleaningIssue:
    """One conservative, source-bound text-cleaning diagnostic."""

    note: str
    start: int
    end: int


@dataclass(frozen=True)
class ScriptFormatProfileExtraction:
    """Revision-level projection of already-computed script input structure."""

    format_style: ScriptFormatStyle
    cleaning_issues: tuple[ScriptCleaningIssue, ...]
    scene_occurrences: tuple[ExtractedItem, ...]

    @property
    def cleaning_notes(self) -> tuple[str, ...]:
        return tuple(issue.note for issue in self.cleaning_issues)

    @property
    def scene_boundary_count(self) -> int:
        return len(self.scene_occurrences)


@dataclass(frozen=True)
class ExtractedBeatBoundary:
    """One explicit numbered Beat label and its reviewed Scene-local source range."""

    order_index: int
    source_start: int
    source_end: int
    evidence_start: int
    evidence_end: int
    marker: str
    label: str
    method: str = "explicit_numbered_beat_label"


BeatFacetName = Literal["conflict", "turn", "info_release", "emotion_shift"]


@dataclass(frozen=True)
class ExtractedBeatFacet:
    """One labeled-only Beat facet (or emotion sub-part) inside a Beat range."""

    facet: BeatFacetName
    field_suffix: str
    item: ExtractedItem
    evidence_start: int | None = None
    evidence_end: int | None = None
    uncertainty_note: str | None = None


@dataclass
class ExtractionResult:
    """Per-script extraction with explicit missing slots when nothing credible."""

    characters: list[ExtractedItem] = field(default_factory=list)
    scenes: list[ExtractedItem] = field(default_factory=list)
    character_name_status: ExtractStatus = ExtractStatus.EXTRACTED_FROM_TEXT
    scene_status: ExtractStatus = ExtractStatus.EXTRACTED_FROM_TEXT
    notes: list[str] = field(default_factory=list)

    def character_texts(self) -> list[str]:
        return [c.text for c in self.characters]

    def scene_texts(self) -> list[str]:
        return [s.text for s in self.scenes]


# ---------------------------------------------------------------------------
# Lexicons / filters
# ---------------------------------------------------------------------------

# Tokens that must not appear as name start/end (blocks 苏晴没 / 从信封 / 道他可能).
_NAME_BAD_EDGE = frozenset(
    "没从不道的了着过在是和与把被让给向往到用对比很也都就才又再还已会能要想说问看走跑递开发现决定进入握住停下坐站拿翻举递望听喊叫哭笑"
)

_NAME_BAD_START = frozenset("从在到把被让向往和与对用比这那有不也都很就才又再还只又将把一")

# Standalone generics — not proper names (《陌生来电》「女人」).
_GENERIC_PERSON = frozenset(
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
        "职员",  # alone; 「邮局职员老王」 handled separately
    }
)

# Allowed kinship / role display names (《旧照片》「母亲」).
_ALLOWED_ROLE_DISPLAY = frozenset(
    {
        "母亲",
        "父亲",
        "妈妈",
        "爸爸",
        "娘",
        "爹",
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

# Scene fragments that look like direction / verb junk (yesterday's M6 failures).
_SCENE_JUNK_EXACT = frozenset(
    {
        "颤抖",
        "灯上",
        "柜台前",
        "柜台上",
        "礁石上",
        "她身边坐下",
        "书桌前",
        "一叠信纸上",
        "远处",
        "从远处",
        "身边",
    }
)

_SCENE_BAD_SUFFIX = ("前", "后", "上", "下", "里", "内", "旁", "边")

# Vague location phrases → treat as missing for scene slot (《陌生来电》).
_VAGUE_SCENE = frozenset(
    {
        "房间",
        "昏暗的房间",
        "一个房间",
        "某处",
        "某个地方",
        "室内",
        "室外",
    }
)

_TIME_OF_DAY = frozenset(
    {
        "夜",
        "夜晩",
        "夜晚",
        "深夜",
        "凌晨",
        "黎明",
        "拂晓",
        "傍晚",
        "黄昏",
        "清晨",
        "早晨",
        "早上",
        "中午",
        "正午",
        "下午",
        "白天",
        "连续",
        "日",
        "晨",
        "晚",
    }
)

_INT_EXT = frozenset({"内景", "外景", "内", "外", "INT", "EXT", "int", "ext"})

_SCRIPT_PROFILE_LABEL_PATTERNS: dict[ScriptProfileFacetName, re.Pattern[str]] = {
    "theme": re.compile(
        r"^[ \t]*(?:主题|主旨|Theme)[ \t]*[:：][ \t]*(.*?)[ \t]*$",
        re.I | re.M,
    ),
    "genre": re.compile(
        r"^[ \t]*(?:类型|题材|Genres?)[ \t]*[:：][ \t]*(.*?)[ \t]*$",
        re.I | re.M,
    ),
    "audience": re.compile(
        r"^[ \t]*(?:受众|目标观众|观众|分级|Audience|Rating)"
        r"[ \t]*[:：][ \t]*(.*?)[ \t]*$",
        re.I | re.M,
    ),
    "narrative_goals": re.compile(
        r"^[ \t]*(?:叙事目标|创作意图|故事目标|Narrative[ \t]*goals?)"
        r"[ \t]*[:：][ \t]*(.*?)[ \t]*$",
        re.I | re.M,
    ),
    "style_requirements": re.compile(
        r"^[ \t]*(?:风格要求|风格|视觉风格|Style(?:[ \t]*requirements?)?)"
        r"[ \t]*[:：][ \t]*(.*?)[ \t]*$",
        re.I | re.M,
    ),
}

_SCRIPT_PROFILE_MISSING_NOTES: dict[ScriptProfileFacetName, str] = {
    "theme": "no explicit 主题/主旨 label; refusing plot-level theme inference",
    "genre": "no explicit 类型/题材 label; refusing genre classification from story vibe",
    "audience": "no explicit 受众/分级 label; refusing audience inference",
    "narrative_goals": "no explicit 叙事目标/创作意图 label; refusing narrative-goal inference",
    "style_requirements": "no explicit 风格/风格要求 label; refusing visual-style inference",
}

_SCRIPT_PROFILE_FIELD_PATHS: dict[ScriptProfileFacetName, str] = {
    facet: f"script_profile.{facet}" for facet in _SCRIPT_PROFILE_LABEL_PATTERNS
}

_EXPLICITLY_MISSING_PROFILE_VALUES = frozenset({"无", "未知", "待定", "n/a"})

_EXPLICIT_BEAT_MARKER = re.compile(
    r"^[ \t]*(?P<token>节拍[ \t]*[一二三四五六七八九十百零\d]+|BEAT[ \t]+\d+)"
    r"[ \t]*(?:[-:：][ \t]*(?P<label>[^\r\n]*?))?[ \t]*\r?$",
    re.I | re.M,
)

# Facet labels are whole-line metadata inside a Beat range — never prose inference.
_BEAT_FACET_LABEL_PATTERNS: dict[str, re.Pattern[str]] = {
    "conflict": re.compile(
        r"^[ \t]*(?:冲突|Contradiction|Conflict)[ \t]*[:：][ \t]*(.+?)[ \t]*$",
        re.I | re.M,
    ),
    "turn": re.compile(
        r"^[ \t]*(?:转折|Turn)[ \t]*[:：][ \t]*(.+?)[ \t]*$",
        re.I | re.M,
    ),
    "info_release": re.compile(
        r"^[ \t]*(?:信息释放|信息增量|信息|Info(?:rmation)?(?:[ \t]*release)?)"
        r"[ \t]*[:：][ \t]*(.+?)[ \t]*$",
        re.I | re.M,
    ),
    "emotion_from": re.compile(
        r"^[ \t]*(?:情绪从|情绪起点|From(?:[ \t]*emotion)?)[ \t]*[:：][ \t]*(.+?)[ \t]*$",
        re.I | re.M,
    ),
    "emotion_to": re.compile(
        r"^[ \t]*(?:情绪到|情绪终点|To(?:[ \t]*emotion)?)[ \t]*[:：][ \t]*(.+?)[ \t]*$",
        re.I | re.M,
    ),
    "emotion_change": re.compile(
        r"^[ \t]*(?:情绪变化|情绪转变|Emotion(?:[ \t]*change)?)[ \t]*[:：][ \t]*(.+?)[ \t]*$",
        re.I | re.M,
    ),
}

_BEAT_FACET_MISSING_NOTES: dict[BeatFacetName, str] = {
    "conflict": "no explicit 冲突 label inside Beat range; refusing conflict inference",
    "turn": "no explicit 转折 label inside Beat range; refusing turn inference",
    "info_release": (
        "no explicit 信息释放/信息 label inside Beat range; "
        "info_release is especially interpretive without labels"
    ),
    "emotion_shift": (
        "emotion_shift requires explicit 情绪从 + 情绪到 + 情绪变化 labels together; "
        "partial evidence stays missing"
    ),
}

_EXPLICITLY_MISSING_BEAT_FACET_VALUES = frozenset({"无", "未知", "待定", "n/a"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dedupe_items(items: list[ExtractedItem]) -> list[ExtractedItem]:
    """Prefer higher-confidence / stronger status for the same text."""

    status_rank = {
        ExtractStatus.EXTRACTED_FROM_TEXT: 3,
        ExtractStatus.MODEL_INFERRED: 2,
        ExtractStatus.MISSING: 1,
    }
    best: dict[str, ExtractedItem] = {}
    order: list[str] = []
    for item in items:
        key = item.text.strip()
        if not key:
            continue
        prev = best.get(key)
        if prev is None:
            best[key] = item
            order.append(key)
            continue
        if (status_rank[item.status], item.confidence) > (status_rank[prev.status], prev.confidence):
            best[key] = item
    return [best[k] for k in order]


def _strip_paren(value: str) -> str:
    return re.sub(r"[（(][^）)]*[）)]", "", value).strip(" 、,，/;；")


def _is_plausible_person_name(name: str) -> bool:
    name = name.strip()
    if not name:
        return False
    if name in _GENERIC_PERSON:
        return False
    if name in _ALLOWED_ROLE_DISPLAY:
        return True
    # Chinese 2–4 chars, or short English proper-ish
    if re.fullmatch(r"[\u4e00-\u9fff]{2,4}", name):
        if name[0] in _NAME_BAD_START:
            return False
        if name[-1] in _NAME_BAD_EDGE:
            return False
        # 「一个女人」/ occupation words leaking from bios
        if name.startswith(("一个", "一名", "一位")):
            return False
        if name in {"疲惫", "程序员", "内向", "坚定", "安静", "直率", "期待"}:
            return False
        # Reject names that are mostly function-word glue
        if any(ch in name for ch in ("没", "从", "道他", "可能")):
            return False
        if name.endswith(("没", "从", "道")):
            return False
        return True
    if re.fullmatch(r"[A-Z][a-z]{1,18}", name):
        return True
    return False


def _is_plausible_scene_name(name: str) -> bool:
    name = name.strip()
    if not name or len(name) < 2:
        return False
    if name in _SCENE_JUNK_EXACT or name in _VAGUE_SCENE:
        return False
    if name in _TIME_OF_DAY or name in _INT_EXT:
        return False
    if name in {"标题", "第一场", "第二场", "第三场"}:
        return False
    # Pure directional / positional fragments: 柜台前、灯上、书桌前
    if len(name) <= 4 and name.endswith(_SCENE_BAD_SUFFIX):
        # Allow real places that legitimately end with 里/上 only if longer compound
        # e.g. reject 灯上 / 礁石上 / 柜台上; allow 陈浩家中的老屋 (longer, has 屋)
        place_markers = ("塔", "站", "屋", "房", "厅", "楼", "阁", "厨", "海", "局", "店", "院", "园", "桥", "路", "街", "村", "镇", "城", "岛", "港", "阳台", "厨房", "阁楼", "邮局", "礁石", "火车站", "房间")
        if not any(m in name for m in place_markers):
            return False
        # Still reject short X前/X上 style junk even with 石/台
        if re.fullmatch(r"[\u4e00-\u9fff]{1,3}[前后上下里内外旁边]", name):
            return False
    # Must be mostly CJK / alnum / middle-dot
    if not re.fullmatch(r"[\u4e00-\u9fffA-Za-z0-9·的中之\- ]{2,24}", name):
        return False
    return True


def _looks_vague_scene(name: str) -> bool:
    n = name.strip()
    if n in _VAGUE_SCENE:
        return True
    if re.fullmatch(r"(一[个間]|某个)?(昏暗的|黑暗的|狭小的)?房间", n):
        return True
    return False


# ---------------------------------------------------------------------------
# Character extractors
# ---------------------------------------------------------------------------


def _chars_from_labels(text: str) -> list[ExtractedItem]:
    items: list[ExtractedItem] = []
    for match in re.finditer(r"(?:人物|角色|characters|cast)\s*[:：]\s*([^\n。；;]+)", text, re.I):
        # Strip bios first so commas inside （…） do not invent fake names.
        raw = _strip_paren(match.group(1))
        evidence = match.group(0).strip()[:120]
        for part in re.split(r"[、,，/]|(?:\s*(?:和|与|and)\s*)", raw, flags=re.I):
            name = part.strip(" 、,，/;；")
            if _is_plausible_person_name(name):
                items.append(
                    ExtractedItem(
                        text=name,
                        status=ExtractStatus.EXTRACTED_FROM_TEXT,
                        confidence=0.95,
                        method="labeled_人物_or_角色",
                        evidence=evidence,
                    )
                )
    return items


def _chars_from_speaker_cues(text: str) -> list[ExtractedItem]:
    """Lines that are only a name, followed by parenthetical or dialogue."""

    items: list[ExtractedItem] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        cue = line.strip()
        if not cue or len(cue) > 8:
            continue
        if not (
            re.fullmatch(r"[\u4e00-\u9fff]{2,4}", cue)
            or re.fullmatch(r"[A-Z][a-z]{1,18}", cue)
        ):
            continue
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        # speaker cue: next is stage direction or non-empty dialogue-ish line
        if not (nxt.startswith("（") or nxt.startswith("(") or (nxt and not nxt.startswith("第"))):
            continue
        # Skip if next looks like another heading
        if re.match(r"^第[一二三四五六七八九十百零\d]+场", nxt):
            continue
        if cue in _GENERIC_PERSON:
            # Generic cue like 「女人」— record note via skip (missing handled later)
            continue
        if not _is_plausible_person_name(cue):
            continue
        items.append(
            ExtractedItem(
                text=cue,
                status=ExtractStatus.EXTRACTED_FROM_TEXT,
                confidence=0.88,
                method="dialogue_speaker_cue",
                evidence=cue,
            )
        )
    return items


def _chars_from_intro_with_bio(text: str) -> list[ExtractedItem]:
    """Patterns: 苏晴（20多岁…） / 她的朋友林悦（…） / 邮局职员老王（…）."""

    items: list[ExtractedItem] = []
    # Title/role + name + bio
    for match in re.finditer(
        r"(?:朋友|职员|同事|邻居|母亲|父亲)?([\u4e00-\u9fff]{2,4})（[^）]{2,40}）",
        text,
    ):
        name = match.group(1)
        # Skip 「一个女人（…）」 — anonymous descriptor, not a proper name.
        pre = text[max(0, match.start() - 2):match.start()]
        if pre.endswith("一") or name.startswith("一个") or name in _GENERIC_PERSON:
            continue
        if not _is_plausible_person_name(name):
            continue
        items.append(
            ExtractedItem(
                text=name,
                status=ExtractStatus.EXTRACTED_FROM_TEXT,
                confidence=0.9,
                method="name_with_parenthetical_bio",
                evidence=match.group(0)[:80],
            )
        )
    # Explicit 「…职员老王」「…朋友林悦」 without relying only on paren
    for match in re.finditer(
        r"(?:职员|朋友|邻居|同事)([\u4e00-\u9fff]{2,3})",
        text,
    ):
        name = match.group(1)
        if _is_plausible_person_name(name):
            items.append(
                ExtractedItem(
                    text=name,
                    status=ExtractStatus.EXTRACTED_FROM_TEXT,
                    confidence=0.86,
                    method="role_title_plus_name",
                    evidence=match.group(0),
                )
            )
    return items


def extract_characters(text: str) -> tuple[list[ExtractedItem], list[str]]:
    notes: list[str] = []
    items = _dedupe_items(
        _chars_from_labels(text)
        + _chars_from_intro_with_bio(text)
        + _chars_from_speaker_cues(text)
    )
    # Drop generics if any slipped through
    items = [i for i in items if i.text not in _GENERIC_PERSON]

    # Detect anonymous / generic presence for missing signal
    if re.search(r"一个([\u4e00-\u9fff]{2,3})（", text) or re.search(
        r"^(女人|男人)\s*$", text, re.M
    ):
        generics = re.findall(r"一个([\u4e00-\u9fff]{2,3})", text)
        generics += re.findall(r"^(女人|男人)\s*$", text, re.M)
        if any(g in _GENERIC_PERSON or g in {"女人", "男人"} for g in generics):
            notes.append("generic_person_present_without_proper_name")

    if re.search(r"陌生号码|电话那头|来电", text) and not any(
        c.text not in _ALLOWED_ROLE_DISPLAY for c in items
    ):
        # caller unknown — only matters when we have no real cast either
        pass
    if re.search(r"陌生号码|电话那头", text):
        notes.append("caller_identity_unknown")

    return items, notes


# ---------------------------------------------------------------------------
# Scene extractors
# ---------------------------------------------------------------------------


def _scenes_from_labels(text: str) -> list[ExtractedItem]:
    items: list[ExtractedItem] = []
    for match in re.finditer(r"(?:地点|场景|locations|scenes)\s*[:：]\s*([^\n。；;]+)", text, re.I):
        raw = _strip_paren(match.group(1))
        evidence = match.group(0).strip()[:120]
        for part in re.split(r"[、,，/]", raw):
            name = part.strip()
            if _looks_vague_scene(name):
                continue
            if _is_plausible_scene_name(name):
                items.append(
                    ExtractedItem(
                        text=name,
                        status=ExtractStatus.EXTRACTED_FROM_TEXT,
                        confidence=0.95,
                        method="labeled_地点_or_场景",
                        evidence=evidence,
                    )
                )
    return items


def _scenes_from_industry_headings(text: str) -> list[ExtractedItem]:
    """第N场 - 内景 - 废弃灯塔 - 夜  →  废弃灯塔"""

    items: list[ExtractedItem] = []
    pattern = re.compile(
        r"第[一二三四五六七八九十百零\d]+场"
        r"(?:\s*[-—–]\s*|\s+)"
        r"(?P<head>.+)"
    )
    for match in pattern.finditer(text):
        # Only treat as heading if it appears at line start
        line_start = text.rfind("\n", 0, match.start()) + 1
        if match.start() != line_start and match.start() != 0:
            continue
        head = match.group("head").strip()
        # Stop at end of line
        head = head.split("\n", 1)[0].strip()
        parts = [p.strip() for p in re.split(r"\s*[-—–]\s*", head) if p.strip()]
        if len(parts) < 2:
            continue
        # Drop INT/EXT and time-of-day tokens; remainder is location
        location_parts = [p for p in parts if p not in _INT_EXT and p not in _TIME_OF_DAY]
        if not location_parts:
            continue
        # Usually one location token; join if multiple non-time parts
        location = location_parts[0] if len(location_parts) == 1 else "·".join(location_parts)
        if _looks_vague_scene(location):
            continue
        if _is_plausible_scene_name(location):
            items.append(
                ExtractedItem(
                    text=location,
                    status=ExtractStatus.EXTRACTED_FROM_TEXT,
                    confidence=0.92,
                    method="industry_scene_heading",
                    evidence=match.group(0).split("\n", 1)[0][:120],
                )
            )
    return items


def extract_scenes(text: str) -> tuple[list[ExtractedItem], list[str]]:
    notes: list[str] = []
    items = _dedupe_items(extract_scene_occurrences(text))

    # Intentionally do NOT run the old 在/进入/回到 capture.
    # If only vague room language exists, mark missing later.
    if not items:
        vague_hits = re.findall(
            r"((?:昏暗的|黑暗的|狭小的)?房间)",
            text,
        )
        if vague_hits:
            notes.append("only_vague_location_phrases")
        elif not re.search(r"(?:地点|场景)\s*[:：]", text) and not re.search(
            r"第[一二三四五六七八九十百零\d]+场\s*[-—–]", text
        ):
            notes.append("no_structured_location_source")

    return items, notes


def extract_scene_occurrences(text: str) -> list[ExtractedItem]:
    """Return structured Scene occurrences before name-based deduplication."""

    return _scenes_from_labels(text) + _scenes_from_industry_headings(text)


# ---------------------------------------------------------------------------
# ScriptFormatProfile projection
# ---------------------------------------------------------------------------


def extract_script_format_profile(text: str) -> ScriptFormatProfileExtraction:
    """Project existing Scene signals plus conservative cleaning diagnostics."""

    source = text or ""
    occurrences = tuple(extract_scene_occurrences(source))
    labeled_count = sum(
        occurrence.method == "labeled_地点_or_场景" for occurrence in occurrences
    )
    industry_count = sum(
        occurrence.method == "industry_scene_heading" for occurrence in occurrences
    )
    if labeled_count and industry_count:
        format_style: ScriptFormatStyle = "mixed"
    elif labeled_count:
        format_style = "labeled"
    elif industry_count:
        format_style = "industry_heading"
    else:
        format_style = "unclear"

    issues: list[ScriptCleaningIssue] = []
    if source.startswith("\ufeff"):
        issues.append(ScriptCleaningIssue("leading_byte_order_mark", 0, 1))
    replacement_index = source.find("\ufffd")
    if replacement_index >= 0:
        issues.append(
            ScriptCleaningIssue(
                "unicode_replacement_character_present",
                replacement_index,
                replacement_index + 1,
            )
        )
    seen_controls: set[int] = set()
    for index, character in enumerate(source):
        codepoint = ord(character)
        if (codepoint < 32 and character not in "\t\n\r") or codepoint == 127:
            if codepoint in seen_controls:
                continue
            seen_controls.add(codepoint)
            issues.append(
                ScriptCleaningIssue(
                    f"unexpected_control_character_U+{codepoint:04X}",
                    index,
                    index + 1,
                )
            )

    return ScriptFormatProfileExtraction(
        format_style=format_style,
        cleaning_issues=tuple(issues),
        scene_occurrences=occurrences,
    )


# ---------------------------------------------------------------------------
# ScriptProfile extractor
# ---------------------------------------------------------------------------


def extract_script_profile_facets(text: str) -> list[ScriptProfileFacetExtraction]:
    """Extract five ScriptProfile facets from explicit metadata label lines only."""

    source = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    facets: list[ScriptProfileFacetExtraction] = []
    for facet, pattern in _SCRIPT_PROFILE_LABEL_PATTERNS.items():
        match = pattern.search(source)
        value = match.group(1).strip() if match else ""
        if value and value.lower() not in _EXPLICITLY_MISSING_PROFILE_VALUES:
            facets.append(
                ScriptProfileFacetExtraction(
                    facet=facet,
                    field_path=_SCRIPT_PROFILE_FIELD_PATHS[facet],
                    item=ExtractedItem(
                        text=value[:2000],
                        status=ExtractStatus.EXTRACTED_FROM_TEXT,
                        confidence=0.9,
                        method=f"labeled_script_profile_{facet}",
                        evidence=match.group(0).strip()[:1200],
                    ),
                )
            )
            continue
        note = (
            f"explicit {facet} label has no supported value"
            if match
            else _SCRIPT_PROFILE_MISSING_NOTES[facet]
        )
        facets.append(
            ScriptProfileFacetExtraction(
                facet=facet,
                field_path=_SCRIPT_PROFILE_FIELD_PATHS[facet],
                item=ExtractedItem(
                    text="(missing)",
                    status=ExtractStatus.MISSING,
                    confidence=0.0,
                    method="explicit_script_profile_label_missing",
                ),
                uncertainty_note=note,
            )
        )
    return facets


def extract_explicit_beat_boundaries(
    scene_text: str,
    *,
    source_offset: int = 0,
) -> list[ExtractedBeatBoundary]:
    """Return explicit numbered Beat ranges inside one already-resolved Scene."""

    markers = list(_EXPLICIT_BEAT_MARKER.finditer(scene_text or ""))
    boundaries: list[ExtractedBeatBoundary] = []
    for index, marker in enumerate(markers):
        local_end = markers[index + 1].start() if index + 1 < len(markers) else len(scene_text)
        if local_end <= marker.start():
            continue
        raw_marker = marker.group(0)
        marker_text = raw_marker.strip()
        leading = len(raw_marker) - len(raw_marker.lstrip())
        label = (marker.group("label") or "").strip()
        boundaries.append(
            ExtractedBeatBoundary(
                order_index=index,
                source_start=source_offset + marker.start(),
                source_end=source_offset + local_end,
                evidence_start=source_offset + marker.start() + leading,
                evidence_end=source_offset + marker.start() + leading + len(marker_text),
                marker=marker_text,
                label=label,
            )
        )
    return boundaries


def _collect_labeled_values_in_range(
    range_text: str,
    *,
    pattern: re.Pattern[str],
    source_offset: int,
    method: str,
) -> list[tuple[ExtractedItem, int, int]] | str:
    """Return unique labeled values, or an ambiguity reason string."""

    matches = list(pattern.finditer(range_text or ""))
    if not matches:
        return []
    values: list[tuple[ExtractedItem, int, int]] = []
    for match in matches:
        raw = (match.group(1) or "").strip()
        if not raw or raw.lower() in _EXPLICITLY_MISSING_BEAT_FACET_VALUES:
            continue
        start = source_offset + match.start(1)
        end = source_offset + match.end(1)
        values.append(
            (
                ExtractedItem(
                    text=raw,
                    status=ExtractStatus.EXTRACTED_FROM_TEXT,
                    confidence=0.92,
                    method=method,
                    evidence=raw[:120],
                ),
                start,
                end,
            )
        )
    if not values:
        return []
    if len(values) > 1:
        return "duplicate_explicit_labels"
    return values


def extract_explicit_beat_facets(
    beat_range_text: str,
    *,
    source_offset: int = 0,
) -> list[ExtractedBeatFacet]:
    """Labeled-only Beat facets inside one Beat source range.

    Hard rules:
    - No label → missing (never invent from prose).
    - Duplicate labels for the same facet → missing (fail closed, no silent pick).
    - emotion_shift present only when from+to+change are all uniquely labeled;
      any partial set → one missing emotion_shift facet (not partial presents).
    """

    facets: list[ExtractedBeatFacet] = []

    for facet, pattern_key, field_suffix, method in (
        ("conflict", "conflict", "conflict", "explicit_beat_conflict_label"),
        ("turn", "turn", "turn", "explicit_beat_turn_label"),
        ("info_release", "info_release", "info_release", "explicit_beat_info_release_label"),
    ):
        collected = _collect_labeled_values_in_range(
            beat_range_text,
            pattern=_BEAT_FACET_LABEL_PATTERNS[pattern_key],
            source_offset=source_offset,
            method=method,
        )
        if isinstance(collected, str):
            facets.append(
                ExtractedBeatFacet(
                    facet=facet,  # type: ignore[arg-type]
                    field_suffix=field_suffix,
                    item=ExtractedItem(
                        text="(missing)",
                        status=ExtractStatus.MISSING,
                        confidence=0.0,
                        method="explicit_beat_facet_ambiguous",
                    ),
                    uncertainty_note=(
                        f"multiple explicit {facet} labels inside Beat range; "
                        "refusing to choose"
                    ),
                )
            )
            continue
        if not collected:
            facets.append(
                ExtractedBeatFacet(
                    facet=facet,  # type: ignore[arg-type]
                    field_suffix=field_suffix,
                    item=ExtractedItem(
                        text="(missing)",
                        status=ExtractStatus.MISSING,
                        confidence=0.0,
                        method="explicit_beat_facet_missing",
                    ),
                    uncertainty_note=_BEAT_FACET_MISSING_NOTES[facet],  # type: ignore[index]
                )
            )
            continue
        item, start, end = collected[0]
        facets.append(
            ExtractedBeatFacet(
                facet=facet,  # type: ignore[arg-type]
                field_suffix=field_suffix,
                item=item,
                evidence_start=start,
                evidence_end=end,
            )
        )

    emotion_parts: dict[str, tuple[ExtractedItem, int, int] | str | None] = {
        "from_state": None,
        "to_state": None,
        "change": None,
    }
    part_specs = (
        ("from_state", "emotion_from", "explicit_beat_emotion_from_label"),
        ("to_state", "emotion_to", "explicit_beat_emotion_to_label"),
        ("change", "emotion_change", "explicit_beat_emotion_change_label"),
    )
    emotion_ambiguous = False
    emotion_partial = False
    for part, pattern_key, method in part_specs:
        collected = _collect_labeled_values_in_range(
            beat_range_text,
            pattern=_BEAT_FACET_LABEL_PATTERNS[pattern_key],
            source_offset=source_offset,
            method=method,
        )
        if isinstance(collected, str):
            emotion_ambiguous = True
            emotion_parts[part] = collected
            continue
        if not collected:
            emotion_partial = True
            emotion_parts[part] = None
            continue
        emotion_parts[part] = collected[0]

    if (
        emotion_ambiguous
        or emotion_partial
        or any(value is None for value in emotion_parts.values())
    ):
        note = _BEAT_FACET_MISSING_NOTES["emotion_shift"]
        if emotion_ambiguous:
            note = (
                "multiple explicit emotion_shift labels inside Beat range; "
                "refusing partial or ambiguous emotion_shift"
            )
        elif any(
            emotion_parts[part] is not None for part in ("from_state", "to_state", "change")
        ):
            note = (
                "partial emotion_shift labels found; "
                "from_state/to_state/change must all be present uniquely"
            )
        facets.append(
            ExtractedBeatFacet(
                facet="emotion_shift",
                field_suffix="emotion_shift",
                item=ExtractedItem(
                    text="(missing)",
                    status=ExtractStatus.MISSING,
                    confidence=0.0,
                    method="explicit_beat_emotion_shift_missing",
                ),
                uncertainty_note=note,
            )
        )
    else:
        for part in ("from_state", "to_state", "change"):
            item, start, end = emotion_parts[part]  # type: ignore[misc]
            facets.append(
                ExtractedBeatFacet(
                    facet="emotion_shift",
                    field_suffix=f"emotion_shift.{part}",
                    item=item,
                    evidence_start=start,
                    evidence_end=end,
                )
            )
    return facets


@dataclass(frozen=True)
class ExtractedCharacterAppearance:
    """One character presence claim inside a resolved Scene source range."""

    character_name: str
    order_index: int
    evidence_start: int
    evidence_end: int
    method: str


@dataclass(frozen=True)
class ExtractedSceneProp:
    """One source-backed prop mention inside a resolved Scene source range."""

    name: str
    order_index: int
    evidence_start: int
    evidence_end: int
    method: str
    confidence: float
    importance: str | None = None
    importance_evidence_start: int | None = None
    importance_evidence_end: int | None = None


# Closed on purpose: these are unambiguous production objects in the current
# screenplay corpus. Unknown prose nouns stay missing until a stronger parser
# can classify them without turning location context into invented props.
_NARRATIVE_PROP_NAMES: tuple[str, ...] = (
    "手电筒",
    "灯塔灯",
    "挂钟",
    "台灯",
    "信纸",
    "相册",
    "照片",
    "手机",
    "钥匙",
    "开关",
    "信",
    "笔",
    "刀",
)

_PROP_ACTION_BEFORE = re.compile(
    r"(?:拿着|拿起|拿出|掏出|握着|紧握着|紧握|攥着|紧攥着|紧攥|抓着|"
    r"捧着|抱着|提着|接过|翻出|打开|合上|举起|转动|按下|抽出|拔出|"
    r"找到|找到了|盯着|看着|写|切|停在|放在|洒在)[^，,。！？!?；;\n]{0,24}$"
)
_PROP_ACTION_AFTER = re.compile(
    r"^[^，,。！？!?；;\n]{0,16}(?:递给|递过去|塞给|放在|放下|亮起|熄灭|"
    r"停住|打开|合上|转动|按下|挂断|响起)"
)
_PROP_PHYSICAL_OUTPUT_AFTER = re.compile(
    r"^(?:屏幕)?的(?:光|声音|滴答声)|^屏幕(?:的光|上)"
)
_PROP_LABEL = re.compile(
    r"(?m)^[ \t]*(?P<importance>关键|重要)?道具[ \t]*[:：][ \t]*"
    r"(?P<values>[^\n。；;]+)"
)


def _clause_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    separators = "，,。！？!?；;\n"
    left = max((text.rfind(mark, 0, start) for mark in separators), default=-1) + 1
    right_hits = [text.find(mark, end) for mark in separators]
    right = min((hit for hit in right_hits if hit >= 0), default=len(text))
    return left, right


def _is_standalone_prop_mention(text: str, start: int, name: str) -> bool:
    """Reject short aliases embedded in a different word (回信/信纸/信息)."""

    if name != "信":
        return True
    previous = text[start - 1] if start > 0 else ""
    following_index = start + len(name)
    following = text[following_index] if following_index < len(text) else ""
    return previous not in "来回书短微通相" and following not in "纸息箱号"


def _has_physical_prop_signal(text: str, start: int, end: int) -> bool:
    clause_start, clause_end = _clause_bounds(text, start, end)
    before = text[clause_start:start]
    after = text[end:clause_end]
    return bool(
        _PROP_ACTION_BEFORE.search(before)
        or _PROP_ACTION_AFTER.search(after)
        or _PROP_PHYSICAL_OUTPUT_AFTER.search(after)
    )


def _explicit_prop_label_hits(
    range_text: str,
    *,
    source_offset: int,
) -> list[tuple[int, int, str, str, float, str | None, int | None, int | None]]:
    hits: list[tuple[int, int, str, str, float, str | None, int | None, int | None]] = []
    for match in _PROP_LABEL.finditer(range_text):
        raw = _strip_paren(match.group("values"))
        for part in re.split(r"[、,，/]|(?:\s*(?:和|与|and)\s*)", raw, flags=re.I):
            name = part.strip(" 、,，/;；")
            if not name or len(name) > 40 or name.lower() in {"无", "未知", "待定", "n/a"}:
                continue
            local = range_text.find(name, match.start("values"), match.end("values"))
            if local < 0:
                continue
            importance = match.group("importance")
            importance_start = match.start("importance") if importance else None
            importance_end = match.end("importance") if importance else None
            hits.append(
                (
                    source_offset + local,
                    source_offset + local + len(name),
                    name,
                    "explicit_scene_prop_label",
                    0.98,
                    importance,
                    source_offset + importance_start if importance_start is not None else None,
                    source_offset + importance_end if importance_end is not None else None,
                )
            )
    return hits


def extract_scene_props_in_range(
    range_text: str,
    *,
    source_offset: int = 0,
) -> list[ExtractedSceneProp]:
    """Extract only explicit, physical Scene props from one owned source range.

    Narrative extraction is intentionally recall-limited. A known object noun
    must be present verbatim and participate in a same-clause physical signal.
    This excludes location-derived guesses and leaves unsupported objects missing.
    """

    source = range_text or ""
    if not source.strip():
        return []

    hits = _explicit_prop_label_hits(source, source_offset=source_offset)
    labeled_spans = {(start, end) for start, end, *_ in hits}
    for name in _NARRATIVE_PROP_NAMES:
        cursor = 0
        while True:
            local = source.find(name, cursor)
            if local < 0:
                break
            end = local + len(name)
            cursor = end
            absolute = (source_offset + local, source_offset + end)
            if absolute in labeled_spans:
                continue
            if not _is_standalone_prop_mention(source, local, name):
                continue
            if not _has_physical_prop_signal(source, local, end):
                continue
            hits.append(
                (
                    absolute[0],
                    absolute[1],
                    name,
                    "explicit_physical_prop_mention",
                    0.88,
                    None,
                    None,
                    None,
                )
            )

    # One requirement per canonical name per Scene. Repeated mentions retain
    # the first evidence span; an explicit importance label wins if present.
    by_name: dict[
        str,
        tuple[int, int, str, str, float, str | None, int | None, int | None],
    ] = {}
    for hit in sorted(hits, key=lambda row: (row[0], row[2])):
        previous = by_name.get(hit[2])
        if previous is None or (hit[5] is not None and previous[5] is None):
            by_name[hit[2]] = hit
    ordered = sorted(by_name.values(), key=lambda row: (row[0], row[2]))
    return [
        ExtractedSceneProp(
            name=hit[2],
            order_index=index,
            evidence_start=hit[0],
            evidence_end=hit[1],
            method=hit[3],
            confidence=hit[4],
            importance=hit[5],
            importance_evidence_start=hit[6],
            importance_evidence_end=hit[7],
        )
        for index, hit in enumerate(ordered)
    ]


def extract_character_appearances_in_range(
    range_text: str,
    *,
    known_character_names: set[str] | frozenset[str],
    source_offset: int = 0,
) -> list[ExtractedCharacterAppearance]:
    """Labeled/cue-only cast presence inside one Scene range.

    Accepts:
      - dialogue speaker cues whose name is already a known Character candidate
      - in-range ``人物：`` / ``角色：`` list entries matching known Characters

    Does not infer presence from prose alone. Same character twice in one range
    collapses to a single appearance (first evidence span).
    """

    known = {name.strip() for name in known_character_names if name and name.strip()}
    if not known or not (range_text or "").strip():
        return []

    first_hit: dict[str, tuple[int, int, str]] = {}

    # In-scene cast labels (e.g. 《归途》 per-scene 人物： lines).
    for match in re.finditer(
        r"(?m)^[ \t]*(?:人物|角色|characters|cast)[ \t]*[:：][ \t]*([^\n。；;]+)",
        range_text,
        re.I,
    ):
        raw = _strip_paren(match.group(1))
        for part in re.split(r"[、,，/]|(?:\s*(?:和|与|and)\s*)", raw, flags=re.I):
            name = part.strip(" 、,，/;；")
            if name not in known or name in first_hit:
                continue
            # Prefer binding evidence to the exact name token inside the label line.
            local = range_text.find(name, match.start(1), match.end(1))
            if local < 0:
                local = match.start(1)
                end = match.end(1)
            else:
                end = local + len(name)
            first_hit[name] = (
                source_offset + local,
                source_offset + end,
                "scene_cast_label",
            )

    lines = range_text.splitlines(keepends=True)
    cursor = 0
    for i, line in enumerate(lines):
        line_start = cursor
        cursor += len(line)
        cue = line.strip()
        if not cue or len(cue) > 8 or cue not in known or cue in first_hit:
            continue
        if not (
            re.fullmatch(r"[\u4e00-\u9fff]{2,4}", cue)
            or re.fullmatch(r"[A-Z][a-z]{1,18}", cue)
        ):
            continue
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if not (
            nxt.startswith("（")
            or nxt.startswith("(")
            or (nxt and not nxt.startswith("第"))
        ):
            continue
        if re.match(r"^第[一二三四五六七八九十百零\d]+场", nxt):
            continue
        leading = len(line) - len(line.lstrip(" \t"))
        name_start = line_start + leading
        name_end = name_start + len(cue)
        first_hit[cue] = (
            source_offset + name_start,
            source_offset + name_end,
            "dialogue_speaker_cue_in_scene",
        )

    ordered = sorted(first_hit.items(), key=lambda row: (row[1][0], row[0]))
    return [
        ExtractedCharacterAppearance(
            character_name=name,
            order_index=index,
            evidence_start=start,
            evidence_end=end,
            method=method,
        )
        for index, (name, (start, end, method)) in enumerate(ordered)
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_characters_and_scenes(text: str) -> ExtractionResult:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    chars, char_notes = extract_characters(text)
    scenes, scene_notes = extract_scenes(text)
    notes = char_notes + scene_notes

    char_status: ExtractStatus
    if chars:
        char_status = ExtractStatus.EXTRACTED_FROM_TEXT
    else:
        char_status = ExtractStatus.MISSING
        notes.append("character_proper_names_missing")

    scene_status: ExtractStatus
    if scenes:
        scene_status = ExtractStatus.EXTRACTED_FROM_TEXT
    else:
        scene_status = ExtractStatus.MISSING
        notes.append("scene_locations_missing")

    return ExtractionResult(
        characters=chars,
        scenes=scenes,
        character_name_status=char_status,
        scene_status=scene_status,
        notes=notes,
    )


def extracted_item_to_dict(item: ExtractedItem) -> dict[str, object]:
    return {
        "text": item.text,
        "status": item.status.value,
        "confidence": item.confidence,
        "method": item.method,
        "evidence": item.evidence,
    }


def extraction_result_to_dict(result: ExtractionResult) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "characters": [extracted_item_to_dict(item) for item in result.characters],
        "scenes": [extracted_item_to_dict(item) for item in result.scenes],
        "character_name_status": result.character_name_status.value,
        "scene_status": result.scene_status.value,
        "notes": list(result.notes),
    }


__all__ = (
    "SCHEMA_VERSION",
    "ExtractStatus",
    "ExtractedItem",
    "ScriptProfileFacetName",
    "ScriptProfileFacetExtraction",
    "ScriptFormatStyle",
    "ScriptCleaningIssue",
    "ScriptFormatProfileExtraction",
    "ExtractedBeatBoundary",
    "BeatFacetName",
    "ExtractedBeatFacet",
    "ExtractedCharacterAppearance",
    "ExtractedSceneProp",
    "ExtractionResult",
    "extract_characters",
    "extract_scenes",
    "extract_scene_occurrences",
    "extract_character_appearances_in_range",
    "extract_scene_props_in_range",
    "extract_script_format_profile",
    "extract_script_profile_facets",
    "extract_explicit_beat_boundaries",
    "extract_explicit_beat_facets",
    "extract_characters_and_scenes",
    "extracted_item_to_dict",
    "extraction_result_to_dict",
)
