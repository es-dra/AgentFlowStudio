"""DRAFT ONLY — not wired into Runtime / apps/api / M6.

Candidate confirmation closed loop (2026-08-02)

Wires three existing drafts into the boss "minimum closed loop":

  extract → candidate review DTO → human correct/confirm → authoritative
                                                          → revision invalidation

Reuses (does not rewrite):
  draft_improved_extraction_20260802.py          ExtractedItem / extract_*
  draft_candidate_fact_status_model_20260802.py  CandidateFact / promote_*
  draft_script_understanding_character_schema_20260801.py  ChangeRecord

Studio gets a presentation contract only (no React). Downstream "M6-like"
reads must go through list_current_authoritative() / resolve_for_downstream().
"""

from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from draft_candidate_fact_status_model_20260802 import (  # noqa: E402
    AuthoritativeScriptFact,
    CandidateFact,
    CandidateStatus,
    ClaimedText,
    EvidenceSpan,
    PromotionError,
    apply_candidate_transition,
    promote_candidate_fact,
)
from draft_improved_extraction_20260802 import (  # noqa: E402
    ExtractStatus,
    ExtractedItem,
    ExtractionResult,
    extract_characters_and_scenes,
)
from draft_script_understanding_character_schema_20260801 import (  # noqa: E402
    ChangeRecord,
)


SCHEMA_VERSION = "afs.script_understanding.confirmation_loop.v0.1.draft"


# ---------------------------------------------------------------------------
# 1) Studio presentation contract (data only — no frontend)
# ---------------------------------------------------------------------------


class ReviewAction(str, Enum):
    ACCEPT = "accept"  # confirm as-is → human_confirmed → promote
    EDIT_CONFIRM = "edit_confirm"  # replace text, then confirm → promote
    REJECT = "reject"  # mark wrong; never promote


class CandidateReviewItem(BaseModel):
    """One row the Studio review UI would render."""

    model_config = ConfigDict(extra="forbid")

    fact_id: str
    entity_kind: Literal["character", "scene"]
    entity_id: str
    field_path: str
    text: str
    status: CandidateStatus
    confidence: float
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)
    uncertainty_note: str | None = None
    producer_method: str = ""
    source_revision_id: str
    source_revision_digest: str
    allowed_actions: list[ReviewAction] = Field(
        default_factory=lambda: [
            ReviewAction.ACCEPT,
            ReviewAction.EDIT_CONFIRM,
            ReviewAction.REJECT,
        ]
    )
    # missing rows are shown but cannot be "accepted" as a real name/place
    is_missing_slot: bool = False


class MissingSlotItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot_id: str
    entity_kind: Literal["character", "scene"]
    field_path: str
    message: str
    status: Literal["missing"] = "missing"


class CandidateReviewBundle(BaseModel):
    """Payload shape for Studio: show candidates + missing slots for one revision."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    project_id: str
    source_revision_id: str
    source_revision_digest: str
    title_hint: str | None = None
    items: list[CandidateReviewItem] = Field(default_factory=list)
    missing_slots: list[MissingSlotItem] = Field(default_factory=list)
    extraction_notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Authoritative ledger + validity (version invalidation)
# ---------------------------------------------------------------------------


class AuthorityValidity(str, Enum):
    """Lifecycle of an AuthoritativeScriptFact on the ledger.

    active                 — may be read as current authority for its revision
    superseded             — replaced by a newer human edit on the same revision
    invalidated_by_revision — script moved to a new revision; keep for audit only
    """

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    INVALIDATED_BY_REVISION = "invalidated_by_revision"


class AuthoritativeFactRecord(BaseModel):
    """Ledger row: authoritative fact + validity (never hard-deleted)."""

    model_config = ConfigDict(extra="forbid")

    record_id: str
    fact: AuthoritativeScriptFact
    validity: AuthorityValidity = AuthorityValidity.ACTIVE
    invalidated_at: datetime | None = None
    invalidated_by_revision_id: str | None = None
    supersedes_record_id: str | None = None
    superseded_by_record_id: str | None = None


class ReviewDecision(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EDITED_AND_CONFIRMED = "edited_and_confirmed"
    REJECTED = "rejected"


class FactLedger(BaseModel):
    """In-memory closed-loop store (draft stand-in for future Runtime tables)."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    current_revision_id: str
    current_revision_digest: str
    candidates: dict[str, CandidateFact] = Field(default_factory=dict)
    review_decisions: dict[str, ReviewDecision] = Field(default_factory=dict)
    authoritative_records: list[AuthoritativeFactRecord] = Field(default_factory=list)
    change_log: list[ChangeRecord] = Field(default_factory=list)

    def append_change(self, record: ChangeRecord) -> None:
        self.change_log.append(record)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def revision_digest(source_text: str) -> str:
    return hashlib.sha256(source_text.encode("utf-8")).hexdigest()


def _evidence_for(source_text: str, quote: str) -> list[EvidenceSpan]:
    q = (quote or "").strip()
    if not q:
        return []
    idx = source_text.find(q)
    if idx < 0:
        # Still attach the quote so human_confirmed promotion has evidence.
        return [EvidenceSpan(start=0, end=max(len(q), 1), quote=q[:1200])]
    return [EvidenceSpan(start=idx, end=idx + len(q), quote=q[:1200])]


def _status_from_extract(status: ExtractStatus) -> CandidateStatus:
    return {
        ExtractStatus.EXTRACTED_FROM_TEXT: CandidateStatus.EXTRACTED_FROM_TEXT,
        ExtractStatus.MODEL_INFERRED: CandidateStatus.MODEL_INFERRED,
        ExtractStatus.MISSING: CandidateStatus.MISSING,
    }[status]


# ---------------------------------------------------------------------------
# ExtractedItem → CandidateFact → Review bundle
# ---------------------------------------------------------------------------


def extracted_item_to_candidate_fact(
    item: ExtractedItem,
    *,
    entity_kind: Literal["character", "scene"],
    project_id: str,
    source_revision_id: str,
    source_revision_digest: str,
    source_text: str,
    index: int,
) -> CandidateFact:
    entity_id = f"{entity_kind}_{index}_{item.text or 'unknown'}"[:120]
    field_path = (
        "identity.display_name" if entity_kind == "character" else "scene.name"
    )
    spans = _evidence_for(source_text, item.evidence or item.text)
    status = _status_from_extract(item.status)
    uncertainty = None
    claim_text = item.text
    if status == CandidateStatus.MISSING:
        claim_text = item.text or "(missing)"
        uncertainty = "extractor found no credible value for this slot"
        spans = []
    elif status == CandidateStatus.MODEL_INFERRED and not spans:
        uncertainty = f"weak heuristic ({item.method}); needs human check"

    if status in {
        CandidateStatus.EXTRACTED_FROM_TEXT,
        CandidateStatus.HUMAN_CONFIRMED,
    } and not spans:
        # Structured extract without locateable quote — use text itself as span.
        spans = _evidence_for(item.text, item.text)

    return CandidateFact(
        fact_id=_id("fact"),
        entity_kind=entity_kind,
        entity_id=entity_id,
        field_path=field_path,
        claim=ClaimedText(
            text=claim_text,
            confidence=item.confidence,
            evidence_spans=spans,
            uncertainty_note=uncertainty,
        ),
        status=status,
        project_id=project_id,
        source_revision_id=source_revision_id,
        source_revision_digest=source_revision_digest,
        producer="deterministic_extractor",
        produced_at=_now(),
    )


def build_review_bundle_from_extraction(
    extraction: ExtractionResult,
    *,
    source_text: str,
    project_id: str,
    source_revision_id: str,
    source_revision_digest: str | None = None,
    title_hint: str | None = None,
) -> tuple[CandidateReviewBundle, list[CandidateFact]]:
    """Convert extraction → Studio DTO + CandidateFact list (display step)."""

    digest = source_revision_digest or revision_digest(source_text)
    facts: list[CandidateFact] = []
    items: list[CandidateReviewItem] = []
    missing: list[MissingSlotItem] = []

    for i, ch in enumerate(extraction.characters):
        fact = extracted_item_to_candidate_fact(
            ch,
            entity_kind="character",
            project_id=project_id,
            source_revision_id=source_revision_id,
            source_revision_digest=digest,
            source_text=source_text,
            index=i,
        )
        facts.append(fact)
        items.append(_fact_to_review_item(fact, producer_method=ch.method))

    for i, sc in enumerate(extraction.scenes):
        fact = extracted_item_to_candidate_fact(
            sc,
            entity_kind="scene",
            project_id=project_id,
            source_revision_id=source_revision_id,
            source_revision_digest=digest,
            source_text=source_text,
            index=i,
        )
        facts.append(fact)
        items.append(_fact_to_review_item(fact, producer_method=sc.method))

    if extraction.character_name_status == ExtractStatus.MISSING:
        missing.append(
            MissingSlotItem(
                slot_id=_id("miss_char"),
                entity_kind="character",
                field_path="identity.display_name",
                message="No credible character proper name; do not invent one.",
            )
        )
    if extraction.scene_status == ExtractStatus.MISSING:
        missing.append(
            MissingSlotItem(
                slot_id=_id("miss_scene"),
                entity_kind="scene",
                field_path="scene.name",
                message="No credible scene location; do not invent one.",
            )
        )

    bundle = CandidateReviewBundle(
        project_id=project_id,
        source_revision_id=source_revision_id,
        source_revision_digest=digest,
        title_hint=title_hint,
        items=items,
        missing_slots=missing,
        extraction_notes=list(extraction.notes),
    )
    return bundle, facts


def _fact_to_review_item(fact: CandidateFact, *, producer_method: str = "") -> CandidateReviewItem:
    is_missing = fact.status == CandidateStatus.MISSING
    actions = (
        [ReviewAction.EDIT_CONFIRM, ReviewAction.REJECT]
        if is_missing
        else [ReviewAction.ACCEPT, ReviewAction.EDIT_CONFIRM, ReviewAction.REJECT]
    )
    return CandidateReviewItem(
        fact_id=fact.fact_id,
        entity_kind=fact.entity_kind,
        entity_id=fact.entity_id,
        field_path=fact.field_path,
        text=fact.claim.text,
        status=fact.status,
        confidence=fact.claim.confidence,
        evidence_spans=list(fact.claim.evidence_spans),
        uncertainty_note=fact.claim.uncertainty_note,
        producer_method=producer_method,
        source_revision_id=fact.source_revision_id,
        source_revision_digest=fact.source_revision_digest,
        allowed_actions=actions,
        is_missing_slot=is_missing,
    )


def open_ledger_from_extraction(
    source_text: str,
    *,
    project_id: str,
    source_revision_id: str,
    title_hint: str | None = None,
) -> tuple[FactLedger, CandidateReviewBundle]:
    extraction = extract_characters_and_scenes(source_text)
    digest = revision_digest(source_text)
    bundle, facts = build_review_bundle_from_extraction(
        extraction,
        source_text=source_text,
        project_id=project_id,
        source_revision_id=source_revision_id,
        source_revision_digest=digest,
        title_hint=title_hint,
    )
    ledger = FactLedger(
        project_id=project_id,
        current_revision_id=source_revision_id,
        current_revision_digest=digest,
        candidates={f.fact_id: f for f in facts},
        review_decisions={f.fact_id: ReviewDecision.PENDING for f in facts},
    )
    ledger.append_change(
        ChangeRecord(
            change_id=_id("chg"),
            at=_now(),
            actor_kind="extractor",
            actor_id="deterministic_extractor_v0",
            from_version_id=None,
            to_version_id=f"extract:{source_revision_id}",
            summary=f"extraction produced {len(facts)} candidate fact(s)",
            field_paths=[f.field_path for f in facts],
            reason="initial_extract",
        )
    )
    return ledger, bundle


# ---------------------------------------------------------------------------
# 2–3) Human correct / confirm → promote
# ---------------------------------------------------------------------------


class LoopError(ValueError):
    pass


def _require_pending(ledger: FactLedger, fact_id: str) -> CandidateFact:
    if fact_id not in ledger.candidates:
        raise LoopError(f"unknown fact_id: {fact_id}")
    if ledger.review_decisions.get(fact_id) not in {
        ReviewDecision.PENDING,
        None,
    }:
        # allow only pending; rejected/accepted are terminal for that fact_id
        decision = ledger.review_decisions.get(fact_id)
        if decision != ReviewDecision.PENDING:
            raise LoopError(f"fact {fact_id} already decided: {decision}")
    return ledger.candidates[fact_id]


def accept_candidate(
    ledger: FactLedger,
    fact_id: str,
    *,
    human_id: str,
    reason: str | None = None,
) -> AuthoritativeFactRecord:
    """Accept candidate as-is → human_confirmed → AuthoritativeScriptFact."""

    cand = _require_pending(ledger, fact_id)
    if cand.status == CandidateStatus.MISSING:
        raise LoopError("cannot accept a missing slot; use edit_confirm to supply a value")

    when = _now()
    confirmed = apply_candidate_transition(
        cand,
        CandidateStatus.HUMAN_CONFIRMED,
        human_confirmed_by=human_id,
        human_confirmed_at=when,
        producer="human",
    )
    ledger.candidates[fact_id] = confirmed
    auth = promote_candidate_fact(
        confirmed,
        authoritative_fact_id=_id("auth"),
        promoted_at=when,
    )
    record = AuthoritativeFactRecord(record_id=_id("arec"), fact=auth)
    ledger.authoritative_records.append(record)
    ledger.review_decisions[fact_id] = ReviewDecision.ACCEPTED
    ledger.append_change(
        ChangeRecord(
            change_id=_id("chg"),
            at=when,
            actor_kind="human",
            actor_id=human_id,
            from_version_id=fact_id,
            to_version_id=auth.authoritative_fact_id,
            summary=f"accepted candidate {fact_id!r} → authoritative {auth.text!r}",
            field_paths=[cand.field_path],
            reason=reason or "human_accept",
        )
    )
    return record


def edit_and_confirm_candidate(
    ledger: FactLedger,
    fact_id: str,
    *,
    new_text: str,
    human_id: str,
    reason: str,
    source_text: str | None = None,
) -> AuthoritativeFactRecord:
    """Human corrects value then confirms → promote; supersede prior active auth."""

    cand = _require_pending(ledger, fact_id)
    new_text = new_text.strip()
    if not new_text:
        raise LoopError("new_text must be non-empty")

    when = _now()
    spans = list(cand.claim.evidence_spans)
    if source_text:
        found = _evidence_for(source_text, new_text)
        if found:
            spans = found
    if not spans:
        spans = [EvidenceSpan(start=0, end=len(new_text), quote=new_text[:1200])]

    # Corrections create an updated candidate (same fact_id for review continuity)
    # then mark human_confirmed — gate for promote_candidate_fact.
    updated = cand.model_copy(
        deep=True,
        update={
            "claim": ClaimedText(
                text=new_text,
                confidence=1.0,
                evidence_spans=spans,
                uncertainty_note=None,
            ),
            "status": CandidateStatus.HUMAN_CONFIRMED,
            "human_confirmed_by": human_id,
            "human_confirmed_at": when,
            "producer": "human",
        },
    )
    # Validate via model
    updated = CandidateFact.model_validate(updated.model_dump())
    ledger.candidates[fact_id] = updated

    auth = promote_candidate_fact(
        updated,
        authoritative_fact_id=_id("auth"),
        promoted_at=when,
    )

    # Supersede any active authoritative fact for same entity+field on this revision
    prior_id: str | None = None
    for rec in ledger.authoritative_records:
        if (
            rec.validity == AuthorityValidity.ACTIVE
            and rec.fact.entity_id == updated.entity_id
            and rec.fact.field_path == updated.field_path
            and rec.fact.source_revision_id == ledger.current_revision_id
        ):
            rec.validity = AuthorityValidity.SUPERSEDED
            rec.invalidated_at = when
            prior_id = rec.record_id

    record = AuthoritativeFactRecord(
        record_id=_id("arec"),
        fact=auth,
        supersedes_record_id=prior_id,
    )
    if prior_id:
        for rec in ledger.authoritative_records:
            if rec.record_id == prior_id:
                rec.superseded_by_record_id = record.record_id
    ledger.authoritative_records.append(record)
    ledger.review_decisions[fact_id] = ReviewDecision.EDITED_AND_CONFIRMED
    ledger.append_change(
        ChangeRecord(
            change_id=_id("chg"),
            at=when,
            actor_kind="human",
            actor_id=human_id,
            from_version_id=fact_id,
            to_version_id=auth.authoritative_fact_id,
            summary=(
                f"edited candidate {fact_id}: {cand.claim.text!r} → {new_text!r} "
                f"and confirmed"
            ),
            field_paths=[updated.field_path],
            reason=reason,
        )
    )
    return record


def reject_candidate(
    ledger: FactLedger,
    fact_id: str,
    *,
    human_id: str,
    reason: str,
) -> None:
    """Mark candidate rejected — remains on ledger for audit; never promote."""

    cand = _require_pending(ledger, fact_id)
    when = _now()
    ledger.review_decisions[fact_id] = ReviewDecision.REJECTED
    # Keep candidate text; do not mint authoritative. Optional: note via change log.
    ledger.append_change(
        ChangeRecord(
            change_id=_id("chg"),
            at=when,
            actor_kind="human",
            actor_id=human_id,
            from_version_id=fact_id,
            to_version_id=f"rejected:{fact_id}",
            summary=f"rejected candidate {fact_id!r} text={cand.claim.text!r}",
            field_paths=[cand.field_path],
            reason=reason,
        )
    )


# ---------------------------------------------------------------------------
# 4) Version invalidation + current-authority query
# ---------------------------------------------------------------------------


def on_script_revision_changed(
    ledger: FactLedger,
    *,
    new_revision_id: str,
    new_source_text: str,
    actor_id: str = "system",
) -> list[str]:
    """Bind ledger to a new script revision; invalidate prior authoritative facts.

    Rules:
    - Do NOT delete old AuthoritativeScriptFact rows (audit retained).
    - Mark every ACTIVE/SUPERSEDED record whose source_revision_id != new as
      INVALIDATED_BY_REVISION (superseded stays superseded but also not current).
    - Clear candidate set for the old revision (new extract opens a new review).
    - list_current_authoritative() will only return ACTIVE rows for the new revision.
    """

    when = _now()
    new_digest = revision_digest(new_source_text)
    invalidated: list[str] = []
    for rec in ledger.authoritative_records:
        if rec.fact.source_revision_id == new_revision_id:
            continue
        if rec.validity == AuthorityValidity.INVALIDATED_BY_REVISION:
            continue
        # Active and superseded both become non-current for the new revision.
        if rec.validity in {AuthorityValidity.ACTIVE, AuthorityValidity.SUPERSEDED}:
            rec.validity = AuthorityValidity.INVALIDATED_BY_REVISION
            rec.invalidated_at = when
            rec.invalidated_by_revision_id = new_revision_id
            invalidated.append(rec.record_id)

    old_rev = ledger.current_revision_id
    ledger.current_revision_id = new_revision_id
    ledger.current_revision_digest = new_digest
    ledger.candidates.clear()
    ledger.review_decisions.clear()

    ledger.append_change(
        ChangeRecord(
            change_id=_id("chg"),
            at=when,
            actor_kind="system",
            actor_id=actor_id,
            from_version_id=old_rev,
            to_version_id=new_revision_id,
            summary=(
                f"script revision changed {old_rev} → {new_revision_id}; "
                f"invalidated {len(invalidated)} authoritative record(s)"
            ),
            field_paths=[],
            reason="script_revision_changed",
        )
    )
    return invalidated


def list_current_authoritative(
    ledger: FactLedger,
    *,
    revision_id: str | None = None,
) -> list[AuthoritativeScriptFact]:
    """Query used by downstream (M6-like): only ACTIVE facts for the given revision."""

    rev = revision_id or ledger.current_revision_id
    out: list[AuthoritativeScriptFact] = []
    for rec in ledger.authoritative_records:
        if rec.validity != AuthorityValidity.ACTIVE:
            continue
        if rec.fact.source_revision_id != rev:
            continue
        if rec.fact.project_id != ledger.project_id:
            continue
        out.append(rec.fact)
    return out


def resolve_for_downstream(
    ledger: FactLedger,
    *,
    fresh_extraction: ExtractionResult | None = None,
    revision_id: str | None = None,
) -> dict[str, Any]:
    """What a later M6/extract consumer should see.

    Authoritative ACTIVE facts for the revision win over raw extraction.
    Rejected / invalidated / superseded never appear as current authority.
    """

    rev = revision_id or ledger.current_revision_id
    auth = list_current_authoritative(ledger, revision_id=rev)
    auth_chars = [f.text for f in auth if f.entity_kind == "character"]
    auth_scenes = [f.text for f in auth if f.entity_kind == "scene"]

    raw_chars = list(fresh_extraction.character_texts()) if fresh_extraction else []
    raw_scenes = list(fresh_extraction.scene_texts()) if fresh_extraction else []

    return {
        "revision_id": rev,
        "characters": auth_chars or raw_chars,
        "scenes": auth_scenes or raw_scenes,
        "authority_source": "authoritative_ledger" if auth else "raw_extraction_only",
        "authoritative_fact_ids": [f.authoritative_fact_id for f in auth],
        "raw_extraction_characters": raw_chars,
        "raw_extraction_scenes": raw_scenes,
    }


# ---------------------------------------------------------------------------
# Junk candidate helper (reuse status-model scenario A path)
# ---------------------------------------------------------------------------


def inject_raw_junk_candidate(
    ledger: FactLedger,
    *,
    junk_text: str,
    evidence_quote: str,
    confidence: float = 0.96,
) -> CandidateFact:
    """Simulate legacy regex junk landing as a candidate (for scenario A)."""

    spans = [
        EvidenceSpan(start=0, end=max(len(evidence_quote), 1), quote=evidence_quote[:1200])
    ]
    fact = CandidateFact(
        fact_id=_id("fact"),
        entity_kind="character",
        entity_id="char_junk",
        field_path="identity.display_name",
        claim=ClaimedText(
            text=junk_text,
            confidence=confidence,
            evidence_spans=spans,
            uncertainty_note="legacy regex fragment; not a real name",
        ),
        status=CandidateStatus.EXTRACTED_FROM_TEXT,
        project_id=ledger.project_id,
        source_revision_id=ledger.current_revision_id,
        source_revision_digest=ledger.current_revision_digest,
        producer="regex_extractor",
        produced_at=_now(),
    )
    ledger.candidates[fact.fact_id] = fact
    ledger.review_decisions[fact.fact_id] = ReviewDecision.PENDING
    return fact


__all__ = (
    "SCHEMA_VERSION",
    "ReviewAction",
    "CandidateReviewItem",
    "MissingSlotItem",
    "CandidateReviewBundle",
    "AuthorityValidity",
    "AuthoritativeFactRecord",
    "ReviewDecision",
    "FactLedger",
    "LoopError",
    "revision_digest",
    "extracted_item_to_candidate_fact",
    "build_review_bundle_from_extraction",
    "open_ledger_from_extraction",
    "accept_candidate",
    "edit_and_confirm_candidate",
    "reject_candidate",
    "on_script_revision_changed",
    "list_current_authoritative",
    "resolve_for_downstream",
    "inject_raw_junk_candidate",
)
