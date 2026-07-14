from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentflow.harness.json_io import write_json
from agentflow_studio.production.episode_delivery import assemble_episode, sha256_file


MEDIA_SCHEMA_VERSION = "afs_representative_episode_media.v0.1"
MEDIA_INTAKE_CONTRACT = "canonical_media_intake_delivery_bridge.v0.1"
EXPECTED_SLOT_COUNT = 25
EPISODE_SECONDS = Decimal("135")
PROBE_TOLERANCE_SECONDS = Decimal("0.25")
MAX_ASSET_BYTES = 32 * 1024 * 1024
CONTINUITY_LABELS = frozenset({"structural_checked", "blocked", "not_evaluated"})
MIME_SUFFIXES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "video/mp4": ".mp4",
    "audio/wav": ".wav",
}


class RepresentativeEpisodeMediaError(ValueError):
    pass


def derive_authoritative_inventory(binding: dict[str, Any]) -> list[dict[str, Any]]:
    _require_v2_binding(binding)
    refs = [item for item in binding.get("asset_refs") or [] if isinstance(item, dict)]
    if len(refs) != EXPECTED_SLOT_COUNT:
        raise RepresentativeEpisodeMediaError("authoritative episode inventory must contain exactly 25 slots")
    expected_prefixes = (
        ["asset-char-"] * 3
        + ["asset-scene-"] * 3
        + ["asset-shot-"] * 15
        + ["asset-dialogue-stem", "asset-music-stem", "asset-sfx-stem", "asset-audio-master"]
    )
    inventory: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, (item, expected) in enumerate(zip(refs, expected_prefixes, strict=True)):
        asset_id = _text(item.get("asset_id"))
        revision_id = _text(item.get("current_revision_id"))
        if not asset_id or asset_id in seen or not revision_id:
            raise RepresentativeEpisodeMediaError("authoritative episode inventory is invalid or duplicated")
        if expected.startswith("asset-") and expected in {"asset-dialogue-stem", "asset-music-stem", "asset-sfx-stem", "asset-audio-master"}:
            matches = asset_id == expected
        else:
            matches = asset_id.startswith(expected)
        if not matches:
            raise RepresentativeEpisodeMediaError("authoritative episode inventory order is invalid")
        category = "character" if index < 3 else "scene" if index < 6 else "shot" if index < 21 else "audio"
        allowed_kinds = ["image"] if category in {"character", "scene"} else ["image", "video"] if category == "shot" else ["audio"]
        inventory.append(
            {
                "ordinal": index + 1,
                "asset_id": asset_id,
                "revision_id": revision_id,
                "category": category,
                "allowed_media_kinds": allowed_kinds,
                "shot_number": index - 5 if category == "shot" else None,
            }
        )
        seen.add(asset_id)
    canon = binding["episode_canon"]
    shot_assets = [shot["required_asset_ids"][0] for shot in canon["shots"]]
    if shot_assets != [item["asset_id"] for item in inventory if item["category"] == "shot"]:
        raise RepresentativeEpisodeMediaError("shot media inventory does not match the exact canonical shot order")
    audio = canon["audio"]
    audio_refs = [
        audio["dialogue_asset_ref"]["asset_id"],
        audio["music_asset_ref"]["asset_id"],
        audio["sfx_asset_ref"]["asset_id"],
        audio["master_asset_ref"]["asset_id"],
    ]
    if audio_refs != [item["asset_id"] for item in inventory if item["category"] == "audio"]:
        raise RepresentativeEpisodeMediaError("audio media inventory does not match the canonical audio order")
    return inventory


def admit_authoritative_media(
    binding: dict[str, Any],
    admissions: list[dict[str, Any]],
    destination: str | Path,
    *,
    project_id: str,
    run_id: str,
    ffprobe_executable: str = "ffprobe",
    ffmpeg_executable: str = "ffmpeg",
) -> dict[str, Any]:
    inventory = derive_authoritative_inventory(binding)
    if len(admissions) != EXPECTED_SLOT_COUNT:
        raise RepresentativeEpisodeMediaError("media intake must contain every authoritative slot exactly once")
    destination_path = Path(destination).resolve()
    if destination_path.exists():
        raise RepresentativeEpisodeMediaError("authoritative media intake already exists")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    staging = destination_path.parent / f".{destination_path.name}.stage-{uuid4().hex}"
    assets_dir = staging / "assets"
    assets_dir.mkdir(parents=True)
    accepted: list[dict[str, Any]] = []
    try:
        for slot, admission in zip(inventory, admissions, strict=True):
            if not isinstance(admission, dict):
                raise RepresentativeEpisodeMediaError("media intake item must be an object")
            if _text(admission.get("asset_id")) != slot["asset_id"]:
                raise RepresentativeEpisodeMediaError("caller cannot add, omit, or reorder authoritative media slots")
            if _text(admission.get("revision_id")) != slot["revision_id"]:
                raise RepresentativeEpisodeMediaError("media intake references a stale canonical asset revision")
            media_kind = _text(admission.get("media_kind"))
            if media_kind not in slot["allowed_media_kinds"]:
                raise RepresentativeEpisodeMediaError("media kind is not allowed for the authoritative slot")
            mime_type = _text(admission.get("mime_type"))
            suffix = MIME_SUFFIXES.get(mime_type)
            if not suffix or not _mime_matches_kind(mime_type, media_kind):
                raise RepresentativeEpisodeMediaError("media MIME does not match the authoritative slot kind")
            payload = _decode_base64(_text(admission.get("data_base64")))
            declared_sha = _text(admission.get("sha256")).lower()
            actual_sha = hashlib.sha256(payload).hexdigest()
            if declared_sha != actual_sha:
                raise RepresentativeEpisodeMediaError("media sha256 does not match decoded bytes")
            path = assets_dir / f"{slot['ordinal']:02d}-{slot['asset_id']}{suffix}"
            path.write_bytes(payload)
            probe = _probe_and_decode(path, media_kind, ffprobe_executable, ffmpeg_executable)
            _validate_probe(slot, media_kind, mime_type, probe)
            accepted.append(
                {
                    "ordinal": slot["ordinal"],
                    "asset_id": slot["asset_id"],
                    "revision_id": slot["revision_id"],
                    "category": slot["category"],
                    "shot_number": slot["shot_number"],
                    "media_kind": media_kind,
                    "mime_type": mime_type,
                    "sha256": actual_sha,
                    "bytes": len(payload),
                    "relative_ref": path.relative_to(staging).as_posix(),
                    "safe_preview_url": (
                        f"/projects/{project_id}/production-runs/{run_id}/"
                        f"representative-episode-media/assets/{slot['asset_id']}/preview"
                    ),
                    "probe": _safe_probe(probe),
                }
            )
        continuity = structural_continuity_findings(binding, accepted)
        if any(item["status"] != "structural_checked" for item in continuity):
            raise RepresentativeEpisodeMediaError("authoritative structural continuity checks did not close")
        manifest_core = {
            "schema_version": MEDIA_SCHEMA_VERSION,
            "contract": MEDIA_INTAKE_CONTRACT,
            "project_id": project_id,
            "run_id": run_id,
            "episode_id": binding["episode_id"],
            "episode_version_id": binding["episode_version_id"],
            "binding_digest": binding["binding_digest"],
            "canon_digest": binding["canon_digest"],
            "slot_count": EXPECTED_SLOT_COUNT,
            "accepted_count": len(accepted),
            "assets": accepted,
            "continuity_findings": continuity,
            "provider_calls_started": 0,
            "evidence_boundary": {
                "provider_free_mechanics": True,
                "creative_media_quality": False,
                "human_acceptance": False,
                "business_validation": False,
                "deploy_or_release": False,
            },
        }
        manifest = {
            **manifest_core,
            "manifest_sha256": _json_digest(manifest_core),
            "accepted_at": _now(),
            "delivery": None,
        }
        write_json(staging / "media_manifest.json", manifest)
        os.replace(staging, destination_path)
        return manifest
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def revalidate_authoritative_media(
    binding: dict[str, Any],
    media: dict[str, Any],
    root: str | Path,
) -> list[dict[str, Any]]:
    inventory = derive_authoritative_inventory(binding)
    assets = [item for item in media.get("assets") or [] if isinstance(item, dict)]
    if (
        media.get("schema_version") != MEDIA_SCHEMA_VERSION
        or media.get("binding_digest") != binding.get("binding_digest")
        or media.get("canon_digest") != binding.get("canon_digest")
        or media.get("episode_version_id") != binding.get("episode_version_id")
        or len(assets) != EXPECTED_SLOT_COUNT
    ):
        raise RepresentativeEpisodeMediaError("persisted media authority does not match current canon binding")
    manifest_core = {
        key: media[key]
        for key in (
            "schema_version", "contract", "project_id", "run_id", "episode_id",
            "episode_version_id", "binding_digest", "canon_digest", "slot_count",
            "accepted_count", "assets", "continuity_findings", "provider_calls_started",
            "evidence_boundary",
        )
    }
    if _json_digest(manifest_core) != media.get("manifest_sha256"):
        raise RepresentativeEpisodeMediaError("persisted media manifest integrity mismatch")
    root_path = Path(root).resolve()
    manifest_path = root_path / "media_manifest.json"
    try:
        persisted_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RepresentativeEpisodeMediaError("persisted media manifest is missing or unreadable") from exc
    if persisted_manifest != media:
        raise RepresentativeEpisodeMediaError("persisted media manifest does not match runtime state")
    for slot, asset in zip(inventory, assets, strict=True):
        if (
            asset.get("asset_id") != slot["asset_id"]
            or asset.get("revision_id") != slot["revision_id"]
            or asset.get("ordinal") != slot["ordinal"]
        ):
            raise RepresentativeEpisodeMediaError("persisted media inventory drifted from current canon")
        path = _controlled_path(root_path, asset.get("relative_ref"))
        if not path.is_file() or sha256_file(path) != asset.get("sha256"):
            raise RepresentativeEpisodeMediaError("persisted media bytes failed hash revalidation")
    findings = structural_continuity_findings(binding, assets)
    if findings != media.get("continuity_findings"):
        raise RepresentativeEpisodeMediaError("persisted continuity findings are stale")
    delivery = media.get("delivery") if isinstance(media.get("delivery"), dict) else {}
    if delivery:
        evidence = (
            ("delivery/episode.mp4", "episode_sha256"),
            ("delivery/assembly_manifest.json", "assembly_manifest_sha256"),
            ("delivery/technical_qa.json", "technical_qa_sha256"),
        )
        if delivery.get("assembly_complete") is not True:
            raise RepresentativeEpisodeMediaError("persisted technical delivery state is incomplete")
        for relative_ref, digest_field in evidence:
            path = _controlled_path(root_path, relative_ref)
            if not path.is_file() or sha256_file(path) != delivery.get(digest_field):
                raise RepresentativeEpisodeMediaError("persisted technical delivery failed hash revalidation")
    return assets


def assemble_authoritative_episode(
    binding: dict[str, Any],
    media: dict[str, Any],
    root: str | Path,
    *,
    ffmpeg_executable: str = "ffmpeg",
    ffprobe_executable: str = "ffprobe",
) -> dict[str, Any]:
    if binding.get("episode_version_id") != "ep-rainlight-001-v2" or binding.get("propagation_complete") is not True:
        raise RepresentativeEpisodeMediaError("assembly requires exact v2 canon with completed downstream propagation")
    root_path = Path(root).resolve()
    assets = revalidate_authoritative_media(binding, media, root_path)
    if len(assets) != EXPECTED_SLOT_COUNT:
        raise RepresentativeEpisodeMediaError("assembly requires all 25 authoritative media slots")
    spec_path = root_path / "assembly_spec.json"
    subtitle_path = root_path / "derived_subtitles.srt"
    _write_subtitles(binding, subtitle_path)
    subtitle_sha = sha256_file(subtitle_path)
    by_id = {item["asset_id"]: item for item in assets}
    canon = binding["episode_canon"]
    shots = []
    for shot in canon["shots"]:
        asset = by_id[shot["required_asset_ids"][0]]
        shots.append(
            {
                "shot_id": shot["entity_id"],
                "scene_id": shot["scene_ref"]["entity_id"],
                "start_seconds": shot["start_seconds"],
                "end_seconds": shot["end_seconds"],
                "source_start_seconds": 0,
                "visual_asset": _episode_asset(root_path, asset),
                "lineage": {
                    "project_id": media["project_id"],
                    "episode_id": binding["episode_id"],
                    "scene_id": shot["scene_ref"]["entity_id"],
                    "shot_id": shot["entity_id"],
                    "asset_id": asset["asset_id"],
                    "revision_id": asset["revision_id"],
                },
            }
        )
    audio_ids = ["asset-dialogue-stem", "asset-music-stem", "asset-sfx-stem"]
    spec = {
        "schema_version": "0.2.0",
        "contract": "agentflow_studio.production.episode_delivery.v0.1",
        "provider_calls_started": 0,
        "project_id": media["project_id"],
        "episode_id": binding["episode_id"],
        "width": 640,
        "height": 360,
        "frame_rate": 12,
        "shot_count": 15,
        "duration_seconds": 135,
        "shots": shots,
        "audio_stems": {
            name: _episode_asset(root_path, by_id[asset_id])
            for name, asset_id in zip(("dialogue", "music", "sfx"), audio_ids, strict=True)
        },
        "subtitle_asset": {
            "asset_id": "derived-canon-subtitles",
            "revision_id": binding["episode_version_id"],
            "current_revision_id": binding["episode_version_id"],
            "path": subtitle_path.relative_to(root_path).as_posix(),
            "sha256": subtitle_sha,
        },
        "mix": {"target_lufs": -16, "true_peak_db": -2, "music_duck_db": 5},
        "minimum_video_bitrate": 100000,
    }
    write_json(spec_path, spec)
    output_dir = root_path / "delivery"
    if output_dir.exists():
        raise RepresentativeEpisodeMediaError("authoritative assembly output already exists")
    result = assemble_episode(
        spec_path,
        output_dir,
        ffmpeg_executable=ffmpeg_executable,
        ffprobe_executable=ffprobe_executable,
    )
    qa_path = output_dir / "technical_qa.json"
    qa = _run_technical_qa_utf8(
        Path(result["episode"]),
        Path(result["manifest"]),
        qa_path,
        ffprobe_executable=ffprobe_executable,
        ffmpeg_executable=ffmpeg_executable,
    )
    if qa.get("status") != "pass":
        shutil.rmtree(output_dir, ignore_errors=True)
        raise RepresentativeEpisodeMediaError("technical episode QA did not pass")
    delivery = {
        "status": "technical_qa_passed",
        "assembly_complete": True,
        "episode_sha256": sha256_file(result["episode"]),
        "assembly_manifest_sha256": sha256_file(result["manifest"]),
        "technical_qa_sha256": sha256_file(qa_path),
        "duration_seconds": 135,
        "shot_count": 15,
        "media_slot_count": 25,
        "preview_url": (
            f"/projects/{media['project_id']}/production-runs/{media['run_id']}/"
            "representative-episode-media/delivery/preview"
        ),
        "continuity_status": "structural_checked",
        "evidence_label": "canonical_media_delivery_bridge_pass",
        "evidence_layer": "provider_free_technical_media_mechanics",
        "representative_content_proof": "not_started",
        "creative_media_quality": "not_evaluated",
        "human_acceptance": "not_evaluated",
        "business_validation": "not_evaluated",
    }
    return delivery


def structural_continuity_findings(
    binding: dict[str, Any], assets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not assets:
        return [
            {"check": name, "status": "not_evaluated"}
            for name in ("canonical_versions", "shot_timeline", "visual_inventory", "audio_coverage")
        ]
    by_id = {str(item.get("asset_id") or ""): item for item in assets}
    inventory = derive_authoritative_inventory(binding)
    version_ok = all(by_id.get(item["asset_id"], {}).get("revision_id") == item["revision_id"] for item in inventory)
    canon = binding["episode_canon"]
    timeline_ok = all(
        shot["ordinal"] == index
        and shot["entity_id"] == f"shot-{index:03d}"
        and shot["start_seconds"] == (index - 1) * 9
        and shot["end_seconds"] == index * 9
        for index, shot in enumerate(canon["shots"], start=1)
    )
    visual_ids = [item["asset_id"] for item in inventory if item["category"] != "audio"]
    visual_ok = all(by_id.get(asset_id, {}).get("media_kind") in {"image", "video"} for asset_id in visual_ids)
    audio_ids = [item["asset_id"] for item in inventory if item["category"] == "audio"]
    audio_ok = len(audio_ids) == 4 and all(by_id.get(asset_id, {}).get("media_kind") == "audio" for asset_id in audio_ids)
    results = [
        {"check": "canonical_versions", "status": "structural_checked" if version_ok else "blocked"},
        {"check": "shot_timeline", "status": "structural_checked" if timeline_ok else "blocked"},
        {"check": "visual_inventory", "status": "structural_checked" if visual_ok else "blocked"},
        {"check": "audio_coverage", "status": "structural_checked" if audio_ok else "blocked"},
    ]
    if any(item["status"] not in CONTINUITY_LABELS for item in results):
        raise RepresentativeEpisodeMediaError("unsupported continuity evidence label")
    return results


def safe_media_projection(media: Any) -> dict[str, Any]:
    if not isinstance(media, dict):
        return {
            "status": "not_started",
            "accepted_count": 0,
            "required_count": 25,
            "continuity_status": "not_evaluated",
            "assembly_status": "not_started",
            "representative_content_proof": "not_started",
        }
    assets = [item for item in media.get("assets") or [] if isinstance(item, dict)]
    delivery = media.get("delivery") if isinstance(media.get("delivery"), dict) else {}
    findings = [item for item in media.get("continuity_findings") or [] if isinstance(item, dict)]
    checked = bool(findings) and all(item.get("status") == "structural_checked" for item in findings)
    return {
        "status": "media_ready" if len(assets) == 25 else "media_pending",
        "accepted_count": len(assets),
        "required_count": 25,
        "visual_count": sum(item.get("category") != "audio" for item in assets),
        "audio_count": sum(item.get("category") == "audio" for item in assets),
        "continuity_status": "structural_checked" if checked else "blocked" if findings else "not_evaluated",
        "continuity_checks": [
            {"label": _continuity_label(str(item.get("check") or "")), "status": item.get("status")}
            for item in findings
            if item.get("status") in CONTINUITY_LABELS
        ],
        "assembly_status": "technical_qa_passed" if delivery.get("assembly_complete") is True else "not_started",
        "delivery_preview_url": str(delivery.get("preview_url") or ""),
        "duration_seconds": int(delivery.get("duration_seconds") or 0),
        "shot_count": int(delivery.get("shot_count") or 0),
        "representative_content_proof": "not_started",
        "creative_media_quality": "not_evaluated",
        "human_acceptance": "not_evaluated",
    }


def _require_v2_binding(binding: dict[str, Any]) -> None:
    canon = binding.get("episode_canon") if isinstance(binding.get("episode_canon"), dict) else {}
    if (
        binding.get("episode_version_id") != "ep-rainlight-001-v2"
        or binding.get("propagation_complete") is not True
        or canon.get("episode_version_id") != binding.get("episode_version_id")
        or len(canon.get("characters") or []) != 3
        or len(canon.get("scenes") or []) != 3
        or len(canon.get("shots") or []) != 15
        or canon.get("duration_seconds") != 135
    ):
        raise RepresentativeEpisodeMediaError("media intake requires exact propagated v2 fifteen-shot canon")


def _decode_base64(value: str) -> bytes:
    if not value or len(value) > MAX_ASSET_BYTES * 2:
        raise RepresentativeEpisodeMediaError("encoded media payload is missing or exceeds the safe limit")
    try:
        payload = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise RepresentativeEpisodeMediaError("media payload is not canonical base64") from exc
    if not payload or len(payload) > MAX_ASSET_BYTES:
        raise RepresentativeEpisodeMediaError("decoded media payload is empty or exceeds the safe limit")
    return payload


def _probe_and_decode(path: Path, media_kind: str, ffprobe: str, ffmpeg: str) -> dict[str, Any]:
    probe_command = [
        ffprobe, "-v", "error", "-print_format", "json", "-show_entries",
        "stream=codec_type,codec_name,duration,width,height,sample_rate,channels:format=duration", str(path),
    ]
    probe = _run(probe_command, timeout=30)
    if probe.returncode != 0:
        raise RepresentativeEpisodeMediaError("admitted media failed safe probe")
    try:
        value = json.loads(probe.stdout)
    except json.JSONDecodeError as exc:
        raise RepresentativeEpisodeMediaError("admitted media probe was not valid JSON") from exc
    if not isinstance(value, dict):
        raise RepresentativeEpisodeMediaError("admitted media probe was invalid")
    decode = _run([ffmpeg, "-v", "error", "-i", str(path), "-f", "null", "-"], timeout=60)
    if decode.returncode != 0:
        raise RepresentativeEpisodeMediaError(f"admitted {media_kind} bytes are not decodable")
    return value


def _validate_probe(slot: dict[str, Any], media_kind: str, mime_type: str, probe: dict[str, Any]) -> None:
    streams = [item for item in probe.get("streams") or [] if isinstance(item, dict)]
    video = [item for item in streams if item.get("codec_type") == "video"]
    audio = [item for item in streams if item.get("codec_type") == "audio"]
    if media_kind == "image":
        expected_codec = "png" if mime_type == "image/png" else "mjpeg"
        if len(video) != 1 or audio or video[0].get("codec_name") != expected_codec:
            raise RepresentativeEpisodeMediaError("image MIME, signature, and decoded codec do not agree")
        if int(video[0].get("width") or 0) < 320 or int(video[0].get("height") or 0) < 180:
            raise RepresentativeEpisodeMediaError("image dimensions are below the controlled minimum")
    elif media_kind == "video":
        if len(video) != 1 or audio or video[0].get("codec_name") not in {"h264", "hevc", "vp9", "av1"}:
            raise RepresentativeEpisodeMediaError("video must contain one supported visual stream and no audio")
        if int(video[0].get("width") or 0) < 320 or int(video[0].get("height") or 0) < 180:
            raise RepresentativeEpisodeMediaError("video dimensions are below the controlled minimum")
        duration = _probe_duration(probe)
        if duration is None or duration + PROBE_TOLERANCE_SECONDS < Decimal("9"):
            raise RepresentativeEpisodeMediaError("shot video is shorter than the canonical shot duration")
    else:
        if video or len(audio) != 1 or audio[0].get("codec_name") not in {"pcm_s16le", "pcm_s24le", "pcm_f32le"}:
            raise RepresentativeEpisodeMediaError("audio must be one supported WAV stream")
        if int(audio[0].get("sample_rate") or 0) != 48_000 or int(audio[0].get("channels") or 0) != 1:
            raise RepresentativeEpisodeMediaError("audio must use the controlled 48 kHz mono stem profile")
        duration = _probe_duration(probe)
        if duration is None or abs(duration - EPISODE_SECONDS) > PROBE_TOLERANCE_SECONDS:
            raise RepresentativeEpisodeMediaError("audio duration does not match the canonical timeline")


def _safe_probe(probe: dict[str, Any]) -> dict[str, Any]:
    streams = [item for item in probe.get("streams") or [] if isinstance(item, dict)]
    stream = streams[0] if streams else {}
    duration = _probe_duration(probe)
    return {
        "codec": str(stream.get("codec_name") or ""),
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "duration_seconds": float(duration) if duration is not None else 0,
        "sample_rate": int(stream.get("sample_rate") or 0),
        "channels": int(stream.get("channels") or 0),
        "decoded": True,
    }


def _probe_duration(probe: dict[str, Any]) -> Decimal | None:
    values = []
    if isinstance(probe.get("format"), dict):
        values.append(probe["format"].get("duration"))
    values.extend(item.get("duration") for item in probe.get("streams") or [] if isinstance(item, dict))
    for value in values:
        try:
            if value not in {None, "N/A"}:
                return Decimal(str(value))
        except (InvalidOperation, ValueError):
            continue
    return None


def _episode_asset(root: Path, asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset_id": asset["asset_id"],
        "revision_id": asset["revision_id"],
        "current_revision_id": asset["revision_id"],
        "path": _controlled_path(root, asset["relative_ref"]).relative_to(root).as_posix(),
        "sha256": asset["sha256"],
        "media_type": asset["media_kind"],
    }


def _write_subtitles(binding: dict[str, Any], path: Path) -> None:
    blocks: list[str] = []
    for index, shot in enumerate(binding["episode_canon"]["shots"], start=1):
        text = " ".join(str(item.get("text") or "").strip() for item in shot.get("dialogue") or []).strip()
        if not text:
            raise RepresentativeEpisodeMediaError("canonical subtitle text is missing")
        blocks.append(
            f"{index}\n{_srt_time(int(shot['start_seconds']))} --> {_srt_time(int(shot['end_seconds']))}\n{text}"
        )
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def _srt_time(seconds: int) -> str:
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d},000"


def _controlled_path(root: Path, relative_ref: Any) -> Path:
    relative = Path(str(relative_ref or ""))
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise RepresentativeEpisodeMediaError("persisted media ref is unsafe")
    resolved = (root / relative).resolve()
    if root not in resolved.parents:
        raise RepresentativeEpisodeMediaError("persisted media ref escapes the controlled root")
    return resolved


def _mime_matches_kind(mime_type: str, media_kind: str) -> bool:
    return mime_type.startswith(f"{media_kind}/")


def _continuity_label(value: str) -> str:
    return {
        "canonical_versions": "规范版本一致",
        "shot_timeline": "十五镜时间线",
        "visual_inventory": "角色场景与镜头素材",
        "audio_coverage": "对白音乐音效与母版",
    }.get(value, "结构检查")


def _json_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _run(command: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        raise RepresentativeEpisodeMediaError(f"controlled media tool unavailable: {exc}") from exc


def _run_technical_qa_utf8(
    episode_path: Path,
    manifest_path: Path,
    output_path: Path,
    *,
    ffprobe_executable: str,
    ffmpeg_executable: str,
) -> dict[str, Any]:
    code = (
        "import json,sys;"
        "from pathlib import Path;"
        "from agentflow_studio.production.episode_media_quality import run_episode_technical_qa;"
        "value=run_episode_technical_qa(Path(sys.argv[1]),Path(sys.argv[2]),"
        "ffprobe_executable=sys.argv[4],ffmpeg_executable=sys.argv[5]);"
        "Path(sys.argv[3]).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\\n',encoding='utf-8')"
    )
    command = [
        sys.executable, "-X", "utf8", "-c", code,
        str(episode_path), str(manifest_path), str(output_path),
        ffprobe_executable, ffmpeg_executable,
    ]
    completed = _run(command, timeout=180)
    if completed.returncode != 0 or not output_path.is_file():
        raise RepresentativeEpisodeMediaError("technical episode QA execution failed")
    try:
        value = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RepresentativeEpisodeMediaError("technical episode QA evidence is unreadable") from exc
    if not isinstance(value, dict):
        raise RepresentativeEpisodeMediaError("technical episode QA evidence is invalid")
    return value


def _text(value: Any) -> str:
    return str(value or "").strip()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = (
    "MEDIA_SCHEMA_VERSION",
    "MEDIA_INTAKE_CONTRACT",
    "RepresentativeEpisodeMediaError",
    "admit_authoritative_media",
    "assemble_authoritative_episode",
    "derive_authoritative_inventory",
    "revalidate_authoritative_media",
    "safe_media_projection",
    "structural_continuity_findings",
)
