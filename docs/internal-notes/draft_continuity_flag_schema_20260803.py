"""DRAFT ONLY — not wired into Runtime / apps/api.

ContinuityFlag schema (2026-08-03).

§7.2 asks for time / space / character / wardrobe-prop / event *text*
continuity. That is **script diagnosis** (literal contradictions in the
page), not Episode production visual locks.

This draft deliberately:
  - uses entity_kind=\"continuity_flag\" (problem mark), never \"continuity_state\"
  - does NOT import or write ContinuityStateVersion / episode aggregates
  - does NOT ship a production detector (cross-scene contradiction finding
    needs evidenced Scene facets or language understanding — see
    continuity-flag-boundary-20260803.md)

What it does ship:
  - Pydantic shape for a flag with dual evidence spans
  - mapping convention onto CandidateFact for a future promote path
  - schema round-trip self-check on a hand-built adversarial fixture
"""

from __future__ import annotations

import hashlib
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
    EvidenceSpan as StatusEvidenceSpan,
)
from draft_script_understanding_character_schema_20260801 import (  # noqa: E402
    ClaimedText,
    EvidenceSpan,
)


SCHEMA_VERSION = "afs.script_understanding.continuity_flag.v0.1.draft"
FLAG_ENTITY_KIND = "continuity_flag"
ContinuityKind = Literal[
    "time",
    "space",
    "character",
    "wardrobe_prop",
    "event",
]


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class ContinuityFlag(BaseModel):
    """A detected (or human-supplied) literal continuity contradiction mark.

    Not a production continuity *state*. Requires at least two evidence spans
    that quote mutually conflicting source fragments. Single-sided suspicion
    is not a valid flag.
    """

    model_config = ConfigDict(extra="forbid")

    flag_id: str = Field(min_length=1, max_length=120)
    continuity_kind: ContinuityKind
    related_scene_ids: list[str] = Field(default_factory=list, max_length=16)
    related_beat_ids: list[str] = Field(default_factory=list, max_length=16)
    description: ClaimedText
    evidence_spans: list[EvidenceSpan] = Field(min_length=2, max_length=8)
    uncertainty_note: str | None = Field(default=None, max_length=400)
    source_revision_id: str = Field(min_length=1, max_length=120)
    source_revision_digest: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_flag(self) -> "ContinuityFlag":
        if len(self.evidence_spans) < 2:
            raise ValueError("continuity_flag requires at least two conflicting evidence spans")
        if not (self.related_scene_ids or self.related_beat_ids):
            raise ValueError("continuity_flag must relate to at least one scene or beat id")
        # Description evidence should reference the same contradiction; require
        # the claim to carry its own spans or inherit from the flag-level pair.
        if not self.description.evidence_spans and not self.evidence_spans:
            raise ValueError("continuity_flag description needs evidence")
        return self


# ---------------------------------------------------------------------------
# CandidateFact mapping (design-stage only)
# ---------------------------------------------------------------------------


def continuity_flag_to_candidate_fact(
    flag: ContinuityFlag,
    *,
    project_id: str,
    producer: str = "deterministic_extractor",
) -> CandidateFact:
    """Map one flag onto a CandidateFact row for a future confirmation loop.

    field_path convention:
      continuity_flag[{flag_id}].{continuity_kind}

    entity_id is the flag_id (stable problem mark identity). related scene/beat
    ids stay in claim.uncertainty_note / future metadata — not ContinuityStateVersion.
    """

    status_spans = [
        StatusEvidenceSpan(start=span.start, end=span.end, quote=span.quote)
        for span in flag.evidence_spans
    ]
    related = []
    if flag.related_scene_ids:
        related.append("scenes=" + ",".join(flag.related_scene_ids))
    if flag.related_beat_ids:
        related.append("beats=" + ",".join(flag.related_beat_ids))
    note_bits = [f"kind={flag.continuity_kind}", *related]
    if flag.uncertainty_note:
        note_bits.append(flag.uncertainty_note)

    return CandidateFact(
        fact_id=_id("fact"),
        entity_kind=FLAG_ENTITY_KIND,
        entity_id=flag.flag_id,
        field_path=f"continuity_flag[{flag.flag_id}].{flag.continuity_kind}",
        claim=StatusClaimedText(
            text=flag.description.text,
            confidence=flag.description.confidence,
            evidence_spans=status_spans,
            uncertainty_note="; ".join(note_bits),
        ),
        status=CandidateStatus.EXTRACTED_FROM_TEXT,
        project_id=project_id,
        source_revision_id=flag.source_revision_id,
        source_revision_digest=flag.source_revision_digest,
        producer=producer,
        produced_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Hand-built adversarial fixture (schema round-trip only — not a detector)
# ---------------------------------------------------------------------------


ADVERSARIAL_RAIN_DRY_SCRIPT = """第1场 - 外景 - 街口 - 日
雨下得很大。地面全是积水。林秀撑伞走过。

第2场 - 外景 - 街口 - 日
地面干燥，灰尘被风吹起。林秀走过同一街口，鞋面干净。
"""


def build_hand_labeled_rain_dry_flag(*, source_text: str = ADVERSARIAL_RAIN_DRY_SCRIPT) -> ContinuityFlag:
    """Construct a flag from known offsets in the adversarial fixture.

    This is **not** detection: spans are authored by the test author to prove
    the schema accepts dual-evidence contradiction marks.
    """

    a_quote = "雨下得很大。地面全是积水。"
    b_quote = "地面干燥，灰尘被风吹起。"
    a_start = source_text.index(a_quote)
    b_start = source_text.index(b_quote)
    spans = [
        EvidenceSpan(start=a_start, end=a_start + len(a_quote), quote=a_quote),
        EvidenceSpan(start=b_start, end=b_start + len(b_quote), quote=b_quote),
    ]
    for span in spans:
        assert source_text[span.start:span.end] == span.quote

    description = ClaimedText(
        text="同一街口日景：第1场地面有积水下雨，第2场紧接地面干燥，无时间跳跃说明。",
        confidence=0.9,
        evidence_spans=spans,
    )
    return ContinuityFlag(
        flag_id=_id("cflag"),
        continuity_kind="event",
        related_scene_ids=["scene_0_街口", "scene_1_街口"],
        description=description,
        evidence_spans=spans,
        source_revision_id="scrrev_draft_continuity_flag",
        source_revision_digest=_digest(source_text),
    )


def narrative_blank_is_not_a_flag() -> None:
    """Documented non-goal: missing elapsed-time between scenes is not a flag.

    Example prose that must NOT become a ContinuityFlag without mutual
    contradiction evidence:
      第1场 … 清晨
      第2场 … 深夜
    with no other conflicting state claims. Scene change itself is normal
    narrative jump — fail closed, emit nothing.
    """


DESIGN_CHOICES = """
1. Problem mark, not production state
   entity_kind=continuity_flag. Never reuse ContinuityStateVersion,
   continuity_state storage, or continuity.apply / undo commands.

2. Dual evidence required
   A flag without two conflicting source spans is invalid. \"Looks suspicious\"
   on one side is narrative blank, not a contradiction.

3. Related ids are script-understanding ids
   related_scene_ids / related_beat_ids point at candidate/authoritative
   script entities — read-only references. No write into episode aggregate.

4. CandidateFact mapping is future-facing
   Same ClaimedText / status machine / confirmation loop as Character/Scene/
   Beat/Profile. Production CandidateFact.entity_kind is NOT extended in this
   change; only the design-stage draft Literal includes continuity_flag.

5. No detector in this draft
   Finding contradictions needs evidenced Scene time/prop/event facets or
   model_inferred diagnosis (§7.3). Shipping regex \"清晨→深夜\" would false
   positive on normal Chinese screenplays.

6. Do not implement into apps/api yet
   Promote only after Scene facets with evidence exist and a deterministic
   cross-fact checker (plus adversarial + six-script gates) is proven.
"""


def _self_check() -> None:
    flag = build_hand_labeled_rain_dry_flag()
    assert flag.continuity_kind == "event"
    assert len(flag.evidence_spans) == 2
    fact = continuity_flag_to_candidate_fact(flag, project_id="proj_draft_continuity")
    assert fact.entity_kind == FLAG_ENTITY_KIND
    assert fact.field_path.endswith(".event")
    assert len(fact.claim.evidence_spans) == 2
    # Round-trip JSON
    restored = ContinuityFlag.model_validate(flag.model_dump())
    assert restored.flag_id == flag.flag_id
    narrative_blank_is_not_a_flag()
    print("continuity_flag draft self-check PASS")
    print(f"schema_version={SCHEMA_VERSION}")
    print(f"adversarial_flag={flag.flag_id} kind={flag.continuity_kind}")
    print(f"candidate_field_path={fact.field_path}")


if __name__ == "__main__":
    _self_check()
