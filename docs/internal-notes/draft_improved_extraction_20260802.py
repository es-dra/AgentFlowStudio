"""DRAFT archive — production shadow path now lives in:

  apps/api/runtime_script_improved_extraction.py
  (gated by AFS_USE_IMPROVED_EXTRACTION in runtime_m6_script_plan_asset_bible.py)

Improved Character + Scene extraction (2026-08-02)

Originally parallel to M6 heuristics:
  apps/api/runtime_m6_script_plan_asset_bible.py
    _extract_named_characters / _extract_scenes

Kept for local A/B against docs/internal-notes/test-scripts-character-scene/.

Status tags align with draft_candidate_fact_status_model_20260802.py:
  extracted_from_text — literal labeled field or structured heading / speaker cue
  model_inferred      — weak heuristic (kept rare; prefer missing over junk)
  missing             — no credible value; do not invent

Hard rules
----------
1. Labeled 人物：/地点： beats everything (high-confidence extracted_from_text).
2. Industry heading 第N场 - 内景 - <地点> - <时间> is structured extract, not junk regex.
3. Verb-prefix name grab (「苏晴没说话」→「苏晴没」) is intentionally NOT used.
4. 「在柜台前」direction fragments are rejected as scene names.
5. Generic roles (女人/男人…) without a proper name → missing, not a fake name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


SCHEMA_VERSION = "afs.script_understanding.improved_extraction.v0.1.draft"


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
    items = _dedupe_items(_scenes_from_labels(text) + _scenes_from_industry_headings(text))

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


# ---------------------------------------------------------------------------
# Legacy M6-style extractors (copied locally for A/B contrast only)
# ---------------------------------------------------------------------------


def legacy_m6_characters(text: str) -> list[str]:
    """Mirror of production verb-prefix heuristic (for contrast output only)."""

    values: list[str] = []
    for match in re.finditer(r"(?:人物|角色)\s*[:：]\s*([^\n。；;]+)", text):
        raw = re.sub(r"[（(][^）)]*[）)]", "", match.group(1))
        values.extend(p.strip(" 、,，/") for p in re.split(r"[、,，/]", raw) if p.strip(" 、,，/"))
    if values:
        return _dedupe_strings(values)[:12]
    values.extend(re.findall(r"([\u4e00-\u9fff]{2,4})(?:说|问|看|走|跑|递|打开|发现|决定|进入|握住|停下)", text))
    return _dedupe_strings(values)[:12]


def legacy_m6_scenes(text: str) -> list[str]:
    values: list[str] = []
    for match in re.finditer(r"(?:地点|场景)\s*[:：]\s*([^\n。；;]+)", text):
        raw = re.sub(r"[（(][^）)]*[）)]", "", match.group(1))
        values.extend(p.strip(" 、,，/") for p in re.split(r"[、,，/]", raw) if p.strip(" 、,，/"))
    if values:
        return _dedupe_strings(values)[:12]
    values.extend(
        re.findall(
            r"(?:在|进入|回到)([\u4e00-\u9fffA-Za-z0-9·\- ]{2,24})(?:里|内|上|下|前|后|，|。|；|;|,)",
            text,
        )
    )
    return _dedupe_strings(values)[:12]


def _dedupe_strings(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for v in values:
        k = v.lower()
        if k and k not in seen:
            seen.add(k)
            out.append(v)
    return out
