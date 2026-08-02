"""DRAFT ONLY — not wired into Runtime / apps/api.

Candidate Fact Status Model (2026-08-02)

Purpose
-------
Break the M6 assumption that "regex extracted something" == canonical authority.

Builds on yesterday's Character draft:
  docs/internal-notes/draft_script_understanding_character_schema_20260801.py
    ClaimedText, EvidenceSpan, CharacterVersion, CharacterEntity, ChangeRecord

Today's scope (boss direction — do not expand):
  - Design the candidate ↔ authoritative status machine
  - Character entity type only (Scene is next step, not today)
  - Design draft under docs/internal-notes/ only — no apps/api changes

Hard rules
----------
1. Regex / model output is always a candidate fact, never auto-authoritative.
2. Every candidate records: source location, script revision, status, evidence.
3. Status must distinguish exactly these five (semantic names):
     extracted_from_text  — 原文提取
     model_inferred       — 模型推断
     missing              — 信息缺失
     conflicting          — 存在冲突
     human_confirmed      — 人工确认
4. Confidence alone cannot promote a fact to authority.
5. Only deterministic validation OR human confirmation may produce an
   AuthoritativeScriptFact (and only that may later feed Production Graph).

Real failure this blocks
------------------------
《海边的信》 regex produced display names like "苏晴没" with structural PASS.
Under this model those stay candidate (extracted_from_text or conflicting),
never become authoritative without human confirm or a passing deterministic check.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SCHEMA_VERSION = "afs.script_understanding.candidate_fact_status.v0.1.draft"

# Statuses that may never be treated as Production Graph authority by themselves.
NON_AUTHORITATIVE_STATUSES: frozenset[str]
# Populated after CandidateStatus is defined.


# ---------------------------------------------------------------------------
# Primitives (aligned with 2026-08-01 Character draft; kept local for draft isolation)
# ---------------------------------------------------------------------------


class EvidenceSpan(BaseModel):
    """Source location inside a script revision's source_text: [start, end) + quote."""

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
    """Soft claim payload from yesterday's Character draft.

    Confidence lives here as a signal only — never as sole promotion authority.
    """

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list, max_length=12)
    uncertainty_note: str | None = Field(default=None, max_length=400)


# ---------------------------------------------------------------------------
# Status enum — five boss-required distinctions, no more, no less
# ---------------------------------------------------------------------------


class CandidateStatus(str, Enum):
    """Lifecycle status of a script-understanding candidate fact.

    Chinese semantics (do not collapse or rename away from these meanings):
      extracted_from_text — 原文提取：deterministic/regex/span cut from source text
      model_inferred      — 模型推断：LLM or heuristic inference beyond literal span
      missing             — 信息缺失：slot known but value not supported by evidence
      conflicting         — 存在冲突：two+ incompatible candidates for the same slot
      human_confirmed     — 人工确认：creator accepted a concrete value
    """

    EXTRACTED_FROM_TEXT = "extracted_from_text"
    MODEL_INFERRED = "model_inferred"
    MISSING = "missing"
    CONFLICTING = "conflicting"
    HUMAN_CONFIRMED = "human_confirmed"


NON_AUTHORITATIVE_STATUSES = frozenset(
    {
        CandidateStatus.EXTRACTED_FROM_TEXT.value,
        CandidateStatus.MODEL_INFERRED.value,
        CandidateStatus.MISSING.value,
        CandidateStatus.CONFLICTING.value,
    }
)


# ---------------------------------------------------------------------------
# Transition rules (explicit gate — no implicit candidate → authoritative)
# ---------------------------------------------------------------------------


# From-status → allowed next statuses (candidate layer only).
# Becoming authoritative is NOT a status hop inside CandidateFact; it is a
# separate construction of AuthoritativeScriptFact via promote_* helpers.
ALLOWED_CANDIDATE_TRANSITIONS: dict[CandidateStatus, frozenset[CandidateStatus]] = {
    CandidateStatus.EXTRACTED_FROM_TEXT: frozenset(
        {
            CandidateStatus.CONFLICTING,
            CandidateStatus.MISSING,
            CandidateStatus.HUMAN_CONFIRMED,
            # model may re-label / refine an extract as inference in a new candidate
            CandidateStatus.MODEL_INFERRED,
        }
    ),
    CandidateStatus.MODEL_INFERRED: frozenset(
        {
            CandidateStatus.CONFLICTING,
            CandidateStatus.MISSING,
            CandidateStatus.HUMAN_CONFIRMED,
            CandidateStatus.EXTRACTED_FROM_TEXT,  # human/system corrects back to literal extract
        }
    ),
    CandidateStatus.MISSING: frozenset(
        {
            CandidateStatus.EXTRACTED_FROM_TEXT,
            CandidateStatus.MODEL_INFERRED,
            CandidateStatus.HUMAN_CONFIRMED,
            CandidateStatus.CONFLICTING,
        }
    ),
    CandidateStatus.CONFLICTING: frozenset(
        {
            CandidateStatus.HUMAN_CONFIRMED,  # human picks one value
            CandidateStatus.MISSING,  # human/system marks unresolved
            CandidateStatus.EXTRACTED_FROM_TEXT,
            CandidateStatus.MODEL_INFERRED,
        }
    ),
    # human_confirmed is terminal on the candidate ledger for that fact_id;
    # corrections create a NEW candidate / new version, not a silent downgrade.
    CandidateStatus.HUMAN_CONFIRMED: frozenset(),
}


def can_transition(from_status: CandidateStatus, to_status: CandidateStatus) -> bool:
    if from_status == to_status:
        return True
    return to_status in ALLOWED_CANDIDATE_TRANSITIONS[from_status]


def confidence_alone_may_authorize(_confidence: float) -> bool:
    """Boss hard rule: confidence is never sufficient for authority."""

    return False


def status_may_enter_production_graph(status: CandidateStatus) -> bool:
    """Candidate statuses never enter Production Graph directly.

    Even HUMAN_CONFIRMED on CandidateFact is still a candidate-layer record until
    an AuthoritativeScriptFact is explicitly minted (see promote_* below).
    """

    return False


# ---------------------------------------------------------------------------
# CandidateFact — ClaimedText + status + script revision + promotion audit
# ---------------------------------------------------------------------------


class CandidateFact(BaseModel):
    """One candidate understanding claim for Character (today) fields.

    Wraps ClaimedText and adds the status machine + script-revision binding
    that yesterday's ClaimedText alone did not enforce.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=SCHEMA_VERSION, min_length=1, max_length=80)

    fact_id: str = Field(min_length=1, max_length=120)
    entity_kind: Literal["character"] = "character"
    entity_id: str = Field(min_length=1, max_length=120)
    field_path: str = Field(
        min_length=1,
        max_length=160,
        description="e.g. 'identity.display_name' — Character only today",
    )

    # Wrapped soft claim (text + confidence + evidence spans)
    claim: ClaimedText

    # Boss-required status distinction
    status: CandidateStatus

    # Script revision binding (authority for source_text)
    project_id: str = Field(min_length=1, max_length=128)
    source_revision_id: str = Field(min_length=1, max_length=120)
    source_revision_digest: str = Field(min_length=64, max_length=64)

    # How this candidate was produced (provenance of the candidate layer)
    producer: Literal["regex_extractor", "deterministic_extractor", "llm", "human", "system"] = (
        "system"
    )
    produced_at: datetime | None = None

    # Explicit gate fields — who/what may later mint AuthoritativeScriptFact
    # These do NOT by themselves make the fact authoritative; promote_* checks them.
    human_confirmed_by: str | None = Field(default=None, max_length=160)
    human_confirmed_at: datetime | None = None
    deterministic_check_id: str | None = Field(
        default=None,
        max_length=160,
        description="Id of a named deterministic validator that passed for this claim",
    )
    deterministic_check_passed_at: datetime | None = None

    # Conflict bookkeeping (when status == conflicting)
    conflict_with_fact_ids: list[str] = Field(default_factory=list, max_length=32)
    conflict_note: str | None = Field(default=None, max_length=800)

    @model_validator(mode="after")
    def enforce_status_invariants(self) -> "CandidateFact":
        # missing: claim text may be a placeholder; evidence should be empty or note gap
        if self.status == CandidateStatus.MISSING:
            if not self.claim.uncertainty_note and not self.claim.text:
                raise ValueError("missing status requires uncertainty_note or explicit placeholder text")

        # extracted_from_text / model_inferred / human_confirmed need evidence OR explicit missing path
        if self.status in {
            CandidateStatus.EXTRACTED_FROM_TEXT,
            CandidateStatus.MODEL_INFERRED,
            CandidateStatus.HUMAN_CONFIRMED,
        }:
            if not self.claim.evidence_spans and self.status != CandidateStatus.MODEL_INFERRED:
                # model_inferred may cite weak/no span but must set uncertainty_note
                raise ValueError(f"{self.status.value} requires evidence_spans")
            if self.status == CandidateStatus.MODEL_INFERRED and not self.claim.evidence_spans:
                if not self.claim.uncertainty_note:
                    raise ValueError("model_inferred without evidence_spans requires uncertainty_note")

        if self.status == CandidateStatus.CONFLICTING and not self.conflict_with_fact_ids:
            raise ValueError("conflicting status requires conflict_with_fact_ids")

        if self.status == CandidateStatus.HUMAN_CONFIRMED:
            if not self.human_confirmed_by or self.human_confirmed_at is None:
                raise ValueError("human_confirmed requires human_confirmed_by and human_confirmed_at")

        if self.deterministic_check_id and self.deterministic_check_passed_at is None:
            raise ValueError("deterministic_check_id requires deterministic_check_passed_at")

        # Confidence alone is never enough — invariant documented on the type
        if confidence_alone_may_authorize(self.claim.confidence):
            raise ValueError("confidence alone cannot authorize a fact")

        return self

    def is_authoritative(self) -> bool:
        """CandidateFact is never authoritative by itself."""

        return False

    def may_promote_via_human(self) -> bool:
        return self.status == CandidateStatus.HUMAN_CONFIRMED and bool(self.human_confirmed_by)

    def may_promote_via_deterministic_check(self) -> bool:
        """Deterministic path: named check passed AND status is not missing/conflicting.

        Note: EXTRACTED_FROM_TEXT with a passing check may promote; raw extract
        without deterministic_check_id may not. MODEL_INFERRED never promotes
        on confidence alone — needs check id or human confirm.
        """

        if self.status in {CandidateStatus.MISSING, CandidateStatus.CONFLICTING}:
            return False
        if not self.deterministic_check_id or self.deterministic_check_passed_at is None:
            return False
        return self.status in {
            CandidateStatus.EXTRACTED_FROM_TEXT,
            CandidateStatus.MODEL_INFERRED,
            CandidateStatus.HUMAN_CONFIRMED,
        }


class AuthoritativeScriptFact(BaseModel):
    """Authoritative script fact — the only layer allowed toward Production Graph.

    Cannot be constructed by assigning status on a candidate. Must go through
    promote_candidate_fact() which checks the gate.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=SCHEMA_VERSION, min_length=1, max_length=80)

    authoritative_fact_id: str = Field(min_length=1, max_length=120)
    source_candidate_fact_id: str = Field(min_length=1, max_length=120)

    entity_kind: Literal["character"] = "character"
    entity_id: str = Field(min_length=1, max_length=120)
    field_path: str = Field(min_length=1, max_length=160)

    # Frozen accepted value
    text: str = Field(min_length=1, max_length=2000)
    evidence_spans: list[EvidenceSpan] = Field(min_length=1, max_length=12)

    project_id: str = Field(min_length=1, max_length=128)
    source_revision_id: str = Field(min_length=1, max_length=120)
    source_revision_digest: str = Field(min_length=64, max_length=64)

    # Exactly one promotion path must be recorded
    promotion_kind: Literal["human_confirmation", "deterministic_validation"]
    human_confirmed_by: str | None = Field(default=None, max_length=160)
    deterministic_check_id: str | None = Field(default=None, max_length=160)
    promoted_at: datetime

    # Confidence may be copied for display — never used as gate here
    source_confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def promotion_path_complete(self) -> "AuthoritativeScriptFact":
        if self.promotion_kind == "human_confirmation" and not self.human_confirmed_by:
            raise ValueError("human_confirmation promotion requires human_confirmed_by")
        if self.promotion_kind == "deterministic_validation" and not self.deterministic_check_id:
            raise ValueError("deterministic_validation promotion requires deterministic_check_id")
        return self


class PromotionError(ValueError):
    """Raised when candidate → authoritative gate rejects the transition."""


def promote_candidate_fact(
    candidate: CandidateFact,
    *,
    authoritative_fact_id: str,
    promoted_at: datetime | None = None,
) -> AuthoritativeScriptFact:
    """Explicit gate: candidate → authoritative.

    Allowed only if:
      A) status == human_confirmed with human_confirmed_by, OR
      B) deterministic_check_id recorded and may_promote_via_deterministic_check()

    Confidence is ignored as a gate. MISSING / CONFLICTING / bare EXTRACTED
    without check id cannot pass.
    """

    when = promoted_at or datetime.now(timezone.utc)

    if candidate.status == CandidateStatus.MISSING:
        raise PromotionError("cannot promote missing candidate to authoritative")
    if candidate.status == CandidateStatus.CONFLICTING:
        raise PromotionError("cannot promote conflicting candidate to authoritative")

    if candidate.may_promote_via_human():
        if not candidate.claim.evidence_spans:
            raise PromotionError("human_confirmed promotion requires evidence_spans on the claim")
        return AuthoritativeScriptFact(
            authoritative_fact_id=authoritative_fact_id,
            source_candidate_fact_id=candidate.fact_id,
            entity_kind=candidate.entity_kind,
            entity_id=candidate.entity_id,
            field_path=candidate.field_path,
            text=candidate.claim.text,
            evidence_spans=list(candidate.claim.evidence_spans),
            project_id=candidate.project_id,
            source_revision_id=candidate.source_revision_id,
            source_revision_digest=candidate.source_revision_digest,
            promotion_kind="human_confirmation",
            human_confirmed_by=candidate.human_confirmed_by,
            deterministic_check_id=None,
            promoted_at=when,
            source_confidence=candidate.claim.confidence,
        )

    if candidate.may_promote_via_deterministic_check():
        if not candidate.claim.evidence_spans:
            raise PromotionError("deterministic promotion requires evidence_spans")
        return AuthoritativeScriptFact(
            authoritative_fact_id=authoritative_fact_id,
            source_candidate_fact_id=candidate.fact_id,
            entity_kind=candidate.entity_kind,
            entity_id=candidate.entity_id,
            field_path=candidate.field_path,
            text=candidate.claim.text,
            evidence_spans=list(candidate.claim.evidence_spans),
            project_id=candidate.project_id,
            source_revision_id=candidate.source_revision_id,
            source_revision_digest=candidate.source_revision_digest,
            promotion_kind="deterministic_validation",
            human_confirmed_by=None,
            deterministic_check_id=candidate.deterministic_check_id,
            promoted_at=when,
            source_confidence=candidate.claim.confidence,
        )

    raise PromotionError(
        "candidate cannot become authoritative: need human_confirmed "
        "(with human_confirmed_by) or a recorded deterministic_check_id; "
        f"status={candidate.status.value}, confidence={candidate.claim.confidence} "
        "(confidence alone is never enough)"
    )


def apply_candidate_transition(
    candidate: CandidateFact,
    to_status: CandidateStatus,
    **updates: Any,
) -> CandidateFact:
    """Apply an allowed candidate-layer status change; forbid illegal jumps."""

    if not can_transition(candidate.status, to_status):
        raise PromotionError(
            f"illegal candidate transition {candidate.status.value} → {to_status.value}"
        )
    data = candidate.model_dump()
    data.update(updates)
    data["status"] = to_status
    return CandidateFact.model_validate(data)


# ---------------------------------------------------------------------------
# Character-scoped helper (entity type = character only today)
# ---------------------------------------------------------------------------


def character_display_name_candidate(
    *,
    fact_id: str,
    character_id: str,
    display_name: str,
    status: CandidateStatus,
    project_id: str,
    source_revision_id: str,
    source_revision_digest: str,
    evidence_spans: list[EvidenceSpan],
    confidence: float,
    producer: Literal["regex_extractor", "deterministic_extractor", "llm", "human", "system"],
    uncertainty_note: str | None = None,
    human_confirmed_by: str | None = None,
    human_confirmed_at: datetime | None = None,
    deterministic_check_id: str | None = None,
    deterministic_check_passed_at: datetime | None = None,
    conflict_with_fact_ids: list[str] | None = None,
    conflict_note: str | None = None,
) -> CandidateFact:
    """Build a CandidateFact for Character identity.display_name."""

    return CandidateFact(
        fact_id=fact_id,
        entity_kind="character",
        entity_id=character_id,
        field_path="identity.display_name",
        claim=ClaimedText(
            text=display_name,
            confidence=confidence,
            evidence_spans=evidence_spans,
            uncertainty_note=uncertainty_note,
        ),
        status=status,
        project_id=project_id,
        source_revision_id=source_revision_id,
        source_revision_digest=source_revision_digest,
        producer=producer,
        produced_at=datetime.now(timezone.utc),
        human_confirmed_by=human_confirmed_by,
        human_confirmed_at=human_confirmed_at,
        deterministic_check_id=deterministic_check_id,
        deterministic_check_passed_at=deterministic_check_passed_at,
        conflict_with_fact_ids=list(conflict_with_fact_ids or []),
        conflict_note=conflict_note,
    )


# ---------------------------------------------------------------------------
# Concrete examples — prove the gate blocks yesterday's junk PASS
# ---------------------------------------------------------------------------


def example_suqingmei_junk_stays_candidate() -> dict[str, Any]:
    """《海边的信》 regex junk: "苏晴没" must NOT auto-become authoritative.

    Even with high confidence (simulating today's 'extracted something → PASS'),
    promote_candidate_fact must raise.
    """

    digest = "0" * 64
    junk = character_display_name_candidate(
        fact_id="fact_char_suqingmei_extract_1",
        character_id="char_unknown_1",
        display_name="苏晴没",
        status=CandidateStatus.EXTRACTED_FROM_TEXT,
        project_id="proj_last_light_20260801",
        source_revision_id="scrrev_9f3d686832b74175",
        source_revision_digest=digest,
        evidence_spans=[
            EvidenceSpan(start=120, end=125, quote="苏晴没说话"),
        ],
        confidence=0.96,  # deliberately high — still not enough
        producer="regex_extractor",
        uncertainty_note="regex took chars before verb 说; likely fragment not a name",
    )

    assert junk.is_authoritative() is False
    assert status_may_enter_production_graph(junk.status) is False
    assert confidence_alone_may_authorize(junk.claim.confidence) is False

    promoted = None
    error: str | None = None
    try:
        promoted = promote_candidate_fact(junk, authoritative_fact_id="auth_should_not_exist")
    except PromotionError as exc:
        error = str(exc)

    return {
        "case": "suqingmei_junk_regex_extract",
        "candidate_text": junk.claim.text,
        "status": junk.status.value,
        "confidence": junk.claim.confidence,
        "is_authoritative": junk.is_authoritative(),
        "promotion_succeeded": promoted is not None,
        "promotion_error": error,
        "why_blocked": (
            "Status is extracted_from_text with no human_confirmed_by and no "
            "deterministic_check_id. Confidence 0.96 is ignored as a gate. "
            "Therefore Production Graph must not receive 苏晴没."
        ),
    }


def example_suqing_human_confirmed_promotes() -> dict[str, Any]:
    """Correct name 苏晴 after human confirmation → may mint AuthoritativeScriptFact."""

    digest = "1" * 64
    now = datetime.now(timezone.utc)
    confirmed = character_display_name_candidate(
        fact_id="fact_char_suqing_human_1",
        character_id="char_suqing",
        display_name="苏晴",
        status=CandidateStatus.HUMAN_CONFIRMED,
        project_id="proj_last_light_20260801",
        source_revision_id="scrrev_9f3d686832b74175",
        source_revision_digest=digest,
        evidence_spans=[
            EvidenceSpan(start=40, end=42, quote="苏晴"),
        ],
        confidence=0.55,  # low confidence still OK — human is the gate
        producer="human",
        human_confirmed_by="user_creator_demo",
        human_confirmed_at=now,
    )

    auth = promote_candidate_fact(
        confirmed,
        authoritative_fact_id="auth_char_suqing_display_name_1",
        promoted_at=now,
    )
    return {
        "case": "suqing_human_confirmed",
        "candidate_text": confirmed.claim.text,
        "status": confirmed.status.value,
        "confidence": confirmed.claim.confidence,
        "promotion_succeeded": True,
        "authoritative_fact_id": auth.authoritative_fact_id,
        "promotion_kind": auth.promotion_kind,
        "human_confirmed_by": auth.human_confirmed_by,
        "why_allowed": (
            "Status human_confirmed with human_confirmed_by + evidence_spans. "
            "Confidence 0.55 did not block promotion — human confirmation did. "
            "Only this AuthoritativeScriptFact may later feed Production Graph."
        ),
    }


def example_high_confidence_inferred_still_blocked() -> dict[str, Any]:
    """Model-inferred name with confidence 0.99 and no gate → blocked."""

    digest = "2" * 64
    inferred = character_display_name_candidate(
        fact_id="fact_char_inferred_1",
        character_id="char_unknown_2",
        display_name="道他可能",
        status=CandidateStatus.MODEL_INFERRED,
        project_id="proj_last_light_20260801",
        source_revision_id="scrrev_9f3d686832b74175",
        source_revision_digest=digest,
        evidence_spans=[],
        confidence=0.99,
        producer="llm",
        uncertainty_note="model guessed from surrounding tokens; no clean name span",
    )
    error: str | None = None
    try:
        promote_candidate_fact(inferred, authoritative_fact_id="auth_nope")
    except PromotionError as exc:
        error = str(exc)
    return {
        "case": "daotakeneng_model_inferred_high_confidence",
        "candidate_text": inferred.claim.text,
        "status": inferred.status.value,
        "confidence": inferred.claim.confidence,
        "promotion_succeeded": False,
        "promotion_error": error,
    }


def run_examples() -> list[dict[str, Any]]:
    return [
        example_suqingmei_junk_stays_candidate(),
        example_suqing_human_confirmed_promotes(),
        example_high_confidence_inferred_still_blocked(),
    ]


# Rebuild forward refs
EvidenceSpan.model_rebuild()
ClaimedText.model_rebuild()
CandidateFact.model_rebuild()
AuthoritativeScriptFact.model_rebuild()


__all__ = (
    "SCHEMA_VERSION",
    "EvidenceSpan",
    "ClaimedText",
    "CandidateStatus",
    "NON_AUTHORITATIVE_STATUSES",
    "ALLOWED_CANDIDATE_TRANSITIONS",
    "can_transition",
    "confidence_alone_may_authorize",
    "status_may_enter_production_graph",
    "CandidateFact",
    "AuthoritativeScriptFact",
    "PromotionError",
    "promote_candidate_fact",
    "apply_candidate_transition",
    "character_display_name_candidate",
    "example_suqingmei_junk_stays_candidate",
    "example_suqing_human_confirmed_promotes",
    "example_high_confidence_inferred_still_blocked",
    "run_examples",
)


if __name__ == "__main__":
    import json

    print(json.dumps(run_examples(), ensure_ascii=False, indent=2, default=str))
