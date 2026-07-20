from __future__ import annotations

import json
from copy import deepcopy
from decimal import Decimal
from typing import Any

from agentflow_studio.production.manga_first_l4a_schema import (
    CHECKPOINT_STAGES,
    LEGACY_TEMPLATE_TERMS,
    MANGA_FIRST_CONTRACT_VERSION,
    TARGET_MAX_SECONDS,
    TARGET_MIN_SECONDS,
    MangaCharacterBrief,
    MangaFirstBrief,
    MangaFirstError,
    MangaSceneBrief,
    ProductionTruthManifest,
    decimal_string,
    json_digest,
    variable_schedule,
)


def compile_manga_first_manifest(brief_value: MangaFirstBrief | dict[str, Any]) -> ProductionTruthManifest:
    brief = MangaFirstBrief.model_validate(brief_value)
    schedule = variable_schedule(
        count=len(brief.beats),
        target_seconds=brief.target_duration_seconds,
        weights=tuple(beat.duration_weight for beat in brief.beats),
    )
    character_index = {item.character_id: item for item in brief.characters}
    scene_index = {item.scene_id: item for item in brief.scenes}
    story_bible = _story_bible(brief)
    scenes = tuple(_scene_payload(scene) for scene in brief.scenes)
    reference_set = _reference_set(brief)
    shots: list[dict[str, Any]] = []
    for index, beat in enumerate(brief.beats):
        start, end = schedule[index]
        scene = scene_index[beat.scene_id]
        characters = [character_index[item] for item in beat.character_ids]
        shot_id = f"shot-{index + 1:03d}"
        shots.append(
            {
                "shot_id": shot_id,
                "sequence": index + 1,
                "beat_id": beat.beat_id,
                "scene_id": beat.scene_id,
                "character_ids": list(beat.character_ids),
                "start_seconds": decimal_string(start),
                "end_seconds": decimal_string(end),
                "duration_seconds": decimal_string(end - start),
                "visual_action": beat.action,
                "emotional_turn": beat.emotional_turn,
                "canonical_prompt": _shot_prompt(brief, scene, characters, beat),
                "source": "owner_brief",
                "status": "awaiting_provider_authorization",
            }
        )
    production_recipe = _production_recipe(brief)
    fact_chain = _fact_chain(brief.project_id, shots)
    checkpoints = tuple(_checkpoint_contract(brief.project_id, stage) for stage in CHECKPOINT_STAGES)
    timeline = _timeline(brief, shots, schedule)
    assembly_contract = _assembly_contract(brief.project_id)
    body = {
        "schema_version": MANGA_FIRST_CONTRACT_VERSION,
        "project_id": brief.project_id,
        "provider_dispatch_count": 0,
        "owner_decision": brief.owner_decision,
        "story_bible": story_bible,
        "scenes": scenes,
        "shots": tuple(shots),
        "reference_set": reference_set,
        "production_recipe": production_recipe,
        "timeline": timeline,
        "assembly_contract": assembly_contract,
        "fact_chain": fact_chain,
        "checkpoints": checkpoints,
        "studio_projection": _studio_projection(brief, shots, fact_chain, checkpoints, assembly_contract),
        "template_audit": _template_audit(story_bible, scenes, shots),
        "evidence_boundaries": _evidence_boundaries(),
    }
    manifest = {**body, "manifest_sha256": json_digest(body)}
    validated = ProductionTruthManifest.model_validate(manifest)
    validate_manga_first_manifest(validated)
    return validated


def validate_manga_first_manifest(value: ProductionTruthManifest | dict[str, Any]) -> ProductionTruthManifest:
    manifest = ProductionTruthManifest.model_validate(value)
    body = manifest.model_dump(mode="json")
    digest = body.pop("manifest_sha256")
    if json_digest(body) != digest:
        raise MangaFirstError("manifest_sha256 does not match canonical manifest body")
    if len(manifest.shots) < 12 or len(manifest.shots) > 15:
        raise MangaFirstError("manga-first manifest must contain 12 to 15 shots")
    if len(manifest.scenes) < 2 or len(manifest.scenes) > 4:
        raise MangaFirstError("manga-first manifest must contain 2 to 4 scenes")
    character_count = len(manifest.reference_set.get("characters") or [])
    if character_count < 1 or character_count > 3:
        raise MangaFirstError("manga-first manifest must contain 1 to 3 repeat characters")
    total = Decimal(str(manifest.timeline["duration_seconds"]))
    if total < TARGET_MIN_SECONDS or total > TARGET_MAX_SECONDS:
        raise MangaFirstError("canonical schedule must stay inside 90 to 120 seconds")
    durations = [Decimal(str(item["duration_seconds"])) for item in manifest.timeline["variable_duration_schedule"]]
    if len(set(durations)) < 2:
        raise MangaFirstError("canonical schedule must use variable shot durations")
    if tuple(item["stage"] for item in manifest.checkpoints) != CHECKPOINT_STAGES:
        raise MangaFirstError("checkpoint stages are incomplete or out of order")
    if manifest.provider_dispatch_count != 0:
        raise MangaFirstError("L4 provider dispatch count must remain zero")
    if manifest.template_audit.get("legacy_template_dominance_removed") is not True:
        raise MangaFirstError("legacy template dominance audit did not pass")
    if manifest.assembly_contract.get("manual_editing_required") is not False:
        raise MangaFirstError("assembly contract must not require manual editing")
    return manifest


def build_studio_demo_projection(manifest_value: ProductionTruthManifest | dict[str, Any]) -> dict[str, Any]:
    manifest = validate_manga_first_manifest(manifest_value)
    projection = deepcopy(manifest.studio_projection)
    projection["manifest_sha256"] = manifest.manifest_sha256
    projection["truth_source"] = "episode_aggregate_backed_manga_first_manifest"
    projection["provider_dispatch_count"] = 0
    projection["non_claims"] = list(manifest.evidence_boundaries.values())
    return projection


def _story_bible(brief: MangaFirstBrief) -> dict[str, Any]:
    return {
        "title": brief.title,
        "logline": brief.logline,
        "style": brief.style,
        "audience": brief.audience,
        "tone": brief.tone,
        "world_rules": _world_rules(brief),
        "character_count": len(brief.characters),
        "scene_count": len(brief.scenes),
        "shot_count": len(brief.beats),
        "source": "owner_brief",
    }


def _scene_payload(scene: MangaSceneBrief) -> dict[str, Any]:
    return {
        "scene_id": scene.scene_id,
        "name": scene.name,
        "location_type": scene.location_type,
        "visual_mood": scene.visual_mood,
        "story_function": scene.story_function,
        "source": "owner_brief",
    }


def _reference_set(brief: MangaFirstBrief) -> dict[str, Any]:
    return {
        "reference_set_id": f"{brief.project_id}-reference-set-v1",
        "source": "owner_brief",
        "style": brief.style,
        "characters": [
            {
                "character_id": item.character_id,
                "name": item.name,
                "role": item.role,
                "visual_identity": item.visual_identity,
                "continuity_rules": list(item.continuity_rules),
            }
            for item in brief.characters
        ],
        "scene_refs": [scene.scene_id for scene in brief.scenes],
        "provider_asset_status": "not_requested",
        "human_approval_status": "not_claimed",
    }


def _world_rules(brief: MangaFirstBrief) -> list[str]:
    return [
        f"Workload is owner-selected manga/anime narrative: {brief.style}.",
        "Brief drives Bible, Scene, Shot, ReferenceSet, and ProductionRecipe.",
        "No legacy fixed example template may become canonical authority.",
        "Provider calls remain closed until explicit owner cost cap approval.",
    ]


def _shot_prompt(
    brief: MangaFirstBrief,
    scene: MangaSceneBrief,
    characters: list[MangaCharacterBrief],
    beat: Any,
) -> str:
    names = ", ".join(item.name for item in characters)
    identities = "; ".join(f"{item.name}: {item.visual_identity}" for item in characters)
    return (
        f"{brief.style} narrative frame for '{brief.title}'. Scene '{scene.name}' "
        f"({scene.location_type}, {scene.visual_mood}). Characters: {names}. "
        f"Continuity: {identities}. Action: {beat.action}. Emotional turn: {beat.emotional_turn}."
    )


def _production_recipe(brief: MangaFirstBrief) -> dict[str, Any]:
    return {
        "recipe_id": f"{brief.project_id}-recipe-v1",
        "workload": "manga_first_commercial_slice",
        "provider_dispatch_count": 0,
        "provider_policy": "closed_until_OWNER_COST_CAP_NEEDED",
        "stages": [
            {"stage": "story", "mode": "deterministic_compiler", "writes": "story_bible"},
            {"stage": "keyframe", "mode": "provider_gated", "project_lock_held_while_waiting": False},
            {"stage": "video", "mode": "provider_gated", "project_lock_held_while_waiting": False},
            {"stage": "audio_wait", "mode": "blocked_until_visual_QA_and_cost_cap"},
            {"stage": "compose", "mode": "automatic_canonical_timeline"},
            {"stage": "technical_QA", "mode": "ffprobe_hash_lineage"},
            {"stage": "visual_creative_QA", "mode": "independent_evaluator_required"},
        ],
        "audio_failure_policy": "preserve_visual_assets_and_lineage",
        "manual_editing_required": False,
    }


def _fact_chain(project_id: str, shots: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for shot in shots:
        shot_id = shot["shot_id"]
        rows.append(
            {
                "shot_id": shot_id,
                "task_id": f"task-{shot_id}",
                "attempt_id": f"attempt-{shot_id}-001",
                "artifact_version_id": f"artifact-version-{shot_id}-canonical-prompt-v1",
                "candidate_id": f"candidate-{shot_id}-provider-pending",
                "selection_id": f"selection-{shot_id}-pending",
                "review_id": f"review-{shot_id}-pending",
                "delivery_id": f"delivery-{project_id}-pending",
                "chain": [
                    "Shot",
                    "Task",
                    "Attempt",
                    "ArtifactVersion",
                    "Candidate",
                    "Selection",
                    "Review",
                    "Delivery",
                ],
                "candidate": {"status": "waiting_provider_authorization", "artifact_present": False, "fabricated_state": False},
                "selection": {"status": "not_selected", "fabricated_state": False},
                "review": {"status": "not_started", "fabricated_state": False},
            }
        )
    return {
        "schema_version": "afs.manga_first_l4a.fact_chain.v0.2",
        "authority": "episode_production_aggregate_with_runtime_artifact_refs",
        "required_chain": "Shot->Task->Attempt->ArtifactVersion->Candidate->Selection->Review->Delivery",
        "rows": rows,
        "studio_fabricated_state_allowed": False,
    }


def _checkpoint_contract(project_id: str, stage: str) -> dict[str, Any]:
    provider_wait = stage in {"keyframe", "video", "audio_wait"}
    status = "succeeded" if stage == "story" else "queued"
    if provider_wait:
        status = "waiting_provider_authorization"
    if stage in {"technical_QA", "visual_creative_QA"}:
        status = "not_started"
    return {
        "checkpoint_id": f"{project_id}-{stage}",
        "stage": stage,
        "status": status,
        "lease_supported": True,
        "idempotency_supported": True,
        "charge_fingerprint_supported": stage in {"keyframe", "video", "audio_wait"},
        "pause_supported": True,
        "cancel_supported": True,
        "retry_supported": True,
        "dlq_supported": True,
        "restart_takeover_supported": True,
        "project_lock_held_while_waiting": False if provider_wait else True,
        "provider_dispatch_count": 0,
    }


def _timeline(brief: MangaFirstBrief, shots: list[dict[str, Any]], schedule: tuple[tuple[Decimal, Decimal], ...]) -> dict[str, Any]:
    return {
        "target_duration_seconds": decimal_string(brief.target_duration_seconds),
        "duration_seconds": decimal_string(schedule[-1][1]),
        "shot_count": len(shots),
        "range_contract": "90_to_120_seconds",
        "variable_duration_schedule": [
            {
                "shot_id": shot["shot_id"],
                "start_seconds": shot["start_seconds"],
                "end_seconds": shot["end_seconds"],
                "duration_seconds": shot["duration_seconds"],
            }
            for shot in shots
        ],
        "manual_editing_required": False,
        "compose_mode": "automatic_canonical_timeline",
    }


def _assembly_contract(project_id: str) -> dict[str, Any]:
    return {
        "schema_version": "afs.manga_first_l4b.assembly_contract.v0.1",
        "project_id": project_id,
        "final_mp4": {"required": True, "audio_allowed_before_gate": False},
        "timeline_otio": {"required": True, "schema": "afs.otio.timeline-export.v0.1"},
        "proxy_media": {"required": True, "schema": "afs.proxy-media.v0.1"},
        "artifact_version_manifest": {"required": True, "schema": "afs.artifact-version-manifest.v0.1"},
        "rights_manifest": {"required": True, "schema": "afs.rights-manifest.v0.1"},
        "cost_manifest": {"required": True, "schema": "afs.cost-manifest.v0.1"},
        "production_manifest": {"required": True, "schema": "afs.production-truth-manifest.v0.1"},
        "lineage_manifest": {
            "required": True,
            "schema": "afs.lineage-manifest.v0.1",
            "required_chain": "Shot->Task->Attempt->ArtifactVersion->Candidate->Selection->Review->Delivery",
        },
        "manual_editing_required": False,
    }


def _studio_projection(
    brief: MangaFirstBrief,
    shots: list[dict[str, Any]],
    fact_chain: dict[str, Any],
    checkpoints: tuple[dict[str, Any], ...],
    assembly_contract: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "afs.manga_first_l4a.studio_projection.v0.1",
        "project": {
            "project_id": brief.project_id,
            "title": brief.title,
            "workload": "manga_first",
            "status": "L4B_release_readiness_provider_closed",
        },
        "shot_status": [
            {
                "shot_id": shot["shot_id"],
                "sequence": shot["sequence"],
                "scene_id": shot["scene_id"],
                "status": shot["status"],
                "duration_seconds": shot["duration_seconds"],
                "candidate_count": 1,
                "selected_candidate_id": None,
            }
            for shot in shots
        ],
        "candidates": [
            {
                "candidate_id": row["candidate_id"],
                "shot_id": row["shot_id"],
                "status": row["candidate"]["status"],
                "artifact_present": False,
                "fabricated_state": False,
            }
            for row in fact_chain["rows"]
        ],
        "timeline": [{"shot_id": shot["shot_id"], "start_seconds": shot["start_seconds"], "end_seconds": shot["end_seconds"]} for shot in shots],
        "qa": {
            "technical_QA": "not_started",
            "visual_creative_QA": "not_started",
            "p1_count": 0,
            "gate": "RESUMABLE_CANONICAL_PRODUCTION_AND_VISUAL_CREATIVE_QA_BEFORE_AUDIO_OPEN",
        },
        "final_demo": {
            "status": "not_composed_for_new_manga_authority",
            "automatic_compose_contract": "ready_after_visual_candidates_selected",
        },
        "assembly_contract": assembly_contract,
        "checkpoints": [
            {
                "stage": item["stage"],
                "status": item["status"],
                "lease_supported": item["lease_supported"],
                "retry_supported": item["retry_supported"],
            }
            for item in checkpoints
        ],
        "provider_dispatch_count": 0,
    }


def _template_audit(story_bible: dict[str, Any], scenes: tuple[dict[str, Any], ...], shots: list[dict[str, Any]]) -> dict[str, Any]:
    canonical_payload = {"story_bible": story_bible, "scenes": scenes, "shots": shots}
    lower = json.dumps(canonical_payload, ensure_ascii=False, sort_keys=True).lower()
    injected = [term for term in LEGACY_TEMPLATE_TERMS if term in lower]
    return {
        "legacy_template_dominance_removed": not injected,
        "forbidden_legacy_terms_found_in_canonical_truth": injected,
        "legacy_terms_removed_from_defaults": list(LEGACY_TEMPLATE_TERMS),
        "audit_scope": "canonical truth fields only; fixture boundary may mention legacy L3 findings",
    }


def _evidence_boundaries() -> dict[str, Any]:
    return {
        "real_story_fixture_authority": "recovery_regression_only_not_new_canonical_truth",
        "provider_smoke": "not_run",
        "generated_media_qa": "not_claimed",
        "human_acceptance": "not_claimed",
        "business_validation": "not_claimed",
        "gate": "RESUMABLE_CANONICAL_PRODUCTION_AND_VISUAL_CREATIVE_QA_BEFORE_AUDIO_OPEN",
    }
