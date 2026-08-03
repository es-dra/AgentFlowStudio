"""DRAFT ONLY — not wired into Runtime / apps/api.

Scene understanding schema (2026-08-02)

Mirrors CharacterVersion / CharacterEntity from
  draft_script_understanding_character_schema_20260801.py

§7.2 scene slice (boss): 场景、时间、空间、道具、事件和因果关系
  - SceneIdentity / SceneTimeSpace / SceneProps / SceneEvents / SceneCausality
  - ClaimedText for soft facts; explicit missing — no template filler
  - Bind source_revision_id + digest; immutable version + append-only history

Methodology reuse (do not reinvent):
  - CandidateFact / promote_candidate_fact (entity_kind="scene")
  - confirmation loop CandidateReviewBundle / accept / edit_confirm
  - improved extraction for scene names (draft_improved_extraction_20260802)

Beat is out of scope today.
"""

from __future__ import annotations

import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from draft_script_understanding_character_schema_20260801 import (  # noqa: E402
    ChangeRecord,
    ClaimedText,
    EvidenceSpan,
)
from draft_candidate_fact_status_model_20260802 import (  # noqa: E402
    CandidateFact,
    CandidateStatus,
    ClaimedText as StatusClaimedText,
)
from draft_improved_extraction_20260802 import (  # noqa: E402
    ExtractStatus,
    extract_scenes,
)


SCHEMA_VERSION = "afs.script_understanding.scene.v0.1.draft"


# ---------------------------------------------------------------------------
# Facets (§7.2 scene slice — Character-scale, not overbuilt)
# ---------------------------------------------------------------------------


class SceneIdentity(BaseModel):
    """Name / aliases / ordinal — analogue of CharacterIdentity."""

    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=160)
    aliases: list[str] = Field(default_factory=list, max_length=12)
    # e.g. "第一场" when the script states it; None if absent
    scene_ordinal: ClaimedText | None = None
    brief_description: ClaimedText | None = None


class SceneTimeSpace(BaseModel):
    """Time-of-day / clock + interior/exterior + place — usually high-evidence."""

    model_config = ConfigDict(extra="forbid")

    time_of_day: ClaimedText | None = None
    clock_or_duration: ClaimedText | None = Field(
        default=None,
        description="Explicit clock/duration if present, e.g. 还有五分钟",
    )
    interior_exterior: ClaimedText | None = Field(
        default=None,
        description="内景 / 外景 when stated",
    )
    place: ClaimedText | None = Field(
        default=None,
        description="Concrete place noun phrase (阁楼 / 废弃灯塔 / …)",
    )
    spatial_detail: ClaimedText | None = Field(
        default=None,
        description="Optional richer space note only if text supports it",
    )


class ScenePropItem(BaseModel):
    """One prop/object mentioned in the scene body."""

    model_config = ConfigDict(extra="forbid")

    prop_id: str = Field(min_length=1, max_length=120)
    name: ClaimedText
    importance: ClaimedText | None = Field(
        default=None,
        description="Only if script signals importance; else leave None (missing)",
    )


class SceneProps(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ScenePropItem] = Field(default_factory=list, max_length=32)


class SceneEventItem(BaseModel):
    """One observable event/action in scene order — not deep causal inference."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=120)
    order_index: int = Field(ge=0, strict=True)
    statement: ClaimedText


class SceneEvents(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SceneEventItem] = Field(default_factory=list, max_length=48)


class SceneCausalityLink(BaseModel):
    """Optional cross-scene cause/effect — only when text states it."""

    model_config = ConfigDict(extra="forbid")

    link_id: str = Field(min_length=1, max_length=120)
    # Prefer stable ids when known; allow ordinal/name during early extract
    from_scene_id: str | None = Field(default=None, max_length=120)
    to_scene_id: str | None = Field(default=None, max_length=120)
    from_scene_ref: str | None = Field(default=None, max_length=80)
    to_scene_ref: str | None = Field(default=None, max_length=80)
    statement: ClaimedText

    @model_validator(mode="after")
    def need_endpoints(self) -> "SceneCausalityLink":
        if not (self.from_scene_id or self.from_scene_ref):
            raise ValueError("causality link needs from_scene_id or from_scene_ref")
        if not (self.to_scene_id or self.to_scene_ref):
            raise ValueError("causality link needs to_scene_id or to_scene_ref")
        return self


class SceneCausality(BaseModel):
    """Cross-scene causality — expected empty/missing on most test scripts."""

    model_config = ConfigDict(extra="forbid")

    links: list[SceneCausalityLink] = Field(default_factory=list, max_length=16)
    # When no textual evidence exists, set status missing (do not invent links).
    status: Literal["present", "missing"] = "missing"
    uncertainty_note: str | None = Field(default=None, max_length=400)


# ---------------------------------------------------------------------------
# Entity + version envelope (same pattern as Character)
# ---------------------------------------------------------------------------


class SceneVersion(BaseModel):
    """One immutable version of a scene understanding record."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=SCHEMA_VERSION, min_length=1, max_length=80)

    scene_id: str = Field(min_length=1, max_length=120)
    version_id: str = Field(min_length=1, max_length=120)
    version_number: int = Field(ge=1, strict=True)
    parent_version_id: str | None = Field(default=None, max_length=120)

    project_id: str = Field(min_length=1, max_length=128)
    source_revision_id: str = Field(min_length=1, max_length=120)
    source_revision_digest: str = Field(min_length=64, max_length=64)

    identity: SceneIdentity
    time_space: SceneTimeSpace
    props: SceneProps = Field(default_factory=SceneProps)
    events: SceneEvents = Field(default_factory=SceneEvents)
    causality: SceneCausality = Field(default_factory=SceneCausality)

    evidence_spans: list[EvidenceSpan] = Field(min_length=1, max_length=24)
    confidence: float = Field(ge=0.0, le=1.0)
    status: Literal["candidate", "confirmed", "pending_confirmation", "rejected", "retired"] = (
        "candidate"
    )

    produced_by: Literal["human", "deterministic_extractor", "llm", "mixed"] = (
        "deterministic_extractor"
    )
    produced_at: datetime | None = None
    missing_fields: list[str] = Field(default_factory=list, max_length=64)
    contradiction_notes: list[str] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def parent_rules(self) -> "SceneVersion":
        if self.version_number == 1 and self.parent_version_id is not None:
            raise ValueError("version_number 1 must not set parent_version_id")
        if self.version_number > 1 and not self.parent_version_id:
            raise ValueError("version_number > 1 requires parent_version_id")
        return self


class SceneEntity(BaseModel):
    """Stable scene entity with head version + append-only history."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=SCHEMA_VERSION, min_length=1, max_length=80)
    scene_id: str = Field(min_length=1, max_length=120)
    project_id: str = Field(min_length=1, max_length=128)
    head_version_id: str = Field(min_length=1, max_length=120)
    versions: list[SceneVersion] = Field(min_length=1, max_length=256)
    history: list[ChangeRecord] = Field(default_factory=list, max_length=512)

    @model_validator(mode="after")
    def head_and_ids_consistent(self) -> "SceneEntity":
        by_id = {item.version_id: item for item in self.versions}
        if len(by_id) != len(self.versions):
            raise ValueError("duplicate version_id in versions")
        if self.head_version_id not in by_id:
            raise ValueError("head_version_id must reference a version in versions")
        for item in self.versions:
            if item.scene_id != self.scene_id:
                raise ValueError("version.scene_id must match entity.scene_id")
            if item.project_id != self.project_id:
                raise ValueError("version.project_id must match entity.project_id")
        return self


# ---------------------------------------------------------------------------
# Script block parsing + facet extract (deterministic, no inventing)
# ---------------------------------------------------------------------------


_ORDINAL_LINE = re.compile(
    r"^(第[一二三四五六七八九十百零\d]+场)(?:\s*[-—–]\s*(.+))?$"
)
_LABEL = re.compile(r"^(时间|地点|场景|人物|角色)\s*[:：]\s*(.+)$")
# Longer tokens first so 「深夜」wins over bare 「夜」.
_TIME_TOKENS = (
    "深夜",
    "夜晚",
    "凌晨",
    "黎明",
    "傍晚",
    "黄昏",
    "清晨",
    "早晨",
    "早上",
    "中午",
    "正午",
    "下午",
    "白天",
    "夜",
)
_INT_EXT = ("内景", "外景")
# Heading-only tokens stripped from place, not treated as time_of_day.
_HEADING_NON_TIME = frozenset({"连续"})
_HEADING_STRIP = frozenset(_TIME_TOKENS) | _HEADING_NON_TIME | frozenset(_INT_EXT)

# Explicit prop nouns worth capturing when they appear as whole words in body.
# Conservative list — presence must be findable in scene body text.
_PROP_LEXICON = (
    "手电筒",
    "灯塔灯",
    "开关",
    "渔船",
    "照片",
    "相册",
    "信",
    "信封",
    "信纸",
    "台灯",
    "笔",
    "手机",
    "刀",
    "箱子",
    "钥匙",
    "铁门",
    "铁梯",
    "监控",
    "长椅",
    "外套",
    "广播",
)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def _span(source: str, quote: str) -> EvidenceSpan | None:
    q = quote.strip()
    if not q:
        return None
    idx = source.find(q)
    if idx < 0:
        return EvidenceSpan(start=0, end=max(len(q), 1), quote=q[:1200])
    return EvidenceSpan(start=idx, end=idx + len(q), quote=q[:1200])


def _claimed(
    source: str,
    text: str,
    *,
    confidence: float,
    uncertainty: str | None = None,
) -> ClaimedText | None:
    t = text.strip()
    if not t:
        return None
    span = _span(source, t)
    spans = [span] if span else []
    return ClaimedText(
        text=t,
        confidence=confidence,
        evidence_spans=spans,
        uncertainty_note=uncertainty,
    )


class _SceneBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ordinal_raw: str | None = None
    heading_line: str | None = None
    body: str
    full_text: str
    start_offset: int = 0


def _split_scene_blocks(source_text: str) -> list[_SceneBlock]:
    text = source_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    indices: list[int] = []
    for i, line in enumerate(lines):
        if _ORDINAL_LINE.match(line.strip()):
            indices.append(i)
    if not indices:
        # Single prose block (e.g. 《陌生来电》)
        return [
            _SceneBlock(
                ordinal_raw=None,
                heading_line=None,
                body=text.strip(),
                full_text=text.strip(),
                start_offset=0,
            )
        ]

    blocks: list[_SceneBlock] = []
    for bi, start in enumerate(indices):
        end = indices[bi + 1] if bi + 1 < len(indices) else len(lines)
        chunk_lines = lines[start:end]
        heading = chunk_lines[0].strip()
        m = _ORDINAL_LINE.match(heading)
        ordinal = m.group(1) if m else None
        body = "\n".join(chunk_lines[1:]).strip()
        full = "\n".join(chunk_lines).strip()
        # approximate offset
        prefix = "\n".join(lines[:start])
        offset = len(prefix) + (1 if prefix else 0)
        blocks.append(
            _SceneBlock(
                ordinal_raw=ordinal,
                heading_line=heading,
                body=body,
                full_text=full,
                start_offset=offset,
            )
        )
    return blocks


def _parse_heading_parts(heading: str | None) -> tuple[str | None, str | None, str | None]:
    """Return (int_ext, place, time) from `第一场 - 内景 - 废弃灯塔 - 夜`."""

    if not heading:
        return None, None, None
    m = _ORDINAL_LINE.match(heading.strip())
    if not m:
        return None, None, None
    rest = (m.group(2) or "").strip()
    if not rest:
        return None, None, None
    parts = [p.strip() for p in re.split(r"\s*[-—–]\s*", rest) if p.strip()]
    int_ext = next((p for p in parts if p in _INT_EXT), None)
    time = next((p for p in parts if p in _TIME_TOKENS), None)
    place_parts = [
        p
        for p in parts
        if p not in _HEADING_STRIP
    ]
    place = place_parts[0] if place_parts else None
    return int_ext, place, time


def _labels_in_body(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in body.splitlines():
        m = _LABEL.match(line.strip())
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        # strip character bios from 地点? only store 时间/地点/场景
        if key in {"时间", "地点", "场景"}:
            out[key] = re.sub(r"[（(][^）)]*[）)]", "", val).strip()
    return out


def _prop_mentioned(scene_source: str, prop: str) -> bool:
    """Require prop as a token; block 信⊂信号, 灯⊂台灯 false hits where needed."""

    if prop not in scene_source:
        return False
    # Single-char / short props: reject if only embedded in a longer known word
    if prop == "信" and "信号" in scene_source and scene_source.count("信") == scene_source.count("信号"):
        return False
    return True


def _extract_props(scene_source: str) -> list[ScenePropItem]:
    items: list[ScenePropItem] = []
    seen: set[str] = set()
    for prop in _PROP_LEXICON:
        if prop in seen or not _prop_mentioned(scene_source, prop):
            continue
        claimed = _claimed(scene_source, prop, confidence=0.85)
        if claimed is None:
            continue
        seen.add(prop)
        items.append(ScenePropItem(prop_id=_id("prop"), name=claimed))
    return items


def _extract_events(scene_source: str) -> list[SceneEventItem]:
    """Lightweight action lines — keep short, evidence-backed, no causality."""

    events: list[SceneEventItem] = []
    # Prefer full sentences ending with 。 that contain a verb-ish token
    verbish = re.compile(
        r"(攀爬|找到|转动|亮起|走|坐|递|打开|接通|挂断|抱|望|写|翻|停下|推开|跑)"
    )
    order = 0
    for piece in re.split(r"(?<=[。！？])\s*", scene_source):
        line = piece.strip().replace("\n", "")
        if len(line) < 8 or len(line) > 80:
            continue
        if line.startswith("（") or _LABEL.match(line) or _ORDINAL_LINE.match(line):
            continue
        if line in {"标题："} or line.startswith("标题："):
            continue
        if not verbish.search(line):
            continue
        # Skip pure dialogue cues
        if re.fullmatch(r"[\u4e00-\u9fffA-Za-z]{1,8}", line):
            continue
        claimed = _claimed(scene_source, line[:120], confidence=0.7)
        if claimed is None:
            continue
        events.append(
            SceneEventItem(event_id=_id("evt"), order_index=order, statement=claimed)
        )
        order += 1
        if order >= 6:
            break
    return events


def _extract_causality(full_script: str, blocks: list[_SceneBlock]) -> SceneCausality:
    """Only emit links when explicit causal connectives span scenes — else missing."""

    # Explicit markers that claim cross-beat causation in text
    pattern = re.compile(
        r"(因为[^。]{2,40}[，,]?所以[^。]{2,40}[。]?|"
        r"于是[^。]{4,40}[。]|"
        r"因此[^。]{4,40}[。])"
    )
    hits = pattern.findall(full_script)
    if not hits or len(blocks) < 2:
        return SceneCausality(
            links=[],
            status="missing",
            uncertainty_note="no explicit cross-scene causal connective in source text",
        )

    links: list[SceneCausalityLink] = []
    # Attach to first→second ordinal as weak structural hint only when connective exists
    statement = _claimed(full_script, hits[0][:120], confidence=0.55)
    if statement is None:
        return SceneCausality(status="missing", uncertainty_note="causal hit lacked span")
    links.append(
        SceneCausalityLink(
            link_id=_id("cause"),
            from_scene_ref=blocks[0].ordinal_raw or "scene_0",
            to_scene_ref=blocks[1].ordinal_raw or "scene_1",
            statement=statement,
        )
    )
    return SceneCausality(links=links, status="present", uncertainty_note=None)


def build_scene_version_from_block(
    block: _SceneBlock,
    *,
    scene_id: str,
    version_id: str,
    project_id: str,
    source_revision_id: str,
    source_revision_digest: str,
    full_script: str,
    all_blocks: list[_SceneBlock],
    extracted_place_hint: str | None = None,
) -> SceneVersion:
    labels = _labels_in_body(block.body)
    int_ext_h, place_h, time_h = _parse_heading_parts(block.heading_line)

    place_text = labels.get("地点") or labels.get("场景") or place_h or extracted_place_hint
    time_text = labels.get("时间") or time_h
    int_ext_text = int_ext_h

    missing: list[str] = []

    if place_text:
        place_claim = _claimed(block.full_text, place_text, confidence=0.92)
        display_name = place_text
    else:
        place_claim = None
        display_name = "(unnamed scene)"
        missing.append("identity.display_name")
        missing.append("time_space.place")

    ordinal_claim = (
        _claimed(block.full_text, block.ordinal_raw, confidence=0.95)
        if block.ordinal_raw
        else None
    )
    if ordinal_claim is None:
        missing.append("identity.scene_ordinal")

    time_claim = (
        _claimed(block.full_text, time_text, confidence=0.9) if time_text else None
    )
    if time_claim is None:
        # prose-only time cue (e.g. 深夜) — only if in body start
        prose_time = None
        for tok in _TIME_TOKENS:
            if tok in block.body[:40] or (block.heading_line and tok in block.heading_line):
                prose_time = tok
                break
        if prose_time:
            time_claim = _claimed(block.full_text, prose_time, confidence=0.75)
        else:
            missing.append("time_space.time_of_day")

    int_ext_claim = (
        _claimed(block.full_text, int_ext_text, confidence=0.92) if int_ext_text else None
    )
    if int_ext_claim is None:
        missing.append("time_space.interior_exterior")

    # Vague place → keep weak claim but mark missing_fields for place quality
    if place_text and (
        place_text in {"房间", "昏暗的房间"}
        or re.fullmatch(r"(昏暗的|黑暗的)?房间", place_text)
    ):
        missing.append("time_space.place")
        place_claim = ClaimedText(
            text=place_text or "房间",
            confidence=0.4,
            evidence_spans=[_span(block.full_text, place_text or "房间") or EvidenceSpan(start=0, end=2, quote="房间")],
            uncertainty_note="vague location phrase; not a concrete scene name",
        )
        display_name = place_text or "(unnamed scene)"

    props = SceneProps(items=_extract_props(block.full_text))
    if not props.items:
        missing.append("props")

    events = SceneEvents(items=_extract_events(block.full_text))
    if not events.items:
        missing.append("events")

    # Causality is script-level; attach same missing/present to each version
    causality = _extract_causality(full_script, all_blocks)
    if causality.status == "missing":
        missing.append("causality")

    entity_spans: list[EvidenceSpan] = []
    if block.heading_line:
        sp = _span(full_script, block.heading_line)
        if sp:
            entity_spans.append(sp)
    if place_claim and place_claim.evidence_spans:
        entity_spans.extend(place_claim.evidence_spans[:1])
    if not entity_spans:
        # prose-only: use first 40 chars of body
        snippet = block.body[:40] or display_name
        sp = _span(full_script, snippet) or EvidenceSpan(
            start=0, end=max(len(snippet), 1), quote=snippet[:1200]
        )
        entity_spans.append(sp)

    confidence = 0.9 if place_claim and place_claim.uncertainty_note is None else 0.45

    return SceneVersion(
        scene_id=scene_id,
        version_id=version_id,
        version_number=1,
        parent_version_id=None,
        project_id=project_id,
        source_revision_id=source_revision_id,
        source_revision_digest=source_revision_digest,
        identity=SceneIdentity(
            display_name=display_name,
            scene_ordinal=ordinal_claim,
        ),
        time_space=SceneTimeSpace(
            time_of_day=time_claim,
            interior_exterior=int_ext_claim,
            place=place_claim,
        ),
        props=props,
        events=events,
        causality=causality,
        evidence_spans=entity_spans[:24],
        confidence=confidence,
        status="candidate",
        produced_by="deterministic_extractor",
        produced_at=datetime.now(timezone.utc),
        missing_fields=sorted(set(missing)),
    )


def build_scene_entities_from_script(
    source_text: str,
    *,
    project_id: str,
    source_revision_id: str,
) -> list[SceneEntity]:
    """Build SceneEntity list for one script revision (candidate versions)."""

    digest = _digest(source_text)
    blocks = _split_scene_blocks(source_text)
    # Align improved extractor place names (ordered) as hints
    extracted, _notes = extract_scenes(source_text)
    place_hints = [e.text for e in extracted if e.status != ExtractStatus.MISSING]

    entities: list[SceneEntity] = []
    for i, block in enumerate(blocks):
        hint = place_hints[i] if i < len(place_hints) else (place_hints[0] if len(place_hints) == 1 and len(blocks) == 1 else None)
        # If labeled/heading place exists, prefer that over hint
        scene_id = _id("scene")
        version_id = _id("sver")
        version = build_scene_version_from_block(
            block,
            scene_id=scene_id,
            version_id=version_id,
            project_id=project_id,
            source_revision_id=source_revision_id,
            source_revision_digest=digest,
            full_script=source_text,
            all_blocks=blocks,
            extracted_place_hint=hint,
        )
        history = [
            ChangeRecord(
                change_id=_id("chg"),
                at=version.produced_at or datetime.now(timezone.utc),
                actor_kind="extractor",
                actor_id="scene_schema_builder_v0",
                from_version_id=None,
                to_version_id=version_id,
                summary=f"scene candidate v1: {version.identity.display_name}",
                field_paths=["identity", "time_space", "props", "events", "causality"],
                reason="initial_scene_extract",
            )
        ]
        entities.append(
            SceneEntity(
                scene_id=scene_id,
                project_id=project_id,
                head_version_id=version_id,
                versions=[version],
                history=history,
            )
        )
    return entities


# ---------------------------------------------------------------------------
# Bridge to existing CandidateFact status machine (reuse, don't reinvent)
# ---------------------------------------------------------------------------


def _as_status_claim(claim: ClaimedText) -> StatusClaimedText:
    """Character-draft ClaimedText → status-model ClaimedText (same shape, distinct types)."""

    return StatusClaimedText.model_validate(claim.model_dump())


def scene_version_to_candidate_facts(version: SceneVersion) -> list[CandidateFact]:
    """Project SceneVersion soft fields into CandidateFact rows for the confirmation loop."""

    facts: list[CandidateFact] = []
    produced = version.produced_at or datetime.now(timezone.utc)

    def add(
        field_path: str,
        claim: ClaimedText | None,
        *,
        missing: bool = False,
        placeholder: str = "(missing)",
    ) -> None:
        if missing or claim is None:
            facts.append(
                CandidateFact(
                    fact_id=_id("fact"),
                    entity_kind="scene",
                    entity_id=version.scene_id,
                    field_path=field_path,
                    claim=StatusClaimedText(
                        text=placeholder,
                        confidence=0.0,
                        evidence_spans=[],
                        uncertainty_note=f"{field_path} not supported by source evidence",
                    ),
                    status=CandidateStatus.MISSING,
                    project_id=version.project_id,
                    source_revision_id=version.source_revision_id,
                    source_revision_digest=version.source_revision_digest,
                    producer="deterministic_extractor",
                    produced_at=produced,
                )
            )
            return
        status = CandidateStatus.EXTRACTED_FROM_TEXT
        if claim.uncertainty_note:
            status = CandidateStatus.MODEL_INFERRED
        facts.append(
            CandidateFact(
                fact_id=_id("fact"),
                entity_kind="scene",
                entity_id=version.scene_id,
                field_path=field_path,
                claim=_as_status_claim(claim),
                status=status,
                project_id=version.project_id,
                source_revision_id=version.source_revision_id,
                source_revision_digest=version.source_revision_digest,
                producer="deterministic_extractor",
                produced_at=produced,
            )
        )

    unnamed = version.identity.display_name == "(unnamed scene)"
    name_claim = None
    if not unnamed:
        name_claim = ClaimedText(
            text=version.identity.display_name,
            confidence=version.confidence,
            evidence_spans=list(version.evidence_spans[:1]),
        )
    add(
        "scene.name",
        name_claim,
        missing=unnamed,
        placeholder="(unnamed scene)",
    )
    add(
        "scene.time_space.time_of_day",
        version.time_space.time_of_day,
        missing=version.time_space.time_of_day is None,
    )
    add(
        "scene.time_space.interior_exterior",
        version.time_space.interior_exterior,
        missing=version.time_space.interior_exterior is None,
    )
    add(
        "scene.time_space.place",
        version.time_space.place,
        missing=version.time_space.place is None,
    )
    if version.props.items:
        for prop in version.props.items:
            add(f"scene.props.{prop.prop_id}", prop.name)
    else:
        add("scene.props", None, missing=True, placeholder="(no props extracted)")
    if version.events.items:
        for ev in version.events.items[:3]:
            add(f"scene.events.{ev.event_id}", ev.statement)
    else:
        add("scene.events", None, missing=True, placeholder="(no events extracted)")

    if version.causality.status == "missing" or not version.causality.links:
        add(
            "scene.causality",
            None,
            missing=True,
            placeholder="(no cross-scene causality in text)",
        )
    else:
        for link in version.causality.links:
            add(f"scene.causality.{link.link_id}", link.statement)

    return facts


DESIGN_CHOICES = """
1. Mirror CharacterVersion/Entity — immutable version + append-only ChangeRecord.
2. ClaimedText on soft facets; missing_fields when evidence absent (esp. causality).
3. Reuse CandidateFact + promote_candidate_fact (entity_kind=scene); no new gate.
4. Scene names from improved extraction / headings / 地点： labels — not junk regex.
5. Causality defaults to missing unless explicit 因为/所以/于是/因此 appears.
6. Beat out of scope; apps/api not wired.
"""


__all__ = (
    "SCHEMA_VERSION",
    "SceneIdentity",
    "SceneTimeSpace",
    "ScenePropItem",
    "SceneProps",
    "SceneEventItem",
    "SceneEvents",
    "SceneCausalityLink",
    "SceneCausality",
    "SceneVersion",
    "SceneEntity",
    "build_scene_entities_from_script",
    "scene_version_to_candidate_facts",
)


def _summarize_entities(entities: list[SceneEntity]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ent in entities:
        v = next(x for x in ent.versions if x.version_id == ent.head_version_id)
        rows.append(
            {
                "display_name": v.identity.display_name,
                "ordinal": v.identity.scene_ordinal.text if v.identity.scene_ordinal else None,
                "time": v.time_space.time_of_day.text if v.time_space.time_of_day else None,
                "int_ext": (
                    v.time_space.interior_exterior.text
                    if v.time_space.interior_exterior
                    else None
                ),
                "place": v.time_space.place.text if v.time_space.place else None,
                "props": [p.name.text for p in v.props.items],
                "events_n": len(v.events.items),
                "causality": v.causality.status,
                "missing_fields": v.missing_fields,
                "candidate_facts_n": len(scene_version_to_candidate_facts(v)),
            }
        )
    return rows


if __name__ == "__main__":
    import json

    scripts_dir = _HERE / "test-scripts-character-scene"
    files = sorted(scripts_dir.glob("0*.txt"))
    report: list[dict[str, Any]] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        entities = build_scene_entities_from_script(
            text,
            project_id="proj_scene_schema_demo",
            source_revision_id=f"scrrev_{path.stem[:24]}",
        )
        # Sanity: causality should be missing on the standard 6 scripts
        causality_statuses = [
            e.versions[0].causality.status for e in entities
        ]
        report.append(
            {
                "file": path.name,
                "scene_count": len(entities),
                "scenes": _summarize_entities(entities),
                "all_causality_missing": all(s == "missing" for s in causality_statuses),
            }
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
