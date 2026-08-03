"""DRAFT ONLY — not wired into Runtime / apps/api.

ScriptProfile understanding schema (2026-08-03).

Script-level facets from §7.2: theme / genre / audience / narrative_goals /
style_requirements. One profile per script revision (entity_kind=\"script_profile\").

Methodology reuse (do not reinvent):
  - ClaimedText + EvidenceSpan
  - CandidateFact / promote_candidate_fact (entity_kind=\"script_profile\")
  - confirmation loop accept / edit_confirm / reject
  - missing when no textual evidence — never invent genre/audience from vibe

Subjectivity note: theme / narrative_goals / style are often interpretive.
Deterministic extraction only accepts *explicit labeled* metadata lines
(e.g. ``主题：`` / ``类型：``). Plot-based guessing is out of scope and would
be ``model_inferred`` candidates later, never authoritative by confidence.
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


SCHEMA_VERSION = "afs.script_understanding.script_profile.v0.1.draft"
FacetStatus = Literal["present", "missing"]
PROFILE_ENTITY_KIND = "script_profile"

# Explicit metadata labels only — never infer from plot prose.
_LABEL_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "theme": (
        re.compile(r"(?m)^\s*(?:主题|主旨|Theme)\s*[:：]\s*(.+?)\s*$"),
    ),
    "genre": (
        re.compile(r"(?m)^\s*(?:类型|题材|Genre|Genres)\s*[:：]\s*(.+?)\s*$"),
    ),
    "audience": (
        re.compile(
            r"(?m)^\s*(?:受众|目标观众|观众|分级|Audience|Rating)\s*[:：]\s*(.+?)\s*$"
        ),
    ),
    "narrative_goals": (
        re.compile(
            r"(?m)^\s*(?:叙事目标|创作意图|故事目标|Narrative\s*goals?)\s*[:：]\s*(.+?)\s*$",
            re.IGNORECASE,
        ),
    ),
    "style_requirements": (
        re.compile(
            r"(?m)^\s*(?:风格要求|风格|视觉风格|Style(?:\s*requirements?)?)\s*[:：]\s*(.+?)\s*$",
            re.IGNORECASE,
        ),
    ),
}


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Facets
# ---------------------------------------------------------------------------


class SingleClaimFacet(BaseModel):
    """One ClaimedText slot with explicit present/missing discipline."""

    model_config = ConfigDict(extra="forbid")

    status: FacetStatus = "missing"
    claim: ClaimedText | None = None
    uncertainty_note: str | None = Field(default=None, max_length=400)

    @model_validator(mode="after")
    def validate_presence(self) -> "SingleClaimFacet":
        if (self.status == "present") != (self.claim is not None):
            raise ValueError("present facet requires claim; missing facet forbids claim")
        if self.status == "missing" and not self.uncertainty_note:
            raise ValueError("missing facet requires uncertainty_note explaining the gap")
        return self


class GenreFacet(BaseModel):
    """Genre may be a list (悬疑+情感) when the text explicitly lists them."""

    model_config = ConfigDict(extra="forbid")

    status: FacetStatus = "missing"
    items: list[ClaimedText] = Field(default_factory=list, max_length=8)
    uncertainty_note: str | None = Field(default=None, max_length=400)

    @model_validator(mode="after")
    def validate_presence(self) -> "GenreFacet":
        if self.status == "present" and not self.items:
            raise ValueError("present genre requires at least one ClaimedText item")
        if self.status == "missing" and self.items:
            raise ValueError("missing genre must not carry inferred items")
        if self.status == "missing" and not self.uncertainty_note:
            raise ValueError("missing genre requires uncertainty_note")
        return self


class ScriptProfileIdentity(BaseModel):
    """One profile binds to exactly one script revision."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(min_length=1, max_length=120)
    title_hint: str | None = Field(default=None, max_length=200)


class ScriptProfileVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=SCHEMA_VERSION, min_length=1, max_length=80)
    profile_id: str = Field(min_length=1, max_length=120)
    version_id: str = Field(min_length=1, max_length=120)
    version_number: int = Field(ge=1, strict=True)

    project_id: str = Field(min_length=1, max_length=128)
    source_revision_id: str = Field(min_length=1, max_length=120)
    source_revision_digest: str = Field(min_length=64, max_length=64)

    identity: ScriptProfileIdentity
    theme: SingleClaimFacet
    genre: GenreFacet
    audience: SingleClaimFacet
    narrative_goals: SingleClaimFacet
    style_requirements: SingleClaimFacet

    evidence_spans: list[EvidenceSpan] = Field(default_factory=list, max_length=24)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    status: Literal["candidate", "authoritative_pending", "superseded"] = "candidate"
    produced_by: Literal["deterministic_extractor", "human", "llm", "mixed"] = (
        "deterministic_extractor"
    )
    produced_at: datetime | None = None
    missing_fields: list[str] = Field(default_factory=list, max_length=16)


class ScriptProfileEntity(BaseModel):
    """Append-only profile ledger for one project + revision lineage."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(min_length=1, max_length=120)
    project_id: str = Field(min_length=1, max_length=128)
    head_version_id: str = Field(min_length=1, max_length=120)
    versions: list[ScriptProfileVersion] = Field(min_length=1, max_length=64)
    history: list[ChangeRecord] = Field(default_factory=list, max_length=128)


# ---------------------------------------------------------------------------
# Deterministic labeled extraction (fail closed)
# ---------------------------------------------------------------------------


def _span_for_match(source: str, match: re.Match[str], group: int = 1) -> EvidenceSpan:
    start, end = match.span(group)
    quote = source[start:end]
    return EvidenceSpan(start=start, end=end, quote=quote[:1200])


def _split_genre_values(raw: str) -> list[str]:
    parts = re.split(r"[,，/+、]|与|和", raw)
    cleaned = [part.strip() for part in parts if part.strip()]
    return cleaned or [raw.strip()]


def _extract_labeled_claim(
    source: str,
    facet: str,
) -> tuple[FacetStatus, ClaimedText | None, list[ClaimedText], str]:
    """Return (status, single_claim, genre_items, uncertainty_note)."""

    patterns = _LABEL_PATTERNS[facet]
    for pattern in patterns:
        match = pattern.search(source)
        if not match:
            continue
        value = match.group(1).strip()
        if not value or value in {"无", "未知", "待定", "N/A", "n/a"}:
            continue
        if facet == "genre":
            items: list[ClaimedText] = []
            for part in _split_genre_values(value):
                # Prefer span over the whole label value when single token;
                # for multi, locate each part inside the matched group.
                group_start = match.start(1)
                group_text = match.group(1)
                local = group_text.find(part)
                if local < 0:
                    span = _span_for_match(source, match)
                else:
                    start = group_start + local
                    end = start + len(part)
                    span = EvidenceSpan(start=start, end=end, quote=source[start:end][:1200])
                items.append(
                    ClaimedText(
                        text=part,
                        confidence=0.9,
                        evidence_spans=[span],
                        uncertainty_note=None,
                    )
                )
            return "present", None, items, ""
        span = _span_for_match(source, match)
        claim = ClaimedText(
            text=value,
            confidence=0.9,
            evidence_spans=[span],
            uncertainty_note=None,
        )
        return "present", claim, [], ""

    notes = {
        "theme": "no explicit 主题/主旨 label; refusing plot-level theme inference",
        "genre": "no explicit 类型/题材 label; refusing genre classification from story vibe",
        "audience": "no explicit 受众/分级 label; short scripts rarely state audience",
        "narrative_goals": "no explicit 叙事目标/创作意图 label; not inventing audience effect",
        "style_requirements": "no explicit 风格/风格要求 label; not inventing visual style",
    }
    return "missing", None, [], notes[facet]


def extract_script_profile_facets(source_text: str) -> dict[str, object]:
    """Deterministic labeled-only extraction summary for one script body."""

    theme_status, theme_claim, _, theme_note = _extract_labeled_claim(source_text, "theme")
    genre_status, _, genre_items, genre_note = _extract_labeled_claim(source_text, "genre")
    audience_status, audience_claim, _, audience_note = _extract_labeled_claim(
        source_text, "audience"
    )
    goals_status, goals_claim, _, goals_note = _extract_labeled_claim(
        source_text, "narrative_goals"
    )
    style_status, style_claim, _, style_note = _extract_labeled_claim(
        source_text, "style_requirements"
    )
    return {
        "theme": SingleClaimFacet(
            status=theme_status,
            claim=theme_claim,
            uncertainty_note=None if theme_status == "present" else theme_note,
        ),
        "genre": GenreFacet(
            status=genre_status,
            items=genre_items,
            uncertainty_note=None if genre_status == "present" else genre_note,
        ),
        "audience": SingleClaimFacet(
            status=audience_status,
            claim=audience_claim,
            uncertainty_note=None if audience_status == "present" else audience_note,
        ),
        "narrative_goals": SingleClaimFacet(
            status=goals_status,
            claim=goals_claim,
            uncertainty_note=None if goals_status == "present" else goals_note,
        ),
        "style_requirements": SingleClaimFacet(
            status=style_status,
            claim=style_claim,
            uncertainty_note=None if style_status == "present" else style_note,
        ),
    }


def build_script_profile_entity(
    source_text: str,
    *,
    project_id: str,
    source_revision_id: str,
    title_hint: str | None = None,
) -> ScriptProfileEntity:
    """Build one ScriptProfileEntity from labeled extraction (usually mostly missing)."""

    facets = extract_script_profile_facets(source_text)
    profile_id = _id("sprof")
    version_id = _id("sprov")
    produced_at = _now()
    missing = [name for name, facet in facets.items() if facet.status == "missing"]
    present_spans: list[EvidenceSpan] = []
    for name, facet in facets.items():
        if name == "genre" and facet.status == "present":
            for item in facet.items:
                present_spans.extend(item.evidence_spans)
        elif facet.status == "present" and facet.claim is not None:
            present_spans.extend(facet.claim.evidence_spans)

    confidence = 0.0 if len(missing) == 5 else max(0.2, 0.9 * (5 - len(missing)) / 5)
    version = ScriptProfileVersion(
        profile_id=profile_id,
        version_id=version_id,
        version_number=1,
        project_id=project_id,
        source_revision_id=source_revision_id,
        source_revision_digest=_digest(source_text),
        identity=ScriptProfileIdentity(profile_id=profile_id, title_hint=title_hint),
        theme=facets["theme"],  # type: ignore[arg-type]
        genre=facets["genre"],  # type: ignore[arg-type]
        audience=facets["audience"],  # type: ignore[arg-type]
        narrative_goals=facets["narrative_goals"],  # type: ignore[arg-type]
        style_requirements=facets["style_requirements"],  # type: ignore[arg-type]
        evidence_spans=present_spans[:24],
        confidence=confidence,
        status="candidate",
        produced_by="deterministic_extractor",
        produced_at=produced_at,
        missing_fields=missing,
    )
    return ScriptProfileEntity(
        profile_id=profile_id,
        project_id=project_id,
        head_version_id=version_id,
        versions=[version],
        history=[
            ChangeRecord(
                change_id=_id("chg"),
                at=produced_at,
                actor_kind="extractor",
                actor_id="script_profile_labeled_extractor_v0",
                from_version_id=None,
                to_version_id=version_id,
                summary=(
                    f"script profile v1; present={5 - len(missing)} missing={len(missing)}"
                ),
                field_paths=list(facets.keys()),
                reason="initial_labeled_extract",
            )
        ],
    )


def _as_status_claim(claim: ClaimedText) -> StatusClaimedText:
    return StatusClaimedText.model_validate(claim.model_dump())


def script_profile_version_to_candidate_facts(
    version: ScriptProfileVersion,
) -> list[CandidateFact]:
    """Project profile facets into the existing candidate state machine."""

    produced = version.produced_at or _now()
    producer = {
        "human": "human",
        "deterministic_extractor": "deterministic_extractor",
        "llm": "llm",
        "mixed": "system",
    }[version.produced_by]
    entity_id = version.profile_id
    facts: list[CandidateFact] = []

    def _missing(field_path: str, note: str) -> CandidateFact:
        return CandidateFact(
            fact_id=_id("fact"),
            entity_kind=PROFILE_ENTITY_KIND,
            entity_id=entity_id,
            field_path=field_path,
            claim=StatusClaimedText(
                text="(missing)",
                confidence=0.0,
                evidence_spans=[],
                uncertainty_note=note,
            ),
            status=CandidateStatus.MISSING,
            project_id=version.project_id,
            source_revision_id=version.source_revision_id,
            source_revision_digest=version.source_revision_digest,
            producer=producer,
            produced_at=produced,
        )

    def _present(field_path: str, claim: ClaimedText) -> CandidateFact:
        return CandidateFact(
            fact_id=_id("fact"),
            entity_kind=PROFILE_ENTITY_KIND,
            entity_id=entity_id,
            field_path=field_path,
            claim=_as_status_claim(claim),
            status=CandidateStatus.EXTRACTED_FROM_TEXT,
            project_id=version.project_id,
            source_revision_id=version.source_revision_id,
            source_revision_digest=version.source_revision_digest,
            producer=producer,
            produced_at=produced,
        )

    if version.theme.status == "present" and version.theme.claim is not None:
        facts.append(_present("script_profile.theme", version.theme.claim))
    else:
        facts.append(
            _missing(
                "script_profile.theme",
                version.theme.uncertainty_note or "theme missing",
            )
        )

    if version.genre.status == "present" and version.genre.items:
        for index, item in enumerate(version.genre.items):
            facts.append(_present(f"script_profile.genre[{index}]", item))
    else:
        facts.append(
            _missing(
                "script_profile.genre",
                version.genre.uncertainty_note or "genre missing",
            )
        )

    if version.audience.status == "present" and version.audience.claim is not None:
        facts.append(_present("script_profile.audience", version.audience.claim))
    else:
        facts.append(
            _missing(
                "script_profile.audience",
                version.audience.uncertainty_note or "audience missing",
            )
        )

    if (
        version.narrative_goals.status == "present"
        and version.narrative_goals.claim is not None
    ):
        facts.append(
            _present("script_profile.narrative_goals", version.narrative_goals.claim)
        )
    else:
        facts.append(
            _missing(
                "script_profile.narrative_goals",
                version.narrative_goals.uncertainty_note or "narrative_goals missing",
            )
        )

    if (
        version.style_requirements.status == "present"
        and version.style_requirements.claim is not None
    ):
        facts.append(
            _present(
                "script_profile.style_requirements",
                version.style_requirements.claim,
            )
        )
    else:
        facts.append(
            _missing(
                "script_profile.style_requirements",
                version.style_requirements.uncertainty_note
                or "style_requirements missing",
            )
        )

    return facts


def facet_status_table(version: ScriptProfileVersion) -> dict[str, dict[str, object]]:
    """Compact present/missing table for reports."""

    rows: dict[str, dict[str, object]] = {}
    rows["theme"] = {
        "status": version.theme.status,
        "text": None if version.theme.claim is None else version.theme.claim.text,
        "why": version.theme.uncertainty_note,
    }
    if version.genre.status == "present":
        rows["genre"] = {
            "status": "present",
            "text": [item.text for item in version.genre.items],
            "why": None,
        }
    else:
        rows["genre"] = {
            "status": "missing",
            "text": None,
            "why": version.genre.uncertainty_note,
        }
    for name in ("audience", "narrative_goals", "style_requirements"):
        facet: SingleClaimFacet = getattr(version, name)
        rows[name] = {
            "status": facet.status,
            "text": None if facet.claim is None else facet.claim.text,
            "why": facet.uncertainty_note,
        }
    return rows


__all__ = (
    "SCHEMA_VERSION",
    "PROFILE_ENTITY_KIND",
    "FacetStatus",
    "SingleClaimFacet",
    "GenreFacet",
    "ScriptProfileIdentity",
    "ScriptProfileVersion",
    "ScriptProfileEntity",
    "extract_script_profile_facets",
    "build_script_profile_entity",
    "script_profile_version_to_candidate_facts",
    "facet_status_table",
)
