"""DRAFT ONLY - not wired into Runtime / apps/api.

Beat understanding schema (2026-08-03).

Mirrors ``SceneVersion`` / ``SceneEntity`` and reuses the local design-stage
``ClaimedText``, ``CandidateFact``, and candidate promotion state machine.

The central safety rule is that a BeatVersion requires an explicit or reviewed
source range. Paragraphs, action sentences, dialogue turns, and scene headings
are observations, not reliable beat boundaries. When no boundary signal is
available, ``assess_beat_segmentation`` returns ``missing`` and emits no beat.
"""

from __future__ import annotations

import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from draft_candidate_fact_status_model_20260802 import (  # noqa: E402
    CandidateFact,
    CandidateStatus,
    ClaimedText as StatusClaimedText,
)
from draft_script_understanding_character_schema_20260801 import (  # noqa: E402
    ChangeRecord,
    ClaimedText,
    EvidenceSpan,
)


SCHEMA_VERSION = "afs.script_understanding.beat.v0.1.draft"
FacetStatus = Literal["present", "missing"]


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class BeatIdentity(BaseModel):
    """Stable position of a beat inside its owning scene."""

    model_config = ConfigDict(extra="forbid")

    scene_id: str = Field(min_length=1, max_length=120)
    order_index: int = Field(ge=0, strict=True)


class BeatBoundary(BaseModel):
    """Reviewed source range; missing boundaries do not become BeatVersion rows."""

    model_config = ConfigDict(extra="forbid")

    source_start: int = Field(ge=0)
    source_end: int = Field(gt=0)
    determination: Literal["explicit_marker", "human_confirmed", "model_inferred"]
    evidence_spans: list[EvidenceSpan] = Field(min_length=1, max_length=4)
    uncertainty_note: str | None = Field(default=None, max_length=400)

    @model_validator(mode="after")
    def validate_boundary(self) -> "BeatBoundary":
        if self.source_end <= self.source_start:
            raise ValueError("beat boundary end must be greater than start")
        if self.determination == "model_inferred" and not self.uncertainty_note:
            raise ValueError("model-inferred boundary requires uncertainty_note")
        return self


class BeatConflict(BaseModel):
    """Conflict or tension active in this beat, when source evidence supports it."""

    model_config = ConfigDict(extra="forbid")

    status: FacetStatus = "missing"
    tension: ClaimedText | None = None
    uncertainty_note: str | None = Field(default=None, max_length=400)

    @model_validator(mode="after")
    def validate_presence(self) -> "BeatConflict":
        if (self.status == "present") != (self.tension is not None):
            raise ValueError("present conflict requires tension; missing conflict forbids it")
        return self


class BeatTurn(BaseModel):
    """Observable change between the start and end of the beat."""

    model_config = ConfigDict(extra="forbid")

    status: FacetStatus = "missing"
    change: ClaimedText | None = None
    uncertainty_note: str | None = Field(default=None, max_length=400)

    @model_validator(mode="after")
    def validate_presence(self) -> "BeatTurn":
        if (self.status == "present") != (self.change is not None):
            raise ValueError("present turn requires change; missing turn forbids it")
        return self


class BeatInfoRelease(BaseModel):
    """New information made available to the audience or reader."""

    model_config = ConfigDict(extra="forbid")

    status: FacetStatus = "missing"
    information: ClaimedText | None = None
    uncertainty_note: str | None = Field(default=None, max_length=400)

    @model_validator(mode="after")
    def validate_presence(self) -> "BeatInfoRelease":
        if (self.status == "present") != (self.information is not None):
            raise ValueError(
                "present info release requires information; missing info release forbids it"
            )
        return self


class BeatEmotionShift(BaseModel):
    """Evidence-backed emotional movement, never a guessed mood template."""

    model_config = ConfigDict(extra="forbid")

    status: FacetStatus = "missing"
    from_state: ClaimedText | None = None
    to_state: ClaimedText | None = None
    change: ClaimedText | None = None
    uncertainty_note: str | None = Field(default=None, max_length=400)

    @model_validator(mode="after")
    def validate_presence(self) -> "BeatEmotionShift":
        claims = (self.from_state, self.to_state, self.change)
        if self.status == "present" and any(item is None for item in claims):
            raise ValueError("present emotion shift requires from_state, to_state, and change")
        if self.status == "missing" and any(item is not None for item in claims):
            raise ValueError("missing emotion shift must not contain inferred state claims")
        return self


class BeatVersion(BaseModel):
    """One immutable, source-bound version of a scene-internal beat."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=SCHEMA_VERSION, min_length=1, max_length=80)

    beat_id: str = Field(min_length=1, max_length=120)
    version_id: str = Field(min_length=1, max_length=120)
    version_number: int = Field(ge=1, strict=True)
    parent_version_id: str | None = Field(default=None, max_length=120)

    project_id: str = Field(min_length=1, max_length=128)
    source_revision_id: str = Field(min_length=1, max_length=120)
    source_revision_digest: str = Field(min_length=64, max_length=64)

    identity: BeatIdentity
    boundary: BeatBoundary
    conflict: BeatConflict = Field(default_factory=BeatConflict)
    turn: BeatTurn = Field(default_factory=BeatTurn)
    info_release: BeatInfoRelease = Field(default_factory=BeatInfoRelease)
    emotion_shift: BeatEmotionShift = Field(default_factory=BeatEmotionShift)

    evidence_spans: list[EvidenceSpan] = Field(min_length=1, max_length=24)
    confidence: float = Field(ge=0.0, le=1.0)
    status: Literal["candidate", "confirmed", "pending_confirmation", "rejected", "retired"] = (
        "candidate"
    )
    produced_by: Literal["human", "deterministic_extractor", "llm", "mixed"] = "human"
    produced_at: datetime | None = None
    missing_fields: list[str] = Field(default_factory=list, max_length=16)
    contradiction_notes: list[str] = Field(default_factory=list, max_length=16)

    @model_validator(mode="after")
    def validate_version(self) -> "BeatVersion":
        if self.version_number == 1 and self.parent_version_id is not None:
            raise ValueError("version_number 1 must not set parent_version_id")
        if self.version_number > 1 and not self.parent_version_id:
            raise ValueError("version_number > 1 requires parent_version_id")

        claims = [
            self.conflict.tension,
            self.turn.change,
            self.info_release.information,
            self.emotion_shift.from_state,
            self.emotion_shift.to_state,
            self.emotion_shift.change,
        ]
        spans = list(self.evidence_spans)
        for claim in claims:
            if claim is not None:
                spans.extend(claim.evidence_spans)
        for span in spans:
            if (
                span.start < self.boundary.source_start
                or span.end > self.boundary.source_end
            ):
                raise ValueError("beat evidence span must stay inside the reviewed boundary")
        return self


class BeatEntity(BaseModel):
    """Stable beat identity with immutable versions and append-only history."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=SCHEMA_VERSION, min_length=1, max_length=80)
    beat_id: str = Field(min_length=1, max_length=120)
    project_id: str = Field(min_length=1, max_length=128)
    scene_id: str = Field(min_length=1, max_length=120)
    head_version_id: str = Field(min_length=1, max_length=120)
    versions: list[BeatVersion] = Field(min_length=1, max_length=256)
    history: list[ChangeRecord] = Field(default_factory=list, max_length=512)

    @model_validator(mode="after")
    def head_and_ids_consistent(self) -> "BeatEntity":
        by_id = {item.version_id: item for item in self.versions}
        if len(by_id) != len(self.versions):
            raise ValueError("duplicate version_id in versions")
        if self.head_version_id not in by_id:
            raise ValueError("head_version_id must reference a version in versions")
        for item in self.versions:
            if item.beat_id != self.beat_id:
                raise ValueError("version.beat_id must match entity.beat_id")
            if item.project_id != self.project_id:
                raise ValueError("version.project_id must match entity.project_id")
            if item.identity.scene_id != self.scene_id:
                raise ValueError("version.identity.scene_id must match entity.scene_id")
        return self


class BeatRangeCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_index: int = Field(ge=0, strict=True)
    source_start: int = Field(ge=0)
    source_end: int = Field(gt=0)
    marker: str = Field(min_length=1, max_length=120)


class BeatSegmentationAssessment(BaseModel):
    """Fail-closed assessment; ``missing`` means no BeatVersion may be emitted."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["explicit_boundaries", "missing"]
    boundary_candidates: list[BeatRangeCandidate] = Field(default_factory=list)
    explicit_marker_count: int = Field(ge=0)
    scene_heading_count: int = Field(ge=0)
    paragraph_break_count: int = Field(ge=0)
    notes: list[str] = Field(default_factory=list, max_length=16)


_EXPLICIT_BEAT_MARKER = re.compile(
    r"(?im)^[ \t]*(?:节拍\s*[一二三四五六七八九十百零\d]+|BEAT\s+\d+)"
    r"(?:\s*[-:：]\s*[^\n]*)?$"
)
_SCENE_HEADING = re.compile(r"(?m)^\s*第[一二三四五六七八九十百零\d]+场(?:\s|$)")


def assess_beat_segmentation(source_text: str) -> BeatSegmentationAssessment:
    """Recognize explicit labels only; production callers should invoke this per Scene."""

    markers = list(_EXPLICIT_BEAT_MARKER.finditer(source_text))
    ranges: list[BeatRangeCandidate] = []
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(source_text)
        if end > marker.start():
            ranges.append(
                BeatRangeCandidate(
                    order_index=index,
                    source_start=marker.start(),
                    source_end=end,
                    marker=marker.group(0).strip(),
                )
            )

    paragraphs = len(re.findall(r"\n\s*\n", source_text))
    scene_headings = len(_SCENE_HEADING.findall(source_text))
    if not ranges:
        return BeatSegmentationAssessment(
            status="missing",
            boundary_candidates=[],
            explicit_marker_count=0,
            scene_heading_count=scene_headings,
            paragraph_break_count=paragraphs,
            notes=[
                "no explicit beat labels found",
                "scene headings and paragraph breaks were observed but rejected as beat boundaries",
                "human review or a language-understanding candidate pass is required",
            ],
        )
    return BeatSegmentationAssessment(
        status="explicit_boundaries",
        boundary_candidates=ranges,
        explicit_marker_count=len(markers),
        scene_heading_count=scene_headings,
        paragraph_break_count=paragraphs,
        notes=["only explicit numbered beat labels were accepted as boundaries"],
    )


def claimed_text_from_exact_quote(
    source_text: str,
    quote: str,
    *,
    confidence: float,
    scope_start: int = 0,
    scope_end: int | None = None,
    uncertainty_note: str | None = None,
) -> ClaimedText:
    """Create a claim only when its quote is present inside the reviewed range."""

    end = len(source_text) if scope_end is None else scope_end
    index = source_text.find(quote, scope_start, end)
    if index < 0:
        raise ValueError("claimed text quote is not present inside the reviewed beat range")
    return ClaimedText(
        text=quote,
        confidence=confidence,
        evidence_spans=[EvidenceSpan(start=index, end=index + len(quote), quote=quote)],
        uncertainty_note=uncertainty_note,
    )


def build_beat_entity_from_reviewed_range(
    source_text: str,
    *,
    project_id: str,
    source_revision_id: str,
    scene_id: str,
    order_index: int,
    source_start: int,
    source_end: int,
    boundary_determination: Literal["explicit_marker", "human_confirmed", "model_inferred"],
    conflict: BeatConflict | None = None,
    turn: BeatTurn | None = None,
    info_release: BeatInfoRelease | None = None,
    emotion_shift: BeatEmotionShift | None = None,
    boundary_uncertainty_note: str | None = None,
) -> BeatEntity:
    """Build one candidate BeatEntity after a boundary was explicitly reviewed."""

    if source_end <= source_start or source_end > len(source_text):
        raise ValueError("reviewed beat range is outside source_text")
    snippet = source_text[source_start:source_end]
    if not snippet.strip():
        raise ValueError("reviewed beat range must contain source text")

    beat_id = _id("beat")
    version_id = _id("bver")
    produced_at = datetime.now(timezone.utc)
    evidence_quote = snippet[:1200]
    boundary_span = EvidenceSpan(
        start=source_start,
        end=source_start + len(evidence_quote),
        quote=evidence_quote,
    )
    resolved_conflict = conflict or BeatConflict(
        uncertainty_note="no conflict claim supported by reviewed source range"
    )
    resolved_turn = turn or BeatTurn(
        uncertainty_note="no turn claim supported by reviewed source range"
    )
    resolved_info = info_release or BeatInfoRelease(
        uncertainty_note="no information-release claim supported by reviewed source range"
    )
    resolved_emotion = emotion_shift or BeatEmotionShift(
        uncertainty_note="no explicit from/to emotion evidence in reviewed source range"
    )
    facets = {
        "conflict": resolved_conflict,
        "turn": resolved_turn,
        "info_release": resolved_info,
        "emotion_shift": resolved_emotion,
    }
    missing = [name for name, value in facets.items() if value.status == "missing"]
    confidence = {
        "explicit_marker": 0.95,
        "human_confirmed": 1.0,
        "model_inferred": 0.5,
    }[boundary_determination]
    produced_by: Literal["human", "deterministic_extractor", "llm"] = {
        "explicit_marker": "deterministic_extractor",
        "human_confirmed": "human",
        "model_inferred": "llm",
    }[boundary_determination]
    version = BeatVersion(
        beat_id=beat_id,
        version_id=version_id,
        version_number=1,
        project_id=project_id,
        source_revision_id=source_revision_id,
        source_revision_digest=_digest(source_text),
        identity=BeatIdentity(scene_id=scene_id, order_index=order_index),
        boundary=BeatBoundary(
            source_start=source_start,
            source_end=source_end,
            determination=boundary_determination,
            evidence_spans=[boundary_span],
            uncertainty_note=boundary_uncertainty_note,
        ),
        conflict=resolved_conflict,
        turn=resolved_turn,
        info_release=resolved_info,
        emotion_shift=resolved_emotion,
        evidence_spans=[boundary_span],
        confidence=confidence,
        status="candidate",
        produced_by=produced_by,
        produced_at=produced_at,
        missing_fields=missing,
    )
    return BeatEntity(
        beat_id=beat_id,
        project_id=project_id,
        scene_id=scene_id,
        head_version_id=version_id,
        versions=[version],
        history=[
            ChangeRecord(
                change_id=_id("chg"),
                at=produced_at,
                actor_kind="human" if produced_by == "human" else "extractor",
                actor_id=f"beat_boundary_{boundary_determination}",
                from_version_id=None,
                to_version_id=version_id,
                summary=f"beat candidate v1 at scene order {order_index}",
                field_paths=["identity", "boundary", *facets.keys()],
                reason="initial_reviewed_beat_range",
            )
        ],
    )


def _as_status_claim(claim: ClaimedText) -> StatusClaimedText:
    return StatusClaimedText.model_validate(claim.model_dump())


def beat_version_to_candidate_facts(version: BeatVersion) -> list[CandidateFact]:
    """Project Beat facets into the existing candidate state machine."""

    produced = version.produced_at or datetime.now(timezone.utc)
    producer = {
        "human": "human",
        "deterministic_extractor": "deterministic_extractor",
        "llm": "llm",
        "mixed": "system",
    }[version.produced_by]
    facet_claims: list[tuple[str, FacetStatus, ClaimedText | None]] = [
        ("beat.conflict.tension", version.conflict.status, version.conflict.tension),
        ("beat.turn.change", version.turn.status, version.turn.change),
        (
            "beat.info_release.information",
            version.info_release.status,
            version.info_release.information,
        ),
        (
            "beat.emotion_shift",
            "missing",
            None,
        ),
    ]
    if version.emotion_shift.status == "present":
        facet_claims[-1:] = [
            (
                "beat.emotion_shift.from_state",
                "present",
                version.emotion_shift.from_state,
            ),
            (
                "beat.emotion_shift.to_state",
                "present",
                version.emotion_shift.to_state,
            ),
            (
                "beat.emotion_shift.change",
                "present",
                version.emotion_shift.change,
            ),
        ]
    facts: list[CandidateFact] = []
    for field_path, facet_status, claim in facet_claims:
        if facet_status == "missing" or claim is None:
            facts.append(
                CandidateFact(
                    fact_id=_id("fact"),
                    entity_kind="beat",
                    entity_id=version.beat_id,
                    field_path=field_path,
                    claim=StatusClaimedText(
                        text="(missing)",
                        confidence=0.0,
                        evidence_spans=[],
                        uncertainty_note=f"{field_path} not supported by source evidence",
                    ),
                    status=CandidateStatus.MISSING,
                    project_id=version.project_id,
                    source_revision_id=version.source_revision_id,
                    source_revision_digest=version.source_revision_digest,
                    producer=producer,
                    produced_at=produced,
                )
            )
            continue
        status = (
            CandidateStatus.MODEL_INFERRED
            if claim.uncertainty_note
            else CandidateStatus.EXTRACTED_FROM_TEXT
        )
        facts.append(
            CandidateFact(
                fact_id=_id("fact"),
                entity_kind="beat",
                entity_id=version.beat_id,
                field_path=field_path,
                claim=_as_status_claim(claim),
                status=status,
                project_id=version.project_id,
                source_revision_id=version.source_revision_id,
                source_revision_digest=version.source_revision_digest,
                producer=producer,
                produced_at=produced,
            )
        )
    return facts


__all__ = (
    "SCHEMA_VERSION",
    "BeatIdentity",
    "BeatBoundary",
    "BeatConflict",
    "BeatTurn",
    "BeatInfoRelease",
    "BeatEmotionShift",
    "BeatVersion",
    "BeatEntity",
    "BeatRangeCandidate",
    "BeatSegmentationAssessment",
    "assess_beat_segmentation",
    "claimed_text_from_exact_quote",
    "build_beat_entity_from_reviewed_range",
    "beat_version_to_candidate_facts",
)
