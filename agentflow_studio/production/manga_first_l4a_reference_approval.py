from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentflow_studio.production.manga_first_l4a_schema import MangaFirstError, json_digest
from apps.api.runtime_episode_domain_contract import (
    AssetCandidateVersion,
    DeliveryVersion,
    EntityVersionRef,
    ProductionProjectAggregate,
    ReferenceAssetVersion,
    ReferenceSetVersion,
    ReviewDecision,
    SelectedVersion,
    ShotVersion,
    TenantScope,
)
from apps.api.runtime_episode_domain_store import (
    AggregateSaveResult,
    AggregateVersionConflictError,
    EpisodeDomainAggregateStore,
)
from apps.api.runtime_store import RuntimeStore, safe_id


REFERENCE_APPROVED_AT = "2026-07-18T00:01:00+00:00"


class MangaFirstReferenceApprovalError(MangaFirstError):
    pass


@dataclass(frozen=True)
class MangaFirstReferenceApprovalResult:
    aggregate_result: AggregateSaveResult
    reference_approval_gate: dict[str, Any]
    decision_ref: dict[str, Any]


def reference_set_digest(reference_set: ReferenceSetVersion) -> str:
    return json_digest(
        {
            "ref": _ref(reference_set.as_ref()),
            "revision": reference_set.revision,
            "content_digest": reference_set.content_digest,
            "approval_state": reference_set.approval_state,
            "human_confirmed": reference_set.human_confirmed,
            "asset_refs": [_ref(item) for item in reference_set.asset_refs],
        }
    )


def build_reference_approval_gate(aggregate: ProductionProjectAggregate) -> dict[str, Any]:
    current_set = _current_reference_set(aggregate)
    current_assets = _latest_by_entity(aggregate.reference_assets)
    current_shots = _latest_by_entity(aggregate.shots)
    bound_count = sum(1 for shot in current_shots if shot.reference_set_ref == current_set.as_ref())
    confirmed = (
        current_set.approval_state == "approved"
        and current_set.human_confirmed is True
        and bound_count == len(current_shots)
        and all(item.approval_state == "approved" and item.human_confirmed is True for item in current_assets)
    )
    return {
        "schema_version": "afs.manga_first_l4b.reference_approval_gate.v0.1",
        "status": "confirmed" if confirmed else "pending_human",
        "status_label": "参考设定已确认" if confirmed else "参考设定待确认",
        "approval_state": current_set.approval_state,
        "human_confirmed": current_set.human_confirmed,
        "reference_set_ref": _ref(current_set.as_ref()),
        "reference_set_digest": reference_set_digest(current_set),
        "aggregate_version": aggregate.aggregate_version,
        "provider_ready": confirmed,
        "bound_shot_count": bound_count,
        "shot_count": len(current_shots),
        "approval_required_before_provider": not confirmed,
        "non_claims": [
            "not_creative_qa",
            "not_human_final_acceptance",
            "not_business_validation",
        ],
    }


def approve_manga_first_reference_set(
    store: RuntimeStore,
    *,
    scope: TenantScope,
    decision_id: str,
    expected_aggregate_version: int,
    reference_set_digest_value: str,
    idempotency_key: str,
) -> MangaFirstReferenceApprovalResult:
    aggregate_store = EpisodeDomainAggregateStore(store.root)
    current = aggregate_store.load(org_id=scope.org_id, project_id=scope.project_id)
    operation_payload = _approval_payload(
        scope=scope,
        decision_id=decision_id,
        expected_aggregate_version=expected_aggregate_version,
        reference_set_digest_value=reference_set_digest_value,
    )
    operation_digest = json_digest(operation_payload)
    if current.aggregate_version != expected_aggregate_version:
        replay = _existing_approval_result(current, decision_id=decision_id, operation_digest=operation_digest)
        if replay is not None:
            return replay
        raise AggregateVersionConflictError(
            f"aggregate version conflict: expected {expected_aggregate_version}, current {current.aggregate_version}"
        )
    gate = build_reference_approval_gate(current)
    if gate["status"] != "pending_human":
        raise MangaFirstReferenceApprovalError("reference set is already confirmed by a different decision")
    if gate["reference_set_digest"] != reference_set_digest_value:
        raise MangaFirstReferenceApprovalError("reference set digest does not match the current pending version")
    approved = _approved_successor_aggregate(current, scope=scope, decision_id=decision_id, operation_payload=operation_payload)
    save_result = aggregate_store.save(
        approved,
        expected_aggregate_version=expected_aggregate_version,
        idempotency_key=idempotency_key,
        payload_digest=operation_digest,
    )
    return MangaFirstReferenceApprovalResult(
        aggregate_result=save_result,
        reference_approval_gate=build_reference_approval_gate(save_result.aggregate),
        decision_ref=_ref(_approval_decision(save_result.aggregate, decision_id).as_ref()),
    )


def _approved_successor_aggregate(
    aggregate: ProductionProjectAggregate,
    *,
    scope: TenantScope,
    decision_id: str,
    operation_payload: dict[str, Any],
) -> ProductionProjectAggregate:
    current_set = _current_reference_set(aggregate)
    asset_index = {item.as_ref(): item for item in _latest_by_entity(aggregate.reference_assets)}
    current_assets = tuple(asset_index[ref] for ref in current_set.asset_refs)
    approved_assets = tuple(_approve_reference_asset(item) for item in current_assets)
    asset_ref_map = {old.as_ref(): new.as_ref() for old, new in zip(current_assets, approved_assets)}
    approved_set = _approve_reference_set(current_set, asset_ref_map=asset_ref_map)

    current_shots = _latest_by_entity(aggregate.shots)
    shot_ref_map: dict[EntityVersionRef, EntityVersionRef] = {}
    approved_shots: list[ShotVersion] = []
    for shot in current_shots:
        successor = _bind_shot_reference_set(shot, approved_set.as_ref())
        approved_shots.append(successor)
        shot_ref_map[shot.as_ref()] = successor.as_ref()

    candidate_ref_map: dict[EntityVersionRef, EntityVersionRef] = {}
    successor_candidates: list[AssetCandidateVersion] = []
    for candidate in _latest_by_entity(aggregate.asset_candidates):
        target_ref = shot_ref_map.get(candidate.target_ref)
        if target_ref is None:
            continue
        successor = _retarget_candidate(candidate, target_ref)
        successor_candidates.append(successor)
        candidate_ref_map[candidate.as_ref()] = successor.as_ref()

    selection_ref_map: dict[EntityVersionRef, EntityVersionRef] = {}
    successor_selections: list[SelectedVersion] = []
    for selection in _latest_by_entity(aggregate.selections):
        target_ref = shot_ref_map.get(selection.target_ref)
        candidate_ref = candidate_ref_map.get(selection.candidate_ref)
        if target_ref is None or candidate_ref is None:
            continue
        successor = _retarget_selection(selection, target_ref=target_ref, candidate_ref=candidate_ref)
        successor_selections.append(successor)
        selection_ref_map[selection.as_ref()] = successor.as_ref()

    review_ref_map: dict[EntityVersionRef, EntityVersionRef] = {}
    successor_reviews: list[ReviewDecision] = []
    for review in _latest_by_entity(aggregate.review_decisions):
        subject_ref = selection_ref_map.get(review.subject_ref)
        if subject_ref is None:
            continue
        successor = _retarget_review(review, subject_ref)
        successor_reviews.append(successor)
        review_ref_map[review.as_ref()] = successor.as_ref()

    successor_deliveries = tuple(
        _retarget_delivery(item, selection_ref_map=selection_ref_map, review_ref_map=review_ref_map)
        for item in _latest_by_entity(aggregate.deliveries)
        if any(ref in selection_ref_map for ref in item.selection_refs)
    )
    approval_decision = _new_approval_decision(
        scope=scope,
        decision_id=decision_id,
        subject_ref=approved_set.as_ref(),
        operation_payload=operation_payload,
    )
    payload = aggregate.model_dump(mode="python")
    payload.update(
        {
            "aggregate_version": aggregate.aggregate_version + 1,
            "evaluated_at": REFERENCE_APPROVED_AT,
            "reference_assets": (*aggregate.reference_assets, *approved_assets),
            "reference_sets": (*aggregate.reference_sets, approved_set),
            "shots": (*aggregate.shots, *approved_shots),
            "asset_candidates": (*aggregate.asset_candidates, *successor_candidates),
            "selections": (*aggregate.selections, *successor_selections),
            "review_decisions": (*aggregate.review_decisions, *successor_reviews, approval_decision),
            "deliveries": (*aggregate.deliveries, *successor_deliveries),
        }
    )
    return ProductionProjectAggregate.model_validate(payload)


def _approve_reference_asset(item: ReferenceAssetVersion) -> ReferenceAssetVersion:
    return item.model_copy(
        update={
            "version_id": _next_version_id(item),
            "revision": item.revision + 1,
            "parent_version_id": item.version_id,
            "lifecycle_state": "approved",
            "review_state": "approved",
            "approval_state": "approved",
            "human_confirmed": True,
            "created_at": REFERENCE_APPROVED_AT,
        }
    )


def _approve_reference_set(
    item: ReferenceSetVersion,
    *,
    asset_ref_map: dict[EntityVersionRef, EntityVersionRef],
) -> ReferenceSetVersion:
    return item.model_copy(
        update={
            "version_id": _next_version_id(item),
            "revision": item.revision + 1,
            "parent_version_id": item.version_id,
            "lifecycle_state": "approved",
            "review_state": "approved",
            "asset_refs": tuple(asset_ref_map[ref] for ref in item.asset_refs),
            "approval_state": "approved",
            "human_confirmed": True,
            "created_at": REFERENCE_APPROVED_AT,
        }
    )


def _bind_shot_reference_set(item: ShotVersion, reference_set_ref: EntityVersionRef) -> ShotVersion:
    return item.model_copy(
        update={
            "version_id": _next_version_id(item),
            "revision": item.revision + 1,
            "parent_version_id": item.version_id,
            "reference_set_ref": reference_set_ref,
            "created_at": REFERENCE_APPROVED_AT,
        }
    )


def _retarget_candidate(item: AssetCandidateVersion, target_ref: EntityVersionRef) -> AssetCandidateVersion:
    return item.model_copy(
        update={
            "version_id": _next_version_id(item),
            "revision": item.revision + 1,
            "parent_version_id": item.version_id,
            "target_ref": target_ref,
            "created_at": REFERENCE_APPROVED_AT,
        }
    )


def _retarget_selection(
    item: SelectedVersion,
    *,
    target_ref: EntityVersionRef,
    candidate_ref: EntityVersionRef,
) -> SelectedVersion:
    return item.model_copy(
        update={
            "version_id": _next_version_id(item),
            "revision": item.revision + 1,
            "parent_version_id": item.version_id,
            "target_ref": target_ref,
            "candidate_ref": candidate_ref,
            "created_at": REFERENCE_APPROVED_AT,
        }
    )


def _retarget_review(item: ReviewDecision, subject_ref: EntityVersionRef) -> ReviewDecision:
    return item.model_copy(
        update={
            "version_id": _next_version_id(item),
            "revision": item.revision + 1,
            "parent_version_id": item.version_id,
            "subject_ref": subject_ref,
            "created_at": REFERENCE_APPROVED_AT,
        }
    )


def _retarget_delivery(
    item: DeliveryVersion,
    *,
    selection_ref_map: dict[EntityVersionRef, EntityVersionRef],
    review_ref_map: dict[EntityVersionRef, EntityVersionRef],
) -> DeliveryVersion:
    return item.model_copy(
        update={
            "version_id": _next_version_id(item),
            "revision": item.revision + 1,
            "parent_version_id": item.version_id,
            "selection_refs": tuple(selection_ref_map.get(ref, ref) for ref in item.selection_refs),
            "review_decision_refs": tuple(review_ref_map.get(ref, ref) for ref in item.review_decision_refs),
            "created_at": REFERENCE_APPROVED_AT,
        }
    )


def _new_approval_decision(
    *,
    scope: TenantScope,
    decision_id: str,
    subject_ref: EntityVersionRef,
    operation_payload: dict[str, Any],
) -> ReviewDecision:
    return ReviewDecision(
        entity_id=safe_id(decision_id),
        version_id=f"{safe_id(decision_id)}-v1",
        revision=1,
        parent_version_id=None,
        lifecycle_state="approved",
        review_state="approved",
        content_digest=json_digest(operation_payload),
        scope=scope,
        created_at=REFERENCE_APPROVED_AT,
        subject_ref=subject_ref,
        decision="approve",
        note="Owner approved manga-first reference set only; not creative QA, final acceptance, or business validation.",
    )


def _existing_approval_result(
    aggregate: ProductionProjectAggregate,
    *,
    decision_id: str,
    operation_digest: str,
) -> MangaFirstReferenceApprovalResult | None:
    decision = next(
        (
            item
            for item in aggregate.review_decisions
            if item.entity_id == safe_id(decision_id)
            and item.decision == "approve"
            and item.content_digest == operation_digest
        ),
        None,
    )
    if decision is None:
        return None
    aggregate_sha = json_digest(aggregate.model_dump(mode="json"))
    return MangaFirstReferenceApprovalResult(
        aggregate_result=AggregateSaveResult(
            aggregate=aggregate,
            replayed=True,
            aggregate_sha256=aggregate_sha,
        ),
        reference_approval_gate=build_reference_approval_gate(aggregate),
        decision_ref=_ref(decision.as_ref()),
    )


def _approval_decision(aggregate: ProductionProjectAggregate, decision_id: str) -> ReviewDecision:
    return next(item for item in aggregate.review_decisions if item.entity_id == safe_id(decision_id))


def _approval_payload(
    *,
    scope: TenantScope,
    decision_id: str,
    expected_aggregate_version: int,
    reference_set_digest_value: str,
) -> dict[str, Any]:
    return {
        "operation": "manga_first_l4b_reference_set_approval",
        "actor_id": scope.actor_id,
        "project_id": scope.project_id,
        "decision_id": safe_id(decision_id),
        "expected_aggregate_version": expected_aggregate_version,
        "reference_set_digest": reference_set_digest_value,
        "non_claims": [
            "not_creative_qa",
            "not_human_final_acceptance",
            "not_business_validation",
        ],
    }


def _current_reference_set(aggregate: ProductionProjectAggregate) -> ReferenceSetVersion:
    current = _latest_by_entity(aggregate.reference_sets)
    if len(current) != 1:
        raise MangaFirstReferenceApprovalError("manga-first aggregate must expose exactly one current reference set")
    return current[0]


def _latest_by_entity(records: tuple[Any, ...]) -> tuple[Any, ...]:
    latest: dict[str, Any] = {}
    for item in records:
        current = latest.get(item.entity_id)
        if current is None or item.revision > current.revision:
            latest[item.entity_id] = item
    return tuple(sorted(latest.values(), key=lambda item: (item.entity_id, item.version_id)))


def _next_version_id(item: Any) -> str:
    return safe_id(f"{item.entity_id}-v{item.revision + 1}")


def _ref(ref: EntityVersionRef) -> dict[str, str]:
    return {
        "entity_type": ref.entity_type,
        "entity_id": ref.entity_id,
        "version_id": ref.version_id,
    }
