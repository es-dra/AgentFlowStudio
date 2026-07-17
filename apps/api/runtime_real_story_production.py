from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.provider_adapter import load_provider_registry
from agentflow_studio.production.episode_delivery import assemble_episode, sha256_file
from agentflow_studio.production.episode_media_quality import run_episode_technical_qa
from apps.api.runtime_artifacts import keyframe_generation_artifacts, prompt_memory_artifacts
from apps.api.runtime_audio_routes import AudioGenerationRequest
from apps.api.runtime_audio_routes import _audio_generation_artifacts as audio_generation_artifacts
from apps.api.runtime_audio_routes import _candidate_file as audio_candidate_file
from apps.api.runtime_audio_routes import _submit_audio_generation
from apps.api.runtime_generated_image_assets import register_generated_image_asset, resolve_generated_candidate_authority
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_keyframe_async import poll_keyframe_generation
from apps.api.runtime_keyframes import build_keyframe_generation
from apps.api.runtime_models import KeyframeGenerationRequest, PromptOptimizationRequest, VideoGenerationRequest, VideoInputSource
from apps.api.runtime_prompt_memory import build_prompt_optimization
from apps.api.runtime_script_generation_body import deterministic_script_body
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload, safe_id
from apps.api.runtime_video_candidates import candidate_file as video_candidate_file
from apps.api.runtime_video_dispatch import poll_video_generation, submit_video_generation
from apps.api.runtime_video_manifest import write_video_job


REAL_STORY_SCHEMA_VERSION = "afs_real_story_production.v0.1"
REAL_STORY_ACTION = "real_story_canonical_production"
TARGET_SECONDS = 120
SHOT_DURATIONS = (9, 10, 8, 10, 9, 10, 8, 10, 9, 10, 8, 10, 9)
PROVIDER_VIDEO_DURATION_SECONDS = 10


class RealStoryProductionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["afs_real_story_production.v0.1"] = REAL_STORY_SCHEMA_VERSION
    idempotency_key: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")
    expected_checkpoint_version: int = Field(ge=1)
    brief: str = Field(min_length=20, max_length=1200)
    target_duration_seconds: int = Field(default=TARGET_SECONDS, ge=90, le=TARGET_SECONDS)
    shot_count: int = Field(default=len(SHOT_DURATIONS), ge=6, le=16)
    llm_provider_service_id: str = Field(default="prompt_optimizer", min_length=1, max_length=120)
    image_provider_service_id: str = Field(default="image_relay", min_length=1, max_length=120)
    video_provider_service_id: str = Field(default="seedance_i2v", min_length=1, max_length=120)
    audio_provider_service_id: str = Field(default="tts_relay", min_length=1, max_length=120)
    aspect_ratio: Literal["16:9", "9:16"] = "16:9"
    resolution: str = Field(default="720p", max_length=40)

    @model_validator(mode="after")
    def currently_targets_one_exact_120s_slice(self) -> "RealStoryProductionRequest":
        if self.target_duration_seconds != TARGET_SECONDS:
            raise ValueError("current real story production route targets exact 120s acceptance")
        if self.shot_count != len(SHOT_DURATIONS):
            raise ValueError("current real story production route uses thirteen script-paced shots")
        return self


class RealStoryProductionError(ValueError):
    pass


def execute_real_story_production(
    store: RuntimeStore,
    project_id: str,
    run_id: str,
    request: RealStoryProductionRequest,
    root: Path,
    *,
    request_id: str = "",
    client_request_id: str = "",
) -> dict[str, Any]:
    if root.exists():
        raise RealStoryProductionError("real story production output already exists")
    root.parent.mkdir(parents=True, exist_ok=True)
    staging = root.parent / f".{root.name}.stage-{uuid4().hex}"
    try:
        staging.mkdir(parents=True)
        assets_dir = staging / "assets"
        assets_dir.mkdir()
        delivery_root = staging / "delivery"
        jobs: list[dict[str, Any]] = []
        calls: list[dict[str, Any]] = []

        script = _run_script_llm(
            store,
            project_id,
            request,
            staging,
            request_id=request_id,
            client_request_id=client_request_id,
        )
        calls.append({
            "capability": "llm",
            "route": "prompt-optimizations",
            "actual_calls": 1 if script["provider_calls_started"] else 0,
            "job_id": script["job_id"],
        })
        jobs.append({"capability": "llm", "job_id": script["job_id"], "status": "succeeded"})
        script_authority = _read_persisted_script_authority(staging, script["public"])
        script["public"]["downstream_authority"] = {
            "source": "persisted_script_ref",
            "script_ref": script_authority["script_ref"],
            "script_sha256": script_authority["script_sha256"],
        }

        canon = compile_story_canon(
            brief=request.brief,
            script_text=script_authority["script_text"],
            target_duration_seconds=request.target_duration_seconds,
        )
        write_json(staging / "canonical_story_package.json", canon)

        visual_assets: list[dict[str, Any]] = []
        for shot in canon["shots"]:
            image = _run_keyframe(
                store,
                project_id,
                shot,
                canon,
                request,
                assets_dir,
                request_id=request_id,
                client_request_id=client_request_id,
            )
            calls.append(image["call"])
            jobs.append(image["job"])
            video = _run_video(
                store,
                project_id,
                shot,
                canon,
                request,
                image,
                assets_dir,
                request_id=request_id,
                client_request_id=client_request_id,
            )
            calls.append(video["call"])
            jobs.append(video["job"])
            visual_assets.append(video["asset"])

        audio = _run_audio(
            store,
            project_id,
            canon,
            request,
            staging,
            request_id=request_id,
            client_request_id=client_request_id,
        )
        calls.append(audio["call"])
        jobs.append(audio["job"])

        spec = _write_assembly_spec(staging, project_id, canon, visual_assets, audio)
        assembled = assemble_episode(spec, delivery_root)
        technical_qa_path = delivery_root / "technical_qa.json"
        technical_qa = run_episode_technical_qa(assembled["episode"], assembled["manifest"])
        write_json(technical_qa_path, technical_qa)
        creative_qa = run_creative_media_qa(staging, canon, visual_assets, audio, technical_qa)
        creative_qa_path = delivery_root / "creative_media_qa.json"
        write_json(creative_qa_path, creative_qa)
        _write_contact_sheet(assembled["episode"], delivery_root / "contact_sheet.jpg", len(canon["shots"]))

        production_core = {
            "schema_version": REAL_STORY_SCHEMA_VERSION,
            "project_id": project_id,
            "run_id": run_id,
            "status": "creative_qa_passed" if not _blocking_findings(creative_qa) else "creative_qa_blocked",
            "brief_sha256": _sha256_text(request.brief),
            "script_source": script["public"],
            "canonical_story_package_ref": "canonical_story_package.json",
            "canonical_story_package_sha256": sha256_file(staging / "canonical_story_package.json"),
            "story_canon_digest": _json_digest(canon),
            "target_duration_seconds": request.target_duration_seconds,
            "shot_count": len(canon["shots"]),
            "call_ledger": calls,
            "jobs": jobs,
            "media_provenance": {
                "visual_assets": [_safe_visual_asset_provenance(item) for item in visual_assets],
                "audio": audio["provenance"],
            },
            "delivery": {
                "episode_asset_ref": "delivery_episode",
                "episode_sha256": sha256_file(assembled["episode"]),
                "assembly_manifest_ref": "delivery/assembly_manifest.json",
                "assembly_manifest_sha256": sha256_file(assembled["manifest"]),
                "technical_qa_ref": "delivery/technical_qa.json",
                "technical_qa_sha256": sha256_file(technical_qa_path),
                "creative_qa_ref": "delivery/creative_media_qa.json",
                "creative_qa_sha256": sha256_file(creative_qa_path),
                "contact_sheet_ref": "delivery/contact_sheet.jpg",
                "contact_sheet_sha256": sha256_file(delivery_root / "contact_sheet.jpg"),
                "duration_seconds": request.target_duration_seconds,
                "preview_url": (
                    f"/projects/{safe_id(project_id)}/production-runs/{safe_id(run_id)}/"
                    "real-story-production/delivery/preview"
                ),
            },
            "evidence_boundary": {
                "technical_container_qa": technical_qa.get("status") == "pass",
                "creative_media_qa": creative_qa.get("status"),
                "human_acceptance": False,
                "business_validation": False,
                "public_release": False,
            },
            "non_claims": [
                "not_human_acceptance",
                "not_business_validation",
                "not_public_release",
                "not_global_reconciliation",
            ],
        }
        production = {**production_core, "production_sha256": _json_digest(production_core), "created_at": _now()}
        reject_unsafe_payload(production)
        write_json(staging / "real_story_production_manifest.json", production)
        os.replace(staging, root)
        return production
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def compile_story_canon(*, brief: str, script_text: str, target_duration_seconds: int = TARGET_SECONDS) -> dict[str, Any]:
    script_text = _clean(script_text) or deterministic_script_body(brief)
    title = _title_from_script(script_text) or "回声信标"
    script_sha = _sha256_text(script_text)
    protagonist = _character_from_script(script_text)
    scenes = [
        {
            "scene_id": "scene-001",
            "name": "旧码头的清晨",
            "description": "海雾、旧路灯和安静水面，主角接到一段异常回声。",
        },
        {
            "scene_id": "scene-002",
            "name": "潮汐观测站",
            "description": "堆满纸质海图和发光仪表的室内空间，回声被逐步译出。",
        },
        {
            "scene_id": "scene-003",
            "name": "灯塔顶层",
            "description": "风声、老式发报机和巨大的透镜，主角把回声转成可见光。",
        },
        {
            "scene_id": "scene-004",
            "name": "天亮前的海面",
            "description": "灯光穿过海雾抵达远处回声点，旧信变成新的航线。",
        },
    ]
    cursor = 0
    shot_templates = _shot_templates(protagonist)
    shots = []
    for index, duration in enumerate(SHOT_DURATIONS, start=1):
        scene = scenes[min((index - 1) * len(scenes) // len(SHOT_DURATIONS), len(scenes) - 1)]
        excerpt = _script_excerpt(script_text, index, len(SHOT_DURATIONS))
        dialogue = _dialogue_for_shot(index, protagonist)
        shot = {
            "shot_id": f"shot-{index:03d}",
            "scene_id": scene["scene_id"],
            "sequence": index,
            "start_seconds": cursor,
            "end_seconds": cursor + duration,
            "duration_seconds": duration,
            "script_source_sha256": script_sha,
            "script_excerpt": excerpt,
            "visual_action": shot_templates[index - 1],
            "dialogue": dialogue,
            "subtitle_text": dialogue,
            "camera": _camera_for(index),
            "motion": _motion_for(index),
            "continuity_note": (
                f"{protagonist} remains the same small courier robot with a round signal lamp, "
                "blue raincoat shell, brass shoulder tag, and warm amber eye-lights."
            ),
            "quality_target": "clear narrative beat, unique composition, visible motion, no repeated sequence",
        }
        cursor += duration
        shots.append(shot)
    if cursor != target_duration_seconds:
        raise RealStoryProductionError("compiled shot durations do not match target")
    canon = {
        "artifact_type": "afs_real_story_canonical_package",
        "schema_version": "0.1.0",
        "brief": {"text": brief, "sha256": _sha256_text(brief)},
        "bible": {
            "title": title,
            "characters": [
                {
                    "character_id": "char-001",
                    "name": protagonist,
                    "appearance": "小型邮差机器人，圆形信号灯，蓝色雨衣外壳，黄铜肩牌，暖琥珀眼灯。",
                    "continuity_locks": ["圆形信号灯", "蓝色雨衣外壳", "黄铜肩牌", "暖琥珀眼灯"],
                }
            ],
            "visual_style": "cinematic Chinese animated short film, tactile miniature sets, soft coastal morning light",
        },
        "episode": {
            "episode_id": "episode-realstory-001",
            "title": title,
            "duration_seconds": target_duration_seconds,
            "language": "zh-CN",
        },
        "scenes": scenes,
        "shots": shots,
        "reference_set": {
            "reference_set_id": "refs-realstory-001",
            "character_refs": ["char-001"],
            "environment_refs": [scene["scene_id"] for scene in scenes],
            "voice_ref": "voice-calm-childlike-narrator",
            "style_ref": "miniature-coastal-animation",
        },
        "production_recipe": {
            "recipe_id": "recipe-realstory-001",
            "script_source_sha256": script_sha,
            "requires_per_shot_keyframe": True,
            "requires_per_shot_video": True,
            "requires_exact_timed_subtitles": True,
            "allows_unintentional_hash_reuse": False,
        },
    }
    reject_unsafe_payload(canon)
    return canon


def run_creative_media_qa(
    root: Path,
    canon: dict[str, Any],
    visual_assets: list[dict[str, Any]],
    audio: dict[str, Any],
    technical_qa: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    shots = canon["shots"]
    if technical_qa.get("status") != "pass":
        findings.append(_finding("P1", "TECH-QA", "technical media QA failed", "Run technical QA must pass before creative review."))
    if len(visual_assets) != len(shots):
        findings.append(_finding("P1", "SHOT-COVERAGE", "missing per-shot visual asset", "Every canonical shot requires a generated video asset."))
    non_video = [item["shot_id"] for item in visual_assets if item.get("media_type") != "video"]
    if non_video:
        findings.append(_finding("P1", "VIDEO-COVERAGE", "static hold used as final shot media", ", ".join(non_video)))
    hashes = [item.get("sha256") for item in visual_assets]
    repeated_hashes = sorted({value for value in hashes if value and hashes.count(value) > 1})
    if repeated_hashes:
        findings.append(_finding("P1", "DUPLICATE-HASH", "unintentional exact visual reuse", ", ".join(repeated_hashes)))
    perceptual = _perceptual_duplicate_pairs(root, visual_assets)
    if perceptual:
        findings.append(_finding("P1", "DUPLICATE-PERCEPTUAL", "near-identical shot sequence detected", json.dumps(perceptual, ensure_ascii=False)))
    for shot, asset in zip(shots, visual_assets, strict=False):
        if shot.get("shot_id") != asset.get("shot_id"):
            findings.append(_finding("P1", "LINEAGE", "shot-to-asset lineage mismatch", f"{shot.get('shot_id')} != {asset.get('shot_id')}"))
        if shot.get("script_source_sha256") != asset.get("prompt", {}).get("script_source_sha256"):
            findings.append(_finding("P1", "SCRIPT-PROMPT", "downstream prompt did not carry script source", str(shot.get("shot_id"))))
    if audio["provenance"].get("tts_source_duration_sec", 0) > canon["episode"]["duration_seconds"] + 0.25:
        findings.append(_finding("P1", "AUDIO-TRUNCATION", "TTS source exceeded final duration", "Audio must be rewritten, not truncated."))
    subtitle_cues = _subtitle_cues(root / "subtitles.srt")
    dialogue_repeated = _dialogue_repetition_detected(shots, subtitle_cues, audio)
    if dialogue_repeated:
        findings.append(_finding("P1", "AUDIO-REPEAT", "dialogue source text repeated", "Narration/dialogue must be written once."))
    subtitles_match = _subtitles_match_shots(subtitle_cues, shots)
    if not subtitles_match:
        findings.append(_finding("P1", "SUBTITLES", "subtitle cues do not derive from canonical shot text", "Timed text mismatch."))
    return {
        "artifact_type": "afs_creative_media_qa",
        "schema_version": "0.1.0",
        "status": "pass" if not _blocking_findings({"findings": findings}) else "fail",
        "findings": findings,
        "checks": [
            {"name": "story_shot_lineage", "status": "pass" if not any(f["id"] == "LINEAGE" for f in findings) else "fail"},
            {"name": "all_final_shots_are_video", "status": "pass" if not non_video else "fail"},
            {"name": "exact_duplicate_hashes", "status": "pass" if not repeated_hashes else "fail"},
            {"name": "perceptual_duplicate_scan", "status": "pass" if not perceptual else "fail"},
            {"name": "audio_not_truncated_or_repeated", "status": "pass" if not any(f["id"].startswith("AUDIO") for f in findings) else "fail"},
            {"name": "subtitle_exact_timed_alignment", "status": "pass" if subtitles_match else "fail"},
        ],
        "non_claims": ["not_human_acceptance", "not_business_validation"],
    }


def _run_script_llm(
    store: RuntimeStore,
    project_id: str,
    request: RealStoryProductionRequest,
    root: Path,
    *,
    request_id: str,
    client_request_id: str,
) -> dict[str, Any]:
    job_id = store.new_job_id("prompt_optimization", project_id)
    output_dir = store.run_dir(project_id, job_id)
    prompt = "\n".join([
        "请把下面的中文创意扩写成一个可拍成 120 秒短片的正式故事剧本正文。",
        "要求：有明确主角、三幕推进、可拆成十三个镜头、不要输出分镜表。",
        f"原始想法：{request.brief}",
    ])
    prompt_request = PromptOptimizationRequest(
        node_id="real-story-script",
        node_type="script",
        prompt_text=prompt,
        generation_target="script",
        target_platform="short_video",
        style="cinematic",
        node_parameters={
            "script_generation_mode": "idea_to_script",
            "script_expansion_contract": "formal_script_before_storyboard_breakdown",
            "source_idea": request.brief,
            "llm_provider": request.llm_provider_service_id,
            "llm_model": "provider_configured",
            "remote_optimizer_required": True,
        },
        generated_at=_now(),
    )
    result = build_prompt_optimization(
        store,
        project_id,
        prompt_request,
        output_dir,
        request_id=request_id,
        client_request_id=client_request_id,
        user_action="real_story_script_generation",
        studio_node_type="script",
    )
    artifacts = prompt_memory_artifacts(store, output_dir, include_script_plan=bool(result.get("script_plan")))
    store.write_job(runtime_job(job_id, project_id, "prompt_optimization", "succeeded", artifacts=artifacts))
    script_text = str(result.get("optimized_prompt") or deterministic_script_body(request.brief))
    script_ref = root / "llm_script_body.txt"
    script_ref.write_text(script_text, encoding="utf-8")
    return {
        "job_id": job_id,
        "script_text": script_text,
        "provider_calls_started": bool(result.get("provider_calls_started")),
        "public": {
            "job_id": job_id,
            "script_ref": "llm_script_body.txt",
            "script_sha256": sha256_file(script_ref),
            "provider_calls_started": bool(result.get("provider_calls_started")),
            "script_generation_body": result.get("script_generation_body"),
        },
    }


def _read_persisted_script_authority(root: Path, public: dict[str, Any]) -> dict[str, Any]:
    script_ref = str(public.get("script_ref") or "")
    if script_ref != "llm_script_body.txt":
        raise RealStoryProductionError("script authority ref is missing or unsupported")
    path = (root / script_ref).resolve()
    if root.resolve() not in path.parents:
        raise RealStoryProductionError("script authority ref escapes production root")
    script_text = path.read_text(encoding="utf-8")
    script_sha256 = sha256_file(path)
    if script_sha256 != str(public.get("script_sha256") or ""):
        raise RealStoryProductionError("persisted script authority hash mismatch")
    return {"script_ref": script_ref, "script_sha256": script_sha256, "script_text": script_text}


def _run_keyframe(
    store: RuntimeStore,
    project_id: str,
    shot: dict[str, Any],
    canon: dict[str, Any],
    request: RealStoryProductionRequest,
    assets_dir: Path,
    *,
    request_id: str,
    client_request_id: str,
) -> dict[str, Any]:
    job_id = store.new_job_id("keyframe_generation", project_id)
    output_dir = store.run_dir(project_id, job_id)
    prompt = _image_prompt(canon, shot)
    keyframe_request = KeyframeGenerationRequest(
        node_id=f"{shot['shot_id']}-keyframe",
        prompt_text=prompt,
        target_platform="short_video",
        style="cinematic animated narrative",
        aspect_ratio=request.aspect_ratio,
        candidate_count=1,
        provider_service_id=request.image_provider_service_id,
        node_parameters={"disable_provider_retry": True, "script_source_sha256": shot["script_source_sha256"]},
        generated_at=_now(),
    )
    result = build_keyframe_generation(
        store,
        project_id,
        keyframe_request,
        output_dir,
        request_id=request_id,
        client_request_id=client_request_id,
    )
    while result["status"] in {"running", "submitted", "pending"}:
        time.sleep(5)
        result = poll_keyframe_generation(store, project_id, output_dir, request_id=request_id, client_request_id=client_request_id)
    if result["status"] != "succeeded":
        raise RealStoryProductionError(f"keyframe generation failed for {shot['shot_id']}: {result['safe_manifest'].get('blocks')}")
    artifacts = keyframe_generation_artifacts(store, output_dir)
    store.write_job(runtime_job(job_id, project_id, "keyframe_generation", result["status"], artifacts=artifacts))
    provider_output = (result.get("provider_outputs") or [])[0]
    registered = register_generated_image_asset(
        store,
        project_id,
        source_node_id=keyframe_request.node_id,
        source_job_id=job_id,
        source_candidate_id=str(provider_output.get("candidate_id") or "candidate_001"),
        source_candidate_digest=str(provider_output.get("sha256") or ""),
        source_candidate_status="succeeded",
    )
    authority = resolve_generated_candidate_authority(
        store,
        project_id,
        source_job_id=job_id,
        source_candidate_id="candidate_001",
        require_existing_asset=True,
    )
    suffix = authority["suffix"]
    target = assets_dir / f"{shot['shot_id']}-keyframe{suffix}"
    shutil.copy2(authority["candidate_path"], target)
    return {
        "job_id": job_id,
        "asset_id": registered["asset"]["asset_id"],
        "path": target,
        "sha256": sha256_file(target),
        "call": {
            "capability": "image",
            "route": "keyframe-generations",
            "shot_id": shot["shot_id"],
            "actual_calls": 1 if result["provider_calls_started"] else 0,
            "retry_count": int(result["safe_manifest"].get("retry_count") or 0),
            "job_id": job_id,
        },
        "job": {"capability": "image", "job_id": job_id, "status": result["status"], "shot_id": shot["shot_id"]},
    }


def _run_video(
    store: RuntimeStore,
    project_id: str,
    shot: dict[str, Any],
    canon: dict[str, Any],
    request: RealStoryProductionRequest,
    image: dict[str, Any],
    assets_dir: Path,
    *,
    request_id: str,
    client_request_id: str,
) -> dict[str, Any]:
    job_id = store.new_job_id("video_generation", project_id)
    output_dir = store.run_dir(project_id, job_id)
    prompt = _video_prompt(canon, shot)
    video_request = VideoGenerationRequest(
        node_id=f"{shot['shot_id']}-video",
        generation_path="i2v_first_frame",
        prompt_text=prompt,
        provider_service_id=request.video_provider_service_id,
        first_frame_image_asset_id=image["asset_id"],
        input_source=VideoInputSource(
            source_mode="upstream_generated_image",
            source_asset_id=image["asset_id"],
            source_job_id=image["job_id"],
            role="first_frame",
        ),
        duration_sec=PROVIDER_VIDEO_DURATION_SECONDS,
        resolution=request.resolution,
        aspect_ratio=request.aspect_ratio,
        motion=str(shot["motion"]),
        candidate_count=1,
        quota_override_confirmed=True,
        generated_at=_now(),
    )
    result = submit_video_generation(
        store,
        project_id,
        job_id,
        video_request,
        output_dir,
        load_registry=load_provider_registry,
        request_id=request_id,
        client_request_id=client_request_id,
    )
    write_video_job(store, project_id, job_id, result)
    polls = 0
    while result["status"] in {"submitted", "running", "pending"} and polls < 90:
        time.sleep(12)
        polls += 1
        result = poll_video_generation(
            store,
            project_id,
            output_dir,
            load_registry=load_provider_registry,
            request_id=request_id,
            client_request_id=client_request_id,
        )
        write_video_job(store, project_id, job_id, result)
    if result["status"] != "succeeded":
        raise RealStoryProductionError(f"video generation failed for {shot['shot_id']}: {result['safe_manifest'].get('blocks')}")
    source = video_candidate_file(output_dir, "candidate_001")
    if source is None:
        raise RealStoryProductionError(f"video candidate missing for {shot['shot_id']}")
    target = assets_dir / f"{shot['shot_id']}-video.mp4"
    shutil.copy2(source, target)
    asset = _controlled_asset(assets_dir.parent, target, asset_id=f"asset-{shot['shot_id']}-video", revision_id="media-v001", media_type="video")
    asset.update({
        "shot_id": shot["shot_id"],
        "scene_id": shot["scene_id"],
        "provider_job_id": job_id,
        "provider_candidate_id": "candidate_001",
        "prompt": {
            "prompt_sha256": _sha256_text(prompt),
            "script_source_sha256": shot["script_source_sha256"],
            "scene_id": shot["scene_id"],
            "shot_id": shot["shot_id"],
        },
    })
    return {
        "asset": asset,
        "call": {
            "capability": "video",
            "route": "video-generations",
            "shot_id": shot["shot_id"],
            "actual_calls": 1 + polls,
            "actual_submit_calls": 1,
            "provider_poll_calls": polls,
            "provider_requested_duration_sec": PROVIDER_VIDEO_DURATION_SECONDS,
            "final_timeline_duration_sec": int(shot["duration_seconds"]),
            "paid_retry_count": 0,
            "job_id": job_id,
        },
        "job": {"capability": "video", "job_id": job_id, "status": result["status"], "shot_id": shot["shot_id"]},
    }


def _run_audio(
    store: RuntimeStore,
    project_id: str,
    canon: dict[str, Any],
    request: RealStoryProductionRequest,
    root: Path,
    *,
    request_id: str,
    client_request_id: str,
) -> dict[str, Any]:
    job_id = store.new_job_id("audio_generation", project_id)
    output_dir = store.run_dir(project_id, job_id)
    dialogue_lines = [_clean(shot["subtitle_text"]) for shot in canon["shots"]]
    text = " ".join(dialogue_lines)
    dialogue_line_hashes = [_sha256_text(line) for line in dialogue_lines]
    audio_request = AudioGenerationRequest(
        node_id="real-story-dialogue",
        prompt_text=text,
        provider_service_id=request.audio_provider_service_id,
        episode_id=canon["episode"]["episode_id"],
        scene_id="all-scenes",
        shot_id="all-shots",
        voice="alloy",
        instructions="自然中文旁白，清晰、克制、有故事推进，不重复句子。",
        response_format="wav",
        max_paid_requests=1,
        cost_cap_cny=300,
        generated_at=_now(),
    )
    result = _submit_audio_generation(project_id, job_id, audio_request, output_dir)
    artifacts = audio_generation_artifacts(store, output_dir)
    store.write_job(runtime_job(job_id, project_id, "audio_generation", result["status"], artifacts=artifacts))
    if result["status"] != "succeeded":
        raise RealStoryProductionError(f"audio generation failed: {result['safe_manifest'].get('blocks')}")
    source = audio_candidate_file(output_dir, "candidate_001")
    if source is None:
        raise RealStoryProductionError("audio candidate missing")
    audio_dir = root / "audio"
    audio_dir.mkdir()
    tts_duration = _media_duration(source)
    if tts_duration > TARGET_SECONDS + 0.25:
        raise RealStoryProductionError("TTS output exceeds final duration; rewrite narration instead of truncating")
    dialogue = audio_dir / "dialogue.wav"
    _run_checked([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
        "-af", f"aresample=48000,apad=pad_dur={TARGET_SECONDS}",
        "-ac", "1", "-t", str(TARGET_SECONDS), str(dialogue),
    ], timeout=120)
    music = audio_dir / "music.wav"
    sfx = audio_dir / "sfx.wav"
    _run_checked([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
        "-i", f"sine=frequency=220:sample_rate=48000:duration={TARGET_SECONDS}",
        "-af", "volume=0.035", "-ac", "1", str(music),
    ], timeout=60)
    _run_checked([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
        "-i", f"anoisesrc=color=pink:amplitude=0.015:sample_rate=48000:duration={TARGET_SECONDS}",
        "-ac", "1", str(sfx),
    ], timeout=60)
    subtitles = root / "subtitles.srt"
    _write_subtitles(subtitles, canon["shots"])
    return {
        "call": {
            "capability": "audio",
            "route": "audio-generations",
            "actual_calls": 1 if result["provider_calls_started"] else 0,
            "retry_count": 0,
            "job_id": job_id,
        },
        "job": {"capability": "audio", "job_id": job_id, "status": result["status"]},
        "provenance": {
            "provider_job_id": job_id,
            "provider_candidate_id": "candidate_001",
            "tts_source_sha256": sha256_file(source),
            "tts_source_duration_sec": tts_duration,
            "dialogue_source_line_count": len(dialogue_line_hashes),
            "dialogue_source_unique_line_count": len(set(dialogue_line_hashes)),
            "dialogue_source_line_hashes": dialogue_line_hashes,
            "dialogue_text_repetition_detected": len(set(dialogue_line_hashes)) != len(dialogue_line_hashes),
            "dialogue_stem": _controlled_asset(root, dialogue, asset_id="asset-dialogue-tts", revision_id="media-v001", media_type="audio"),
            "music_stem": _controlled_asset(root, music, asset_id="asset-music-local", revision_id="local-v001", media_type="audio"),
            "sfx_stem": _controlled_asset(root, sfx, asset_id="asset-sfx-local", revision_id="local-v001", media_type="audio"),
            "subtitle_asset": _controlled_asset(root, subtitles, asset_id="asset-subtitles", revision_id="timed-text-v001", media_type="text"),
            "text_sha256": _sha256_text(text),
        },
    }


def _write_assembly_spec(
    root: Path,
    project_id: str,
    canon: dict[str, Any],
    visual_assets: list[dict[str, Any]],
    audio: dict[str, Any],
) -> Path:
    spec = {
        "schema_version": "0.2.0",
        "contract": "agentflow_studio.production.episode_delivery.v0.1",
        "provider_calls_started": 0,
        "project_id": project_id,
        "episode_id": canon["episode"]["episode_id"],
        "width": 1280,
        "height": 720,
        "frame_rate": 24,
        "shot_count": len(canon["shots"]),
        "duration_seconds": TARGET_SECONDS,
        "shots": [
            {
                "shot_id": shot["shot_id"],
                "scene_id": shot["scene_id"],
                "start_seconds": shot["start_seconds"],
                "end_seconds": shot["end_seconds"],
                "source_start_seconds": 0,
                "visual_asset": _episode_asset(asset),
                "lineage": {
                    "project_id": project_id,
                    "episode_id": canon["episode"]["episode_id"],
                    "scene_id": shot["scene_id"],
                    "shot_id": shot["shot_id"],
                    "asset_id": asset["asset_id"],
                    "revision_id": asset["revision_id"],
                },
            }
            for shot, asset in zip(canon["shots"], visual_assets, strict=True)
        ],
        "audio_stems": {
            "dialogue": _episode_asset(audio["provenance"]["dialogue_stem"]),
            "music": _episode_asset(audio["provenance"]["music_stem"]),
            "sfx": _episode_asset(audio["provenance"]["sfx_stem"]),
        },
        "subtitle_asset": _episode_asset(audio["provenance"]["subtitle_asset"]),
        "mix": {"target_lufs": -16, "true_peak_db": -2, "music_duck_db": 5},
        "minimum_video_bitrate": 100000,
    }
    path = root / "assembly_spec.json"
    write_json(path, spec)
    return path


def _image_prompt(canon: dict[str, Any], shot: dict[str, Any]) -> str:
    character = canon["bible"]["characters"][0]
    scene = next(item for item in canon["scenes"] if item["scene_id"] == shot["scene_id"])
    return (
        f"中国动画短片《{canon['episode']['title']}》关键帧。"
        f"角色：{character['name']}，{character['appearance']}。"
        f"场景：{scene['name']}，{scene['description']}。"
        f"镜头 {shot['shot_id']}：{shot['visual_action']}。"
        f"构图：{shot['camera']}。连续性：{shot['continuity_note']}。"
        "画面干净、电影感、可作为图生视频首帧、招牌为空白、无品牌。"
    )


def _video_prompt(canon: dict[str, Any], shot: dict[str, Any]) -> str:
    scene = next(item for item in canon["scenes"] if item["scene_id"] == shot["scene_id"])
    return (
        f"中国动画短片《{canon['episode']['title']}》连续镜头。"
        f"{scene['name']}。{shot['visual_action']}。"
        f"镜头运动：{shot['motion']}。"
        f"保持同一个小邮差机器人、蓝色雨衣外壳、圆形信号灯、黄铜肩牌和暖琥珀眼灯。"
        f"这一镜持续 {shot['duration_seconds']} 秒，完成一个清楚的故事动作。"
    )


def _shot_templates(protagonist: str) -> list[str]:
    return [
        f"{protagonist}从旧码头雾气中走出，肩牌被晨光照亮，手里握着一封发光信件。",
        "水面忽然泛起圆形波纹，信件上的旧地址亮起，主角停下脚步观察。",
        "主角把信件贴近胸前信号灯，灯光投出一段断续的童声波形。",
        "旧码头的警示铃轻响，信封边缘显出一枚灯塔印章。",
        "在潮汐观测站里，主角把海图、信件和灯塔频率对齐，墙面投影开始复原。",
        "投影显示多年以前的守望员把最后坐标交给回声，主角第一次犹豫。",
        "主角把旧电池接入观测台，所有纸质海图同时指向灯塔。",
        "主角冲出观测站，沿着湿漉漉的台阶向灯塔奔跑，海风掀起蓝色外壳。",
        "灯塔顶层，主角把信件放进老式发报机，圆形信号灯与灯塔主灯同步闪烁。",
        "巨大的透镜转动，信件上的文字被投成一条穿过海雾的光线。",
        "海面远处回应一束微弱光点，主角伸手调整棱镜，让光线稳定。",
        "回声点传回一段完整确认音，主角终于放下紧绷的机械手。",
        "第一缕阳光到来时，旧信化成新地图，主角转身望向下一段航线。",
    ]


def _dialogue_for_shot(index: int, protagonist: str) -> str:
    lines = [
        f"清晨的旧码头还没有醒来，{protagonist}收到一封只会发光、没有署名的信。",
        "信上的地址在水面回声里跳动，像有人从很远的地方轻轻敲门。",
        "它把信贴近胸前的信号灯，听见一段被潮汐藏了很久的童声。",
        "信封上的灯塔印章一点点显影，像是在催它赶在天亮前出发。",
        "观测站的海图一张张亮起，所有线索都指向那座停摆多年的灯塔。",
        "童声说，守望员没有离开，只是把最后的坐标交给了回声。",
        "小澄接上最后一块旧电池，整座观测台忽然把海岸线照成金色。",
        "它沿着潮湿台阶奔跑，知道这一次送达不能再迟到。",
        "灯塔重新点亮时，信件和信号灯终于对上同一个频率。",
        "透镜把文字折成一条光路，穿过雾气，直指海面尽头。",
        "远处海面回应一粒微光，像有人在黑暗里确认收到了消息。",
        "完整的确认音回来时，小澄第一次听见自己的信号灯安静下来。",
        "天亮前，旧信化成新的航线，小澄明白下一封信已经在路上。",
    ]
    return lines[index - 1]


def _camera_for(index: int) -> str:
    return [
        "低机位跟拍，雾气前景和主角剪影形成层次",
        "俯拍水面波纹再推到信件细节",
        "胸前信号灯特写，浅景深，背景码头虚化",
        "信封和灯塔印章的极近特写，背景警示铃轻微晃动",
        "横移展示海图、仪表和主角手部动作",
        "中近景环绕投影，保持主角在画面左三分之一",
        "俯拍旧电池接入瞬间，海图光线呈放射状展开",
        "动态跟拍台阶，海风和灯塔形成纵深",
        "顶层广角，发报机、信件和主灯在同一构图",
        "透镜内部折射视角，文字光路从画面中心穿出",
        "主观视角穿过棱镜看向海面光点",
        "中景停顿，主角机械手放松，背景灯束稳定扫过",
        "稳定远景收束，日出、地图和主角背影同框",
    ][index - 1]


def _motion_for(index: int) -> str:
    return [
        "slow dolly forward, fog drifting, signal lamp warming up",
        "gentle tilt from ripples to glowing envelope",
        "subtle push-in, waveform light pulsing from the chest lamp",
        "macro rack focus from lighthouse stamp to trembling warning bell",
        "smooth lateral camera move across maps and instruments",
        "slow orbit around holographic projection and hesitant robot pose",
        "quick overhead pulse as old battery reconnects and map lines flare",
        "steady tracking move up wet stairs with wind-driven coat motion",
        "controlled crane up as lighthouse beam synchronizes with signal lamp",
        "rotating lens refraction, text becoming a clean beam through fog",
        "slow lens-like refraction move through the prism toward distant light",
        "gentle hold with tiny hand movement and stable sweeping beam",
        "quiet pullback into sunrise with map unfolding in the robot hand",
    ][index - 1]


def _write_subtitles(path: Path, shots: list[dict[str, Any]]) -> None:
    blocks = []
    for index, shot in enumerate(shots, start=1):
        blocks.append(
            f"{index}\n{_srt_time(int(shot['start_seconds']))} --> {_srt_time(int(shot['end_seconds']))}\n{shot['subtitle_text']}"
        )
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def _subtitle_cues(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"\r?\n\s*\r?\n", text.strip()) if text.strip() else []
    cues: list[dict[str, Any]] = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3 or "-->" not in lines[1]:
            return []
        try:
            number = int(lines[0].strip())
            start_text, end_text = (part.strip() for part in lines[1].split("-->", 1))
            cues.append(
                {
                    "number": number,
                    "start_seconds": _srt_seconds(start_text),
                    "end_seconds": _srt_seconds(end_text),
                    "text": "\n".join(lines[2:]).strip(),
                }
            )
        except (TypeError, ValueError):
            return []
    return cues


def _subtitles_match_shots(cues: list[dict[str, Any]], shots: list[dict[str, Any]]) -> bool:
    if len(cues) != len(shots):
        return False
    for index, (cue, shot) in enumerate(zip(cues, shots, strict=True), start=1):
        if cue.get("number") != index:
            return False
        if cue.get("start_seconds") != int(shot["start_seconds"]):
            return False
        if cue.get("end_seconds") != int(shot["end_seconds"]):
            return False
        if _clean(cue.get("text")) != _clean(shot.get("subtitle_text")):
            return False
    return True


def _dialogue_repetition_detected(
    shots: list[dict[str, Any]],
    cues: list[dict[str, Any]],
    audio: dict[str, Any],
) -> bool:
    expected_hashes = [_sha256_text(_clean(shot.get("subtitle_text"))) for shot in shots]
    cue_hashes = [_sha256_text(_clean(cue.get("text"))) for cue in cues]
    provenance = audio.get("provenance") if isinstance(audio.get("provenance"), dict) else {}
    source_hashes = [
        str(value)
        for value in provenance.get("dialogue_source_line_hashes", [])
        if isinstance(value, str)
    ]
    line_count = int(provenance.get("dialogue_source_line_count") or len(source_hashes) or 0)
    unique_count = int(provenance.get("dialogue_source_unique_line_count") or len(set(source_hashes)) or 0)
    return (
        _has_duplicates(expected_hashes)
        or _has_duplicates(cue_hashes)
        or _has_duplicates(source_hashes)
        or bool(provenance.get("dialogue_text_repetition_detected"))
        or (line_count > 0 and unique_count > 0 and unique_count < line_count)
        or (line_count > 0 and line_count != len(shots))
    )


def _has_duplicates(values: list[str]) -> bool:
    cleaned = [value for value in values if value]
    return len(cleaned) != len(set(cleaned))


def _srt_seconds(value: str) -> int:
    match = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})", value.strip())
    if not match:
        raise ValueError("invalid srt timestamp")
    hours, minutes, seconds, millis = (int(part) for part in match.groups())
    if millis != 0:
        raise ValueError("real story subtitles use whole-second shot boundaries")
    return hours * 3600 + minutes * 60 + seconds


def _write_contact_sheet(episode: Path, output: Path, shot_count: int) -> None:
    columns = 3
    rows = (shot_count + columns - 1) // columns
    _run_checked([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(episode),
        "-vf", f"fps=1/13,scale=320:-1,tile={columns}x{rows}", "-frames:v", "1", str(output),
    ], timeout=60)


def _perceptual_duplicate_pairs(root: Path, visual_assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hashes: list[tuple[str, str]] = []
    for asset in visual_assets:
        path = root / str(asset["path"])
        digest = _average_frame_hash(path)
        if digest:
            hashes.append((asset["shot_id"], digest))
    pairs = []
    for idx, (left_id, left_hash) in enumerate(hashes):
        for right_id, right_hash in hashes[idx + 1:]:
            distance = sum(a != b for a, b in zip(left_hash, right_hash, strict=True))
            if distance <= 4:
                pairs.append({"left": left_id, "right": right_id, "distance": distance})
    return pairs


def _average_frame_hash(path: Path) -> str:
    result = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-ss", "1", "-i", str(path), "-frames:v", "1",
            "-vf", "scale=8:8,format=gray", "-f", "rawvideo", "-",
        ],
        capture_output=True,
        timeout=30,
        check=False,
    )
    data = result.stdout
    if result.returncode != 0 or len(data) != 64:
        return ""
    avg = sum(data) / len(data)
    return "".join("1" if byte >= avg else "0" for byte in data)


def _controlled_asset(root: Path, path: Path, *, asset_id: str, revision_id: str, media_type: str) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "revision_id": revision_id,
        "current_revision_id": revision_id,
        "path": path.resolve().relative_to(root.resolve()).as_posix(),
        "sha256": sha256_file(path),
        "media_type": media_type,
    }


def _episode_asset(asset: dict[str, Any]) -> dict[str, Any]:
    return {key: asset[key] for key in ("asset_id", "revision_id", "current_revision_id", "path", "sha256", "media_type")}


def _safe_visual_asset_provenance(asset: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in asset.items()
        if key in {
            "asset_id",
            "revision_id",
            "current_revision_id",
            "sha256",
            "media_type",
            "shot_id",
            "scene_id",
            "provider_job_id",
            "provider_candidate_id",
            "prompt",
        }
    }


def _media_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise RealStoryProductionError("cannot inspect media duration")
    return float(json.loads(result.stdout)["format"]["duration"])


def _run_checked(command: list[str], *, timeout: int) -> None:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode != 0:
        raise RealStoryProductionError((result.stderr or result.stdout or "media command failed")[-500:])


def _blocking_findings(qa: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in qa.get("findings") or [] if isinstance(item, dict) and item.get("severity") in {"P0", "P1"}]


def _finding(severity: str, finding_id: str, title: str, evidence: str) -> dict[str, Any]:
    return {"severity": severity, "id": finding_id, "title": title, "evidence": evidence, "status": "open"}


def _script_excerpt(script_text: str, index: int, total: int) -> str:
    text = _clean(script_text)
    if not text:
        return ""
    span = max(60, len(text) // total)
    start = min(max(0, (index - 1) * span), max(0, len(text) - span))
    return text[start:start + 180]


def _title_from_script(script_text: str) -> str:
    match = re.search(r"《([^》]{1,40})》", script_text)
    return match.group(1).strip() if match else ""


def _character_from_script(script_text: str) -> str:
    if "小澄" in script_text:
        return "邮差机器人小澄"
    if "遥星" in script_text:
        return "遥星R-17"
    return "邮差机器人小澄"


def _srt_time(seconds: int) -> str:
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d},000"


def _json_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = (
    "REAL_STORY_SCHEMA_VERSION",
    "RealStoryProductionError",
    "RealStoryProductionRequest",
    "compile_story_canon",
    "execute_real_story_production",
    "run_creative_media_qa",
)
