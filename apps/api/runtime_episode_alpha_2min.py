from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from agentflow_studio.production_control.harness import StateConflictError
from agentflow_studio.production.alpha_2min import (
    MEDIA_MODALITIES,
    PROTECTED_NON_CLAIMS,
    Alpha2MinBrief,
    Alpha2MinProductionRecipe,
    Alpha2MinStoryboardFrame,
    build_alpha_2min_candidate_manifest,
    build_alpha_2min_export_manifest,
    build_alpha_2min_recipe,
    build_alpha_2min_storyboard,
    digest,
)
from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_creator_production_integration import (
    CreatorProductionControlError,
    apply_creator_preview_episode_candidate,
    confirm_creator_preview_control_run,
    prepare_creator_preview_control_plan,
    read_creator_preview_control_projection,
    record_creator_preview_control_writeback,
)
from apps.api.runtime_episode_domain_contract import (
    AgentProposal,
    ArcVersion,
    DeliveryVersion,
    EntityVersionRef,
    EpisodeVersion,
    ProductionProjectAggregate,
    ProjectDataPolicy,
    ProjectVersion,
    ReferenceAssetVersion,
    ReferenceSetVersion,
    SafeArtifactRef,
    SceneVersion,
    SelectedVersion,
    SeriesVersion,
    ShotVersion,
    SourceEvidenceRef,
    StoryBibleVersion,
    TenantScope,
)
from apps.api.runtime_episode_domain_routes import (
    IdempotencyKey,
    _raise_api_error,
    _raise_store_error,
    _require_project_scope,
    _safe_aggregate_payload,
)
from apps.api.runtime_episode_domain_store import (
    AggregateNotFoundError,
    EpisodeDomainAggregateStore,
    EpisodeDomainStoreError,
)
from apps.api.runtime_episode_workspace_projection import (
    build_creator_authoring_projection,
    build_episode_workspace_projection,
)
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_logging import client_request_id_from_request, request_id_from_request
from apps.api.runtime_store import RuntimeStore, safe_id
from apps.api.runtime_submit_idempotency import (
    begin_submit_idempotency,
    complete_submit_idempotency,
    submit_idempotency_error_detail,
)


ALPHA_SCHEMA_VERSION = "afs.alpha_2min.pipeline_response.v0.1"
ALPHA_ACTION = "alpha_2min_vertical_slice"
ALPHA_CREATED_AT = "2026-07-16T00:00:00+00:00"
ALPHA_STORY_BIBLE_ID = "alpha-bible-001"
ALPHA_SERIES_ID = "alpha-series-001"
ALPHA_ARC_ID = "alpha-arc-001"
ALPHA_EPISODE_ID = "alpha-episode-001"
ALPHA_REFERENCE_SET_ID = "alpha-reference-set-001"
ALPHA_DELIVERY_ID = "alpha-delivery-001"
ALPHA_SCENE_IDS = ("alpha-scene-001", "alpha-scene-002", "alpha-scene-003")
ALPHA_SHOT_IDS = tuple(f"alpha-shot-{index:03d}" for index in range(1, 7))
ALPHA_REFERENCE_ASSET_IDS = (
    "alpha-ref-lead",
    "alpha-ref-location",
    "alpha-ref-style",
    "alpha-ref-voice",
)


class Alpha2MinBriefConflictError(RuntimeError):
    pass


class Alpha2MinRouteModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Alpha2MinPipelineRequest(Alpha2MinRouteModel):
    expected_aggregate_version: int = Field(default=0, ge=0, strict=True)
    brief: Alpha2MinBrief
    created_at: str = Field(default=ALPHA_CREATED_AT, min_length=1, max_length=64)


def register_runtime_episode_alpha_2min_routes(
    app: FastAPI,
    store: RuntimeStore,
    auth: RuntimeAuthStore,
) -> None:
    @app.post("/projects/{project_id}/episode-production-aggregate/alpha-2min")
    def execute_alpha_2min_pipeline(
        project_id: str,
        body: Alpha2MinPipelineRequest,
        request: Request,
        idempotency_key: IdempotencyKey,
    ) -> dict[str, Any]:
        scope = _require_project_scope(store, auth, request, project_id)
        crash_after = str(request.headers.get("X-AFS-Crash-After") or "none")
        try:
            response = _execute_alpha_2min_pipeline(
                store,
                scope=scope,
                body=body,
                idempotency_key=idempotency_key,
                request=request,
                crash_after=crash_after,
            )
            return response
        except EpisodeDomainStoreError as exc:
            _raise_store_error(exc, request=request, project_id=project_id)
        except (CreatorProductionControlError, StateConflictError) as exc:
            _raise_api_error(
                request,
                project_id,
                status_code=409,
                error="alpha_2min_production_control_conflict",
                message="Alpha 2-minute production control state changed; retry with the same request.",
                stage="alpha_2min_production_control",
                retryable=True,
                cause=exc,
            )
        except Alpha2MinBriefConflictError as exc:
            _raise_api_error(
                request,
                project_id,
                status_code=409,
                error="alpha_2min_brief_conflict",
                message=(
                    "Alpha 2-minute project already has canonical brief truth. "
                    "Retry with the original brief or create a new project."
                ),
                stage="alpha_2min_brief_match",
                cause=exc,
            )
        except ValueError as exc:
            _raise_api_error(
                request,
                project_id,
                status_code=422,
                error="alpha_2min_pipeline_invalid",
                message="Alpha 2-minute pipeline input or state is invalid.",
                stage="alpha_2min_validation",
                cause=exc,
            )
        raise AssertionError("unreachable alpha_2min route error")


def _execute_alpha_2min_pipeline(
    store: RuntimeStore,
    *,
    scope: TenantScope,
    body: Alpha2MinPipelineRequest,
    idempotency_key: str,
    request: Request,
    crash_after: str,
) -> dict[str, Any]:
    request_id = request_id_from_request(request)
    client_request_id = client_request_id_from_request(request) or idempotency_key
    reservation = begin_submit_idempotency(
        store,
        project_id=scope.project_id,
        action=ALPHA_ACTION,
        request=body.model_dump(mode="json"),
        client_request_id=idempotency_key,
        request_id=request_id,
    )
    if reservation.state == "replay":
        replay = dict(reservation.response or {})
        replay["idempotent_replay"] = True
        return replay
    if reservation.state in {"pending", "conflict"}:
        detail = submit_idempotency_error_detail(
            reservation,
            request_id=request_id,
            client_request_id=client_request_id,
        )
        raise HTTPException(status_code=409, detail=detail)

    _crash_if(crash_after, "reserved", request, scope.project_id)

    stamp = _stamp(body.created_at)
    aggregate = _ensure_base_alpha_aggregate(
        store,
        scope=scope,
        brief=body.brief,
        expected_aggregate_version=body.expected_aggregate_version,
        idempotency_key=f"{reservation.stable_request_id}-base",
        created_at=stamp,
        request=request,
    )
    _crash_if(crash_after, "base_aggregate", request, scope.project_id)

    storyboard = build_alpha_2min_storyboard(
        body.brief,
        scene_ids=ALPHA_SCENE_IDS,
        shot_ids=ALPHA_SHOT_IDS,
    )
    recipe = build_alpha_2min_recipe(
        body.brief,
        reference_set_id=ALPHA_REFERENCE_SET_ID,
        reference_asset_ids=ALPHA_REFERENCE_ASSET_IDS,
        storyboard=storyboard,
    )
    aggregate = _ensure_alpha_candidates(
        store,
        scope=scope,
        aggregate=aggregate,
        recipe=recipe,
        idempotency_token=reservation.stable_request_id,
        created_at=stamp,
    )
    _crash_if(crash_after, "candidates", request, scope.project_id)

    aggregate, export_manifest = _ensure_alpha_delivery(
        store,
        scope=scope,
        brief=body.brief,
        recipe=recipe,
        storyboard=storyboard,
        idempotency_key=f"{reservation.stable_request_id}-delivery",
        created_at=stamp,
    )
    _crash_if(crash_after, "before_complete", request, scope.project_id)

    response = _alpha_response(
        store,
        scope=scope,
        brief=body.brief,
        recipe=recipe,
        storyboard=storyboard,
        aggregate=aggregate,
        export_manifest=export_manifest,
        reservation_ledger=reservation.ledger,
        idempotent_replay=False,
    )
    complete_submit_idempotency(
        reservation,
        job_id=response["job"]["job_id"],
        response=response,
        provider_calls_started=False,
    )
    return response


def _ensure_base_alpha_aggregate(
    store: RuntimeStore,
    *,
    scope: TenantScope,
    brief: Alpha2MinBrief,
    expected_aggregate_version: int,
    idempotency_key: str,
    created_at: str,
    request: Request,
) -> ProductionProjectAggregate:
    aggregate_store = EpisodeDomainAggregateStore(store.root)
    try:
        existing = aggregate_store.load(org_id=scope.org_id, project_id=scope.project_id)
    except AggregateNotFoundError:
        if expected_aggregate_version != 0:
            raise ValueError("alpha_2min bootstrap requires expected aggregate version 0")
        aggregate = _build_base_aggregate(scope=scope, brief=brief, created_at=created_at)
        _safe_aggregate_payload(
            aggregate,
            request=request,
            project_id=scope.project_id,
            status_code=422,
            stage="alpha_2min_base_aggregate",
        )
        result = aggregate_store.save(
            aggregate,
            expected_aggregate_version=0,
            idempotency_key=safe_id(idempotency_key)[:150],
            payload_digest=digest(
                {
                    "operation": "alpha_2min_base_aggregate",
                    "aggregate": aggregate.model_dump(mode="json"),
                }
            ),
        )
        return result.aggregate
    if existing.scope != scope:
        raise ValueError("existing aggregate scope does not match alpha_2min request")
    if not _existing_alpha_matches_brief(existing, brief):
        raise Alpha2MinBriefConflictError(
            "incoming alpha_2min brief does not match canonical aggregate truth"
        )
    return existing


def _build_base_aggregate(
    *,
    scope: TenantScope,
    brief: Alpha2MinBrief,
    created_at: str,
) -> ProductionProjectAggregate:
    source = SourceEvidenceRef(
        source_id="alpha-brief-source-001",
        scope=scope,
        source_type="creator_input",
        uploaded_by=scope.actor_id,
        rights_basis="creator_owned",
        allowed_uses=("production",),
        training_status="denied",
    )
    project = ProjectVersion(
        **_fact(
            scope,
            "project",
            scope.project_id,
            created_at=created_at,
            content={
                "title": brief.project_title,
                "logline": brief.logline,
                "target_duration_seconds": brief.target_duration_seconds,
            },
        ),
        title=brief.project_title,
        summary=brief.logline,
        creative_intent=f"{brief.genre}; {brief.tone}; {brief.core_theme}",
        ip_profile="alpha_2min_provider_free_fixture",
        data_policy=ProjectDataPolicy(),
        source_refs=(source,),
    )
    story_bible = StoryBibleVersion(
        **_fact(
            scope,
            "story_bible",
            ALPHA_STORY_BIBLE_ID,
            created_at=created_at,
            content={"brief": brief.model_dump(mode="json")},
        ),
        project_ref=project.as_ref(),
        title=f"{brief.project_title} Bible",
        summary=brief.logline,
        world_rules=(
            "Provider calls remain closed for this executable slice.",
            "Reference assets are fixture metadata, not generated media.",
            *brief.must_include,
            *brief.constraints,
        ),
        source_refs=(source,),
    )
    series = SeriesVersion(
        **_fact(
            scope,
            "series",
            ALPHA_SERIES_ID,
            created_at=created_at,
            content={"title": brief.project_title},
        ),
        project_ref=project.as_ref(),
        title=f"{brief.project_title} Series",
        summary=brief.logline,
        creative_intent=project.creative_intent,
        source_refs=(source,),
    )
    arc = ArcVersion(
        **_fact(
            scope,
            "arc",
            ALPHA_ARC_ID,
            created_at=created_at,
            content={"theme": brief.core_theme},
        ),
        series_ref=series.as_ref(),
        story_bible_ref=story_bible.as_ref(),
        sequence=1,
        title="Alpha Arc",
        summary=f"A 90-120 second arc around {brief.core_theme}.",
        creative_intent=brief.logline,
        source_refs=(source,),
    )
    reference_assets = _reference_assets(scope, project.as_ref(), created_at, source)
    episode_ref = EntityVersionRef(
        entity_type="episode",
        entity_id=ALPHA_EPISODE_ID,
        version_id=f"{ALPHA_EPISODE_ID}-v1",
    )
    reference_set = ReferenceSetVersion(
        **_fact(
            scope,
            "reference_set",
            ALPHA_REFERENCE_SET_ID,
            created_at=created_at,
            content={"asset_ids": ALPHA_REFERENCE_ASSET_IDS},
        ),
        project_ref=project.as_ref(),
        title="Alpha 2-minute ReferenceSet",
        summary="Approved fixture references for image, video, and audio placeholder candidates.",
        scope_kind="episode",
        scope_refs=(episode_ref,),
        asset_refs=tuple(item.as_ref() for item in reference_assets),
        approval_state="approved",
        human_confirmed=True,
        source_refs=(source,),
    )
    episode = EpisodeVersion(
        **_fact(
            scope,
            "episode",
            ALPHA_EPISODE_ID,
            created_at=created_at,
            content={"duration": brief.target_duration_seconds, "brief": brief.brief_id},
        ),
        series_ref=series.as_ref(),
        arc_ref=arc.as_ref(),
        sequence=1,
        title="Alpha 2-minute Episode",
        summary=brief.logline,
        creative_intent=brief.core_theme,
        reference_set_ref=reference_set.as_ref(),
        source_refs=(source,),
    )
    storyboard = build_alpha_2min_storyboard(
        brief,
        scene_ids=ALPHA_SCENE_IDS,
        shot_ids=ALPHA_SHOT_IDS,
    )
    scenes = _scenes(scope, episode.as_ref(), reference_set.as_ref(), storyboard, created_at, source)
    shots = _shots(scope, scenes, reference_set.as_ref(), storyboard, created_at, source)
    proposals = tuple(
        AgentProposal(
            **_fact(
                scope,
                "agent_proposal",
                f"alpha-director-proposal-{index:03d}",
                created_at=created_at,
                content={"shot_id": shot.entity_id, "brief": brief.brief_id},
            ),
            target_ref=shot.as_ref(),
            impact_refs=(shot.as_ref(),),
            action="alpha_2min.provider_free_candidate_review",
            decision_state="pending",
            source_refs=(source,),
        )
        for index, shot in enumerate(shots, start=1)
    )
    return ProductionProjectAggregate(
        aggregate_version=1,
        evaluated_at=created_at,
        scope=scope,
        projects=(project,),
        series=(series,),
        story_bibles=(story_bible,),
        arcs=(arc,),
        episodes=(episode,),
        scenes=scenes,
        shots=shots,
        reference_assets=reference_assets,
        reference_sets=(reference_set,),
        agent_proposals=proposals,
    )


def _ensure_alpha_candidates(
    store: RuntimeStore,
    *,
    scope: TenantScope,
    aggregate: ProductionProjectAggregate,
    recipe: Alpha2MinProductionRecipe,
    idempotency_token: str,
    created_at: str,
) -> ProductionProjectAggregate:
    latest = aggregate
    for shot in _alpha_shots(latest):
        protected_refs = tuple(
            item.as_ref() for item in _alpha_shots(latest) if item.as_ref() != shot.as_ref()
        )
        for modality in MEDIA_MODALITIES:
            candidate_ref = _candidate_ref(shot.entity_id, modality)
            existing = _alpha_candidates(latest).get(candidate_ref.entity_id)
            if (
                existing is not None
                and existing.control_provenance is not None
                and existing.artifact_ref is not None
                and existing.job_state == "succeeded"
            ):
                continue
            manifest = build_alpha_2min_candidate_manifest(
                recipe,
                shot_id=shot.entity_id,
                modality=modality,  # type: ignore[arg-type]
                candidate_id=candidate_ref.entity_id,
            )
            key = f"a2m-{idempotency_token[:32]}-{shot.sequence:02d}-{modality}"
            control_plan = prepare_creator_preview_control_plan(store, scope=scope)
            control = record_creator_preview_control_writeback(
                store,
                scope=scope,
                control_plan=control_plan,
                idempotency_key=key,
                target_ref=shot.as_ref(),
                protected_refs=protected_refs,
                artifact_id=f"artifact-{candidate_ref.entity_id}",
                artifact_digest=digest(manifest.model_dump(mode="json")),
                candidate_ref=candidate_ref,
                created_at=created_at,
            )
            apply_creator_preview_episode_candidate(
                store,
                scope=scope,
                control=control,
                idempotency_key=key,
                created_at=created_at,
            )
            confirm_creator_preview_control_run(
                store,
                scope=scope,
                control=control,
                idempotency_key=key,
            )
            latest = EpisodeDomainAggregateStore(store.root).load(
                org_id=scope.org_id,
                project_id=scope.project_id,
            )
    return latest


def _ensure_alpha_delivery(
    store: RuntimeStore,
    *,
    scope: TenantScope,
    brief: Alpha2MinBrief,
    recipe: Alpha2MinProductionRecipe,
    storyboard: tuple[Alpha2MinStoryboardFrame, ...],
    idempotency_key: str,
    created_at: str,
) -> tuple[ProductionProjectAggregate, dict[str, Any]]:
    aggregate_store = EpisodeDomainAggregateStore(store.root)
    aggregate = aggregate_store.load(org_id=scope.org_id, project_id=scope.project_id)
    existing = next((item for item in aggregate.deliveries if item.entity_id == ALPHA_DELIVERY_ID), None)
    if existing is not None:
        return aggregate, _export_manifest_for_existing(brief, recipe, storyboard, aggregate, existing)

    stamp = _next_stamp(aggregate.evaluated_at, created_at)
    candidates = _alpha_candidates(aggregate)
    expected_candidate_ids = {
        _candidate_ref(shot.entity_id, modality).entity_id
        for shot in _alpha_shots(aggregate)
        for modality in MEDIA_MODALITIES
    }
    if set(candidates) != expected_candidate_ids:
        raise ValueError("alpha_2min candidates are incomplete")

    selections = tuple(
        SelectedVersion(
            **_fact(
                scope,
                "selected_version",
                _selection_id(candidate),
                created_at=stamp,
                lifecycle_state="candidate",
                review_state="needs_review",
                content={
                    "candidate": candidate.as_ref().model_dump(mode="json"),
                    "purpose": _candidate_modality(candidate.entity_id),
                },
            ),
            target_ref=candidate.target_ref,
            purpose=_candidate_modality(candidate.entity_id),  # type: ignore[arg-type]
            candidate_ref=candidate.as_ref(),
        )
        for candidate in sorted(
            candidates.values(),
            key=lambda item: (item.target_ref.entity_id, _candidate_modality(item.entity_id)),
        )
    )
    delivery_ref = EntityVersionRef(
        entity_type="delivery_version",
        entity_id=ALPHA_DELIVERY_ID,
        version_id=f"{ALPHA_DELIVERY_ID}-v1",
    )
    export_manifest = build_alpha_2min_export_manifest(
        brief,
        recipe=recipe,
        storyboard=storyboard,
        candidate_refs=_candidate_rows(candidates),
        selection_refs=tuple(item.as_ref().model_dump(mode="json") for item in selections),
        delivery_ref=delivery_ref.model_dump(mode="json"),
        aggregate_version=aggregate.aggregate_version + 1,
    )
    export_ref = SafeArtifactRef(
        artifact_id="alpha2min-export-manifest",
        artifact_type="alpha_2min_export_manifest",
        content_digest=digest(export_manifest),
    )
    delivery = DeliveryVersion(
        **_fact(
            scope,
            "delivery_version",
            ALPHA_DELIVERY_ID,
            created_at=stamp,
            lifecycle_state="candidate",
            review_state="needs_review",
            content=export_manifest,
        ),
        episode_ref=_alpha_episode(aggregate).as_ref(),
        selection_refs=tuple(item.as_ref() for item in selections),
        review_decision_refs=(),
        preview_artifact_ref=None,
        export_artifact_refs=(export_ref,),
    )
    payload = aggregate.model_dump(mode="python")
    payload.update(
        {
            "aggregate_version": aggregate.aggregate_version + 1,
            "evaluated_at": stamp,
            "selections": (*aggregate.selections, *selections),
            "deliveries": (*aggregate.deliveries, delivery),
        }
    )
    updated = ProductionProjectAggregate.model_validate(payload)
    result = aggregate_store.save(
        updated,
        expected_aggregate_version=aggregate.aggregate_version,
        idempotency_key=safe_id(idempotency_key)[:150],
        payload_digest=digest(
            {
                "operation": "alpha_2min_delivery",
                "delivery": delivery.model_dump(mode="json"),
                "selections": [item.model_dump(mode="json") for item in selections],
                "expected_aggregate_version": aggregate.aggregate_version,
            }
        ),
    )
    return result.aggregate, export_manifest


def _alpha_response(
    store: RuntimeStore,
    *,
    scope: TenantScope,
    brief: Alpha2MinBrief,
    recipe: Alpha2MinProductionRecipe,
    storyboard: tuple[Alpha2MinStoryboardFrame, ...],
    aggregate: ProductionProjectAggregate,
    export_manifest: dict[str, Any],
    reservation_ledger: dict[str, Any],
    idempotent_replay: bool,
) -> dict[str, Any]:
    episode = _alpha_episode(aggregate)
    creator_projection = build_creator_authoring_projection(aggregate)
    workspace_projection = build_episode_workspace_projection(aggregate, episode_ref=episode.as_ref())
    control_projection = read_creator_preview_control_projection(store, scope=scope)
    candidates = _alpha_candidates(aggregate)
    delivery = next(item for item in aggregate.deliveries if item.entity_id == ALPHA_DELIVERY_ID)
    response = {
        "schema_version": ALPHA_SCHEMA_VERSION,
        "project_id": scope.project_id,
        "job": {
            "job_id": f"{safe_id(scope.project_id)}-alpha-2min-{aggregate.aggregate_version}",
            "status": "succeeded",
            "action": ALPHA_ACTION,
        },
        "idempotent_replay": idempotent_replay,
        "aggregate_version": aggregate.aggregate_version,
        "missing_link": "brief_to_provider_free_alpha_2min_episode_pipeline",
        "truth_chain": {
            "story_bible_ref": _entity_ref(_alpha_story_bible(aggregate).as_ref()),
            "arc_ref": _entity_ref(_alpha_arc(aggregate).as_ref()),
            "episode_ref": _entity_ref(episode.as_ref()),
            "scene_refs": [_entity_ref(item.as_ref()) for item in _alpha_scenes(aggregate)],
            "shot_refs": [_entity_ref(item.as_ref()) for item in _alpha_shots(aggregate)],
            "reference_set_ref": _entity_ref(_alpha_reference_set(aggregate).as_ref()),
            "production_recipe_id": recipe.recipe_id,
            "delivery_ref": _entity_ref(delivery.as_ref()),
        },
        "production_recipe": recipe.model_dump(mode="json"),
        "storyboard": [item.model_dump(mode="json") for item in storyboard],
        "candidate_inventory": {
            "total": len(candidates),
            "image": _modality_count(candidates, "image"),
            "video": _modality_count(candidates, "video"),
            "audio": _modality_count(candidates, "audio"),
            "records": list(_candidate_rows(candidates)),
        },
        "export_manifest": export_manifest,
        "projections": {
            "creator_authoring_schema": creator_projection["schema_version"],
            "episode_workspace_schema": workspace_projection["schema_version"],
            "creator_counts": creator_projection["counts"],
            "workspace_truth": workspace_projection["workspace"]["truth"],
            "workspace_delivery": workspace_projection["workspace"]["delivery"],
        },
        "production_control": {
            "schema_version": control_projection["schema_version"],
            "version": control_projection["version"],
            "event_count": control_projection["event_count"],
            "artifact_count": len(control_projection["artifacts"]),
            "provider_dispatch_count": control_projection["provider_dispatch_count"],
            "artifact_status_digest": control_projection["artifact_status_digest"],
        },
        "review": {
            "status": "pending_fixture_review",
            "retry_enabled": True,
            "delivery_lifecycle_state": delivery.lifecycle_state,
            "delivery_review_state": delivery.review_state,
        },
        "recovery": {
            "submit_idempotency_schema": reservation_ledger.get("schema_version", ""),
            "attempt_number": reservation_ledger.get("attempt_number", 0),
            "attempt_status": reservation_ledger.get("attempt_status", ""),
            "lease_status": (reservation_ledger.get("lease") or {}).get("status", ""),
            "reclaimed_attempts": reservation_ledger.get("reclaimed_attempts", []),
        },
        "call_counters": {
            "provider_calls": 0,
            "model_calls": 0,
            "media_calls": 0,
            "external_downloads": 0,
        },
        "provider_dispatch_count": 0,
        "non_claims": dict(PROTECTED_NON_CLAIMS),
    }
    if control_projection["provider_dispatch_count"] != 0:
        raise ValueError("alpha_2min provider dispatch count must remain zero")
    return response


def _reference_assets(
    scope: TenantScope,
    project_ref: EntityVersionRef,
    created_at: str,
    source: SourceEvidenceRef,
) -> tuple[ReferenceAssetVersion, ...]:
    specs = (
        ("alpha-ref-lead", "human", "Lead", "Fixture lead identity; no generated portrait."),
        ("alpha-ref-location", "location", "Location", "Fixture location identity; no external asset."),
        ("alpha-ref-style", "style", "Style", "Fixture style guide; metadata only."),
        ("alpha-ref-voice", "voice", "Voice", "Fixture voice direction; no voice synthesis."),
    )
    return tuple(
        ReferenceAssetVersion(
            **_fact(
                scope,
                "reference_asset",
                entity_id,
                created_at=created_at,
                content={"asset_kind": kind, "identity": identity},
            ),
            project_ref=project_ref,
            asset_kind=kind,  # type: ignore[arg-type]
            label=label,
            identity=identity,
            confidence=1.0,
            approval_state="approved",
            human_confirmed=True,
            source_refs=(source,),
        )
        for entity_id, kind, label, identity in specs
    )


def _scenes(
    scope: TenantScope,
    episode_ref: EntityVersionRef,
    reference_set_ref: EntityVersionRef,
    storyboard: tuple[Alpha2MinStoryboardFrame, ...],
    created_at: str,
    source: SourceEvidenceRef,
) -> tuple[SceneVersion, ...]:
    rows = []
    for index, scene_id in enumerate(ALPHA_SCENE_IDS, start=1):
        scene_frames = [item for item in storyboard if item.scene_id == scene_id]
        rows.append(
            SceneVersion(
                **_fact(
                    scope,
                    "scene",
                    scene_id,
                    created_at=created_at,
                    content={"frames": [item.frame_id for item in scene_frames]},
                ),
                episode_ref=episode_ref,
                sequence=index,
                title=f"Alpha Scene {index}",
                summary="; ".join(item.beat for item in scene_frames),
                creative_intent="Provider-free fixture scene for the canonical alpha slice.",
                reference_set_ref=reference_set_ref,
                source_refs=(source,),
            )
        )
    return tuple(rows)


def _shots(
    scope: TenantScope,
    scenes: tuple[SceneVersion, ...],
    reference_set_ref: EntityVersionRef,
    storyboard: tuple[Alpha2MinStoryboardFrame, ...],
    created_at: str,
    source: SourceEvidenceRef,
) -> tuple[ShotVersion, ...]:
    scene_by_id = {item.entity_id: item for item in scenes}

    return tuple(
        ShotVersion(
            **_fact(
                scope,
                "shot",
                frame.shot_id,
                created_at=created_at,
                content=frame.model_dump(mode="json"),
            ),
            scene_ref=scene_by_id[frame.scene_id].as_ref(),
            sequence=frame.sequence,
            title=f"Alpha Shot {frame.sequence}",
            summary=frame.visual_summary,
            creative_intent=frame.beat,
            duration_seconds=float(frame.duration_seconds),
            reference_set_ref=reference_set_ref,
            source_refs=(source,),
        )
        for frame in storyboard
    )


def _fact(
    scope: TenantScope,
    entity_type: str,
    entity_id: str,
    *,
    created_at: str,
    content: Any,
    lifecycle_state: str = "draft",
    review_state: str = "not_requested",
) -> dict[str, Any]:
    version_id = f"{entity_id}-v1"
    return {
        "entity_id": entity_id,
        "version_id": version_id,
        "revision": 1,
        "parent_version_id": None,
        "lifecycle_state": lifecycle_state,
        "review_state": review_state,
        "content_digest": digest(
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "version_id": version_id,
                "scope": scope.model_dump(mode="json"),
                "content": content,
            }
        ),
        "scope": scope,
        "created_at": created_at,
    }


def _existing_alpha_matches_brief(
    aggregate: ProductionProjectAggregate,
    brief: Alpha2MinBrief,
) -> bool:
    try:
        project = max(aggregate.projects, key=lambda item: item.revision)
        expected = _build_base_aggregate(
            scope=aggregate.scope,
            brief=brief,
            created_at=project.created_at,
        )
    except ValueError:
        return False
    return _alpha_base_signature(aggregate) == _alpha_base_signature(expected)


def _alpha_base_signature(aggregate: ProductionProjectAggregate) -> dict[str, Any]:
    return {
        "project": max(aggregate.projects, key=lambda item: item.revision).model_dump(mode="json"),
        "story_bible": _alpha_story_bible(aggregate).model_dump(mode="json"),
        "series": _alpha_series(aggregate).model_dump(mode="json"),
        "arc": _alpha_arc(aggregate).model_dump(mode="json"),
        "episode": _alpha_episode(aggregate).model_dump(mode="json"),
        "scenes": [item.model_dump(mode="json") for item in _alpha_scenes(aggregate)],
        "shots": [item.model_dump(mode="json") for item in _alpha_shots(aggregate)],
        "reference_assets": [
            _latest_exact(aggregate.reference_assets, asset_id).model_dump(mode="json")
            for asset_id in ALPHA_REFERENCE_ASSET_IDS
        ],
        "reference_set": _alpha_reference_set(aggregate).model_dump(mode="json"),
    }


def _export_manifest_for_existing(
    brief: Alpha2MinBrief,
    recipe: Alpha2MinProductionRecipe,
    storyboard: tuple[Alpha2MinStoryboardFrame, ...],
    aggregate: ProductionProjectAggregate,
    delivery: DeliveryVersion,
) -> dict[str, Any]:
    return build_alpha_2min_export_manifest(
        brief,
        recipe=recipe,
        storyboard=storyboard,
        candidate_refs=_candidate_rows(_alpha_candidates(aggregate)),
        selection_refs=tuple(
            item.as_ref().model_dump(mode="json")
            for item in aggregate.selections
            if item.entity_id.startswith("alpha-selection-")
        ),
        delivery_ref=delivery.as_ref().model_dump(mode="json"),
        aggregate_version=aggregate.aggregate_version,
    )


def _candidate_ref(shot_id: str, modality: str) -> EntityVersionRef:
    entity_id = f"alpha-candidate-{shot_id.rsplit('-', 1)[-1]}-{modality}"
    return EntityVersionRef(
        entity_type="asset_candidate",
        entity_id=entity_id,
        version_id=f"{entity_id}-v1",
    )


def _selection_id(candidate: Any) -> str:
    return f"alpha-selection-{candidate.entity_id.removeprefix('alpha-candidate-')}"


def _candidate_modality(candidate_id: str) -> str:
    modality = candidate_id.rsplit("-", 1)[-1]
    if modality not in MEDIA_MODALITIES:
        raise ValueError("alpha_2min candidate modality is invalid")
    return modality


def _candidate_rows(candidates: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    rows = []
    for candidate in sorted(candidates.values(), key=lambda item: item.entity_id):
        rows.append(
            {
                "ref": candidate.as_ref().model_dump(mode="json"),
                "target_ref": candidate.target_ref.model_dump(mode="json"),
                "modality": _candidate_modality(candidate.entity_id),
                "artifact_ref": (
                    candidate.artifact_ref.model_dump(mode="json")
                    if candidate.artifact_ref is not None
                    else None
                ),
                "job_id": candidate.job_id,
                "job_state": candidate.job_state,
                "provider_dispatch_count": 0,
            }
        )
    return tuple(rows)


def _alpha_candidates(aggregate: ProductionProjectAggregate) -> dict[str, Any]:
    latest: dict[str, Any] = {}
    for candidate in aggregate.asset_candidates:
        if not candidate.entity_id.startswith("alpha-candidate-"):
            continue
        current = latest.get(candidate.entity_id)
        if current is None or candidate.revision > current.revision:
            latest[candidate.entity_id] = candidate
    return latest


def _modality_count(candidates: dict[str, Any], modality: str) -> int:
    return sum(1 for candidate_id in candidates if candidate_id.endswith(f"-{modality}"))


def _entity_ref(ref: EntityVersionRef) -> dict[str, str]:
    return ref.model_dump(mode="json")


def _alpha_story_bible(aggregate: ProductionProjectAggregate) -> StoryBibleVersion:
    return _latest_exact(aggregate.story_bibles, ALPHA_STORY_BIBLE_ID)


def _alpha_series(aggregate: ProductionProjectAggregate) -> SeriesVersion:
    return _latest_exact(aggregate.series, ALPHA_SERIES_ID)


def _alpha_arc(aggregate: ProductionProjectAggregate) -> ArcVersion:
    return _latest_exact(aggregate.arcs, ALPHA_ARC_ID)


def _alpha_episode(aggregate: ProductionProjectAggregate) -> EpisodeVersion:
    return _latest_exact(aggregate.episodes, ALPHA_EPISODE_ID)


def _alpha_reference_set(aggregate: ProductionProjectAggregate) -> ReferenceSetVersion:
    return _latest_exact(aggregate.reference_sets, ALPHA_REFERENCE_SET_ID)


def _alpha_scenes(aggregate: ProductionProjectAggregate) -> tuple[SceneVersion, ...]:
    rows = tuple(_latest_exact(aggregate.scenes, scene_id) for scene_id in ALPHA_SCENE_IDS)
    return tuple(sorted(rows, key=lambda item: item.sequence))


def _alpha_shots(aggregate: ProductionProjectAggregate) -> tuple[ShotVersion, ...]:
    rows = tuple(_latest_exact(aggregate.shots, shot_id) for shot_id in ALPHA_SHOT_IDS)
    return tuple(sorted(rows, key=lambda item: item.sequence))


def _latest_exact(records: tuple[Any, ...], entity_id: str) -> Any:
    matches = [item for item in records if item.entity_id == entity_id]
    if not matches:
        raise ValueError(f"alpha_2min record is missing: {entity_id}")
    return max(matches, key=lambda item: item.revision)


def _stamp(value: str) -> str:
    text = str(value or ALPHA_CREATED_AT).strip().replace("Z", "+00:00")
    datetime.fromisoformat(text or ALPHA_CREATED_AT)
    return text or ALPHA_CREATED_AT


def _next_stamp(first: str, second: str) -> str:
    first_value = datetime.fromisoformat(_stamp(first))
    second_value = datetime.fromisoformat(_stamp(second))
    value = first_value if first_value >= second_value else second_value
    if value <= first_value:
        value = first_value + timedelta(microseconds=1)
    return value.isoformat()


def _crash_if(crash_after: str, phase: str, request: Request, project_id: str) -> None:
    if crash_after != phase:
        return
    detail = safe_error_detail(
        "alpha_2min_injected_crash",
        message="Injected crash after durable alpha_2min phase.",
        request_id=request_id_from_request(request),
        client_request_id=client_request_id_from_request(request),
        project_id=project_id,
        action=ALPHA_ACTION,
        stage=phase,
        retryable=True,
        details={"provider_calls_started": False},
    )
    raise HTTPException(status_code=500, detail=detail)


__all__ = (
    "Alpha2MinPipelineRequest",
    "register_runtime_episode_alpha_2min_routes",
)
