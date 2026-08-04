"""Candidate confirmation loop — persisted ledger + feature-flagged API.

Promoted from docs/internal-notes/draft_candidate_confirmation_loop_20260802.py.

Gate: AFS_USE_CANDIDATE_CONFIRMATION_LOOP (default off).
Refresh from improved extraction also requires AFS_USE_IMPROVED_EXTRACTION.

Does NOT change M6 candidate generation. Production Graph writes are optional
via AFS_CANDIDATE_FACTS_FEED_PRODUCTION_GRAPH (default off) — only newly
promoted AuthoritativeScriptFact rows are fed; never candidates/missing.
Storage: projects/{id}/candidate_facts/ledger.json (+ .lock).
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Mapping
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from agentflow.harness.json_io import exclusive_file_lock, write_json
from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_authoritative_facts_graph import (
    candidate_facts_feed_production_graph_enabled,
    feed_authoritative_facts_to_production_graph,
)
from apps.api.runtime_candidate_fact_status import (
    AuthoritativeScriptFact,
    CandidateFact,
    CandidateStatus,
    ClaimedText,
    EvidenceSpan,
    apply_candidate_transition,
    promote_candidate_fact,
)
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_m6_script_plan_asset_bible import improved_extraction_enabled
from apps.api.runtime_production_graph import ProductionGraphError, ProductionGraphStore
from apps.api.runtime_script_core_truth import current_script_revision_binding
from apps.api.runtime_script_improved_extraction import (
    ExtractStatus,
    ExtractedBeatBoundary,
    ExtractedBeatFacet,
    ExtractedCharacterAppearance,
    ExtractedItem,
    ExtractionResult,
    ScriptFormatProfileExtraction,
    ScriptProfileFacetExtraction,
    extract_character_appearances_in_range,
    extract_characters_and_scenes,
    extract_explicit_beat_boundaries,
    extract_explicit_beat_facets,
    extract_scene_occurrences,
    extract_script_format_profile,
    extract_script_profile_facets,
)
from apps.api.runtime_asset_requirements import (
    asset_requirements_payload,
    project_scene_character_asset_requirements,
)
from apps.api.runtime_entity_asset_bindings import (
    bind_authoritative_fact_to_core_asset,
    load_bindings,
    lookup_asset_id_for_entity,
    lookup_entity_for_asset_id,
    mark_bindings_stale_for_revision_change,
)
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id


CONFIRMATION_LOOP_ENV = "AFS_USE_CANDIDATE_CONFIRMATION_LOOP"
RECOVERABLE_GRAPH_FEED_ENV = "AFS_CANDIDATE_FACTS_RECOVERABLE_GRAPH_FEED"
CONFIRMATION_LOOP_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
LEDGER_SCHEMA_VERSION = "afs.candidate_fact_ledger.v0.3"
LOOP_SCHEMA_VERSION = "afs.script_understanding.confirmation_loop.v0.1"
ARTIFACT_TYPE = "afs_candidate_fact_ledger"


# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------


def confirmation_loop_enabled(env: Mapping[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return str(values.get(CONFIRMATION_LOOP_ENV, "")).strip().lower() in CONFIRMATION_LOOP_TRUE_VALUES


def recoverable_graph_feed_enabled(env: Mapping[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return str(values.get(RECOVERABLE_GRAPH_FEED_ENV, "")).strip().lower() in CONFIRMATION_LOOP_TRUE_VALUES


def confirmation_refresh_ready(env: Mapping[str, str] | None = None) -> bool:
    """Refresh needs both gates: confirmation API + improved extractor."""

    return confirmation_loop_enabled(env) and improved_extraction_enabled(env)


# ---------------------------------------------------------------------------
# Shared history + review DTOs
# ---------------------------------------------------------------------------


class ChangeRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    change_id: str = Field(min_length=1, max_length=120)
    at: datetime
    actor_kind: Literal["extractor", "human", "agent", "system"] = "system"
    actor_id: str | None = Field(default=None, max_length=160)
    from_version_id: str | None = Field(default=None, max_length=120)
    to_version_id: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1, max_length=800)
    field_paths: list[str] = Field(default_factory=list, max_length=64)
    reason: str | None = Field(default=None, max_length=400)


class ReviewAction(str, Enum):
    ACCEPT = "accept"
    EDIT_CONFIRM = "edit_confirm"
    REJECT = "reject"


class CandidateReviewItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: str
    entity_kind: Literal[
        "character", "scene", "script_profile", "script_format_profile", "beat"
    ]
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
    review_decision: str = "pending"
    allowed_actions: list[ReviewAction] = Field(
        default_factory=lambda: [
            ReviewAction.ACCEPT,
            ReviewAction.EDIT_CONFIRM,
            ReviewAction.REJECT,
        ]
    )
    is_missing_slot: bool = False


class MissingSlotItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot_id: str
    entity_kind: Literal[
        "character", "scene", "script_profile", "script_format_profile", "beat"
    ]
    field_path: str
    message: str
    status: Literal["missing"] = "missing"


class CandidateReviewBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = LOOP_SCHEMA_VERSION
    project_id: str
    source_revision_id: str
    source_revision_digest: str
    title_hint: str | None = None
    items: list[CandidateReviewItem] = Field(default_factory=list)
    missing_slots: list[MissingSlotItem] = Field(default_factory=list)
    extraction_notes: list[str] = Field(default_factory=list)


class AuthorityValidity(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    INVALIDATED_BY_REVISION = "invalidated_by_revision"


class GraphFeedStatus(str, Enum):
    NOT_REQUESTED = "not_requested"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AuthoritativeFactRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    fact: AuthoritativeScriptFact
    validity: AuthorityValidity = AuthorityValidity.ACTIVE
    invalidated_at: datetime | None = None
    invalidated_by_revision_id: str | None = None
    supersedes_record_id: str | None = None
    superseded_by_record_id: str | None = None
    graph_feed_status: GraphFeedStatus = GraphFeedStatus.NOT_REQUESTED
    graph_feed_attempt_count: int = Field(default=0, ge=0)
    graph_feed_last_attempt_at: datetime | None = None
    graph_feed_succeeded_at: datetime | None = None
    graph_feed_last_error: str | None = Field(default=None, max_length=400)
    graph_feed_node_ids: list[str] = Field(default_factory=list, max_length=16)
    graph_feed_graph_version: int | None = Field(default=None, ge=0)


class ReviewDecision(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EDITED_AND_CONFIRMED = "edited_and_confirmed"
    REJECTED = "rejected"


class FactLedger(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    current_revision_id: str = ""
    current_revision_digest: str = ""
    candidates: dict[str, CandidateFact] = Field(default_factory=dict)
    review_decisions: dict[str, ReviewDecision] = Field(default_factory=dict)
    missing_slots: list[MissingSlotItem] = Field(default_factory=list)
    extraction_notes: list[str] = Field(default_factory=list)
    title_hint: str | None = Field(default=None, max_length=200)
    authoritative_records: list[AuthoritativeFactRecord] = Field(default_factory=list)
    change_log: list[ChangeRecord] = Field(default_factory=list)

    def append_change(self, record: ChangeRecord) -> None:
        self.change_log.append(record)


class LoopError(ValueError):
    pass


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
        return [EvidenceSpan(start=0, end=max(len(q), 1), quote=q[:1200])]
    return [EvidenceSpan(start=idx, end=idx + len(q), quote=q[:1200])]


def _exact_evidence_for(source_text: str, quote: str) -> list[EvidenceSpan]:
    """Return source-backed evidence only; never synthesize a span."""

    q = (quote or "").strip()
    if not q:
        return []
    idx = source_text.find(q)
    if idx < 0:
        return []
    return [EvidenceSpan(start=idx, end=idx + len(q), quote=q[:1200])]


def _status_from_extract(status: ExtractStatus) -> CandidateStatus:
    return {
        ExtractStatus.EXTRACTED_FROM_TEXT: CandidateStatus.EXTRACTED_FROM_TEXT,
        ExtractStatus.MODEL_INFERRED: CandidateStatus.MODEL_INFERRED,
        ExtractStatus.MISSING: CandidateStatus.MISSING,
    }[status]


# ---------------------------------------------------------------------------
# Extract → candidates
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
    field_path = "identity.display_name" if entity_kind == "character" else "scene.name"
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
    if status in {CandidateStatus.EXTRACTED_FROM_TEXT, CandidateStatus.HUMAN_CONFIRMED} and not spans:
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


def script_profile_facet_to_candidate_fact(
    facet: ScriptProfileFacetExtraction,
    *,
    entity_id: str,
    project_id: str,
    source_revision_id: str,
    source_revision_digest: str,
    source_text: str,
) -> CandidateFact:
    item = facet.item
    status = _status_from_extract(item.status)
    spans = _evidence_for(source_text, item.evidence or item.text)
    if status == CandidateStatus.MISSING:
        spans = []
    return CandidateFact(
        fact_id=_id("fact"),
        entity_kind="script_profile",
        entity_id=entity_id,
        field_path=facet.field_path,
        claim=ClaimedText(
            text=item.text,
            confidence=item.confidence,
            evidence_spans=spans,
            uncertainty_note=facet.uncertainty_note,
        ),
        status=status,
        project_id=project_id,
        source_revision_id=source_revision_id,
        source_revision_digest=source_revision_digest,
        producer="deterministic_extractor",
        produced_at=_now(),
    )


def _source_anchor_evidence(source_text: str) -> list[EvidenceSpan]:
    """Bind whole-revision projections to a real, reviewable source anchor."""

    start = next(
        (index for index, character in enumerate(source_text) if not character.isspace()),
        None,
    )
    if start is None:
        return []
    line_end = source_text.find("\n", start)
    if line_end < 0:
        line_end = len(source_text)
    end = min(line_end, start + 1200)
    if end <= start:
        end = min(len(source_text), start + 1)
    return [EvidenceSpan(start=start, end=end, quote=source_text[start:end])]


def _script_format_profile_evidence(
    profile: ScriptFormatProfileExtraction,
    *,
    facet: Literal["format_style", "cleaning_notes", "scene_boundary_count"],
    source_text: str,
) -> list[EvidenceSpan]:
    spans: list[EvidenceSpan] = []
    if facet == "cleaning_notes" and profile.cleaning_issues:
        for issue in profile.cleaning_issues[:12]:
            if 0 <= issue.start < issue.end <= len(source_text):
                quote = source_text[issue.start:issue.end]
                if quote:
                    spans.append(
                        EvidenceSpan(start=issue.start, end=issue.end, quote=quote)
                    )
    elif facet in {"format_style", "scene_boundary_count"}:
        search_offsets: dict[str, int] = {}
        for occurrence in profile.scene_occurrences:
            quote = occurrence.evidence.strip()[:1200]
            if not quote:
                continue
            start = source_text.find(quote, search_offsets.get(quote, 0))
            if start < 0:
                continue
            search_offsets[quote] = start + len(quote)
            spans.append(EvidenceSpan(start=start, end=start + len(quote), quote=quote))
            if len(spans) == 12:
                break
    return spans or _source_anchor_evidence(source_text)


def script_format_profile_facet_to_candidate_fact(
    profile: ScriptFormatProfileExtraction,
    *,
    facet: Literal["format_style", "cleaning_notes", "scene_boundary_count"],
    entity_id: str,
    project_id: str,
    source_revision_id: str,
    source_revision_digest: str,
    source_text: str,
) -> CandidateFact:
    values = {
        "format_style": profile.format_style,
        "cleaning_notes": json.dumps(
            list(profile.cleaning_notes), ensure_ascii=False, separators=(",", ":")
        ),
        "scene_boundary_count": str(profile.scene_boundary_count),
    }
    when = _now()
    return CandidateFact(
        fact_id=_id("fact"),
        entity_kind="script_format_profile",
        entity_id=entity_id,
        field_path=f"script_format_profile.{facet}",
        claim=ClaimedText(
            text=values[facet],
            confidence=1.0,
            evidence_spans=_script_format_profile_evidence(
                profile,
                facet=facet,
                source_text=source_text,
            ),
        ),
        status=CandidateStatus.EXTRACTED_FROM_TEXT,
        project_id=project_id,
        source_revision_id=source_revision_id,
        source_revision_digest=source_revision_digest,
        producer="deterministic_extractor",
        produced_at=when,
        deterministic_check_id="script_format_profile_projection_v1",
        deterministic_check_passed_at=when,
    )


def beat_boundary_to_candidate_fact(
    boundary: ExtractedBeatBoundary,
    *,
    scene_entity_id: str,
    project_id: str,
    source_revision_id: str,
    source_revision_digest: str,
) -> CandidateFact:
    revision_key = hashlib.sha256(source_revision_id.encode("utf-8")).hexdigest()[:12]
    raw_entity_id = f"{scene_entity_id}.beat_{boundary.order_index:04d}.{revision_key}"
    if len(raw_entity_id) <= 120:
        entity_id = raw_entity_id
    else:
        identity_key = hashlib.sha256(raw_entity_id.encode("utf-8")).hexdigest()[:24]
        entity_id = f"beat_{identity_key}_{boundary.order_index:04d}.{revision_key}"
    field_path = (
        f"scene[{scene_entity_id}].beats[{boundary.order_index}].boundary"
    )
    claim_text = boundary.label or boundary.marker
    return CandidateFact(
        fact_id=_id("fact"),
        entity_kind="beat",
        entity_id=entity_id,
        field_path=field_path,
        claim=ClaimedText(
            text=claim_text,
            confidence=0.95,
            evidence_spans=[
                EvidenceSpan(
                    start=boundary.evidence_start,
                    end=boundary.evidence_end,
                    quote=boundary.marker,
                )
            ],
        ),
        status=CandidateStatus.EXTRACTED_FROM_TEXT,
        project_id=project_id,
        source_revision_id=source_revision_id,
        source_revision_digest=source_revision_digest,
        producer="deterministic_extractor",
        produced_at=_now(),
    )


def beat_facet_to_candidate_fact(
    facet: ExtractedBeatFacet,
    *,
    scene_entity_id: str,
    beat_order_index: int,
    beat_entity_id: str,
    project_id: str,
    source_revision_id: str,
    source_revision_digest: str,
    source_text: str,
) -> CandidateFact:
    field_path = (
        f"scene[{scene_entity_id}].beats[{beat_order_index}].{facet.field_suffix}"
    )
    status = _status_from_extract(facet.item.status)
    spans: list[EvidenceSpan] = []
    uncertainty = facet.uncertainty_note
    if (
        status != CandidateStatus.MISSING
        and facet.evidence_start is not None
        and facet.evidence_end is not None
        and 0 <= facet.evidence_start < facet.evidence_end <= len(source_text)
    ):
        quote = source_text[facet.evidence_start:facet.evidence_end]
        if quote == facet.item.text:
            spans = [
                EvidenceSpan(
                    start=facet.evidence_start,
                    end=facet.evidence_end,
                    quote=quote[:1200],
                )
            ]
    if status == CandidateStatus.MISSING:
        spans = []
    elif not spans:
        status = CandidateStatus.MISSING
        uncertainty = (
            facet.uncertainty_note
            or "Beat facet label could not be bound to a source evidence span"
        )
    return CandidateFact(
        fact_id=_id("fact"),
        entity_kind="beat",
        entity_id=beat_entity_id,
        field_path=field_path,
        claim=ClaimedText(
            text=facet.item.text if status != CandidateStatus.MISSING else "(missing)",
            confidence=0.0 if status == CandidateStatus.MISSING else facet.item.confidence,
            evidence_spans=spans,
            uncertainty_note=uncertainty if status == CandidateStatus.MISSING else None,
        ),
        status=status,
        project_id=project_id,
        source_revision_id=source_revision_id,
        source_revision_digest=source_revision_digest,
        producer="deterministic_extractor",
        produced_at=_now(),
    )


def character_appearance_to_candidate_fact(
    appearance: ExtractedCharacterAppearance,
    *,
    scene_entity_id: str,
    character_entity_id: str,
    project_id: str,
    source_revision_id: str,
    source_revision_digest: str,
    source_text: str,
) -> CandidateFact:
    field_path = (
        f"scene[{scene_entity_id}].cast[{appearance.order_index}].appearance"
    )
    spans: list[EvidenceSpan] = []
    status = CandidateStatus.EXTRACTED_FROM_TEXT
    uncertainty: str | None = None
    if (
        0 <= appearance.evidence_start < appearance.evidence_end <= len(source_text)
        and source_text[appearance.evidence_start:appearance.evidence_end]
        == appearance.character_name
    ):
        spans = [
            EvidenceSpan(
                start=appearance.evidence_start,
                end=appearance.evidence_end,
                quote=appearance.character_name[:1200],
            )
        ]
    else:
        status = CandidateStatus.MISSING
        uncertainty = (
            "Scene cast appearance could not be bound to a source evidence span"
        )
        spans = []
    return CandidateFact(
        fact_id=_id("fact"),
        entity_kind="character",
        entity_id=character_entity_id,
        field_path=field_path,
        claim=ClaimedText(
            text=appearance.character_name if status != CandidateStatus.MISSING else "(missing)",
            confidence=0.0 if status == CandidateStatus.MISSING else 0.9,
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


def _is_scene_cast_appearance(field_path: str) -> bool:
    return ".cast[" in field_path and field_path.endswith(".appearance")


def _unique_evidence_start(source_text: str, evidence: str) -> int | None:
    quote = evidence.strip()
    if not quote:
        return None
    first = source_text.find(quote)
    if first < 0 or source_text.find(quote, first + 1) >= 0:
        return None
    return first


def build_review_bundle_from_extraction(
    extraction: ExtractionResult,
    *,
    script_profile_facets: list[ScriptProfileFacetExtraction] | None = None,
    script_format_profile: ScriptFormatProfileExtraction | None = None,
    source_text: str,
    project_id: str,
    source_revision_id: str,
    source_revision_digest: str | None = None,
    title_hint: str | None = None,
    review_decisions: Mapping[str, ReviewDecision] | None = None,
) -> tuple[CandidateReviewBundle, list[CandidateFact]]:
    digest = source_revision_digest or revision_digest(source_text)
    decisions = dict(review_decisions or {})
    facts: list[CandidateFact] = []
    items: list[CandidateReviewItem] = []
    missing: list[MissingSlotItem] = []
    scene_rows: list[tuple[ExtractedItem, CandidateFact]] = []

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
        items.append(_fact_to_review_item(fact, producer_method=ch.method, decision=decisions.get(fact.fact_id)))

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
        scene_rows.append((sc, fact))
        items.append(_fact_to_review_item(fact, producer_method=sc.method, decision=decisions.get(fact.fact_id)))

    profile_revision_key = hashlib.sha256(source_revision_id.encode("utf-8")).hexdigest()[:24]
    profile_entity_id = f"script_profile_{profile_revision_key}"
    for facet in script_profile_facets or []:
        fact = script_profile_facet_to_candidate_fact(
            facet,
            entity_id=profile_entity_id,
            project_id=project_id,
            source_revision_id=source_revision_id,
            source_revision_digest=digest,
            source_text=source_text,
        )
        facts.append(fact)
        items.append(
            _fact_to_review_item(
                fact,
                producer_method=facet.item.method,
                decision=decisions.get(fact.fact_id),
            )
        )

    format_profile_entity_id = f"script_format_profile_{profile_revision_key}"
    if script_format_profile is not None:
        for facet, method in (
            ("format_style", "projected_existing_scene_signals"),
            ("cleaning_notes", "conservative_text_cleaning_scan"),
            ("scene_boundary_count", "projected_scene_occurrence_count"),
        ):
            fact = script_format_profile_facet_to_candidate_fact(
                script_format_profile,
                facet=facet,
                entity_id=format_profile_entity_id,
                project_id=project_id,
                source_revision_id=source_revision_id,
                source_revision_digest=digest,
                source_text=source_text,
            )
            facts.append(fact)
            items.append(
                _fact_to_review_item(
                    fact,
                    producer_method=method,
                    decision=decisions.get(fact.fact_id),
                )
            )

    beat_notes: list[str] = []
    positioned_scenes: list[tuple[int, ExtractedItem, CandidateFact]] = []
    scene_positions_are_unique = bool(scene_rows)
    occurrence_counts: dict[str, int] = {}
    for occurrence in extract_scene_occurrences(source_text):
        occurrence_counts[occurrence.text] = occurrence_counts.get(occurrence.text, 0) + 1
    if any(occurrence_counts.get(scene_item.text, 0) != 1 for scene_item, _ in scene_rows):
        scene_positions_are_unique = False
    for scene_item, scene_fact in scene_rows:
        position = _unique_evidence_start(source_text, scene_item.evidence)
        if position is None:
            scene_positions_are_unique = False
            break
        positioned_scenes.append((position, scene_item, scene_fact))
    if len({row[0] for row in positioned_scenes}) != len(positioned_scenes):
        scene_positions_are_unique = False

    if scene_positions_are_unique:
        positioned_scenes.sort(key=lambda row: row[0])
        associated_marker_count = 0
        character_entity_by_name = {
            fact.claim.text: fact.entity_id
            for fact in facts
            if fact.entity_kind == "character" and fact.field_path == "identity.display_name"
        }
        known_character_names = set(character_entity_by_name)
        for scene_index, (scene_start, _, scene_fact) in enumerate(positioned_scenes):
            scene_end = (
                positioned_scenes[scene_index + 1][0]
                if scene_index + 1 < len(positioned_scenes)
                else len(source_text)
            )
            range_text = source_text[scene_start:scene_end]
            for appearance in extract_character_appearances_in_range(
                range_text,
                known_character_names=known_character_names,
                source_offset=scene_start,
            ):
                character_entity_id = character_entity_by_name.get(appearance.character_name)
                if not character_entity_id:
                    continue
                appearance_fact = character_appearance_to_candidate_fact(
                    appearance,
                    scene_entity_id=scene_fact.entity_id,
                    character_entity_id=character_entity_id,
                    project_id=project_id,
                    source_revision_id=source_revision_id,
                    source_revision_digest=digest,
                    source_text=source_text,
                )
                facts.append(appearance_fact)
                items.append(
                    _fact_to_review_item(
                        appearance_fact,
                        producer_method=appearance.method,
                        decision=decisions.get(appearance_fact.fact_id),
                    )
                )
            boundaries = extract_explicit_beat_boundaries(
                range_text,
                source_offset=scene_start,
            )
            associated_marker_count += len(boundaries)
            if not boundaries:
                missing.append(
                    MissingSlotItem(
                        slot_id=_id("miss_beat"),
                        entity_kind="beat",
                        field_path=f"scene[{scene_fact.entity_id}].beats",
                        message="No explicit numbered Beat labels in this Scene; no Beat candidate emitted.",
                    )
                )
                continue
            for boundary in boundaries:
                fact = beat_boundary_to_candidate_fact(
                    boundary,
                    scene_entity_id=scene_fact.entity_id,
                    project_id=project_id,
                    source_revision_id=source_revision_id,
                    source_revision_digest=digest,
                )
                facts.append(fact)
                items.append(
                    _fact_to_review_item(
                        fact,
                        producer_method=boundary.method,
                        decision=decisions.get(fact.fact_id),
                    )
                )
                beat_range_text = source_text[boundary.source_start:boundary.source_end]
                for facet in extract_explicit_beat_facets(
                    beat_range_text,
                    source_offset=boundary.source_start,
                ):
                    facet_fact = beat_facet_to_candidate_fact(
                        facet,
                        scene_entity_id=scene_fact.entity_id,
                        beat_order_index=boundary.order_index,
                        beat_entity_id=fact.entity_id,
                        project_id=project_id,
                        source_revision_id=source_revision_id,
                        source_revision_digest=digest,
                        source_text=source_text,
                    )
                    facts.append(facet_fact)
                    items.append(
                        _fact_to_review_item(
                            facet_fact,
                            producer_method=facet.item.method,
                            decision=decisions.get(facet_fact.fact_id),
                        )
                    )
        global_marker_count = len(extract_explicit_beat_boundaries(source_text))
        if global_marker_count != associated_marker_count:
            beat_notes.append(
                "explicit_beat_labels_outside_resolved_scene_ranges_ignored"
            )
    else:
        if scene_rows:
            beat_notes.append("beat_scene_ownership_ambiguous; no Beat candidate emitted")
            for _, scene_fact in scene_rows:
                missing.append(
                    MissingSlotItem(
                        slot_id=_id("miss_beat"),
                        entity_kind="beat",
                        field_path=f"scene[{scene_fact.entity_id}].beats",
                        message="Owning Scene source range is ambiguous; no Beat candidate emitted.",
                    )
                )
        else:
            if extract_explicit_beat_boundaries(source_text):
                beat_notes.append(
                    "explicit_beat_labels_without_resolved_scene_ignored"
                )
            missing.append(
                MissingSlotItem(
                    slot_id=_id("miss_beat"),
                    entity_kind="beat",
                    field_path="scene[(missing)].beats",
                    message="No resolved Scene is available to own a Beat candidate.",
                )
            )

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
        extraction_notes=[*extraction.notes, *beat_notes],
    )
    return bundle, facts


def _fact_to_review_item(
    fact: CandidateFact,
    *,
    producer_method: str = "",
    decision: ReviewDecision | None = None,
) -> CandidateReviewItem:
    is_missing = fact.status == CandidateStatus.MISSING
    decided = decision if decision is not None else ReviewDecision.PENDING
    if decided != ReviewDecision.PENDING:
        actions: list[ReviewAction] = []
    elif is_missing:
        actions = [ReviewAction.EDIT_CONFIRM, ReviewAction.REJECT]
    else:
        actions = [ReviewAction.ACCEPT, ReviewAction.EDIT_CONFIRM, ReviewAction.REJECT]
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
        review_decision=decided.value if isinstance(decided, ReviewDecision) else str(decided),
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
    script_profile_facets = extract_script_profile_facets(source_text)
    script_format_profile = extract_script_format_profile(source_text)
    digest = revision_digest(source_text)
    bundle, facts = build_review_bundle_from_extraction(
        extraction,
        script_profile_facets=script_profile_facets,
        script_format_profile=script_format_profile,
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
        missing_slots=list(bundle.missing_slots),
        extraction_notes=list(bundle.extraction_notes),
        title_hint=title_hint,
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


def bundle_from_ledger(ledger: FactLedger) -> CandidateReviewBundle:
    items = [
        _fact_to_review_item(
            fact,
            decision=ledger.review_decisions.get(fact_id, ReviewDecision.PENDING),
        )
        for fact_id, fact in ledger.candidates.items()
    ]
    return CandidateReviewBundle(
        project_id=ledger.project_id,
        source_revision_id=ledger.current_revision_id,
        source_revision_digest=ledger.current_revision_digest,
        title_hint=ledger.title_hint,
        items=items,
        missing_slots=list(ledger.missing_slots),
        extraction_notes=list(ledger.extraction_notes),
    )


# ---------------------------------------------------------------------------
# Human actions
# ---------------------------------------------------------------------------


def _require_pending(ledger: FactLedger, fact_id: str) -> CandidateFact:
    if fact_id not in ledger.candidates:
        raise LoopError(f"unknown fact_id: {fact_id}")
    decision = ledger.review_decisions.get(fact_id, ReviewDecision.PENDING)
    if decision != ReviewDecision.PENDING:
        raise LoopError(f"fact {fact_id} already decided: {decision}")
    return ledger.candidates[fact_id]


def _supersede_matching_authority(
    ledger: FactLedger,
    candidate: CandidateFact,
    *,
    when: datetime,
) -> list[AuthoritativeFactRecord]:
    superseded: list[AuthoritativeFactRecord] = []
    for record in ledger.authoritative_records:
        if (
            record.validity == AuthorityValidity.ACTIVE
            and record.fact.entity_id == candidate.entity_id
            and record.fact.field_path == candidate.field_path
            and record.fact.source_revision_id == ledger.current_revision_id
        ):
            record.validity = AuthorityValidity.SUPERSEDED
            record.invalidated_at = when
            superseded.append(record)
    return superseded


def _link_superseded_authority(
    record: AuthoritativeFactRecord,
    superseded: list[AuthoritativeFactRecord],
) -> None:
    if not superseded:
        return
    record.supersedes_record_id = superseded[-1].record_id
    for prior in superseded:
        prior.superseded_by_record_id = record.record_id


def _normalize_script_format_profile_edit(candidate: CandidateFact, value: str) -> str:
    facet = candidate.field_path.removeprefix("script_format_profile.")
    if facet == "format_style":
        allowed = {"labeled", "industry_heading", "mixed", "unclear"}
        if value not in allowed:
            raise LoopError(
                "script_format_profile.format_style must be one of "
                "labeled, industry_heading, mixed, unclear"
            )
        return value
    if facet == "cleaning_notes":
        try:
            notes = json.loads(value)
        except json.JSONDecodeError as exc:
            raise LoopError(
                "script_format_profile.cleaning_notes must be a JSON string list"
            ) from exc
        if not isinstance(notes, list) or any(not isinstance(note, str) for note in notes):
            raise LoopError(
                "script_format_profile.cleaning_notes must be a JSON string list"
            )
        return json.dumps(notes, ensure_ascii=False, separators=(",", ":"))
    if facet == "scene_boundary_count":
        if not value.isascii() or not value.isdecimal():
            raise LoopError(
                "script_format_profile.scene_boundary_count must be a nonnegative integer"
            )
        return str(int(value))
    raise LoopError(f"unknown script_format_profile facet: {facet}")


def accept_candidate(
    ledger: FactLedger,
    fact_id: str,
    *,
    human_id: str,
    reason: str | None = None,
) -> AuthoritativeFactRecord:
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
    auth = promote_candidate_fact(confirmed, authoritative_fact_id=_id("auth"), promoted_at=when)
    superseded = _supersede_matching_authority(ledger, confirmed, when=when)
    record = AuthoritativeFactRecord(record_id=_id("arec"), fact=auth)
    _link_superseded_authority(record, superseded)
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
    cand = _require_pending(ledger, fact_id)
    new_text = new_text.strip()
    if not new_text:
        raise LoopError("new_text must be non-empty")
    if cand.entity_kind == "script_format_profile":
        new_text = _normalize_script_format_profile_edit(cand, new_text)
    when = _now()
    spans = list(cand.claim.evidence_spans)
    if source_text:
        require_exact = cand.entity_kind in {"beat", "script_format_profile"} or _is_scene_cast_appearance(
            cand.field_path
        )
        found = (
            _exact_evidence_for(source_text, new_text)
            if require_exact
            else _evidence_for(source_text, new_text)
        )
        if found:
            spans = found
    if cand.entity_kind in {"beat", "script_format_profile"} and not spans:
        raise LoopError(
            f"{cand.entity_kind} edit_confirm requires source-backed evidence"
        )
    if _is_scene_cast_appearance(cand.field_path) and not spans:
        raise LoopError("Scene cast appearance edit_confirm requires source-backed evidence")
    if not spans:
        spans = [EvidenceSpan(start=0, end=len(new_text), quote=new_text[:1200])]
    updated = CandidateFact.model_validate(
        cand.model_copy(
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
        ).model_dump()
    )
    ledger.candidates[fact_id] = updated
    auth = promote_candidate_fact(updated, authoritative_fact_id=_id("auth"), promoted_at=when)
    superseded = _supersede_matching_authority(ledger, updated, when=when)
    record = AuthoritativeFactRecord(record_id=_id("arec"), fact=auth)
    _link_superseded_authority(record, superseded)
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
            summary=f"edited candidate {fact_id}: {cand.claim.text!r} → {new_text!r} and confirmed",
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
    cand = _require_pending(ledger, fact_id)
    when = _now()
    ledger.review_decisions[fact_id] = ReviewDecision.REJECTED
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


def on_script_revision_changed(
    ledger: FactLedger,
    *,
    new_revision_id: str,
    new_source_text: str,
    actor_id: str = "system",
) -> list[str]:
    when = _now()
    new_digest = revision_digest(new_source_text)
    invalidated: list[str] = []
    for rec in ledger.authoritative_records:
        if rec.fact.source_revision_id == new_revision_id:
            continue
        if rec.validity == AuthorityValidity.INVALIDATED_BY_REVISION:
            continue
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
    ledger.missing_slots.clear()
    ledger.extraction_notes.clear()
    ledger.title_hint = None
    ledger.append_change(
        ChangeRecord(
            change_id=_id("chg"),
            at=when,
            actor_kind="system",
            actor_id=actor_id,
            from_version_id=old_rev or None,
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
    store: RuntimeStore | None = None,
) -> dict[str, Any]:
    rev = revision_id or ledger.current_revision_id
    auth = list_current_authoritative(ledger, revision_id=rev)
    auth_chars = [
        f.text
        for f in auth
        if f.entity_kind == "character" and f.field_path == "identity.display_name"
    ]
    auth_scenes = [f.text for f in auth if f.entity_kind == "scene"]
    auth_cast = [
        {
            "entity_id": fact.entity_id,
            "field_path": fact.field_path,
            "text": fact.text,
        }
        for fact in auth
        if fact.entity_kind == "character" and _is_scene_cast_appearance(fact.field_path)
    ]
    auth_profile = {
        f.field_path.removeprefix("script_profile."): f.text
        for f in auth
        if f.entity_kind == "script_profile"
    }
    auth_format_profile: dict[str, Any] = {}
    for fact in auth:
        if fact.entity_kind != "script_format_profile":
            continue
        facet = fact.field_path.removeprefix("script_format_profile.")
        value: Any = fact.text
        if facet == "scene_boundary_count" and fact.text.isdecimal():
            value = int(fact.text)
        elif facet == "cleaning_notes":
            try:
                parsed = json.loads(fact.text)
            except json.JSONDecodeError:
                parsed = fact.text
            value = parsed if isinstance(parsed, list) else fact.text
        auth_format_profile[facet] = value
    auth_beats = [
        {
            "entity_id": fact.entity_id,
            "field_path": fact.field_path,
            "text": fact.text,
        }
        for fact in auth
        if fact.entity_kind == "beat" and fact.field_path.endswith(".boundary")
    ]
    auth_beat_facets = [
        {
            "entity_id": fact.entity_id,
            "field_path": fact.field_path,
            "text": fact.text,
        }
        for fact in auth
        if fact.entity_kind == "beat" and not fact.field_path.endswith(".boundary")
    ]
    raw_chars = list(fresh_extraction.character_texts()) if fresh_extraction else []
    raw_scenes = list(fresh_extraction.scene_texts()) if fresh_extraction else []
    asset_requirements = asset_requirements_payload(
        project_scene_character_asset_requirements(
            store,
            project_id=ledger.project_id,
            authoritative_facts=auth,
            revision_id=rev,
        )
    )
    return {
        "revision_id": rev,
        "characters": auth_chars or raw_chars,
        "scenes": auth_scenes or raw_scenes,
        "script_profile": auth_profile,
        "script_format_profile": auth_format_profile,
        "beats": auth_beats,
        "beat_facets": auth_beat_facets,
        "scene_cast": auth_cast,
        "asset_requirements": asset_requirements,
        "authority_source": "authoritative_ledger" if auth else "raw_extraction_only",
        "authoritative_fact_ids": [f.authoritative_fact_id for f in auth],
        "raw_extraction_characters": raw_chars,
        "raw_extraction_scenes": raw_scenes,
    }


def inject_raw_junk_candidate(
    ledger: FactLedger,
    *,
    junk_text: str,
    evidence_quote: str,
    confidence: float = 0.96,
) -> CandidateFact:
    spans = [EvidenceSpan(start=0, end=max(len(evidence_quote), 1), quote=evidence_quote[:1200])]
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


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _ledger_dir(store: RuntimeStore, project_id: str) -> Path:
    return store.projects_dir / safe_id(project_id) / "candidate_facts"


def _ledger_path(store: RuntimeStore, project_id: str) -> Path:
    return _ledger_dir(store, project_id) / "ledger.json"


def _lock_path(store: RuntimeStore, project_id: str) -> Path:
    return _ledger_dir(store, project_id) / "ledger.lock"


def _empty_ledger_state(project_id: str) -> dict[str, Any]:
    return {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": LEDGER_SCHEMA_VERSION,
        "project_id": project_id,
        "current_revision_id": "",
        "current_revision_digest": "",
        "candidates": {},
        "review_decisions": {},
        "missing_slots": [],
        "extraction_notes": [],
        "title_hint": None,
        "authoritative_records": [],
        "change_log": [],
        "updated_at": _now().isoformat(),
    }


def ledger_to_state(ledger: FactLedger) -> dict[str, Any]:
    payload = {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": LEDGER_SCHEMA_VERSION,
        "project_id": ledger.project_id,
        "current_revision_id": ledger.current_revision_id,
        "current_revision_digest": ledger.current_revision_digest,
        "candidates": {k: v.model_dump(mode="json") for k, v in ledger.candidates.items()},
        "review_decisions": {k: (v.value if isinstance(v, ReviewDecision) else str(v)) for k, v in ledger.review_decisions.items()},
        "missing_slots": [slot.model_dump(mode="json") for slot in ledger.missing_slots],
        "extraction_notes": list(ledger.extraction_notes),
        "title_hint": ledger.title_hint,
        "authoritative_records": [r.model_dump(mode="json") for r in ledger.authoritative_records],
        "change_log": [c.model_dump(mode="json") for c in ledger.change_log],
        "updated_at": _now().isoformat(),
    }
    reject_unsafe_payload(payload)
    return payload


def ledger_from_state(state: Mapping[str, Any], project_id: str) -> FactLedger:
    decisions_raw = state.get("review_decisions") or {}
    decisions: dict[str, ReviewDecision] = {}
    for key, value in decisions_raw.items():
        try:
            decisions[str(key)] = ReviewDecision(str(value))
        except ValueError:
            decisions[str(key)] = ReviewDecision.PENDING
    candidates = {
        str(k): CandidateFact.model_validate(v)
        for k, v in (state.get("candidates") or {}).items()
    }
    records = [
        AuthoritativeFactRecord.model_validate(item)
        for item in (state.get("authoritative_records") or [])
    ]
    changes = [ChangeRecord.model_validate(item) for item in (state.get("change_log") or [])]
    missing_slots = [
        MissingSlotItem.model_validate(item) for item in (state.get("missing_slots") or [])
    ]
    return FactLedger(
        project_id=project_id,
        current_revision_id=str(state.get("current_revision_id") or ""),
        current_revision_digest=str(state.get("current_revision_digest") or ""),
        candidates=candidates,
        review_decisions=decisions,
        missing_slots=missing_slots,
        extraction_notes=[str(note) for note in (state.get("extraction_notes") or [])],
        title_hint=str(state.get("title_hint") or "") or None,
        authoritative_records=records,
        change_log=changes,
    )


def load_ledger(store: RuntimeStore, project_id: str) -> FactLedger:
    path = _ledger_path(store, project_id)
    if path.is_file():
        state = read_json(path)
        reject_unsafe_payload(state)
        if state.get("project_id") != project_id:
            raise ValueError("candidate fact ledger project id mismatch")
        return ledger_from_state(state, project_id)
    return FactLedger(project_id=project_id)


def save_ledger(store: RuntimeStore, ledger: FactLedger) -> Path:
    path = _ledger_path(store, ledger.project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, ledger_to_state(ledger))
    return path


def _authoritative_record(
    ledger: FactLedger,
    authoritative_fact_id: str,
) -> AuthoritativeFactRecord:
    for record in ledger.authoritative_records:
        if record.fact.authoritative_fact_id == authoritative_fact_id:
            return record
    raise LoopError(f"unknown authoritative_fact_id: {authoritative_fact_id}")


def graph_feed_status_rows(ledger: FactLedger) -> list[dict[str, Any]]:
    return [
        {
            "record_id": record.record_id,
            "authoritative_fact_id": record.fact.authoritative_fact_id,
            "source_candidate_fact_id": record.fact.source_candidate_fact_id,
            "source_revision_id": record.fact.source_revision_id,
            "validity": record.validity.value,
            "status": record.graph_feed_status.value,
            "attempt_count": record.graph_feed_attempt_count,
            "last_attempt_at": (
                record.graph_feed_last_attempt_at.isoformat()
                if record.graph_feed_last_attempt_at
                else None
            ),
            "succeeded_at": (
                record.graph_feed_succeeded_at.isoformat()
                if record.graph_feed_succeeded_at
                else None
            ),
            "last_error": record.graph_feed_last_error,
            "node_ids": list(record.graph_feed_node_ids),
            "graph_version": record.graph_feed_graph_version,
            "retry_available": (
                record.validity == AuthorityValidity.ACTIVE
                and record.graph_feed_status in {GraphFeedStatus.PENDING, GraphFeedStatus.FAILED}
            ),
        }
        for record in ledger.authoritative_records
    ]


def _attempt_durable_graph_feed(
    store: RuntimeStore,
    project_id: str,
    authoritative_fact_id: str,
) -> tuple[dict[str, Any], FactLedger]:
    """Attempt one idempotent graph write and durably record its outcome."""

    with exclusive_file_lock(_lock_path(store, project_id)):
        ledger = load_ledger(store, project_id)
        record = _authoritative_record(ledger, authoritative_fact_id)
        if record.validity != AuthorityValidity.ACTIVE:
            raise LoopError("only an active authoritative fact may feed Production Graph")
        if record.fact.source_revision_id != ledger.current_revision_id:
            raise LoopError("authoritative fact is not bound to the current script revision")
        if record.graph_feed_status == GraphFeedStatus.SUCCEEDED:
            return {
                "fed": True,
                "skipped": True,
                "reason": "graph_feed_already_succeeded",
                "node_ids": list(record.graph_feed_node_ids),
                "graph_version": record.graph_feed_graph_version,
                "idempotent_replay": True,
                "affects_production_graph": False,
            }, ledger
        if record.graph_feed_status not in {GraphFeedStatus.PENDING, GraphFeedStatus.FAILED}:
            raise LoopError(
                f"graph feed is not retryable from status {record.graph_feed_status.value}"
            )
        record.graph_feed_status = GraphFeedStatus.PENDING
        record.graph_feed_attempt_count += 1
        record.graph_feed_last_attempt_at = _now()
        record.graph_feed_last_error = None
        save_ledger(store, ledger)
        fact = record.fact

    try:
        result = feed_authoritative_facts_to_production_graph(
            ProductionGraphStore(store),
            project_id,
            [fact],
        )
        if not result.get("fed"):
            raise ProductionGraphError(str(result.get("reason") or "graph feed was skipped"))
    except ProductionGraphError as exc:
        with exclusive_file_lock(_lock_path(store, project_id)):
            ledger = load_ledger(store, project_id)
            record = _authoritative_record(ledger, authoritative_fact_id)
            record.graph_feed_status = GraphFeedStatus.FAILED
            record.graph_feed_last_error = str(exc)[:400]
            save_ledger(store, ledger)
        return {
            "fed": False,
            "skipped": False,
            "reason": "graph_feed_failed",
            "error": str(exc)[:400],
            "node_ids": [],
            "graph_version": None,
            "affects_production_graph": False,
        }, ledger

    with exclusive_file_lock(_lock_path(store, project_id)):
        ledger = load_ledger(store, project_id)
        record = _authoritative_record(ledger, authoritative_fact_id)
        record.graph_feed_status = GraphFeedStatus.SUCCEEDED
        record.graph_feed_succeeded_at = _now()
        record.graph_feed_last_error = None
        record.graph_feed_node_ids = list(result.get("node_ids") or [])
        graph_version = result.get("graph_version")
        record.graph_feed_graph_version = int(graph_version) if graph_version is not None else None
        save_ledger(store, ledger)
    return result, ledger


# ---------------------------------------------------------------------------
# Script Truth helpers
# ---------------------------------------------------------------------------


def _load_script_revision_text(store: RuntimeStore, project_id: str, revision_id: str) -> tuple[str, str]:
    """Return (source_text, source_digest) for a Script Truth revision."""

    path = store.projects_dir / safe_id(project_id) / "script_core_truth" / "truth_state.json"
    if not path.is_file():
        raise LookupError(f"script truth not found for project: {project_id}")
    truth = read_json(path)
    reject_unsafe_payload(truth)
    revision = dict((truth.get("revisions") or {}).get(revision_id) or {})
    if not revision:
        raise LookupError(f"script revision not found: {revision_id}")
    source_text = str(revision.get("source_text") or "")
    source_digest = str(revision.get("source_digest") or "")
    if not source_text or not source_digest:
        raise LookupError(f"script revision missing source text/digest: {revision_id}")
    return source_text, source_digest


def _enforce_project_access(auth: RuntimeAuthStore, request: Request, project_id: str) -> None:
    if not auth.enabled():
        return
    user = auth.require_user(request)
    if not project_id or not auth.user_can_access_project(str(user["user_id"]), project_id):
        raise HTTPException(status_code=403, detail="project access denied")


def _require_loop_enabled() -> None:
    if not confirmation_loop_enabled():
        raise HTTPException(
            status_code=404,
            detail=safe_error_detail(
                "candidate_confirmation_disabled",
                message=f"{CONFIRMATION_LOOP_ENV} is not enabled",
                stage="candidate_confirmation",
            ),
        )


def _require_recoverable_graph_feed_enabled() -> None:
    if not recoverable_graph_feed_enabled():
        raise HTTPException(
            status_code=404,
            detail=safe_error_detail(
                "recoverable_graph_feed_disabled",
                message=f"{RECOVERABLE_GRAPH_FEED_ENV} is not enabled",
                stage="candidate_confirmation_graph_feed_retry",
            ),
        )


def _human_id(auth: RuntimeAuthStore, request: Request) -> str:
    if not auth.enabled():
        return "local-runtime-owner"
    user = auth.require_user(request)
    return str(user.get("user_id") or "unknown-user")


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class CandidateReviewRefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_revision_id: str = Field(min_length=1, max_length=120)
    source_revision_digest: str = Field(min_length=64, max_length=64)
    title_hint: str | None = Field(default=None, max_length=200)


class CandidateFactActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["accept", "edit_confirm", "reject"]
    fact_id: str = Field(min_length=1, max_length=120)
    source_revision_id: str = Field(min_length=1, max_length=120)
    source_revision_digest: str = Field(min_length=64, max_length=64)
    new_text: str | None = Field(default=None, max_length=2000)
    reason: str | None = Field(default=None, max_length=400)


class CandidateGraphFeedRetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authoritative_fact_id: str = Field(min_length=1, max_length=120)
    source_revision_id: str = Field(min_length=1, max_length=120)
    source_revision_digest: str = Field(min_length=64, max_length=64)


def _with_graph_feed_status(
    payload: dict[str, Any],
    ledger: FactLedger,
) -> dict[str, Any]:
    if recoverable_graph_feed_enabled():
        payload["graph_feed_records"] = graph_feed_status_rows(ledger)
    return payload


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def register_runtime_candidate_confirmation_routes(
    app: FastAPI,
    store: RuntimeStore,
    auth: RuntimeAuthStore,
) -> None:
    @app.get("/projects/{project_id}/candidate-facts/review")
    def get_candidate_fact_review(
        project_id: str,
        request: Request,
        source_revision_id: str | None = None,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        _require_loop_enabled()
        store.ensure_project_manifest(project_id)
        ledger = load_ledger(store, project_id)
        rev = source_revision_id or ledger.current_revision_id
        if rev and ledger.current_revision_id and rev != ledger.current_revision_id:
            # Still return ledger, but note mismatch — client should refresh.
            bundle = bundle_from_ledger(ledger)
            return _with_graph_feed_status({
                "enabled": True,
                "bundle": bundle.model_dump(mode="json"),
                "authoritative": [f.model_dump(mode="json") for f in list_current_authoritative(ledger, revision_id=rev)],
                "warning": "requested_revision_differs_from_ledger_current",
                "ledger_current_revision_id": ledger.current_revision_id,
                "affects_production_graph": False,
            }, ledger)
        bundle = bundle_from_ledger(ledger)
        return _with_graph_feed_status({
            "enabled": True,
            "bundle": bundle.model_dump(mode="json"),
            "authoritative": [
                f.model_dump(mode="json")
                for f in list_current_authoritative(ledger)
            ],
            "affects_production_graph": False,
        }, ledger)

    @app.post("/projects/{project_id}/candidate-facts/review/refresh")
    def refresh_candidate_fact_review(
        project_id: str,
        body: CandidateReviewRefreshRequest,
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        _require_loop_enabled()
        if not improved_extraction_enabled():
            raise HTTPException(
                status_code=409,
                detail=safe_error_detail(
                    "improved_extraction_required",
                    message="candidate-facts refresh requires AFS_USE_IMPROVED_EXTRACTION=true",
                    project_id=project_id,
                    stage="candidate_confirmation_refresh",
                ),
            )
        store.ensure_project_manifest(project_id)
        try:
            source_text, source_digest = _load_script_revision_text(
                store, project_id, body.source_revision_id
            )
        except LookupError as exc:
            raise HTTPException(
                status_code=404,
                detail=safe_error_detail(
                    "script_revision_not_found",
                    message=str(exc),
                    project_id=project_id,
                    stage="candidate_confirmation_refresh",
                ),
            ) from exc
        if source_digest != body.source_revision_digest:
            raise HTTPException(
                status_code=409,
                detail=safe_error_detail(
                    "script_revision_digest_mismatch",
                    message="source_revision_digest does not match Script Truth revision",
                    project_id=project_id,
                    stage="candidate_confirmation_refresh",
                ),
            )

        with exclusive_file_lock(_lock_path(store, project_id)):
            ledger = load_ledger(store, project_id)
            if ledger.current_revision_id and ledger.current_revision_id != body.source_revision_id:
                on_script_revision_changed(
                    ledger,
                    new_revision_id=body.source_revision_id,
                    new_source_text=source_text,
                    actor_id=_human_id(auth, request),
                )
                mark_bindings_stale_for_revision_change(
                    store,
                    project_id=project_id,
                    new_revision_id=body.source_revision_id,
                )
            # Preserve prior authoritative + change_log audit rows; replace candidates.
            new_ledger, bundle = open_ledger_from_extraction(
                source_text,
                project_id=project_id,
                source_revision_id=body.source_revision_id,
                title_hint=body.title_hint,
            )
            # Keep invalidated/superseded history from previous ledger
            new_ledger.authoritative_records = list(ledger.authoritative_records) + list(
                new_ledger.authoritative_records
            )
            # Accumulate human/system audit trail across revision refreshes
            new_ledger.change_log = list(ledger.change_log) + list(new_ledger.change_log)
            # Prefer digest from Script Truth binding
            new_ledger.current_revision_digest = source_digest
            for fact in new_ledger.candidates.values():
                fact.source_revision_digest = source_digest
            for item in bundle.items:
                item.source_revision_digest = source_digest
            bundle.source_revision_digest = source_digest
            save_ledger(store, new_ledger)

        return _with_graph_feed_status({
            "enabled": True,
            "bundle": bundle.model_dump(mode="json"),
            "authoritative": [
                f.model_dump(mode="json")
                for f in list_current_authoritative(new_ledger)
            ],
            "affects_production_graph": False,
            "script_truth_binding": current_script_revision_binding(store, project_id),
        }, new_ledger)

    @app.post("/projects/{project_id}/candidate-facts/actions")
    def apply_candidate_fact_action(
        project_id: str,
        body: CandidateFactActionRequest,
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        _require_loop_enabled()
        store.ensure_project_manifest(project_id)
        human_id = _human_id(auth, request)
        try:
            source_text, source_digest = _load_script_revision_text(
                store, project_id, body.source_revision_id
            )
        except LookupError as exc:
            raise HTTPException(
                status_code=404,
                detail=safe_error_detail(
                    "script_revision_not_found",
                    message=str(exc),
                    project_id=project_id,
                    stage="candidate_confirmation_action",
                ),
            ) from exc
        if source_digest != body.source_revision_digest:
            raise HTTPException(
                status_code=409,
                detail=safe_error_detail(
                    "script_revision_digest_mismatch",
                    message="source_revision_digest does not match Script Truth revision",
                    project_id=project_id,
                    stage="candidate_confirmation_action",
                ),
            )

        newly_authoritative: list[AuthoritativeScriptFact] = []
        authoritative_fact_id_for_feed = ""
        with exclusive_file_lock(_lock_path(store, project_id)):
            ledger = load_ledger(store, project_id)
            if ledger.current_revision_id != body.source_revision_id:
                raise HTTPException(
                    status_code=409,
                    detail=safe_error_detail(
                        "ledger_revision_mismatch",
                        message="refresh candidate review for this revision before acting",
                        project_id=project_id,
                        stage="candidate_confirmation_action",
                    ),
                )
            try:
                if body.action == "accept":
                    record = accept_candidate(
                        ledger,
                        body.fact_id,
                        human_id=human_id,
                        reason=body.reason,
                    )
                    newly_authoritative = [record.fact]
                    authoritative_fact_id_for_feed = record.fact.authoritative_fact_id
                    action_result = {"authoritative_fact_id": record.fact.authoritative_fact_id, "text": record.fact.text}
                elif body.action == "edit_confirm":
                    if not body.new_text:
                        raise LoopError("edit_confirm requires new_text")
                    record = edit_and_confirm_candidate(
                        ledger,
                        body.fact_id,
                        new_text=body.new_text,
                        human_id=human_id,
                        reason=body.reason or "human_edit_confirm",
                        source_text=source_text,
                    )
                    newly_authoritative = [record.fact]
                    authoritative_fact_id_for_feed = record.fact.authoritative_fact_id
                    action_result = {"authoritative_fact_id": record.fact.authoritative_fact_id, "text": record.fact.text}
                else:
                    reject_candidate(
                        ledger,
                        body.fact_id,
                        human_id=human_id,
                        reason=body.reason or "human_reject",
                    )
                    action_result = {"rejected_fact_id": body.fact_id}
            except LoopError as exc:
                raise HTTPException(
                    status_code=409,
                    detail=safe_error_detail(
                        "candidate_action_rejected",
                        message=str(exc),
                        project_id=project_id,
                        stage="candidate_confirmation_action",
                    ),
                ) from exc
            if (
                newly_authoritative
                and recoverable_graph_feed_enabled()
                and candidate_facts_feed_production_graph_enabled()
            ):
                _authoritative_record(
                    ledger,
                    authoritative_fact_id_for_feed,
                ).graph_feed_status = GraphFeedStatus.PENDING
            save_ledger(store, ledger)

        graph_feed: dict[str, Any] = {
            "fed": False,
            "skipped": True,
            "reason": "no_new_authoritative_fact",
            "node_ids": [],
        }
        entity_asset_binding: dict[str, Any] | None = None
        if newly_authoritative:
            binding = bind_authoritative_fact_to_core_asset(store, newly_authoritative[0])
            if binding is not None:
                entity_asset_binding = binding.model_dump(mode="json")
            if (
                recoverable_graph_feed_enabled()
                and candidate_facts_feed_production_graph_enabled()
            ):
                graph_feed, ledger = _attempt_durable_graph_feed(
                    store,
                    project_id,
                    authoritative_fact_id_for_feed,
                )
            else:
                try:
                    graph_feed = feed_authoritative_facts_to_production_graph(
                        ProductionGraphStore(store),
                        project_id,
                        newly_authoritative,
                    )
                except ProductionGraphError as exc:
                    raise HTTPException(
                        status_code=409,
                        detail=safe_error_detail(
                            "authoritative_fact_graph_feed_failed",
                            message=str(exc),
                            project_id=project_id,
                            stage="candidate_confirmation_graph_feed",
                        ),
                    ) from exc

        payload = {
            "enabled": True,
            "action": body.action,
            "result": action_result,
            "bundle": bundle_from_ledger(ledger).model_dump(mode="json"),
            "authoritative": [
                f.model_dump(mode="json") for f in list_current_authoritative(ledger)
            ],
            "resolved": resolve_for_downstream(ledger, store=store),
            "graph_feed": graph_feed,
            "entity_asset_binding": entity_asset_binding,
            "affects_production_graph": bool(graph_feed.get("fed")),
            "production_graph_feed_enabled": candidate_facts_feed_production_graph_enabled(),
        }
        if recoverable_graph_feed_enabled():
            graph_feed_failed = graph_feed.get("reason") == "graph_feed_failed"
            payload.update(
                {
                    "operation_status": "partial_success" if graph_feed_failed else "succeeded",
                    "confirmation_status": "succeeded" if newly_authoritative else "not_applicable",
                    "graph_feed_status": "failed" if graph_feed_failed else (
                        "succeeded" if graph_feed.get("fed") else "not_requested"
                    ),
                    "retry_available": graph_feed_failed,
                }
            )
        return _with_graph_feed_status(payload, ledger)

    @app.post("/projects/{project_id}/candidate-facts/graph-feed/retry")
    def retry_candidate_fact_graph_feed(
        project_id: str,
        body: CandidateGraphFeedRetryRequest,
        request: Request,
    ) -> dict[str, Any]:
        _enforce_project_access(auth, request, project_id)
        _require_loop_enabled()
        _require_recoverable_graph_feed_enabled()
        store.ensure_project_manifest(project_id)
        try:
            _, source_digest = _load_script_revision_text(
                store,
                project_id,
                body.source_revision_id,
            )
        except LookupError as exc:
            raise HTTPException(
                status_code=404,
                detail=safe_error_detail(
                    "script_revision_not_found",
                    message=str(exc),
                    project_id=project_id,
                    stage="candidate_confirmation_graph_feed_retry",
                ),
            ) from exc
        if source_digest != body.source_revision_digest:
            raise HTTPException(
                status_code=409,
                detail=safe_error_detail(
                    "script_revision_digest_mismatch",
                    message="source_revision_digest does not match Script Truth revision",
                    project_id=project_id,
                    stage="candidate_confirmation_graph_feed_retry",
                ),
            )

        try:
            with exclusive_file_lock(_lock_path(store, project_id)):
                ledger = load_ledger(store, project_id)
                record = _authoritative_record(ledger, body.authoritative_fact_id)
                if ledger.current_revision_id != body.source_revision_id:
                    raise LoopError("retry requires the ledger's current script revision")
                if (
                    record.fact.source_revision_id != body.source_revision_id
                    or record.fact.source_revision_digest != body.source_revision_digest
                ):
                    raise LoopError("authoritative fact does not match the requested script revision")
                if record.validity != AuthorityValidity.ACTIVE:
                    raise LoopError("only an active authoritative fact may retry graph feed")
                if record.graph_feed_status not in {
                    GraphFeedStatus.PENDING,
                    GraphFeedStatus.FAILED,
                    GraphFeedStatus.SUCCEEDED,
                }:
                    raise LoopError(
                        f"graph feed is not retryable from status {record.graph_feed_status.value}"
                    )
            graph_feed, ledger = _attempt_durable_graph_feed(
                store,
                project_id,
                body.authoritative_fact_id,
            )
        except LoopError as exc:
            raise HTTPException(
                status_code=409,
                detail=safe_error_detail(
                    "graph_feed_retry_rejected",
                    message=str(exc),
                    project_id=project_id,
                    stage="candidate_confirmation_graph_feed_retry",
                ),
            ) from exc

        failed = graph_feed.get("reason") == "graph_feed_failed"
        payload = {
            "enabled": True,
            "operation_status": "partial_success" if failed else "succeeded",
            "confirmation_status": "already_succeeded",
            "graph_feed_status": "failed" if failed else "succeeded",
            "retry_available": failed,
            "authoritative_fact_id": body.authoritative_fact_id,
            "graph_feed": graph_feed,
            "affects_production_graph": bool(
                graph_feed.get("fed")
                and not graph_feed.get("skipped")
                and not graph_feed.get("idempotent_replay")
            ),
            "authoritative": [
                fact.model_dump(mode="json") for fact in list_current_authoritative(ledger)
            ],
        }
        return _with_graph_feed_status(payload, ledger)

    @app.get("/projects/{project_id}/entity-asset-bindings")
    def get_entity_asset_bindings(
        project_id: str,
        request: Request,
        entity_id: str | None = None,
        core_asset_id: str | None = None,
        revision_id: str | None = None,
    ) -> dict[str, Any]:
        """Bidirectional lookup over active entity↔core-asset bindings."""

        _enforce_project_access(auth, request, project_id)
        _require_loop_enabled()
        store.ensure_project_manifest(project_id)
        if entity_id and core_asset_id:
            raise HTTPException(
                status_code=400,
                detail=safe_error_detail(
                    "invalid_binding_query",
                    message="pass entity_id or core_asset_id, not both",
                    project_id=project_id,
                    stage="entity_asset_bindings",
                ),
            )
        if entity_id:
            rows = lookup_asset_id_for_entity(
                store,
                project_id=project_id,
                entity_id=entity_id,
                revision_id=revision_id,
            )
        elif core_asset_id:
            rows = lookup_entity_for_asset_id(
                store,
                project_id=project_id,
                core_asset_id=core_asset_id,
                revision_id=revision_id,
            )
        else:
            rows = [
                row
                for row in load_bindings(store, project_id).bindings
                if row.status == "active"
                and (revision_id is None or row.revision_id == revision_id)
            ]
        return {
            "enabled": True,
            "project_id": project_id,
            "bindings": [row.model_dump(mode="json") for row in rows],
        }

    @app.get("/projects/{project_id}/asset-requirements")
    def get_asset_requirements(
        project_id: str,
        request: Request,
        source_revision_id: str | None = None,
        scope_entity_id: str | None = None,
    ) -> dict[str, Any]:
        """Read-only Scene character asset needs derived from confirmed cast."""

        _enforce_project_access(auth, request, project_id)
        _require_loop_enabled()
        store.ensure_project_manifest(project_id)
        ledger = load_ledger(store, project_id)
        rev = source_revision_id or ledger.current_revision_id
        authoritative = list_current_authoritative(ledger, revision_id=rev)
        rows = project_scene_character_asset_requirements(
            store,
            project_id=project_id,
            authoritative_facts=authoritative,
            revision_id=rev,
        )
        if scope_entity_id:
            rows = [row for row in rows if row.scope_entity_id == scope_entity_id]
        return {
            "enabled": True,
            "project_id": project_id,
            "revision_id": rev,
            "projection": "derived_from_confirmed_scene_cast",
            "asset_kinds_included": ["character"],
            "asset_kinds_omitted": [
                {
                    "asset_kind": "prop",
                    "reason": "SceneProps is draft-only; not in production candidate loop",
                }
            ],
            "requirements": asset_requirements_payload(rows),
        }


__all__ = (
    "CONFIRMATION_LOOP_ENV",
    "RECOVERABLE_GRAPH_FEED_ENV",
    "LEDGER_SCHEMA_VERSION",
    "confirmation_loop_enabled",
    "confirmation_refresh_ready",
    "recoverable_graph_feed_enabled",
    "GraphFeedStatus",
    "FactLedger",
    "load_ledger",
    "save_ledger",
    "open_ledger_from_extraction",
    "accept_candidate",
    "edit_and_confirm_candidate",
    "reject_candidate",
    "list_current_authoritative",
    "resolve_for_downstream",
    "graph_feed_status_rows",
    "inject_raw_junk_candidate",
    "on_script_revision_changed",
    "register_runtime_candidate_confirmation_routes",
)
