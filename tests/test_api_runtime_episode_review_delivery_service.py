from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from apps.api.runtime_episode_domain_contract import (
    AssetCandidateVersion,
    ContinuityStateVersion,
    EntityVersionRef,
    EpisodeVersion,
    ProductionProjectAggregate,
    ProjectVersion,
    ReviewDecision,
    SafeArtifactRef,
    SceneVersion,
    SeriesVersion,
    ShotVersion,
    TenantScope,
)
from apps.api.runtime_episode_review_delivery_service import (
    DeliveryNotReadyError,
    ReviewDeliveryReferenceError,
    ReviewDeliveryScopeError,
    ReviewDeliveryStateError,
    ReviewDeliveryVersionConflictError,
    assess_delivery_readiness,
    compare_candidate_versions,
    freeze_delivery,
    lock_selection,
    restore_selection,
    review_selection,
    select_candidate,
    unlock_delivery,
    unlock_selection,
)


SCOPE = TenantScope(org_id="small-studio", project_id="rainlight", actor_id="creator-1")
TIMES = tuple(f"2026-07-15T08:{minute:02d}:00+00:00" for minute in range(30))


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _ref(item) -> EntityVersionRef:
    return item.as_ref()


def _fact(
    entity_id: str,
    *,
    created_at: str = TIMES[0],
    lifecycle_state: str = "approved",
    review_state: str = "approved",
) -> dict:
    return {
        "entity_id": entity_id,
        "version_id": f"{entity_id}.v1",
        "revision": 1,
        "lifecycle_state": lifecycle_state,
        "review_state": review_state,
        "content_digest": _digest(entity_id),
        "scope": SCOPE,
        "created_at": created_at,
    }


def _aggregate() -> ProductionProjectAggregate:
    project = ProjectVersion(**_fact(SCOPE.project_id), title="Rainlight")
    series = SeriesVersion(**_fact("series-1"), project_ref=_ref(project), title="Series")
    episode = EpisodeVersion(**_fact("episode-1"), series_ref=_ref(series), title="Episode")
    scene = SceneVersion(
        **_fact("scene-1"), episode_ref=_ref(episode), sequence=1, title="Archive Tower"
    )
    shot = ShotVersion(
        **_fact("shot-1"), scene_ref=_ref(scene), sequence=1, duration_seconds=9
    )
    continuity = ContinuityStateVersion(
        **_fact("character-lin"),
        subject_type="character",
        subject_id="lin",
    )
    candidate_v1 = AssetCandidateVersion(
        **_fact("candidate-shot-1", created_at=TIMES[1]),
        target_ref=_ref(shot),
        artifact_ref=_artifact("artifact-shot-v1"),
    )
    candidate_v2 = candidate_v1.model_copy(
        update={
            "version_id": "candidate-shot-1.v2",
            "revision": 2,
            "parent_version_id": candidate_v1.version_id,
            "content_digest": _digest("candidate-shot-v2"),
            "artifact_ref": _artifact("artifact-shot-v2"),
            "created_at": TIMES[2],
        }
    )
    candidate_v2_approval = ReviewDecision(
        **_fact("review-candidate-v2", created_at=TIMES[2]),
        subject_ref=_ref(candidate_v2),
        decision="approve",
    )
    continuity_candidate = AssetCandidateVersion(
        **_fact("candidate-character", created_at=TIMES[1]),
        target_ref=_ref(continuity),
        artifact_ref=_artifact("artifact-character"),
    )
    return ProductionProjectAggregate(
        aggregate_version=1,
        evaluated_at=TIMES[3],
        scope=SCOPE,
        projects=(project,),
        series=(series,),
        episodes=(episode,),
        scenes=(scene,),
        shots=(shot,),
        continuity_states=(continuity,),
        asset_candidates=(candidate_v1, candidate_v2, continuity_candidate),
        review_decisions=(candidate_v2_approval,),
    )


def _artifact(name: str, artifact_type: str = "image") -> SafeArtifactRef:
    return SafeArtifactRef(
        artifact_id=name,
        artifact_type=artifact_type,
        content_digest=_digest(name),
    )


def _selected_v2(aggregate: ProductionProjectAggregate) -> ProductionProjectAggregate:
    return select_candidate(
        aggregate,
        scope=SCOPE,
        expected_aggregate_version=aggregate.aggregate_version,
        candidate_ref=_ref(aggregate.asset_candidates[1]),
        purpose="storyboard",
        selection_entity_id="selection-shot-1",
        selection_version_id="selection-shot-1.v1",
        created_at=TIMES[4],
    )


def _approved(aggregate: ProductionProjectAggregate) -> ProductionProjectAggregate:
    return review_selection(
        aggregate,
        scope=SCOPE,
        expected_aggregate_version=aggregate.aggregate_version,
        selection_ref=_ref(aggregate.selections[-1]),
        decision="approve",
        selection_version_id="selection-shot-1.v2",
        decision_entity_id="review-selection-v2",
        decision_version_id="review-selection-v2.v1",
        created_at=TIMES[5],
    )


def _locked(aggregate: ProductionProjectAggregate) -> ProductionProjectAggregate:
    return lock_selection(
        aggregate,
        scope=SCOPE,
        expected_aggregate_version=aggregate.aggregate_version,
        selection_ref=_ref(aggregate.selections[-1]),
        selection_version_id="selection-shot-1.v3",
        decision_entity_id="lock-selection-v3",
        decision_version_id="lock-selection-v3.v1",
        created_at=TIMES[6],
    )


def _frozen(aggregate: ProductionProjectAggregate) -> ProductionProjectAggregate:
    return freeze_delivery(
        aggregate,
        scope=SCOPE,
        expected_aggregate_version=aggregate.aggregate_version,
        episode_ref=_ref(aggregate.episodes[0]),
        selection_refs=(_ref(aggregate.selections[-1]),),
        missing_inventory_count=0,
        preview_artifact_ref=_artifact("preview-episode", "video"),
        export_artifact_refs=(_artifact("export-episode", "video"),),
        delivery_entity_id="delivery-episode-1",
        delivery_version_id="delivery-episode-1.v1",
        created_at=TIMES[7],
    )


def test_compare_v1_v2_and_reject_cross_target_versions() -> None:
    aggregate = _aggregate()
    comparison = compare_candidate_versions(
        aggregate,
        scope=SCOPE,
        target_ref=_ref(aggregate.shots[0]),
        candidate_refs=(_ref(aggregate.asset_candidates[1]), _ref(aggregate.asset_candidates[0])),
    )

    assert [item.version_id for item in comparison.candidates] == [
        "candidate-shot-1.v1",
        "candidate-shot-1.v2",
    ]
    with pytest.raises(ReviewDeliveryReferenceError, match="cannot cross"):
        compare_candidate_versions(
            aggregate,
            scope=SCOPE,
            target_ref=_ref(aggregate.shots[0]),
            candidate_refs=(
                _ref(aggregate.asset_candidates[0]),
                _ref(aggregate.asset_candidates[2]),
            ),
        )


def test_select_v2_approve_lock_and_freeze_append_exact_history() -> None:
    original = _aggregate()
    selected = _selected_v2(original)
    approved = _approved(selected)
    locked = _locked(approved)
    frozen = _frozen(locked)

    assert original.selections == ()
    assert [item.lifecycle_state for item in frozen.selections] == [
        "candidate",
        "approved",
        "locked",
    ]
    assert frozen.selections[-1].candidate_ref == _ref(original.asset_candidates[1])
    assert frozen.deliveries[-1].selection_refs == (_ref(frozen.selections[-1]),)
    assert frozen.deliveries[-1].preview_artifact_ref == _artifact("preview-episode", "video")
    assert frozen.deliveries[-1].export_artifact_refs == (
        _artifact("export-episode", "video"),
    )
    assert frozen.aggregate_version == 5
    assert ProductionProjectAggregate.model_validate(frozen.model_dump()) == frozen


def test_reject_appends_history_without_deleting_candidate_or_selection() -> None:
    selected = _selected_v2(_aggregate())
    rejected = review_selection(
        selected,
        scope=SCOPE,
        expected_aggregate_version=selected.aggregate_version,
        selection_ref=_ref(selected.selections[-1]),
        decision="reject",
        selection_version_id="selection-shot-1.v2",
        decision_entity_id="reject-selection-v2",
        decision_version_id="reject-selection-v2.v1",
        created_at=TIMES[5],
        note="continuity mismatch",
    )

    assert len(rejected.asset_candidates) == 3
    assert [item.lifecycle_state for item in rejected.selections] == ["candidate", "rejected"]
    assert rejected.review_decisions[-1].decision == "reject"
    assert rejected.review_decisions[-1].subject_ref == _ref(rejected.selections[-1])


def test_unlock_appends_decision_and_makes_old_lock_stale() -> None:
    locked = _locked(_approved(_selected_v2(_aggregate())))
    unlocked = unlock_selection(
        locked,
        scope=SCOPE,
        expected_aggregate_version=locked.aggregate_version,
        selection_ref=_ref(locked.selections[-1]),
        selection_version_id="selection-shot-1.v4",
        decision_entity_id="unlock-selection-v3",
        decision_version_id="unlock-selection-v3.v1",
        created_at=TIMES[7],
    )

    assert unlocked.selections[-2].lifecycle_state == "locked"
    assert unlocked.selections[-1].lifecycle_state == "approved"
    assert unlocked.review_decisions[-1].decision == "unlock"
    readiness = assess_delivery_readiness(
        unlocked,
        scope=SCOPE,
        episode_ref=_ref(unlocked.episodes[0]),
        selection_refs=(_ref(unlocked.selections[-2]),),
        missing_inventory_count=0,
        preview_artifact_ref=_artifact("preview-episode", "video"),
    )
    assert "selection_not_latest:selection-shot-1:selection-shot-1.v3" in readiness.blockers


def test_restore_v1_creates_new_selection_version_and_requires_new_exact_review() -> None:
    approved = _approved(_selected_v2(_aggregate()))
    restored = restore_selection(
        approved,
        scope=SCOPE,
        expected_aggregate_version=approved.aggregate_version,
        selection_ref=_ref(approved.selections[-1]),
        historical_candidate_ref=_ref(approved.asset_candidates[0]),
        selection_version_id="selection-shot-1.v3",
        created_at=TIMES[6],
    )

    assert restored.selections[-1].candidate_ref.version_id == "candidate-shot-1.v1"
    assert restored.selections[-1].lifecycle_state == "candidate"
    assert restored.selections[-1].review_state == "needs_review"
    readiness = assess_delivery_readiness(
        restored,
        scope=SCOPE,
        episode_ref=_ref(restored.episodes[0]),
        selection_refs=(_ref(restored.selections[-1]),),
        missing_inventory_count=0,
        preview_artifact_ref=_artifact("preview-episode", "video"),
    )
    assert "selection_approval_missing:selection-shot-1:selection-shot-1.v3" in readiness.blockers
    assert "selection_not_locked:selection-shot-1:selection-shot-1.v3" in readiness.blockers


def test_changed_candidate_selection_cannot_reuse_old_approval() -> None:
    v1_selected = select_candidate(
        _aggregate(),
        scope=SCOPE,
        expected_aggregate_version=1,
        candidate_ref=_ref(_aggregate().asset_candidates[0]),
        purpose="storyboard",
        selection_entity_id="selection-shot-1",
        selection_version_id="selection-shot-1.v1",
        created_at=TIMES[4],
    )
    v1_approved = _approved(v1_selected)
    changed = restore_selection(
        v1_approved,
        scope=SCOPE,
        expected_aggregate_version=v1_approved.aggregate_version,
        selection_ref=_ref(v1_approved.selections[-1]),
        historical_candidate_ref=_ref(v1_approved.asset_candidates[1]),
        selection_version_id="selection-shot-1.v3",
        created_at=TIMES[6],
    )

    exact_old_approvals = [
        item
        for item in changed.review_decisions
        if item.decision == "approve" and item.subject_ref == _ref(changed.selections[-1])
    ]
    assert exact_old_approvals == []
    with pytest.raises(ReviewDeliveryStateError, match="only an approved selection"):
        lock_selection(
            changed,
            scope=SCOPE,
            expected_aggregate_version=changed.aggregate_version,
            selection_ref=_ref(changed.selections[-1]),
            selection_version_id="selection-shot-1.v4",
            decision_entity_id="lock-selection-v4",
            decision_version_id="lock-selection-v4.v1",
            created_at=TIMES[7],
        )


def test_cross_scope_cross_target_and_stale_cas_are_rejected() -> None:
    aggregate = _aggregate()
    foreign_scope = TenantScope(
        org_id=SCOPE.org_id,
        project_id="another-project",
        actor_id=SCOPE.actor_id,
    )
    with pytest.raises(ReviewDeliveryScopeError, match="exactly match"):
        compare_candidate_versions(
            aggregate,
            scope=foreign_scope,
            target_ref=_ref(aggregate.shots[0]),
        )
    foreign_actor = TenantScope(
        org_id=SCOPE.org_id,
        project_id=SCOPE.project_id,
        actor_id="creator-2",
    )
    with pytest.raises(ReviewDeliveryScopeError, match="actor"):
        compare_candidate_versions(
            aggregate,
            scope=foreign_actor,
            target_ref=_ref(aggregate.shots[0]),
        )
    with pytest.raises(ReviewDeliveryVersionConflictError, match="expected 0, current 1"):
        select_candidate(
            aggregate,
            scope=SCOPE,
            expected_aggregate_version=0,
            candidate_ref=_ref(aggregate.asset_candidates[1]),
            purpose="storyboard",
            selection_entity_id="selection-shot-1",
            selection_version_id="selection-shot-1.v1",
            created_at=TIMES[4],
        )
    selected = _selected_v2(aggregate)
    approved = _approved(selected)
    with pytest.raises(ReviewDeliveryVersionConflictError, match="not the latest"):
        review_selection(
            approved,
            scope=SCOPE,
            expected_aggregate_version=approved.aggregate_version,
            selection_ref=_ref(approved.selections[0]),
            decision="approve",
            selection_version_id="selection-shot-1.v3",
            decision_entity_id="review-stale-selection",
            decision_version_id="review-stale-selection.v1",
            created_at=TIMES[6],
        )
    with pytest.raises(ReviewDeliveryReferenceError, match="exact selection target"):
        restore_selection(
            selected,
            scope=SCOPE,
            expected_aggregate_version=selected.aggregate_version,
            selection_ref=_ref(selected.selections[-1]),
            historical_candidate_ref=_ref(selected.asset_candidates[2]),
            selection_version_id="selection-shot-1.v2",
            created_at=TIMES[5],
        )


@pytest.mark.parametrize("job_state", ["running", "failed"])
def test_running_or_failed_candidate_cannot_be_selected(job_state: str) -> None:
    aggregate = _aggregate()
    candidate = aggregate.asset_candidates[0].model_copy(
        update={
            "lifecycle_state": "candidate",
            "review_state": "needs_review",
            "artifact_ref": None,
            "job_id": "job-1",
            "job_state": job_state,
        }
    )
    payload = aggregate.model_dump(mode="python")
    payload.update(
        {
            "asset_candidates": (candidate, aggregate.asset_candidates[2]),
            "review_decisions": (),
        }
    )
    isolated = ProductionProjectAggregate.model_validate(payload)

    with pytest.raises(ReviewDeliveryStateError, match=f"{job_state} state"):
        select_candidate(
            isolated,
            scope=SCOPE,
            expected_aggregate_version=isolated.aggregate_version,
            candidate_ref=_ref(candidate),
            purpose="storyboard",
            selection_entity_id="selection-shot-1",
            selection_version_id="selection-shot-1.v1",
            created_at=TIMES[4],
        )


def test_candidate_without_artifact_cannot_be_selected() -> None:
    aggregate = _aggregate()
    candidate = aggregate.asset_candidates[0].model_copy(
        update={
            "lifecycle_state": "candidate",
            "review_state": "needs_review",
            "artifact_ref": None,
        }
    )
    payload = aggregate.model_dump(mode="python")
    payload.update(
        {
            "asset_candidates": (candidate, aggregate.asset_candidates[2]),
            "review_decisions": (),
        }
    )
    isolated = ProductionProjectAggregate.model_validate(payload)

    with pytest.raises(ReviewDeliveryStateError, match="without a safe artifact"):
        select_candidate(
            isolated,
            scope=SCOPE,
            expected_aggregate_version=isolated.aggregate_version,
            candidate_ref=_ref(candidate),
            purpose="storyboard",
            selection_entity_id="selection-shot-1",
            selection_version_id="selection-shot-1.v1",
            created_at=TIMES[4],
        )


def test_twenty_five_missing_inventory_blocks_delivery_without_fake_preview() -> None:
    aggregate = _aggregate()
    readiness = assess_delivery_readiness(
        aggregate,
        scope=SCOPE,
        episode_ref=_ref(aggregate.episodes[0]),
        selection_refs=(),
        missing_inventory_count=25,
        preview_artifact_ref=None,
    )

    assert readiness.ready is False
    assert readiness.missing_inventory_count == 25
    assert readiness.preview_artifact_ref is None
    assert "missing_inventory:25" in readiness.blockers
    assert "playable_preview_missing" in readiness.blockers
    with pytest.raises(DeliveryNotReadyError) as exc_info:
        freeze_delivery(
            aggregate,
            scope=SCOPE,
            expected_aggregate_version=aggregate.aggregate_version,
            episode_ref=_ref(aggregate.episodes[0]),
            selection_refs=(),
            missing_inventory_count=25,
            preview_artifact_ref=None,
            export_artifact_refs=(),
            delivery_entity_id="delivery-blocked",
            delivery_version_id="delivery-blocked.v1",
            created_at=TIMES[4],
        )
    assert exc_info.value.readiness.preview_artifact_ref is None
    assert aggregate.deliveries == ()


def test_delivery_blocks_when_episode_continuity_exact_selection_is_open() -> None:
    aggregate = _aggregate()
    shot_with_continuity = aggregate.shots[0].model_copy(
        update={"continuity_refs": (_ref(aggregate.continuity_states[0]),)}
    )
    payload = aggregate.model_dump(mode="python")
    payload["shots"] = (shot_with_continuity,)
    with_continuity = ProductionProjectAggregate.model_validate(payload)
    locked = _locked(_approved(_selected_v2(with_continuity)))

    readiness = assess_delivery_readiness(
        locked,
        scope=SCOPE,
        episode_ref=_ref(locked.episodes[0]),
        selection_refs=(_ref(locked.selections[-1]),),
        missing_inventory_count=0,
        preview_artifact_ref=_artifact("preview-episode", "video"),
    )

    assert "continuity_selection_missing:character-lin:character-lin.v1" in readiness.blockers
    with pytest.raises(DeliveryNotReadyError):
        freeze_delivery(
            locked,
            scope=SCOPE,
            expected_aggregate_version=locked.aggregate_version,
            episode_ref=_ref(locked.episodes[0]),
            selection_refs=(_ref(locked.selections[-1]),),
            missing_inventory_count=0,
            preview_artifact_ref=_artifact("preview-episode", "video"),
            export_artifact_refs=(),
            delivery_entity_id="delivery-open-continuity",
            delivery_version_id="delivery-open-continuity.v1",
            created_at=TIMES[7],
        )


def test_delivery_unlock_is_append_only_and_serializes_roundtrip() -> None:
    frozen = _frozen(_locked(_approved(_selected_v2(_aggregate()))))
    unlocked = unlock_delivery(
        frozen,
        scope=SCOPE,
        expected_aggregate_version=frozen.aggregate_version,
        delivery_ref=_ref(frozen.deliveries[-1]),
        delivery_version_id="delivery-episode-1.v2",
        decision_entity_id="unlock-delivery-v1",
        decision_version_id="unlock-delivery-v1.v1",
        created_at=TIMES[8],
    )
    restored = ProductionProjectAggregate.model_validate_json(unlocked.model_dump_json())

    assert [item.lifecycle_state for item in restored.deliveries] == ["locked", "approved"]
    assert restored.review_decisions[-1].decision == "unlock"
    assert restored.review_decisions[-1].subject_ref == _ref(restored.deliveries[0])
    assert restored == unlocked


def test_unsafe_preview_or_export_ref_fails_contract_validation() -> None:
    locked = _locked(_approved(_selected_v2(_aggregate())))
    with pytest.raises(ValidationError):
        SafeArtifactRef(
            artifact_id="../private-preview",
            artifact_type="video",
            content_digest=_digest("unsafe"),
        )
    with pytest.raises(ValidationError):
        assess_delivery_readiness(
            locked,
            scope=SCOPE,
            episode_ref=_ref(locked.episodes[0]),
            selection_refs=(_ref(locked.selections[-1]),),
            missing_inventory_count=0,
            preview_artifact_ref={  # type: ignore[arg-type]
                "artifact_id": "../private-preview",
                "artifact_type": "video",
                "content_digest": _digest("unsafe"),
            },
        )
    assert assess_delivery_readiness(
        locked,
        scope=SCOPE,
        episode_ref=_ref(locked.episodes[0]),
        selection_refs=(_ref(locked.selections[-1]),),
        missing_inventory_count=0,
        preview_artifact_ref=_artifact("safe-preview", "video"),
        export_artifact_refs=(_artifact("safe-export", "video"),),
    ).ready
