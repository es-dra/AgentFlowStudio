from __future__ import annotations

from importlib import import_module
from typing import Any

from agentflow_studio.production.manga_first_l4a_compiler import validate_manga_first_manifest
from agentflow_studio.production.manga_first_l4a_schema import ProductionTruthManifest, json_digest
from agentflow_studio.production.runtime_safe_io import safe_id


_CONTRACT = import_module("apps.api.runtime_episode_domain_contract")
AssetCandidateVersion = _CONTRACT.AssetCandidateVersion
ContinuityStateVersion = _CONTRACT.ContinuityStateVersion
DeliveryVersion = _CONTRACT.DeliveryVersion
EpisodeVersion = _CONTRACT.EpisodeVersion
ProductionProjectAggregate = _CONTRACT.ProductionProjectAggregate
ProjectDataPolicy = _CONTRACT.ProjectDataPolicy
ProjectVersion = _CONTRACT.ProjectVersion
ReferenceAssetVersion = _CONTRACT.ReferenceAssetVersion
ReferenceSetVersion = _CONTRACT.ReferenceSetVersion
ReviewDecision = _CONTRACT.ReviewDecision
SceneVersion = _CONTRACT.SceneVersion
SelectedVersion = _CONTRACT.SelectedVersion
SeriesVersion = _CONTRACT.SeriesVersion
ShotVersion = _CONTRACT.ShotVersion
StoryBibleVersion = _CONTRACT.StoryBibleVersion
TenantScope = _CONTRACT.TenantScope


MANGA_FIRST_CREATED_AT = "2026-07-18T00:00:00+00:00"


def build_manga_first_episode_aggregate(
    manifest_value: ProductionTruthManifest | dict[str, Any],
    *,
    scope: TenantScope,
    aggregate_version: int = 1,
) -> ProductionProjectAggregate:
    manifest = validate_manga_first_manifest(manifest_value)
    project = ProjectVersion(
        **_fact(scope, "project", scope.project_id, manifest.story_bible),
        title=str(manifest.story_bible["title"]),
        summary=str(manifest.story_bible["logline"]),
        creative_intent=f"{manifest.story_bible['style']} / {manifest.story_bible['tone']}",
        data_policy=ProjectDataPolicy(),
    )
    series = SeriesVersion(
        **_fact(scope, "series", _id(manifest.project_id, "series"), manifest.story_bible),
        project_ref=project.as_ref(),
        title=str(manifest.story_bible["title"]),
        summary=str(manifest.story_bible["logline"]),
        creative_intent=str(manifest.story_bible["tone"]),
    )
    story_bible = StoryBibleVersion(
        **_fact(scope, "story_bible", _id(manifest.project_id, "bible"), manifest.story_bible),
        project_ref=project.as_ref(),
        title=str(manifest.story_bible["title"]),
        summary=str(manifest.story_bible["logline"]),
        world_rules=tuple(str(item) for item in manifest.story_bible.get("world_rules") or ()),
    )
    episode = EpisodeVersion(
        **_fact(scope, "episode", _id(manifest.project_id, "episode"), manifest.timeline),
        series_ref=series.as_ref(),
        title=str(manifest.story_bible["title"]),
        summary=str(manifest.story_bible["logline"]),
        creative_intent="manga_first_owner_brief",
    )
    scenes = _scenes(scope, episode, manifest)
    reference_assets = _reference_assets(scope, project, manifest)
    reference_set = _reference_set(scope, project, manifest, reference_assets, scenes)
    continuity = _continuity(scope, manifest)
    scene_by_source = {str(scene_payload["scene_id"]): scene for scene_payload, scene in zip(manifest.scenes, scenes)}
    continuity_refs = {item.subject_id: item.as_ref() for item in continuity}
    shots = _shots(scope, manifest, scene_by_source, reference_set, continuity_refs)
    candidates = _candidates(scope, manifest, shots)
    selections = _selections(scope, manifest, shots, candidates)
    reviews = _reviews(scope, manifest, selections)
    delivery = DeliveryVersion(
        **_fact(scope, "delivery_version", _id(manifest.project_id, "delivery"), manifest.assembly_contract),
        episode_ref=episode.as_ref(),
        selection_refs=tuple(item.as_ref() for item in selections),
        review_decision_refs=tuple(item.as_ref() for item in reviews),
    )
    return ProductionProjectAggregate(
        aggregate_version=aggregate_version,
        evaluated_at=MANGA_FIRST_CREATED_AT,
        scope=scope,
        projects=(project,),
        series=(series,),
        story_bibles=(story_bible,),
        episodes=(episode,),
        scenes=scenes,
        shots=shots,
        reference_assets=reference_assets,
        reference_sets=(reference_set,),
        continuity_states=continuity,
        asset_candidates=candidates,
        selections=selections,
        review_decisions=reviews,
        deliveries=(delivery,),
    )


def _scenes(scope: TenantScope, episode: EpisodeVersion, manifest: ProductionTruthManifest) -> tuple[SceneVersion, ...]:
    return tuple(
        SceneVersion(
            **_fact(scope, "scene", str(scene["scene_id"]), scene),
            episode_ref=episode.as_ref(),
            sequence=index,
            title=str(scene["name"]),
            summary=str(scene["story_function"]),
            creative_intent=str(scene["visual_mood"]),
        )
        for index, scene in enumerate(manifest.scenes, start=1)
    )


def _reference_assets(scope: TenantScope, project: ProjectVersion, manifest: ProductionTruthManifest) -> tuple[ReferenceAssetVersion, ...]:
    assets: list[ReferenceAssetVersion] = []
    for item in manifest.reference_set.get("characters") or []:
        assets.append(
            ReferenceAssetVersion(
                **_fact(
                    scope,
                    "reference_asset",
                    str(item["character_id"]),
                    item,
                    lifecycle_state="candidate",
                    review_state="needs_review",
                ),
                project_ref=project.as_ref(),
                asset_kind="human",
                label=str(item["name"]),
                identity=str(item["visual_identity"]),
                confidence=1.0,
                approval_state="pending_human",
                human_confirmed=False,
            )
        )
    for scene in manifest.scenes:
        assets.append(
            ReferenceAssetVersion(
                **_fact(
                    scope,
                    "reference_asset",
                    f"{scene['scene_id']}-ref",
                    scene,
                    lifecycle_state="candidate",
                    review_state="needs_review",
                ),
                project_ref=project.as_ref(),
                asset_kind="scene",
                label=str(scene["name"]),
                identity=f"{scene['location_type']} / {scene['visual_mood']}",
                confidence=1.0,
                approval_state="pending_human",
                human_confirmed=False,
            )
        )
    return tuple(assets)


def _reference_set(
    scope: TenantScope,
    project: ProjectVersion,
    manifest: ProductionTruthManifest,
    assets: tuple[ReferenceAssetVersion, ...],
    scenes: tuple[SceneVersion, ...],
) -> ReferenceSetVersion:
    return ReferenceSetVersion(
        **_fact(
            scope,
            "reference_set",
            _id(manifest.project_id, "reference-set"),
            manifest.reference_set,
            lifecycle_state="candidate",
            review_state="needs_review",
        ),
        project_ref=project.as_ref(),
        title="Manga-first reference set",
        summary="Owner brief characters, scenes, and style references.",
        scope_kind="project",
        scope_refs=(project.as_ref(),),
        asset_refs=tuple(item.as_ref() for item in assets),
        approval_state="pending_human",
        human_confirmed=False,
    )


def _continuity(scope: TenantScope, manifest: ProductionTruthManifest) -> tuple[ContinuityStateVersion, ...]:
    rows: list[ContinuityStateVersion] = []
    for item in manifest.reference_set.get("characters") or []:
        rows.append(
            ContinuityStateVersion(
                **_fact(scope, "continuity_state", str(item["character_id"]), item),
                subject_type="character",
                subject_id=str(item["character_id"]),
                identity_baseline=(str(item["visual_identity"]),),
                prohibited_changes=tuple(str(rule) for rule in item.get("continuity_rules") or ()),
            )
        )
    for scene in manifest.scenes:
        rows.append(
            ContinuityStateVersion(
                **_fact(scope, "continuity_state", f"{scene['scene_id']}-continuity", scene),
                subject_type="scene",
                subject_id=str(scene["scene_id"]),
                identity_baseline=(str(scene["location_type"]), str(scene["visual_mood"])),
            )
        )
    return tuple(rows)


def _shots(
    scope: TenantScope,
    manifest: ProductionTruthManifest,
    scene_by_source: dict[str, SceneVersion],
    reference_set: ReferenceSetVersion,
    continuity_refs: dict[str, Any],
) -> tuple[ShotVersion, ...]:
    rows: list[ShotVersion] = []
    for shot in manifest.shots:
        refs = [continuity_refs[item] for item in shot["character_ids"]]
        scene_ref_id = f"{shot['scene_id']}-continuity"
        if scene_ref_id in continuity_refs:
            refs.append(continuity_refs[scene_ref_id])
        rows.append(
            ShotVersion(
                **_fact(scope, "shot", str(shot["shot_id"]), shot),
                scene_ref=scene_by_source[str(shot["scene_id"])].as_ref(),
                sequence=int(shot["sequence"]),
                title=str(shot["beat_id"]),
                summary=str(shot["visual_action"]),
                creative_intent=str(shot["canonical_prompt"]),
                duration_seconds=float(shot["duration_seconds"]),
                continuity_refs=tuple(refs),
                reference_set_ref=None,
            )
        )
    return tuple(rows)


def _candidates(scope: TenantScope, manifest: ProductionTruthManifest, shots: tuple[ShotVersion, ...]) -> tuple[AssetCandidateVersion, ...]:
    shot_by_id = {item.entity_id: item for item in shots}
    return tuple(
        AssetCandidateVersion(
            **_fact(scope, "asset_candidate", str(row["candidate_id"]), row),
            target_ref=shot_by_id[str(row["shot_id"])].as_ref(),
            job_id=str(row["attempt_id"]),
            job_state="queued",
        )
        for row in manifest.fact_chain["rows"]
    )


def _selections(
    scope: TenantScope,
    manifest: ProductionTruthManifest,
    shots: tuple[ShotVersion, ...],
    candidates: tuple[AssetCandidateVersion, ...],
) -> tuple[SelectedVersion, ...]:
    shot_by_id = {item.entity_id: item for item in shots}
    candidate_by_id = {item.entity_id: item for item in candidates}
    return tuple(
        SelectedVersion(
            **_fact(scope, "selected_version", str(row["selection_id"]), row),
            target_ref=shot_by_id[str(row["shot_id"])].as_ref(),
            purpose="video",
            candidate_ref=candidate_by_id[str(row["candidate_id"])].as_ref(),
        )
        for row in manifest.fact_chain["rows"]
    )


def _reviews(scope: TenantScope, manifest: ProductionTruthManifest, selections: tuple[SelectedVersion, ...]) -> tuple[ReviewDecision, ...]:
    selection_by_id = {item.entity_id: item for item in selections}
    return tuple(
        ReviewDecision(
            **_fact(scope, "review_decision", str(row["review_id"]), row),
            subject_ref=selection_by_id[str(row["selection_id"])].as_ref(),
            decision="request_revision",
            note="pending visual creative QA before audio gate",
        )
        for row in manifest.fact_chain["rows"]
    )


def _fact(
    scope: TenantScope,
    entity_type: str,
    entity_id: str,
    payload: Any,
    *,
    lifecycle_state: str = "draft",
    review_state: str = "not_requested",
) -> dict[str, Any]:
    safe_entity_id = safe_id(entity_id, max_length=160)
    return {
        "entity_id": safe_entity_id,
        "version_id": safe_id(f"{safe_entity_id}-v1", max_length=160),
        "revision": 1,
        "parent_version_id": None,
        "lifecycle_state": lifecycle_state,
        "review_state": review_state,
        "content_digest": json_digest({"entity_type": entity_type, "entity_id": entity_id, "payload": payload}),
        "scope": scope,
        "created_at": MANGA_FIRST_CREATED_AT,
    }


def _id(project_id: str, suffix: str) -> str:
    return safe_id(f"{project_id}-{suffix}", max_length=160)
