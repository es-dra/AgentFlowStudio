"""DRAFT ONLY — not wired into Runtime.

Proposed Pydantic schema for a §7.2 script-understanding Character entity.

Date: 2026-08-01
Status: design draft for review; do not import from apps/api yet.
Base: evolves `CandidateCharacter` / `EvidenceSpan` in
`apps/api/runtime_script_core_truth.py` rather than replacing them cold.

§7.2 coverage (character slice):
  - identity, goals, motivation, relationships, character arc, language/voice
  - stable ID, source location (evidence spans), version, confidence, change history

Related gap note: docs/internal-notes/script-flow-findings-20260801.md
Task context: AFS 智能体内核 §7.2 完善专业剧本理解能力
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SCHEMA_VERSION = "afs.script_understanding.character.v0.1.draft"


# ---------------------------------------------------------------------------
# Shared primitives (compatible with today's CandidateCharacter helpers)
# ---------------------------------------------------------------------------


class EvidenceSpan(BaseModel):
    """Source location inside a script revision's source_text.

    Same contract as Runtime `EvidenceSpan`: [start, end) offsets + quote.
    Kept local in this draft so the file is self-contained; a future promote
    step should import the Runtime type instead of duplicating it.
    """

    model_config = ConfigDict(extra="forbid")

    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str = Field(min_length=1, max_length=1200)

    @model_validator(mode="after")
    def validate_span_order(self) -> "EvidenceSpan":
        if self.end <= self.start:
            raise ValueError("evidence span end must be greater than start")
        return self


class ClaimedText(BaseModel):
    """A soft understanding claim: text + confidence + evidence.

    Design choice: §7.2 fields like motivation/arc are often incomplete.
    Wrapping them as ClaimedText lets extractors emit partial results with
    explicit uncertainty instead of inventing filler (a failure mode we saw
    in deterministic M6 templates).
    """

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list, max_length=12)
    uncertainty_note: str | None = Field(default=None, max_length=400)


class ChangeRecord(BaseModel):
    """Append-only history entry for one character version transition."""

    model_config = ConfigDict(extra="forbid")

    change_id: str = Field(min_length=1, max_length=120)
    at: datetime
    actor_kind: Literal["extractor", "human", "agent", "system"] = "system"
    actor_id: str | None = Field(default=None, max_length=160)
    from_version_id: str | None = Field(default=None, max_length=120)
    to_version_id: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=800)
    field_paths: list[str] = Field(
        default_factory=list,
        max_length=64,
        description="Dot-paths that changed, e.g. 'goals', 'relationships.0.label'",
    )
    reason: str | None = Field(default=None, max_length=400)


# ---------------------------------------------------------------------------
# §7.2 character facets
# ---------------------------------------------------------------------------


class CharacterIdentity(BaseModel):
    """Who the character is on the page (naming + demographic cues).

    Evolves CandidateCharacter.display_name / aliases / pronoun_links.
    Visual continuity locks stay in Episode ContinuityStateVersion — this
    identity block is script-semantic, not wardrobe/signature production state.
    """

    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=120)
    aliases: list[str] = Field(default_factory=list, max_length=20)
    pronoun_links: list[str] = Field(default_factory=list, max_length=20)
    age_or_life_stage: ClaimedText | None = None
    role_label: ClaimedText | None = Field(
        default=None,
        description="e.g. 主角 / 对手 / 母亲 — narrative role, not casting",
    )
    brief_description: ClaimedText | None = None


class CharacterGoal(BaseModel):
    """A concrete want/need expressed or implied in the script."""

    model_config = ConfigDict(extra="forbid")

    goal_id: str = Field(min_length=1, max_length=120)
    statement: ClaimedText
    scope: Literal["scene", "episode", "series", "unspecified"] = "unspecified"
    is_primary: bool = False


class CharacterMotivation(BaseModel):
    """Why the character pursues goals (internal / external drivers)."""

    model_config = ConfigDict(extra="forbid")

    motivation_id: str = Field(min_length=1, max_length=120)
    statement: ClaimedText
    linked_goal_ids: list[str] = Field(default_factory=list, max_length=16)


class CharacterRelationship(BaseModel):
    """Directed or labeled relation to another character (or unresolved name)."""

    model_config = ConfigDict(extra="forbid")

    relationship_id: str = Field(min_length=1, max_length=120)
    # Prefer stable id when known; allow unresolved display name during early extract.
    other_character_id: str | None = Field(default=None, max_length=120)
    other_display_name: str | None = Field(default=None, max_length=120)
    label: ClaimedText = Field(description="e.g. 母女 / 旧友 / 对立")
    stance: ClaimedText | None = Field(
        default=None,
        description="Current emotional/power stance if script supports it",
    )
    direction: Literal["from_self", "to_self", "bidirectional", "unspecified"] = "unspecified"

    @model_validator(mode="after")
    def require_other_ref(self) -> "CharacterRelationship":
        if not self.other_character_id and not self.other_display_name:
            raise ValueError("relationship requires other_character_id or other_display_name")
        return self


class CharacterArc(BaseModel):
    """Change vector across the understood script span (not series ArcVersion)."""

    model_config = ConfigDict(extra="forbid")

    starting_state: ClaimedText | None = None
    ending_state: ClaimedText | None = None
    change_summary: ClaimedText | None = None
    turning_points: list[ClaimedText] = Field(default_factory=list, max_length=12)


class CharacterLanguageVoice(BaseModel):
    """How the character speaks / is written on the page."""

    model_config = ConfigDict(extra="forbid")

    speech_register: ClaimedText | None = Field(
        default=None,
        description="Formality / social register, e.g. 口语、克制、命令口吻",
    )
    diction_notes: ClaimedText | None = None
    recurring_phrases: list[ClaimedText] = Field(default_factory=list, max_length=20)
    silence_or_subtext_notes: ClaimedText | None = None


# ---------------------------------------------------------------------------
# Entity + version envelope
# ---------------------------------------------------------------------------


class CharacterVersion(BaseModel):
    """One immutable version of a character understanding record.

    Cross-cutting §7.2 requirements:
      - stable ID          → character_id (entity) + version_id (this snapshot)
      - source location    → evidence_spans (+ per-claim spans)
      - version            → version_id / version_number / parent_version_id
      - confidence         → confidence (entity) + ClaimedText.confidence
      - change history     → carried on CharacterEntity.history (see below)
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=SCHEMA_VERSION, min_length=1, max_length=80)

    # Identity / lineage
    character_id: str = Field(min_length=1, max_length=120)
    version_id: str = Field(min_length=1, max_length=120)
    version_number: int = Field(ge=1, strict=True)
    parent_version_id: str | None = Field(default=None, max_length=120)

    # Binding to Script Truth (authority for source_text)
    project_id: str = Field(min_length=1, max_length=128)
    source_revision_id: str = Field(min_length=1, max_length=120)
    source_revision_digest: str = Field(min_length=64, max_length=64)

    # Evolved CandidateCharacter core
    identity: CharacterIdentity
    evidence_spans: list[EvidenceSpan] = Field(
        min_length=1,
        max_length=24,
        description="Entity-level evidence that this character exists in the script",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall extractor/human confidence for this version",
    )
    status: Literal["candidate", "confirmed", "pending_confirmation", "rejected", "retired"] = (
        "candidate"
    )

    # §7.2 understanding facets (all optional for migration / partial extract)
    goals: list[CharacterGoal] = Field(default_factory=list, max_length=16)
    motivations: list[CharacterMotivation] = Field(default_factory=list, max_length=16)
    relationships: list[CharacterRelationship] = Field(default_factory=list, max_length=32)
    arc: CharacterArc | None = None
    language_voice: CharacterLanguageVoice | None = None

    # Provenance of this version
    produced_by: Literal["human", "deterministic_extractor", "llm", "mixed"] = "human"
    produced_at: datetime | None = None
    missing_fields: list[str] = Field(
        default_factory=list,
        max_length=64,
        description="Explicit gaps, e.g. 'motivations', 'arc.ending_state'",
    )
    contradiction_notes: list[str] = Field(
        default_factory=list,
        max_length=32,
        description="Known conflicts inside this version; empty means none recorded",
    )

    @model_validator(mode="after")
    def parent_rules(self) -> "CharacterVersion":
        if self.version_number == 1 and self.parent_version_id is not None:
            raise ValueError("version_number 1 must not set parent_version_id")
        if self.version_number > 1 and not self.parent_version_id:
            raise ValueError("version_number > 1 requires parent_version_id")
        return self


class CharacterEntity(BaseModel):
    """Stable character entity with head version + append-only change history.

    Design choice: split entity (stable id + history) from version (immutable
    content snapshot), mirroring Episode Production Fact Contract's
    entity_id / version_id pattern without coupling to ContinuityStateVersion.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=SCHEMA_VERSION, min_length=1, max_length=80)
    character_id: str = Field(min_length=1, max_length=120)
    project_id: str = Field(min_length=1, max_length=128)
    head_version_id: str = Field(min_length=1, max_length=120)
    versions: list[CharacterVersion] = Field(min_length=1, max_length=256)
    history: list[ChangeRecord] = Field(default_factory=list, max_length=512)

    @model_validator(mode="after")
    def head_and_ids_consistent(self) -> "CharacterEntity":
        by_id = {item.version_id: item for item in self.versions}
        if len(by_id) != len(self.versions):
            raise ValueError("duplicate version_id in versions")
        if self.head_version_id not in by_id:
            raise ValueError("head_version_id must reference a version in versions")
        for item in self.versions:
            if item.character_id != self.character_id:
                raise ValueError("version.character_id must match entity.character_id")
            if item.project_id != self.project_id:
                raise ValueError("version.project_id must match entity.project_id")
        return self


# ---------------------------------------------------------------------------
# Migration helper (documentation-level; not Runtime-wired)
# ---------------------------------------------------------------------------


def character_version_from_candidate_character(
    *,
    candidate: dict[str, Any],
    character_id: str,
    version_id: str,
    project_id: str,
    source_revision_id: str,
    source_revision_digest: str,
    produced_at: datetime | None = None,
) -> CharacterVersion:
    """Show how today's CandidateCharacter dict maps into CharacterVersion v1.

    Missing §7.2 facets stay empty and are listed in missing_fields so PASS
    cannot be confused with full comprehension.
    """

    identity = CharacterIdentity(
        display_name=str(candidate["display_name"]),
        aliases=list(candidate.get("aliases") or []),
        pronoun_links=list(candidate.get("pronoun_links") or []),
    )
    spans = [EvidenceSpan.model_validate(item) for item in candidate.get("evidence_spans") or []]
    return CharacterVersion(
        character_id=character_id,
        version_id=version_id,
        version_number=1,
        parent_version_id=None,
        project_id=project_id,
        source_revision_id=source_revision_id,
        source_revision_digest=source_revision_digest,
        identity=identity,
        evidence_spans=spans,
        confidence=float(candidate.get("confidence") or 0.0),
        status=_coerce_status(candidate.get("status")),
        produced_by="human",
        produced_at=produced_at,
        missing_fields=[
            "goals",
            "motivations",
            "relationships",
            "arc",
            "language_voice",
        ],
    )


def _coerce_status(
    value: Any,
) -> Literal["candidate", "confirmed", "pending_confirmation", "rejected", "retired"]:
    allowed = {"candidate", "confirmed", "pending_confirmation", "rejected", "retired"}
    text = str(value or "candidate")
    if text not in allowed:
        return "candidate"
    return text  # type: ignore[return-value]


# Rebuild forward refs created by `from __future__ import annotations`.
EvidenceSpan.model_rebuild()
ClaimedText.model_rebuild()
ChangeRecord.model_rebuild()
CharacterIdentity.model_rebuild()
CharacterGoal.model_rebuild()
CharacterMotivation.model_rebuild()
CharacterRelationship.model_rebuild()
CharacterArc.model_rebuild()
CharacterLanguageVoice.model_rebuild()
CharacterVersion.model_rebuild()
CharacterEntity.model_rebuild()


DESIGN_CHOICES = """
1. Natural evolution, not rewrite
   Keep display_name / aliases / pronoun_links / evidence_spans / confidence /
   status semantics from CandidateCharacter. Add structure around them
   (CharacterIdentity) instead of renaming fields cold.

2. ClaimedText for soft facts
   Goals/motivation/arc/voice are often partial. Per-claim confidence +
   evidence + uncertainty_note avoid M6-style template filler that still PASS.

3. Entity vs version split
   Matches Episode fact-contract habit (stable entity_id + immutable
   version_id) so Character can later feed Production Graph without using
   ContinuityStateVersion as a fake story model. Continuity remains visual /
   production locks; this schema is script understanding.

4. Bind to Script Truth revision + digest
   Today's M6 pain: dual ids and edits that don't rebind. Every version must
   name the exact source_revision_id / source_revision_digest it was read from.

5. Relationships allow unresolved names
   Early extract may know "林秀" before ids exist. other_display_name lets the
   graph close later via merge_alias-style resolution.

6. Explicit missing_fields / contradiction_notes
   §7.2 asks for information gaps and contradictions. Empty optional lists are
   not enough — missing_fields makes incompleteness machine-checkable.

7. Change history on the entity
   Append-only ChangeRecord list; versions themselves stay immutable. Human
   edit_asset today mutates labels without a typed history — this draft makes
   that history first-class for the understanding layer.

8. Do not implement into apps/api yet
   Promote path later: move models beside script_core_truth, accept
   CharacterVersion in analysis candidates, keep CandidateCharacter as a
   deprecated projection for one migration window.
"""


__all__ = (
    "SCHEMA_VERSION",
    "EvidenceSpan",
    "ClaimedText",
    "ChangeRecord",
    "CharacterIdentity",
    "CharacterGoal",
    "CharacterMotivation",
    "CharacterRelationship",
    "CharacterArc",
    "CharacterLanguageVoice",
    "CharacterVersion",
    "CharacterEntity",
    "character_version_from_candidate_character",
)
