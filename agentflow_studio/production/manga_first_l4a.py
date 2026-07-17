from __future__ import annotations

import hashlib
import json
import subprocess
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MANGA_FIRST_CONTRACT_VERSION = "afs.manga_first_l4a.v0.1"
SAFE_ID = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$"
SHA256 = r"^[a-f0-9]{64}$"
TARGET_MIN_SECONDS = Decimal("90.000")
TARGET_MAX_SECONDS = Decimal("120.000")
CHECKPOINT_STAGES = (
    "story",
    "keyframe",
    "video",
    "audio_wait",
    "compose",
    "technical_QA",
    "visual_creative_QA",
)
LEGACY_TEMPLATE_TERMS = (
    "pier",
    "lighthouse",
    "robot",
    "blue raincoat",
    "old pier",
    "failed lighthouse climb",
)
L3_P1_TITLES = (
    "Canonical story authority diverges before generation",
    "Main character identity and costume are not locked",
    "Exact 120-second editorial schedule is absent",
    "Shot-013 misses resolution action and breaks location continuity",
    "Shot-007 contains an unplanned internal scene transformation",
)


class MangaFirstError(ValueError):
    pass


class CheckpointStateError(RuntimeError):
    pass


class MangaFirstModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MangaCharacterBrief(MangaFirstModel):
    character_id: str = Field(pattern=SAFE_ID)
    name: str = Field(min_length=1, max_length=80)
    role: str = Field(min_length=1, max_length=120)
    visual_identity: str = Field(min_length=1, max_length=500)
    continuity_rules: tuple[str, ...] = Field(min_length=1, max_length=12)


class MangaSceneBrief(MangaFirstModel):
    scene_id: str = Field(pattern=SAFE_ID)
    name: str = Field(min_length=1, max_length=120)
    location_type: str = Field(min_length=1, max_length=160)
    visual_mood: str = Field(min_length=1, max_length=240)
    story_function: str = Field(min_length=1, max_length=240)


class MangaBeatBrief(MangaFirstModel):
    beat_id: str = Field(pattern=SAFE_ID)
    scene_id: str = Field(pattern=SAFE_ID)
    character_ids: tuple[str, ...] = Field(min_length=1, max_length=3)
    action: str = Field(min_length=1, max_length=500)
    emotional_turn: str = Field(min_length=1, max_length=240)
    duration_weight: Decimal = Field(default=Decimal("1.0"), gt=Decimal("0.1"), le=Decimal("3.0"))

    @field_validator("duration_weight", mode="before")
    @classmethod
    def duration_weight_to_decimal(cls, value: Any) -> Decimal:
        return Decimal(str(value))


class MangaFirstBrief(MangaFirstModel):
    project_id: str = Field(pattern=SAFE_ID)
    title: str = Field(min_length=1, max_length=160)
    logline: str = Field(min_length=1, max_length=800)
    style: Literal["anime", "manga", "manhua", "webtoon", "manga_drama"]
    target_duration_seconds: Decimal = Field(ge=TARGET_MIN_SECONDS, le=TARGET_MAX_SECONDS)
    characters: tuple[MangaCharacterBrief, ...] = Field(min_length=1, max_length=3)
    scenes: tuple[MangaSceneBrief, ...] = Field(min_length=2, max_length=4)
    beats: tuple[MangaBeatBrief, ...] = Field(min_length=12, max_length=15)
    audience: str = Field(min_length=1, max_length=200)
    tone: str = Field(min_length=1, max_length=240)
    owner_decision: Literal["manga_first"] = "manga_first"

    @field_validator("target_duration_seconds", mode="before")
    @classmethod
    def duration_to_decimal(cls, value: Any) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

    @model_validator(mode="after")
    def references_are_exact_and_brief_drives_all_shots(self) -> "MangaFirstBrief":
        character_ids = {item.character_id for item in self.characters}
        scene_ids = {item.scene_id for item in self.scenes}
        if len(character_ids) != len(self.characters):
            raise ValueError("characters must use unique ids")
        if len(scene_ids) != len(self.scenes):
            raise ValueError("scenes must use unique ids")
        seen_beats: set[str] = set()
        for beat in self.beats:
            if beat.beat_id in seen_beats:
                raise ValueError("beats must use unique ids")
            seen_beats.add(beat.beat_id)
            if beat.scene_id not in scene_ids:
                raise ValueError("beat scene_id must resolve to a scene in the brief")
            missing = [item for item in beat.character_ids if item not in character_ids]
            if missing:
                raise ValueError("beat character_ids must resolve to characters in the brief")
        return self


class ProductionTruthManifest(MangaFirstModel):
    schema_version: Literal["afs.manga_first_l4a.v0.1"] = MANGA_FIRST_CONTRACT_VERSION
    project_id: str = Field(pattern=SAFE_ID)
    manifest_sha256: str = Field(pattern=SHA256)
    provider_dispatch_count: Literal[0] = 0
    owner_decision: Literal["manga_first"]
    story_bible: dict[str, Any]
    scenes: tuple[dict[str, Any], ...]
    shots: tuple[dict[str, Any], ...]
    reference_set: dict[str, Any]
    production_recipe: dict[str, Any]
    timeline: dict[str, Any]
    fact_chain: dict[str, Any]
    checkpoints: tuple[dict[str, Any], ...]
    studio_projection: dict[str, Any]
    template_audit: dict[str, Any]
    evidence_boundaries: dict[str, Any]


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def json_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compile_manga_first_manifest(brief_value: MangaFirstBrief | dict[str, Any]) -> ProductionTruthManifest:
    brief = MangaFirstBrief.model_validate(brief_value)
    schedule = _variable_schedule(
        count=len(brief.beats),
        target_seconds=brief.target_duration_seconds,
        weights=tuple(beat.duration_weight for beat in brief.beats),
    )
    character_index = {item.character_id: item for item in brief.characters}
    scene_index = {item.scene_id: item for item in brief.scenes}
    story_bible = {
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
    scenes = tuple(
        {
            "scene_id": scene.scene_id,
            "name": scene.name,
            "location_type": scene.location_type,
            "visual_mood": scene.visual_mood,
            "story_function": scene.story_function,
            "source": "owner_brief",
        }
        for scene in brief.scenes
    )
    reference_set = {
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
    shots = []
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
                "start_seconds": _decimal_string(start),
                "end_seconds": _decimal_string(end),
                "duration_seconds": _decimal_string(end - start),
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
    timeline = {
        "target_duration_seconds": _decimal_string(brief.target_duration_seconds),
        "duration_seconds": _decimal_string(schedule[-1][1]),
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
        "otio_contract": {
            "status": "reserved",
            "schema": "afs.otio.timeline-export.v0.1",
            "requires_exact_same_schedule": True,
        },
        "proxy_media_contract": {
            "status": "reserved",
            "schema": "afs.proxy-media.v0.1",
            "must_reference_artifact_versions": True,
        },
        "lineage_manifest_contract": {
            "status": "active",
            "schema": "afs.lineage-manifest.v0.1",
            "required_chain": "Shot->Task->Attempt->ArtifactVersion->Candidate->Selection->Review->Delivery",
        },
    }
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
        "fact_chain": fact_chain,
        "checkpoints": checkpoints,
        "studio_projection": _studio_projection(brief, shots, fact_chain, checkpoints),
        "template_audit": _template_audit(story_bible, scenes, shots),
        "evidence_boundaries": {
            "real_story_fixture_authority": "recovery_regression_only_not_new_canonical_truth",
            "provider_smoke": "not_run",
            "generated_media_qa": "not_claimed",
            "human_acceptance": "not_claimed",
            "business_validation": "not_claimed",
            "gate": "RESUMABLE_CANONICAL_PRODUCTION_AND_VISUAL_CREATIVE_QA_BEFORE_AUDIO_OPEN",
        },
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
        raise MangaFirstError("L4A provider dispatch count must remain zero")
    if manifest.template_audit.get("legacy_template_dominance_removed") is not True:
        raise MangaFirstError("legacy template dominance audit did not pass")
    return manifest


def build_studio_demo_projection(manifest_value: ProductionTruthManifest | dict[str, Any]) -> dict[str, Any]:
    manifest = validate_manga_first_manifest(manifest_value)
    projection = deepcopy(manifest.studio_projection)
    projection["manifest_sha256"] = manifest.manifest_sha256
    projection["truth_source"] = "schema_validated_manga_first_manifest"
    projection["provider_dispatch_count"] = 0
    projection["non_claims"] = list(manifest.evidence_boundaries.values())
    return projection


def build_legacy_fixture_regression_manifest(
    *,
    l1_root: str | Path,
    l2_root: str | Path,
    l3_root: str | Path,
) -> dict[str, Any]:
    l1 = Path(l1_root)
    l2 = Path(l2_root)
    l3 = Path(l3_root)
    l1_manifest = _read_json(l1 / "recovery_manifest.json")
    l2_manifest = _read_json(l2 / "timeline_manifest.json")
    l3_eval = _read_json(l3 / "visual_creative_evaluation.json")
    p1_findings = [
        {
            "id": item["id"],
            "severity": item["severity"],
            "title": item["title"],
            "observation": item["observation"],
        }
        for item in l3_eval.get("findings", [])
        if item.get("severity") == "P1"
    ]
    body = {
        "schema_version": "afs.manga_first_l4a.legacy_regression_fixture.v0.1",
        "authority": "recovery_and_regression_fixture_only",
        "not_new_canonical_truth": True,
        "l1": {
            "root": str(l1),
            "manifest_sha256": sha256_file(l1 / "recovery_manifest.json"),
            "status": l1_manifest.get("status"),
            "png_count": len(list((l1 / "media" / "keyframes").glob("*.png"))),
            "mp4_count": len(list((l1 / "media" / "videos").glob("*.mp4"))),
            "verification": l1_manifest.get("verification", {}),
        },
        "l2": {
            "root": str(l2),
            "timeline_manifest_sha256": sha256_file(l2 / "timeline_manifest.json"),
            "status": l2_manifest.get("status"),
            "duration_seconds": l2_manifest.get("outputs", {}).get("full_coverage_silent_review", {}).get("duration_seconds"),
            "audio_stream_count": l2_manifest.get("outputs", {}).get("full_coverage_silent_review", {}).get("audio_stream_count"),
        },
        "l3": {
            "root": str(l3),
            "evaluation_sha256": sha256_file(l3 / "visual_creative_evaluation.json"),
            "verdict": l3_eval.get("verdict"),
            "severity_counts": l3_eval.get("severity_counts"),
            "p1_findings": p1_findings,
            "inspection": l3_eval.get("inspection", {}),
        },
        "provider_dispatch_count": 0,
        "non_claims": [
            "not_final_manga_first_canonical_authority",
            "not_visual_creative_qa_pass",
            "not_human_acceptance",
            "not_business_validation",
        ],
    }
    return {**body, "fixture_manifest_sha256": json_digest(body)}


def compose_legacy_fixture_silent_assembly(
    *,
    l1_root: str | Path,
    l3_root: str | Path,
    output_dir: str | Path,
    target_duration_seconds: Decimal | int | str = Decimal("120.000"),
    ffmpeg_executable: str = "ffmpeg",
    ffprobe_executable: str = "ffprobe",
) -> dict[str, Any]:
    l1 = Path(l1_root)
    l3 = Path(l3_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    target = Decimal(str(target_duration_seconds)).quantize(Decimal("0.001"))
    source_videos = tuple(l1 / "media" / "videos" / f"shot-{index:03d}.mp4" for index in range(1, 14))
    missing = [str(path) for path in source_videos if not path.is_file()]
    if missing:
        raise MangaFirstError(f"legacy fixture videos are missing: {missing[:3]}")
    source_duration = Decimal("10.041667")
    schedule = _variable_schedule(
        count=len(source_videos),
        target_seconds=target,
        source_max_seconds=source_duration,
    )
    episode_path = out / "manga_first_l4a_fixture_silent_assembly.mp4"
    command = _silent_concat_command(
        source_videos,
        schedule,
        episode_path,
        ffmpeg_executable=ffmpeg_executable,
    )
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "ffmpeg failed")[-3000:])
    probe = _ffprobe(episode_path, ffprobe_executable)
    video_streams = [item for item in probe.get("streams", []) if item.get("codec_type") == "video"]
    audio_streams = [item for item in probe.get("streams", []) if item.get("codec_type") == "audio"]
    if len(video_streams) != 1 or audio_streams:
        raise MangaFirstError("silent assembly must contain exactly one video stream and no audio")
    duration = Decimal(str(probe.get("format", {}).get("duration", "0"))).quantize(Decimal("0.001"))
    if duration < TARGET_MIN_SECONDS or duration > TARGET_MAX_SECONDS:
        raise MangaFirstError("silent assembly duration must stay inside 90 to 120 seconds")
    l3_eval = _read_json(l3 / "visual_creative_evaluation.json")
    p1 = [
        {"id": item["id"], "title": item["title"]}
        for item in l3_eval.get("findings", [])
        if item.get("severity") == "P1"
    ]
    timeline = [
        {
            "shot_id": f"shot-{index + 1:03d}",
            "source_path": str(source_videos[index]),
            "source_sha256": sha256_file(source_videos[index]),
            "start_seconds": _decimal_string(start),
            "end_seconds": _decimal_string(end),
            "duration_seconds": _decimal_string(end - start),
            "source_in_seconds": "0.000",
            "source_out_seconds": _decimal_string(end - start),
        }
        for index, (start, end) in enumerate(schedule)
    ]
    manifest = {
        "schema_version": "afs.manga_first_l4a.silent_fixture_assembly.v0.1",
        "artifact_type": "provider_free_silent_fixture_regression",
        "episode_path": str(episode_path),
        "episode_sha256": sha256_file(episode_path),
        "episode_bytes": episode_path.stat().st_size,
        "duration_seconds": _decimal_string(duration),
        "shot_count": len(timeline),
        "provider_dispatch_count": 0,
        "audio_stream_count": 0,
        "manual_editing_required": False,
        "timeline": timeline,
        "lineage_manifest_contract": "afs.lineage-manifest.v0.1",
        "p1_preserved": p1,
        "verdict": "fixture_regression_only_p1_open",
        "non_claims": [
            "not_final_manga_first_delivery",
            "not_visual_creative_qa_pass",
            "not_human_acceptance",
            "not_business_validation",
        ],
    }
    manifest_path = out / "lineage_manifest.json"
    timeline_path = out / "timeline_manifest.json"
    qa_path = out / "technical_qa.json"
    _write_json(manifest_path, manifest)
    _write_json(timeline_path, {"timeline": timeline, "timeline_sha256": json_digest(timeline)})
    _write_json(
        qa_path,
        {
            "schema_version": "afs.manga_first_l4a.technical_qa.v0.1",
            "ffprobe": probe,
            "full_ffmpeg_decode_ok": _decode_ok(episode_path, ffmpeg_executable),
            "no_audio": True,
            "episode_sha256": manifest["episode_sha256"],
            "lineage_manifest_sha256": sha256_file(manifest_path),
            "provider_dispatch_count": 0,
        },
    )
    projection = {
        "schema_version": "afs.manga_first_l4a.studio_demo_projection.v0.1",
        "project_id": "real-story-20260717T143658Z-6ea4fbee",
        "truth_source": "legacy_recovery_fixture_regression_only",
        "final_demo": {
            "status": "technical_silent_assembly_ready",
            "preview_path": str(episode_path),
            "sha256": manifest["episode_sha256"],
            "duration_seconds": manifest["duration_seconds"],
            "audio_status": "no_audio",
        },
        "qa": {
            "technical_QA": "passed",
            "visual_creative_QA": "P1_open_from_L3",
            "p1_count": len(p1),
            "p1_findings": p1,
        },
        "non_claims": manifest["non_claims"],
    }
    projection_path = out / "studio_demo_projection.json"
    _write_json(projection_path, projection)
    return {
        "episode_path": episode_path,
        "episode_sha256": manifest["episode_sha256"],
        "manifest_path": manifest_path,
        "manifest_sha256": sha256_file(manifest_path),
        "timeline_path": timeline_path,
        "technical_qa_path": qa_path,
        "studio_projection_path": projection_path,
        "duration_seconds": manifest["duration_seconds"],
        "p1_count": len(p1),
        "provider_dispatch_count": 0,
    }


class CheckpointLedgerStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self, manifest: ProductionTruthManifest | dict[str, Any]) -> dict[str, Any]:
        parsed = validate_manga_first_manifest(manifest)
        state = {
            "schema_version": "afs.manga_first_l4a.checkpoint_ledger.v0.1",
            "project_id": parsed.project_id,
            "manifest_sha256": parsed.manifest_sha256,
            "provider_dispatch_count": 0,
            "version": 1,
            "idempotency_records": {},
            "checkpoints": {
                item["stage"]: {
                    **item,
                    "lease": None,
                    "retry_count": 0,
                    "control_state": "active",
                    "dlq": None,
                }
                for item in parsed.checkpoints
            },
        }
        self._write(state)
        return state

    def apply(
        self,
        *,
        stage: str,
        action: Literal["acquire_lease", "takeover_expired", "pause", "cancel", "retry", "dlq", "complete"],
        idempotency_key: str,
        worker_id: str = "l4a-worker",
        now: str = "2026-07-18T00:00:00+00:00",
        lease_expires_at: str = "2026-07-18T00:15:00+00:00",
        reason: str = "",
    ) -> dict[str, Any]:
        state = self._read()
        records = state.setdefault("idempotency_records", {})
        if idempotency_key in records:
            return deepcopy(records[idempotency_key]["result"])
        if stage not in state["checkpoints"]:
            raise CheckpointStateError("checkpoint stage does not exist")
        checkpoint = state["checkpoints"][stage]
        if action == "acquire_lease":
            lease = checkpoint.get("lease")
            if lease and lease.get("expires_at", "") > now and lease.get("worker_id") != worker_id:
                raise CheckpointStateError("checkpoint lease is still active")
            checkpoint["lease"] = {
                "worker_id": worker_id,
                "acquired_at": now,
                "expires_at": lease_expires_at,
            }
            checkpoint["status"] = "running"
        elif action == "takeover_expired":
            lease = checkpoint.get("lease")
            if not lease or lease.get("expires_at", "") > now:
                raise CheckpointStateError("only expired leases can be taken over")
            checkpoint["lease"] = {
                "worker_id": worker_id,
                "acquired_at": now,
                "expires_at": lease_expires_at,
                "takeover_of": lease.get("worker_id"),
            }
            checkpoint["status"] = "running"
        elif action == "pause":
            checkpoint["control_state"] = "paused"
        elif action == "cancel":
            checkpoint["control_state"] = "cancelled"
            checkpoint["status"] = "cancelled"
            checkpoint["lease"] = None
        elif action == "retry":
            checkpoint["retry_count"] = int(checkpoint.get("retry_count") or 0) + 1
            checkpoint["status"] = "queued"
            checkpoint["lease"] = None
        elif action == "dlq":
            checkpoint["status"] = "dead_letter"
            checkpoint["dlq"] = {"reason": reason or "unspecified", "recorded_at": now}
            checkpoint["lease"] = None
        elif action == "complete":
            checkpoint["status"] = "succeeded"
            checkpoint["lease"] = None
        else:
            raise CheckpointStateError("unsupported checkpoint action")
        state["version"] = int(state["version"]) + 1
        result = {"version": state["version"], "checkpoint": deepcopy(checkpoint)}
        records[idempotency_key] = {"stage": stage, "action": action, "result": result}
        self._write(state)
        return result

    def _read(self) -> dict[str, Any]:
        return _read_json(self.path)

    def _write(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(self.path, state)


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
    beat: MangaBeatBrief,
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
        task_id = f"task-{shot_id}"
        attempt_id = f"attempt-{shot_id}-001"
        artifact_version_id = f"artifact-version-{shot_id}-canonical-prompt-v1"
        candidate_id = f"candidate-{shot_id}-provider-pending"
        selection_id = f"selection-{shot_id}-pending"
        review_id = f"review-{shot_id}-pending"
        rows.append(
            {
                "shot_id": shot_id,
                "task_id": task_id,
                "attempt_id": attempt_id,
                "artifact_version_id": artifact_version_id,
                "candidate_id": candidate_id,
                "selection_id": selection_id,
                "review_id": review_id,
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
                "candidate": {
                    "status": "waiting_provider_authorization",
                    "artifact_present": False,
                    "fabricated_state": False,
                },
                "selection": {"status": "not_selected", "fabricated_state": False},
                "review": {"status": "not_started", "fabricated_state": False},
            }
        )
    return {
        "schema_version": "afs.manga_first_l4a.fact_chain.v0.1",
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
        "pause_supported": True,
        "cancel_supported": True,
        "retry_supported": True,
        "dlq_supported": True,
        "restart_takeover_supported": True,
        "project_lock_held_while_waiting": False if provider_wait else True,
        "provider_dispatch_count": 0,
    }


def _studio_projection(
    brief: MangaFirstBrief,
    shots: list[dict[str, Any]],
    fact_chain: dict[str, Any],
    checkpoints: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    return {
        "schema_version": "afs.manga_first_l4a.studio_projection.v0.1",
        "project": {
            "project_id": brief.project_id,
            "title": brief.title,
            "workload": "manga_first",
            "status": "L4A_planning_provider_closed",
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
        "timeline": [
            {
                "shot_id": shot["shot_id"],
                "start_seconds": shot["start_seconds"],
                "end_seconds": shot["end_seconds"],
            }
            for shot in shots
        ],
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
    canonical_payload = {
        "story_bible": story_bible,
        "scenes": scenes,
        "shots": shots,
    }
    lower = json.dumps(canonical_payload, ensure_ascii=False, sort_keys=True).lower()
    injected = [term for term in LEGACY_TEMPLATE_TERMS if term in lower]
    return {
        "legacy_template_dominance_removed": not injected,
        "forbidden_legacy_terms_found_in_canonical_truth": injected,
        "legacy_terms_removed_from_defaults": list(LEGACY_TEMPLATE_TERMS),
        "audit_scope": "canonical truth fields only; fixture boundary may mention legacy L3 findings",
    }


def _variable_schedule(
    *,
    count: int,
    target_seconds: Decimal,
    weights: tuple[Decimal, ...] | None = None,
    source_max_seconds: Decimal | None = None,
) -> tuple[tuple[Decimal, Decimal], ...]:
    target = Decimal(str(target_seconds)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if count <= 0:
        raise MangaFirstError("schedule count must be positive")
    if weights is None:
        pattern = (Decimal("0.96"), Decimal("1.04"), Decimal("0.93"), Decimal("1.07"), Decimal("0.99"))
        weights = tuple(pattern[index % len(pattern)] for index in range(count))
    if len(weights) != count:
        raise MangaFirstError("schedule weights must match shot count")
    total_weight = sum(weights)
    durations = [
        (target * weight / total_weight).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        for weight in weights
    ]
    if source_max_seconds is not None and any(item > source_max_seconds for item in durations):
        overflow = Decimal("0")
        adjusted: list[Decimal] = []
        for item in durations:
            if item > source_max_seconds:
                overflow += item - source_max_seconds
                adjusted.append(source_max_seconds)
            else:
                adjusted.append(item)
        receivers = [index for index, item in enumerate(adjusted) if item < source_max_seconds]
        for index in receivers:
            if overflow <= 0:
                break
            room = source_max_seconds - adjusted[index]
            delta = min(room, overflow / Decimal(max(len(receivers), 1)))
            adjusted[index] = (adjusted[index] + delta).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            overflow -= delta
        durations = adjusted
    correction = target - sum(durations)
    durations[-1] = (durations[-1] + correction).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if any(item <= 0 for item in durations):
        raise MangaFirstError("schedule produced non-positive duration")
    starts: list[tuple[Decimal, Decimal]] = []
    cursor = Decimal("0.000")
    for item in durations:
        end = (cursor + item).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        starts.append((cursor, end))
        cursor = end
    if cursor != target:
        raise MangaFirstError("schedule does not sum exactly to target")
    return tuple(starts)


def _silent_concat_command(
    source_videos: tuple[Path, ...],
    schedule: tuple[tuple[Decimal, Decimal], ...],
    output_path: Path,
    *,
    ffmpeg_executable: str,
) -> list[str]:
    command = [ffmpeg_executable, "-hide_banner", "-loglevel", "error", "-y"]
    filters: list[str] = []
    labels: list[str] = []
    for index, (path, (start, end)) in enumerate(zip(source_videos, schedule)):
        duration = end - start
        command.extend(["-ss", "0", "-t", _decimal_string(duration), "-i", str(path)])
        label = f"v{index}"
        filters.append(
            f"[{index}:v]scale=1280:720:force_original_aspect_ratio=increase,"
            f"crop=1280:720,fps=24,trim=duration={_decimal_string(duration)},"
            f"setpts=PTS-STARTPTS,setsar=1,format=yuv420p[{label}]"
        )
        labels.append(f"[{label}]")
    filters.append(f"{''.join(labels)}concat=n={len(labels)}:v=1:a=0[outv]")
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[outv]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "22",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "24",
            "-threads",
            "1",
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            "-metadata",
            "creation_time=2000-01-01T00:00:00Z",
            str(output_path),
        ]
    )
    return command


def _ffprobe(path: Path, ffprobe_executable: str) -> dict[str, Any]:
    result = subprocess.run(
        [
            ffprobe_executable,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,codec_name,avg_frame_rate,nb_frames,width,height",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "ffprobe failed")[-1000:])
    return json.loads(result.stdout)


def _decode_ok(path: Path, ffmpeg_executable: str) -> bool:
    result = subprocess.run(
        [ffmpeg_executable, "-v", "error", "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _read_json(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MangaFirstError(f"JSON file is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise MangaFirstError("JSON file must contain an object")
    return value


def _write_json(path: str | Path, value: Any) -> None:
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _decimal_string(value: Decimal) -> str:
    return str(Decimal(value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "CHECKPOINT_STAGES",
    "L3_P1_TITLES",
    "MANGA_FIRST_CONTRACT_VERSION",
    "CheckpointLedgerStore",
    "MangaFirstBrief",
    "MangaFirstError",
    "ProductionTruthManifest",
    "build_legacy_fixture_regression_manifest",
    "build_studio_demo_projection",
    "compile_manga_first_manifest",
    "compose_legacy_fixture_silent_assembly",
    "json_digest",
    "sha256_file",
    "validate_manga_first_manifest",
]
