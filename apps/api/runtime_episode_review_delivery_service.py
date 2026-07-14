from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Sequence

from apps.api.runtime_episode_domain_contract import (
    AssetCandidateVersion,
    DeliveryVersion,
    EntityVersionRef,
    ProductionProjectAggregate,
    ReviewDecision,
    SafeArtifactRef,
    SelectedVersion,
    TenantScope,
)


class EpisodeReviewDeliveryError(RuntimeError):
    """Base error for deterministic review, version, and delivery operations."""


class ReviewDeliveryScopeError(EpisodeReviewDeliveryError):
    pass


class ReviewDeliveryVersionConflictError(EpisodeReviewDeliveryError):
    pass


class ReviewDeliveryReferenceError(EpisodeReviewDeliveryError):
    pass


class ReviewDeliveryStateError(EpisodeReviewDeliveryError):
    pass


class DeliveryNotReadyError(EpisodeReviewDeliveryError):
    def __init__(self, readiness: "DeliveryReadiness") -> None:
        self.readiness = readiness
        super().__init__("delivery is not ready: " + ", ".join(readiness.blockers))


@dataclass(frozen=True)
class CandidateComparison:
    target_ref: EntityVersionRef
    candidates: tuple[AssetCandidateVersion, ...]


@dataclass(frozen=True)
class DeliveryReadiness:
    ready: bool
    episode_ref: EntityVersionRef
    selection_refs: tuple[EntityVersionRef, ...]
    missing_inventory_count: int
    blockers: tuple[str, ...]
    preview_artifact_ref: SafeArtifactRef | None
    export_artifact_refs: tuple[SafeArtifactRef, ...]


def compare_candidate_versions(
    aggregate: ProductionProjectAggregate,
    *,
    scope: TenantScope,
    target_ref: EntityVersionRef,
    candidate_refs: Sequence[EntityVersionRef] | None = None,
) -> CandidateComparison:
    """Return exact candidate versions for one exact target, oldest first."""

    _require_scope(aggregate, scope)
    _require_target(aggregate, target_ref)
    if candidate_refs is None:
        candidates = tuple(
            candidate
            for candidate in aggregate.asset_candidates
            if candidate.target_ref == target_ref
        )
    else:
        if len(candidate_refs) != len(set(candidate_refs)):
            raise ReviewDeliveryReferenceError("candidate comparison refs must be unique")
        candidates = tuple(_candidate(aggregate, ref) for ref in candidate_refs)
        if any(candidate.target_ref != target_ref for candidate in candidates):
            raise ReviewDeliveryReferenceError(
                "candidate comparison cannot cross an exact target"
            )
    return CandidateComparison(
        target_ref=target_ref,
        candidates=tuple(sorted(candidates, key=lambda item: (item.revision, item.version_id))),
    )


def select_candidate(
    aggregate: ProductionProjectAggregate,
    *,
    scope: TenantScope,
    expected_aggregate_version: int,
    candidate_ref: EntityVersionRef,
    purpose: Literal[
        "storyboard",
        "image",
        "video",
        "audio",
        "character_reference",
        "scene_reference",
        "prop_reference",
        "voice_reference",
        "style_reference",
    ],
    selection_entity_id: str,
    selection_version_id: str,
    created_at: str,
) -> ProductionProjectAggregate:
    _require_mutation(aggregate, scope, expected_aggregate_version)
    candidate = _candidate(aggregate, candidate_ref)
    _require_selectable_candidate(candidate)
    if any(item.entity_id == selection_entity_id for item in aggregate.selections):
        raise ReviewDeliveryStateError(
            "new candidate selection requires a new selection entity; use restore for history"
        )
    selection = SelectedVersion(
        entity_id=selection_entity_id,
        version_id=selection_version_id,
        revision=1,
        lifecycle_state="candidate",
        review_state="needs_review",
        content_digest=_selection_digest(candidate.target_ref, purpose, candidate.as_ref()),
        scope=scope,
        created_at=created_at,
        target_ref=candidate.target_ref,
        purpose=purpose,
        candidate_ref=candidate.as_ref(),
    )
    return _append(aggregate, evaluated_at=created_at, selections=(selection,))


def review_selection(
    aggregate: ProductionProjectAggregate,
    *,
    scope: TenantScope,
    expected_aggregate_version: int,
    selection_ref: EntityVersionRef,
    decision: Literal["approve", "reject"],
    selection_version_id: str,
    decision_entity_id: str,
    decision_version_id: str,
    created_at: str,
    note: str = "",
) -> ProductionProjectAggregate:
    _require_mutation(aggregate, scope, expected_aggregate_version)
    current = _latest_exact_selection(aggregate, selection_ref)
    if current.lifecycle_state not in ("candidate", "approved"):
        raise ReviewDeliveryStateError("only a candidate or unlocked selection can be reviewed")
    if current.lifecycle_state == "approved" and decision == "reject":
        raise ReviewDeliveryStateError("approved selection cannot transition directly to rejected")
    if decision == "approve":
        _require_approved_candidate(_candidate(aggregate, current.candidate_ref))
        lifecycle_state = "approved"
        review_state = "approved"
    else:
        lifecycle_state = "rejected"
        review_state = "rejected"
    reviewed = current.model_copy(
        update={
            "version_id": selection_version_id,
            "revision": current.revision + 1,
            "parent_version_id": current.version_id,
            "lifecycle_state": lifecycle_state,
            "review_state": review_state,
            "created_at": created_at,
        }
    )
    review = _decision(
        scope=scope,
        entity_id=decision_entity_id,
        version_id=decision_version_id,
        subject_ref=reviewed.as_ref(),
        decision=decision,
        created_at=created_at,
        note=note,
    )
    return _append(
        aggregate,
        evaluated_at=created_at,
        selections=(reviewed,),
        review_decisions=(review,),
    )


def lock_selection(
    aggregate: ProductionProjectAggregate,
    *,
    scope: TenantScope,
    expected_aggregate_version: int,
    selection_ref: EntityVersionRef,
    selection_version_id: str,
    decision_entity_id: str,
    decision_version_id: str,
    created_at: str,
    note: str = "",
) -> ProductionProjectAggregate:
    _require_mutation(aggregate, scope, expected_aggregate_version)
    current = _latest_exact_selection(aggregate, selection_ref)
    if current.lifecycle_state != "approved" or current.review_state != "approved":
        raise ReviewDeliveryStateError("only an approved selection can be locked")
    if not _has_valid_approval(aggregate, current):
        raise ReviewDeliveryStateError("selection lock requires an exact approval decision")
    _require_approved_candidate(_candidate(aggregate, current.candidate_ref))
    locked = current.model_copy(
        update={
            "version_id": selection_version_id,
            "revision": current.revision + 1,
            "parent_version_id": current.version_id,
            "lifecycle_state": "locked",
            "created_at": created_at,
        }
    )
    exact_approval = _decision(
        scope=scope,
        entity_id=decision_entity_id,
        version_id=decision_version_id,
        subject_ref=locked.as_ref(),
        decision="approve",
        created_at=created_at,
        note=note,
    )
    return _append(
        aggregate,
        evaluated_at=created_at,
        selections=(locked,),
        review_decisions=(exact_approval,),
    )


def unlock_selection(
    aggregate: ProductionProjectAggregate,
    *,
    scope: TenantScope,
    expected_aggregate_version: int,
    selection_ref: EntityVersionRef,
    selection_version_id: str,
    decision_entity_id: str,
    decision_version_id: str,
    created_at: str,
    note: str = "",
) -> ProductionProjectAggregate:
    _require_mutation(aggregate, scope, expected_aggregate_version)
    current = _latest_exact_selection(aggregate, selection_ref)
    if current.lifecycle_state != "locked":
        raise ReviewDeliveryStateError("only the latest locked selection can be unlocked")
    unlock = _decision(
        scope=scope,
        entity_id=decision_entity_id,
        version_id=decision_version_id,
        subject_ref=current.as_ref(),
        decision="unlock",
        created_at=created_at,
        note=note,
    )
    unlocked = current.model_copy(
        update={
            "version_id": selection_version_id,
            "revision": current.revision + 1,
            "parent_version_id": current.version_id,
            "lifecycle_state": "approved",
            "created_at": created_at,
        }
    )
    return _append(
        aggregate,
        evaluated_at=created_at,
        selections=(unlocked,),
        review_decisions=(unlock,),
    )


def restore_selection(
    aggregate: ProductionProjectAggregate,
    *,
    scope: TenantScope,
    expected_aggregate_version: int,
    selection_ref: EntityVersionRef,
    historical_candidate_ref: EntityVersionRef,
    selection_version_id: str,
    created_at: str,
) -> ProductionProjectAggregate:
    _require_mutation(aggregate, scope, expected_aggregate_version)
    current = _latest_exact_selection(aggregate, selection_ref)
    if current.lifecycle_state == "locked":
        raise ReviewDeliveryStateError("locked selection must be explicitly unlocked before restore")
    if current.lifecycle_state == "retired":
        raise ReviewDeliveryStateError("retired selection cannot be restored")
    candidate = _candidate(aggregate, historical_candidate_ref)
    _require_selectable_candidate(candidate)
    if candidate.target_ref != current.target_ref:
        raise ReviewDeliveryReferenceError("restore candidate must belong to the exact selection target")
    restored = current.model_copy(
        update={
            "version_id": selection_version_id,
            "revision": current.revision + 1,
            "parent_version_id": current.version_id,
            "lifecycle_state": "candidate",
            "review_state": "needs_review",
            "content_digest": _selection_digest(
                current.target_ref,
                current.purpose,
                candidate.as_ref(),
            ),
            "candidate_ref": candidate.as_ref(),
            "created_at": created_at,
        }
    )
    return _append(aggregate, evaluated_at=created_at, selections=(restored,))


def assess_delivery_readiness(
    aggregate: ProductionProjectAggregate,
    *,
    scope: TenantScope,
    episode_ref: EntityVersionRef,
    selection_refs: Sequence[EntityVersionRef],
    missing_inventory_count: int,
    preview_artifact_ref: SafeArtifactRef | None,
    export_artifact_refs: Sequence[SafeArtifactRef] = (),
) -> DeliveryReadiness:
    _require_scope(aggregate, scope)
    episode = _entity(aggregate, episode_ref, "episode")
    if missing_inventory_count < 0:
        raise ReviewDeliveryStateError("missing inventory count cannot be negative")
    if len(selection_refs) != len(set(selection_refs)):
        raise ReviewDeliveryReferenceError("delivery selection refs must be unique")
    selections = tuple(_selection(aggregate, ref) for ref in selection_refs)
    safe_preview = _safe_artifact(preview_artifact_ref) if preview_artifact_ref is not None else None
    safe_exports = tuple(_safe_artifact(ref) for ref in export_artifact_refs)
    blockers: list[str] = []
    if not _is_latest(aggregate.episodes, episode.entity_id, episode.version_id):
        blockers.append(f"episode_not_latest:{episode.entity_id}:{episode.version_id}")
    if missing_inventory_count:
        blockers.append(f"missing_inventory:{missing_inventory_count}")
    if safe_preview is None:
        blockers.append("playable_preview_missing")
    elif safe_preview.artifact_type != "video":
        blockers.append("playable_preview_type_invalid")

    episode_scenes = {
        scene.as_ref()
        for scene in aggregate.scenes
        if scene.episode_ref == episode.as_ref()
        and _is_latest(aggregate.scenes, scene.entity_id, scene.version_id)
    }
    episode_shots = tuple(
        shot for shot in aggregate.shots if shot.scene_ref in episode_scenes
    )
    latest_shots = tuple(
        shot
        for shot in episode_shots
        if _is_latest(aggregate.shots, shot.entity_id, shot.version_id)
    )
    if not selections:
        blockers.append("delivery_selections_missing")
    if not latest_shots:
        blockers.append("episode_shots_missing")
    selection_targets = {selection.target_ref for selection in selections}
    episode_target_refs = {
        *(shot.as_ref() for shot in latest_shots),
        *(ref for shot in latest_shots for ref in shot.continuity_refs),
    }
    for shot in latest_shots:
        if shot.as_ref() not in selection_targets:
            blockers.append(f"shot_selection_missing:{shot.entity_id}:{shot.version_id}")
        for continuity_ref in shot.continuity_refs:
            continuity = _entity(aggregate, continuity_ref, "continuity_state")
            if not _is_latest(
                aggregate.continuity_states,
                continuity.entity_id,
                continuity.version_id,
            ):
                blockers.append(
                    f"continuity_not_latest:{continuity.entity_id}:{continuity.version_id}"
                )
            continuity_selections = tuple(
                selection
                for selection in selections
                if selection.target_ref == continuity.as_ref()
            )
            if not continuity_selections:
                blockers.append(
                    f"continuity_selection_missing:{continuity.entity_id}:{continuity.version_id}"
                )
            elif not any(
                selection.as_ref() in continuity.approved_asset_selection_refs
                for selection in continuity_selections
            ):
                blockers.append(
                    f"continuity_exact_ref_open:{continuity.entity_id}:{continuity.version_id}"
                )

    for selection in selections:
        if selection.target_ref not in episode_target_refs:
            blockers.append(
                f"selection_outside_episode:{selection.entity_id}:{selection.version_id}"
            )
        if not _is_latest(aggregate.selections, selection.entity_id, selection.version_id):
            blockers.append(f"selection_not_latest:{selection.entity_id}:{selection.version_id}")
        if selection.lifecycle_state != "locked" or selection.review_state != "approved":
            blockers.append(f"selection_not_locked:{selection.entity_id}:{selection.version_id}")
        if not _has_valid_approval(aggregate, selection):
            blockers.append(f"selection_approval_missing:{selection.entity_id}:{selection.version_id}")
        candidate = _candidate(aggregate, selection.candidate_ref)
        try:
            _require_approved_candidate(candidate)
        except ReviewDeliveryStateError:
            blockers.append(f"candidate_not_approved:{candidate.entity_id}:{candidate.version_id}")

    return DeliveryReadiness(
        ready=not blockers,
        episode_ref=episode.as_ref(),
        selection_refs=tuple(selection.as_ref() for selection in selections),
        missing_inventory_count=missing_inventory_count,
        blockers=tuple(dict.fromkeys(blockers)),
        preview_artifact_ref=safe_preview,
        export_artifact_refs=safe_exports,
    )


def freeze_delivery(
    aggregate: ProductionProjectAggregate,
    *,
    scope: TenantScope,
    expected_aggregate_version: int,
    episode_ref: EntityVersionRef,
    selection_refs: Sequence[EntityVersionRef],
    missing_inventory_count: int,
    preview_artifact_ref: SafeArtifactRef | None,
    export_artifact_refs: Sequence[SafeArtifactRef],
    delivery_entity_id: str,
    delivery_version_id: str,
    created_at: str,
) -> ProductionProjectAggregate:
    _require_mutation(aggregate, scope, expected_aggregate_version)
    readiness = assess_delivery_readiness(
        aggregate,
        scope=scope,
        episode_ref=episode_ref,
        selection_refs=selection_refs,
        missing_inventory_count=missing_inventory_count,
        preview_artifact_ref=preview_artifact_ref,
        export_artifact_refs=export_artifact_refs,
    )
    if not readiness.ready:
        raise DeliveryNotReadyError(readiness)
    selections = tuple(_selection(aggregate, ref) for ref in readiness.selection_refs)
    exact_approvals = tuple(
        _latest_valid_approval(aggregate, selection).as_ref() for selection in selections
    )
    if any(item.entity_id == delivery_entity_id for item in aggregate.deliveries):
        raise ReviewDeliveryStateError("frozen delivery requires a new delivery entity id")
    delivery = DeliveryVersion(
        entity_id=delivery_entity_id,
        version_id=delivery_version_id,
        revision=1,
        lifecycle_state="locked",
        review_state="approved",
        content_digest=_delivery_digest(
            readiness.episode_ref,
            readiness.selection_refs,
            exact_approvals,
            readiness.preview_artifact_ref,
            readiness.export_artifact_refs,
        ),
        scope=scope,
        created_at=created_at,
        episode_ref=readiness.episode_ref,
        selection_refs=readiness.selection_refs,
        review_decision_refs=exact_approvals,
        preview_artifact_ref=readiness.preview_artifact_ref,
        export_artifact_refs=readiness.export_artifact_refs,
    )
    return _append(aggregate, evaluated_at=created_at, deliveries=(delivery,))


def unlock_delivery(
    aggregate: ProductionProjectAggregate,
    *,
    scope: TenantScope,
    expected_aggregate_version: int,
    delivery_ref: EntityVersionRef,
    delivery_version_id: str,
    decision_entity_id: str,
    decision_version_id: str,
    created_at: str,
    note: str = "",
) -> ProductionProjectAggregate:
    _require_mutation(aggregate, scope, expected_aggregate_version)
    current = _latest_exact_delivery(aggregate, delivery_ref)
    if current.lifecycle_state != "locked":
        raise ReviewDeliveryStateError("only the latest locked delivery can be unlocked")
    unlock = _decision(
        scope=scope,
        entity_id=decision_entity_id,
        version_id=decision_version_id,
        subject_ref=current.as_ref(),
        decision="unlock",
        created_at=created_at,
        note=note,
    )
    unlocked = current.model_copy(
        update={
            "version_id": delivery_version_id,
            "revision": current.revision + 1,
            "parent_version_id": current.version_id,
            "lifecycle_state": "approved",
            "created_at": created_at,
        }
    )
    return _append(
        aggregate,
        evaluated_at=created_at,
        deliveries=(unlocked,),
        review_decisions=(unlock,),
    )


def _require_mutation(
    aggregate: ProductionProjectAggregate,
    scope: TenantScope,
    expected_aggregate_version: int,
) -> None:
    _require_scope(aggregate, scope)
    if expected_aggregate_version != aggregate.aggregate_version:
        raise ReviewDeliveryVersionConflictError(
            f"aggregate version conflict: expected {expected_aggregate_version}, "
            f"current {aggregate.aggregate_version}"
        )


def _require_scope(aggregate: ProductionProjectAggregate, scope: TenantScope) -> None:
    if scope != aggregate.scope:
        raise ReviewDeliveryScopeError(
            "review and delivery operation scope must exactly match org, project, and actor"
        )


def _records(aggregate: ProductionProjectAggregate):
    return aggregate._records()


def _entity(
    aggregate: ProductionProjectAggregate,
    ref: EntityVersionRef,
    expected_type: str | None = None,
):
    if expected_type is not None and ref.entity_type != expected_type:
        raise ReviewDeliveryReferenceError(f"reference must target {expected_type}")
    for record in _records(aggregate):
        if record.as_ref() == ref:
            return record
    raise ReviewDeliveryReferenceError("exact entity version reference was not found")


def _require_target(aggregate: ProductionProjectAggregate, ref: EntityVersionRef) -> None:
    if ref.entity_type not in ("shot", "continuity_state"):
        raise ReviewDeliveryReferenceError("candidate target must be a shot or continuity state")
    _entity(aggregate, ref, ref.entity_type)


def _candidate(
    aggregate: ProductionProjectAggregate,
    ref: EntityVersionRef,
) -> AssetCandidateVersion:
    item = _entity(aggregate, ref, "asset_candidate")
    if not isinstance(item, AssetCandidateVersion):
        raise ReviewDeliveryReferenceError("reference is not an asset candidate")
    return item


def _selection(
    aggregate: ProductionProjectAggregate,
    ref: EntityVersionRef,
) -> SelectedVersion:
    item = _entity(aggregate, ref, "selected_version")
    if not isinstance(item, SelectedVersion):
        raise ReviewDeliveryReferenceError("reference is not a selected version")
    return item


def _delivery(
    aggregate: ProductionProjectAggregate,
    ref: EntityVersionRef,
) -> DeliveryVersion:
    item = _entity(aggregate, ref, "delivery_version")
    if not isinstance(item, DeliveryVersion):
        raise ReviewDeliveryReferenceError("reference is not a delivery version")
    return item


def _latest_exact_selection(
    aggregate: ProductionProjectAggregate,
    ref: EntityVersionRef,
) -> SelectedVersion:
    item = _selection(aggregate, ref)
    if not _is_latest(aggregate.selections, item.entity_id, item.version_id):
        raise ReviewDeliveryVersionConflictError("selection ref is not the latest exact version")
    return item


def _latest_exact_delivery(
    aggregate: ProductionProjectAggregate,
    ref: EntityVersionRef,
) -> DeliveryVersion:
    item = _delivery(aggregate, ref)
    if not _is_latest(aggregate.deliveries, item.entity_id, item.version_id):
        raise ReviewDeliveryVersionConflictError("delivery ref is not the latest exact version")
    return item


def _is_latest(records, entity_id: str, version_id: str) -> bool:
    history = tuple(item for item in records if item.entity_id == entity_id)
    return bool(history) and max(history, key=lambda item: item.revision).version_id == version_id


def _require_selectable_candidate(candidate: AssetCandidateVersion) -> None:
    if candidate.job_state in ("queued", "running", "paused", "failed", "cancelled"):
        raise ReviewDeliveryStateError(
            f"candidate job in {candidate.job_state} state cannot be selected"
        )
    if candidate.artifact_ref is None:
        raise ReviewDeliveryStateError("candidate without a safe artifact cannot be selected")
    if candidate.lifecycle_state in ("rejected", "retired"):
        raise ReviewDeliveryStateError("rejected or retired candidate cannot be selected")


def _require_approved_candidate(candidate: AssetCandidateVersion) -> None:
    _require_selectable_candidate(candidate)
    if candidate.lifecycle_state not in ("approved", "locked") or candidate.review_state != "approved":
        raise ReviewDeliveryStateError("selection requires an approved exact candidate version")


def _has_valid_approval(
    aggregate: ProductionProjectAggregate,
    selection: SelectedVersion,
) -> bool:
    return any(
        decision.subject_ref == selection.as_ref()
        and decision.decision == "approve"
        and decision.lifecycle_state in ("approved", "locked")
        and decision.review_state == "approved"
        and datetime.fromisoformat(decision.created_at)
        >= datetime.fromisoformat(selection.created_at)
        and datetime.fromisoformat(decision.created_at)
        <= datetime.fromisoformat(aggregate.evaluated_at)
        for decision in aggregate.review_decisions
    )


def _latest_valid_approval(
    aggregate: ProductionProjectAggregate,
    selection: SelectedVersion,
) -> ReviewDecision:
    decisions = tuple(
        decision
        for decision in aggregate.review_decisions
        if decision.subject_ref == selection.as_ref()
        and decision.decision == "approve"
        and decision.lifecycle_state in ("approved", "locked")
        and decision.review_state == "approved"
        and datetime.fromisoformat(decision.created_at)
        >= datetime.fromisoformat(selection.created_at)
        and datetime.fromisoformat(decision.created_at)
        <= datetime.fromisoformat(aggregate.evaluated_at)
    )
    if not decisions:
        raise ReviewDeliveryStateError("selection has no exact approval decision")
    return max(
        decisions,
        key=lambda item: (
            datetime.fromisoformat(item.created_at),
            item.revision,
            item.version_id,
        ),
    )


def _decision(
    *,
    scope: TenantScope,
    entity_id: str,
    version_id: str,
    subject_ref: EntityVersionRef,
    decision: Literal["approve", "reject", "unlock"],
    created_at: str,
    note: str,
) -> ReviewDecision:
    return ReviewDecision(
        entity_id=entity_id,
        version_id=version_id,
        revision=1,
        lifecycle_state="approved",
        review_state="approved",
        content_digest=_digest(
            {
                "subject_ref": subject_ref.model_dump(mode="json"),
                "decision": decision,
                "note": note,
            }
        ),
        scope=scope,
        created_at=created_at,
        subject_ref=subject_ref,
        decision=decision,
        note=note,
    )


def _append(
    aggregate: ProductionProjectAggregate,
    *,
    evaluated_at: str,
    selections: tuple[SelectedVersion, ...] = (),
    review_decisions: tuple[ReviewDecision, ...] = (),
    deliveries: tuple[DeliveryVersion, ...] = (),
) -> ProductionProjectAggregate:
    payload = aggregate.model_dump(mode="python")
    payload.update(
        {
            "aggregate_version": aggregate.aggregate_version + 1,
            "evaluated_at": evaluated_at,
            "selections": (*aggregate.selections, *selections),
            "review_decisions": (*aggregate.review_decisions, *review_decisions),
            "deliveries": (*aggregate.deliveries, *deliveries),
        }
    )
    return ProductionProjectAggregate.model_validate(payload)


def _safe_artifact(value: SafeArtifactRef) -> SafeArtifactRef:
    return SafeArtifactRef.model_validate(value)


def _selection_digest(
    target_ref: EntityVersionRef,
    purpose: str,
    candidate_ref: EntityVersionRef,
) -> str:
    return _digest(
        {
            "target_ref": target_ref.model_dump(mode="json"),
            "purpose": purpose,
            "candidate_ref": candidate_ref.model_dump(mode="json"),
        }
    )


def _delivery_digest(
    episode_ref: EntityVersionRef,
    selection_refs: Sequence[EntityVersionRef],
    review_decision_refs: Sequence[EntityVersionRef],
    preview_artifact_ref: SafeArtifactRef | None,
    export_artifact_refs: Sequence[SafeArtifactRef],
) -> str:
    return _digest(
        {
            "episode_ref": episode_ref.model_dump(mode="json"),
            "selection_refs": [item.model_dump(mode="json") for item in selection_refs],
            "review_decision_refs": [
                item.model_dump(mode="json") for item in review_decision_refs
            ],
            "preview_artifact_ref": (
                preview_artifact_ref.model_dump(mode="json")
                if preview_artifact_ref is not None
                else None
            ),
            "export_artifact_refs": [
                item.model_dump(mode="json") for item in export_artifact_refs
            ],
        }
    )


def _digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = (
    "CandidateComparison",
    "DeliveryNotReadyError",
    "DeliveryReadiness",
    "EpisodeReviewDeliveryError",
    "ReviewDeliveryReferenceError",
    "ReviewDeliveryScopeError",
    "ReviewDeliveryStateError",
    "ReviewDeliveryVersionConflictError",
    "assess_delivery_readiness",
    "compare_candidate_versions",
    "freeze_delivery",
    "lock_selection",
    "restore_selection",
    "review_selection",
    "select_candidate",
    "unlock_delivery",
    "unlock_selection",
)
