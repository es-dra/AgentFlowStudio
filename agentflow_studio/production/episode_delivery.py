from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "0.1.0"
MIN_EPISODE_SECONDS = Decimal("120")
MAX_EPISODE_SECONDS = Decimal("180")


@dataclass(frozen=True)
class FrozenEpisode:
    spec: dict[str, Any]
    spec_path: Path
    duration_seconds: Decimal


class EpisodeContractError(ValueError):
    pass


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_episode_spec(spec_path: str | Path) -> FrozenEpisode:
    path = Path(spec_path).resolve()
    spec = _read_json(path)
    if spec.get("schema_version") != SCHEMA_VERSION:
        raise EpisodeContractError("unsupported episode schema_version")
    if spec.get("provider_calls_started") != 0:
        raise EpisodeContractError("provider calls must remain zero")
    for field in ("project_id", "episode_id"):
        if not _text(spec.get(field)):
            raise EpisodeContractError(f"missing {field}")

    shots = spec.get("shots")
    if not isinstance(shots, list) or not shots:
        raise EpisodeContractError("shots must be a non-empty array")
    cursor = Decimal("0")
    seen_shots: set[str] = set()
    for index, shot in enumerate(shots):
        if not isinstance(shot, dict):
            raise EpisodeContractError(f"shot {index} must be an object")
        shot_id = _text(shot.get("shot_id"))
        if not shot_id or shot_id in seen_shots:
            raise EpisodeContractError(f"shot {index} has missing or duplicate shot_id")
        seen_shots.add(shot_id)
        start = _decimal(shot.get("start_seconds"), f"{shot_id}.start_seconds")
        end = _decimal(shot.get("end_seconds"), f"{shot_id}.end_seconds")
        if start != cursor:
            raise EpisodeContractError(f"timeline gap or overlap before {shot_id}")
        if end <= start:
            raise EpisodeContractError(f"non-positive duration for {shot_id}")
        _validate_controlled_asset(path.parent, shot.get("visual_asset"), f"{shot_id}.visual_asset")
        _validate_lineage(spec, shot)
        cursor = end

    if not MIN_EPISODE_SECONDS <= cursor <= MAX_EPISODE_SECONDS:
        raise EpisodeContractError("episode duration must be between 120 and 180 seconds")
    declared = _decimal(spec.get("duration_seconds"), "duration_seconds")
    if declared != cursor:
        raise EpisodeContractError("declared duration does not match the shot timeline")
    _validate_controlled_asset(path.parent, spec.get("audio_asset"), "audio_asset")
    _validate_controlled_asset(path.parent, spec.get("subtitle_asset"), "subtitle_asset")
    return FrozenEpisode(spec=spec, spec_path=path, duration_seconds=cursor)


def assemble_episode(
    spec_path: str | Path,
    output_dir: str | Path,
    *,
    ffmpeg_executable: str = "ffmpeg",
) -> dict[str, Any]:
    frozen = validate_episode_spec(spec_path)
    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    episode_path = destination / "episode.mp4"
    manifest_path = destination / "assembly_manifest.json"
    command = build_ffmpeg_command(frozen, episode_path, ffmpeg_executable=ffmpeg_executable)
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        episode_path.unlink(missing_ok=True)
        detail = (result.stderr or result.stdout or "ffmpeg failed").strip()
        raise RuntimeError(f"episode assembly failed: {detail[-2000:]}")
    if not episode_path.is_file() or episode_path.stat().st_size == 0:
        raise RuntimeError("episode assembly did not create a non-empty MP4")

    spec = frozen.spec
    timeline = [
        {
            "shot_id": shot["shot_id"],
            "start_seconds": shot["start_seconds"],
            "end_seconds": shot["end_seconds"],
            "asset_id": shot["visual_asset"]["asset_id"],
            "revision_id": shot["visual_asset"]["revision_id"],
            "asset_sha256": shot["visual_asset"]["sha256"],
            "lineage": shot["lineage"],
        }
        for shot in spec["shots"]
    ]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "provider_free_episode_delivery",
        "project_id": spec["project_id"],
        "episode_id": spec["episode_id"],
        "episode_ref": episode_path.name,
        "episode_sha256": sha256_file(episode_path),
        "episode_bytes": episode_path.stat().st_size,
        "duration_seconds": _number(frozen.duration_seconds),
        "shot_timeline": timeline,
        "audio_lineage": _asset_lineage(spec["audio_asset"]),
        "subtitle_lineage": _asset_lineage(spec["subtitle_asset"]),
        "input_spec_sha256": sha256_file(frozen.spec_path),
        "provider_calls_started": 0,
        "deterministic_replay": {
            "contract": "same canonical source bytes, ordered timeline, toolchain, and bitexact command produce the same artifact hash",
            "command_sha256": _command_sha256(command, frozen.spec_path.parent, destination),
            "ffmpeg_flags": ["bitexact", "single_thread", "metadata_stripped", "fixed_frame_rate"],
        },
        "evidence_layer": "runtime_media_structure",
        "non_claims": ["not_creative_media_quality", "not_human_acceptance", "not_business_validation"],
    }
    _write_json(manifest_path, manifest)
    return {
        "episode": episode_path,
        "manifest": manifest_path,
        "manifest_sha256": sha256_file(manifest_path),
        "command": command,
    }


def build_ffmpeg_command(
    frozen: FrozenEpisode,
    output_path: str | Path,
    *,
    ffmpeg_executable: str = "ffmpeg",
) -> list[str]:
    root = frozen.spec_path.parent
    shots = frozen.spec["shots"]
    command = [ffmpeg_executable, "-hide_banner", "-loglevel", "error", "-y"]
    filters: list[str] = []
    labels: list[str] = []
    frame_rate = int(frozen.spec.get("frame_rate") or 6)
    for index, shot in enumerate(shots):
        duration = _decimal(shot["end_seconds"], "end") - _decimal(shot["start_seconds"], "start")
        command.extend(
            ["-loop", "1", "-framerate", str(frame_rate), "-t", str(duration), "-i", str(_asset_path(root, shot["visual_asset"]))]
        )
        label = f"v{index}"
        filters.append(f"[{index}:v]trim=duration={duration},setpts=PTS-STARTPTS[{label}]")
        labels.append(f"[{label}]")
    audio_index = len(shots)
    subtitle_index = audio_index + 1
    command.extend(["-i", str(_asset_path(root, frozen.spec["audio_asset"]))])
    command.extend(["-i", str(_asset_path(root, frozen.spec["subtitle_asset"]))])
    filters.append(f"{''.join(labels)}concat=n={len(shots)}:v=1:a=0[outv]")
    command.extend(
        [
            "-filter_complex", ";".join(filters), "-map", "[outv]", "-map", f"{audio_index}:a:0", "-map", f"{subtitle_index}:s:0",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-pix_fmt", "yuv420p", "-r", str(frame_rate), "-threads", "1",
            "-c:a", "aac", "-b:a", "64k", "-c:s", "mov_text", "-t", str(frozen.duration_seconds),
            "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:v", "+bitexact", "-flags:a", "+bitexact",
            "-metadata", "creation_time=2000-01-01T00:00:00Z", "-movflags", "+faststart", str(Path(output_path).resolve()),
        ]
    )
    return command


def _validate_controlled_asset(root: Path, value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise EpisodeContractError(f"{label} must be an object")
    required = ("asset_id", "revision_id", "current_revision_id", "path", "sha256")
    if any(not _text(value.get(field)) for field in required):
        raise EpisodeContractError(f"{label} is missing controlled asset fields")
    if value["revision_id"] != value["current_revision_id"]:
        raise EpisodeContractError(f"{label} references a stale revision")
    asset_path = _asset_path(root, value)
    if not asset_path.is_file():
        raise EpisodeContractError(f"{label} file is missing")
    if sha256_file(asset_path) != value["sha256"]:
        raise EpisodeContractError(f"{label} sha256 mismatch")


def _validate_lineage(spec: dict[str, Any], shot: dict[str, Any]) -> None:
    lineage = shot.get("lineage")
    asset = shot["visual_asset"]
    expected = {
        "project_id": spec["project_id"], "episode_id": spec["episode_id"], "scene_id": shot.get("scene_id"),
        "shot_id": shot["shot_id"], "asset_id": asset["asset_id"], "revision_id": asset["revision_id"],
    }
    if not isinstance(lineage, dict) or lineage != expected:
        raise EpisodeContractError(f"lineage mismatch for {shot['shot_id']}")


def _asset_path(root: Path, asset: dict[str, Any]) -> Path:
    relative = Path(str(asset.get("path") or ""))
    if relative.is_absolute() or ".." in relative.parts:
        raise EpisodeContractError("asset path must be a safe relative path")
    resolved = (root / relative).resolve()
    if root.resolve() not in resolved.parents:
        raise EpisodeContractError("asset path escapes the episode root")
    return resolved


def _asset_lineage(asset: dict[str, Any]) -> dict[str, str]:
    return {key: str(asset[key]) for key in ("asset_id", "revision_id", "sha256")}


def _command_sha256(command: list[str], source_root: Path, output_root: Path) -> str:
    normalized = [part.replace(str(source_root), "<SOURCE>").replace(str(output_root), "<OUTPUT>") for part in command]
    return hashlib.sha256(json.dumps(normalized, separators=(",", ":")).encode()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EpisodeContractError(f"invalid episode spec: {exc}") from exc
    if not isinstance(value, dict):
        raise EpisodeContractError("episode spec must be an object")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _decimal(value: Any, label: str) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise EpisodeContractError(f"invalid decimal for {label}") from exc


def _number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral() else float(value)


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""
