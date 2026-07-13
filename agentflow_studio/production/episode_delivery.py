from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "0.2.0"
ASSEMBLY_CONTRACT = "agentflow_studio.production.episode_delivery.v0.1"
MIN_EPISODE_SECONDS = Decimal("120")
MAX_EPISODE_SECONDS = Decimal("180")
DURATION_TOLERANCE_SECONDS = Decimal("0.25")
REQUIRED_AUDIO_STEMS = ("dialogue", "music", "sfx")


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


def validate_episode_spec(
    spec_path: str | Path,
    *,
    ffprobe_executable: str = "ffprobe",
) -> FrozenEpisode:
    path = Path(spec_path).resolve()
    spec = _read_json(path)
    if spec.get("schema_version") != SCHEMA_VERSION:
        raise EpisodeContractError("unsupported episode schema_version")
    if spec.get("contract") != ASSEMBLY_CONTRACT:
        raise EpisodeContractError("TP-D assembly contract mapping missing")
    if spec.get("provider_calls_started") != 0:
        raise EpisodeContractError("provider calls must remain zero")
    for field in ("project_id", "episode_id"):
        if not _text(spec.get(field)):
            raise EpisodeContractError(f"missing {field}")

    width = _positive_int(spec.get("width"), "width")
    height = _positive_int(spec.get("height"), "height")
    frame_rate = _decimal(spec.get("frame_rate"), "frame_rate")
    if width % 2 or height % 2 or width < 320 or height < 180:
        raise EpisodeContractError("output dimensions must be even and at least 320x180")
    if not Decimal("6") <= frame_rate <= Decimal("60"):
        raise EpisodeContractError("frame_rate must be between 6 and 60")

    shots = spec.get("shots")
    if not isinstance(shots, list) or not shots:
        raise EpisodeContractError("shots must be a non-empty array")
    if _positive_int(spec.get("shot_count"), "shot_count") != len(shots):
        raise EpisodeContractError("declared shot_count does not match shots")
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
        asset = _validate_controlled_asset(path.parent, shot.get("visual_asset"), f"{shot_id}.visual_asset")
        media_type = _text(asset.get("media_type"))
        if media_type not in {"image", "video"}:
            raise EpisodeContractError(f"{shot_id}.visual_asset has unsupported media_type")
        probe = _probe_asset(_asset_path(path.parent, asset), ffprobe_executable)
        _validate_visual_probe(probe, media_type, shot_id, end - start, shot.get("source_start_seconds", 0))
        _validate_lineage(spec, shot)
        cursor = end

    if not MIN_EPISODE_SECONDS <= cursor <= MAX_EPISODE_SECONDS:
        raise EpisodeContractError("episode duration must be between 120 and 180 seconds")
    declared = _decimal(spec.get("duration_seconds"), "duration_seconds")
    if declared != cursor:
        raise EpisodeContractError("declared duration does not match the shot timeline")

    stems = spec.get("audio_stems")
    if not isinstance(stems, dict) or tuple(sorted(stems)) != tuple(sorted(REQUIRED_AUDIO_STEMS)):
        raise EpisodeContractError("audio_stems must contain exactly dialogue, music, and sfx")
    for stem_name in REQUIRED_AUDIO_STEMS:
        asset = _validate_controlled_asset(path.parent, stems[stem_name], f"audio_stems.{stem_name}")
        probe = _probe_asset(_asset_path(path.parent, asset), ffprobe_executable)
        _validate_audio_probe(probe, f"audio_stems.{stem_name}", declared)

    subtitle = _validate_controlled_asset(path.parent, spec.get("subtitle_asset"), "subtitle_asset")
    subtitle_path = _asset_path(path.parent, subtitle)
    if subtitle_path.suffix.lower() != ".srt":
        raise EpisodeContractError("subtitle_asset must be an SRT file")
    cues = _parse_srt(subtitle_path)
    _validate_subtitle_cues(cues, shots, declared)
    _validate_mix(spec.get("mix"))
    return FrozenEpisode(spec=spec, spec_path=path, duration_seconds=cursor)


def assemble_episode(
    spec_path: str | Path,
    output_dir: str | Path,
    *,
    ffmpeg_executable: str = "ffmpeg",
    ffprobe_executable: str = "ffprobe",
) -> dict[str, Any]:
    frozen = validate_episode_spec(spec_path, ffprobe_executable=ffprobe_executable)
    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    episode_path = destination / "episode.mp4"
    manifest_path = destination / "assembly_manifest.json"
    command = build_ffmpeg_command(frozen, episode_path, ffmpeg_executable=ffmpeg_executable)
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        episode_path.unlink(missing_ok=True)
        detail = (result.stderr or result.stdout or "ffmpeg failed").strip()
        raise RuntimeError(f"episode assembly failed: {detail[-3000:]}")
    if not episode_path.is_file() or episode_path.stat().st_size == 0:
        raise RuntimeError("episode assembly did not create a non-empty MP4")

    spec = frozen.spec
    timeline = [
        {
            "shot_id": shot["shot_id"],
            "scene_id": shot.get("scene_id"),
            "start_seconds": shot["start_seconds"],
            "end_seconds": shot["end_seconds"],
            "source_start_seconds": shot.get("source_start_seconds", 0),
            "media_type": shot["visual_asset"]["media_type"],
            "asset_id": shot["visual_asset"]["asset_id"],
            "revision_id": shot["visual_asset"]["revision_id"],
            "asset_sha256": shot["visual_asset"]["sha256"],
            "lineage": shot["lineage"],
        }
        for shot in spec["shots"]
    ]
    expected_cuts = [shot["start_seconds"] for shot in spec["shots"]]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "source_contract": ASSEMBLY_CONTRACT,
        "artifact_type": "provider_free_mixed_media_episode_delivery",
        "evidence_label": "representative_episode_assembly_engine_pass",
        "project_id": spec["project_id"],
        "episode_id": spec["episode_id"],
        "episode_ref": episode_path.name,
        "episode_sha256": sha256_file(episode_path),
        "episode_bytes": episode_path.stat().st_size,
        "duration_seconds": _number(frozen.duration_seconds),
        "shot_count": len(timeline),
        "shot_timeline": timeline,
        "expected_cut_seconds": expected_cuts,
        "audio_stem_lineage": {name: _asset_lineage(spec["audio_stems"][name]) for name in REQUIRED_AUDIO_STEMS},
        "subtitle_lineage": _asset_lineage(spec["subtitle_asset"]),
        "output_profile": {
            "width": int(spec["width"]),
            "height": int(spec["height"]),
            "frame_rate": _number(_decimal(spec["frame_rate"], "frame_rate")),
            "minimum_video_bitrate": int(spec.get("minimum_video_bitrate") or 100_000),
            "audio_sample_rate": 48_000,
            "audio_channels": 2,
        },
        "mix": dict(spec["mix"]),
        "input_spec_sha256": sha256_file(frozen.spec_path),
        "provider_calls_started": 0,
        "deterministic_replay": {
            "scope": "same canonical bytes, ordered timeline, command, OS, and exact ffmpeg build",
            "codec_limit": "codec/container hashes are not promised across ffmpeg or encoder builds",
            "command_sha256": _command_sha256(command, frozen.spec_path.parent, destination),
            "ffmpeg_flags": ["single_thread", "metadata_stripped", "fixed_frame_rate", "forced_shot_keyframes"],
        },
        "evidence_layer": "technical_media_assembly",
        "non_claims": [
            "not_representative_content_proof",
            "not_creative_media_quality",
            "not_human_acceptance",
            "not_business_validation",
            "not_release_evidence",
        ],
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
    spec = frozen.spec
    shots = spec["shots"]
    width, height = int(spec["width"]), int(spec["height"])
    frame_rate = _decimal(spec["frame_rate"], "frame_rate")
    fps_text = str(frame_rate.normalize())
    command = [ffmpeg_executable, "-hide_banner", "-loglevel", "error", "-y"]
    filters: list[str] = []
    labels: list[str] = []
    for index, shot in enumerate(shots):
        duration = _decimal(shot["end_seconds"], "end") - _decimal(shot["start_seconds"], "start")
        asset_path = str(_asset_path(root, shot["visual_asset"]))
        if shot["visual_asset"]["media_type"] == "image":
            command.extend(["-loop", "1", "-framerate", fps_text, "-t", str(duration), "-i", asset_path])
            enlarged_width = width + max(32, width // 16)
            enlarged_height = height + max(18, height // 16)
            transform = (
                f"scale={enlarged_width}:{enlarged_height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height}:x='(in_w-out_w)*(0.5+0.45*sin(t*0.37))':"
                f"y='(in_h-out_h)*(0.5+0.45*cos(t*0.29))'"
            )
        else:
            source_start = _decimal(shot.get("source_start_seconds", 0), "source_start_seconds")
            command.extend(["-ss", str(source_start), "-t", str(duration), "-i", asset_path])
            transform = (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height}"
            )
        label = f"v{index}"
        filters.append(
            f"[{index}:v]{transform},fps={fps_text},trim=duration={duration},"
            f"setpts=PTS-STARTPTS,setsar=1,format=yuv420p[{label}]"
        )
        labels.append(f"[{label}]")

    audio_start = len(shots)
    for stem_name in REQUIRED_AUDIO_STEMS:
        command.extend(["-i", str(_asset_path(root, spec["audio_stems"][stem_name]))])
    subtitle_index = audio_start + len(REQUIRED_AUDIO_STEMS)
    command.extend(["-i", str(_asset_path(root, spec["subtitle_asset"]))])
    filters.append(f"{''.join(labels)}concat=n={len(shots)}:v=1:a=0[outv]")

    duration = str(frozen.duration_seconds)
    dialogue_index, music_index, sfx_index = audio_start, audio_start + 1, audio_start + 2
    mix = spec["mix"]
    target_lufs = _decimal(mix["target_lufs"], "mix.target_lufs")
    true_peak = _decimal(mix["true_peak_db"], "mix.true_peak_db")
    duck_db = _decimal(mix["music_duck_db"], "mix.music_duck_db")
    filters.extend(
        [
            f"[{dialogue_index}:a]atrim=duration={duration},asetpts=PTS-STARTPTS,aresample=48000,"
            "aformat=sample_fmts=fltp:channel_layouts=stereo,apad[dialogue]",
            f"[{music_index}:a]atrim=duration={duration},asetpts=PTS-STARTPTS,aresample=48000,"
            "aformat=sample_fmts=fltp:channel_layouts=stereo,apad[music]",
            f"[{sfx_index}:a]atrim=duration={duration},asetpts=PTS-STARTPTS,aresample=48000,"
            "aformat=sample_fmts=fltp:channel_layouts=stereo,apad[sfx]",
            "[dialogue]asplit=2[dialogue_main][dialogue_side]",
            f"[music][dialogue_side]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=300,"
            f"volume={float(Decimal(10) ** (-duck_db / Decimal(20))):.8f}[ducked_music]",
            f"[dialogue_main][ducked_music][sfx]amix=inputs=3:duration=longest:dropout_transition=0:normalize=0,"
            f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11[outa]",
        ]
    )
    cut_times = ",".join(str(shot["start_seconds"]) for shot in shots)
    command.extend(
        [
            "-filter_complex", ";".join(filters),
            "-map", "[outv]", "-map", "[outa]", "-map", f"{subtitle_index}:s:0",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", "-pix_fmt", "yuv420p",
            "-r", fps_text, "-threads", "1", "-sc_threshold", "0", "-force_key_frames", cut_times,
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
            "-c:s", "mov_text", "-t", duration,
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-metadata", "creation_time=2000-01-01T00:00:00Z",
            "-metadata:s:s:0", "language=und", "-movflags", "+faststart",
            str(Path(output_path).resolve()),
        ]
    )
    return command


def _validate_controlled_asset(root: Path, value: Any, label: str) -> dict[str, Any]:
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
    return value


def _validate_visual_probe(
    probe: dict[str, Any], media_type: str, shot_id: str, duration: Decimal, source_start: Any,
) -> None:
    streams = probe.get("streams") if isinstance(probe.get("streams"), list) else []
    video = [stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") == "video"]
    other = [stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") != "video"]
    if len(video) != 1 or other:
        raise EpisodeContractError(f"{shot_id}.visual_asset has unsupported streams")
    if media_type == "image":
        if _probe_duration(probe) not in {None, Decimal("0")}:
            raise EpisodeContractError(f"{shot_id}.visual_asset media_type mismatches a timed video")
        return
    available = _probe_duration(probe)
    start = _decimal(source_start, f"{shot_id}.source_start_seconds")
    if start < 0:
        raise EpisodeContractError(f"{shot_id}.source_start_seconds must not be negative")
    if available is None or available + DURATION_TOLERANCE_SECONDS < start + duration:
        raise EpisodeContractError(f"{shot_id}.visual_asset duration is shorter than the requested trim")


def _validate_audio_probe(probe: dict[str, Any], label: str, duration: Decimal) -> None:
    streams = probe.get("streams") if isinstance(probe.get("streams"), list) else []
    audio = [stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") == "audio"]
    other = [stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") != "audio"]
    if len(audio) != 1 or other:
        raise EpisodeContractError(f"{label} has unsupported streams")
    actual = _probe_duration(probe)
    if actual is None or abs(actual - duration) > DURATION_TOLERANCE_SECONDS:
        raise EpisodeContractError(f"{label} duration does not match the episode")


def _validate_mix(value: Any) -> None:
    if not isinstance(value, dict):
        raise EpisodeContractError("mix must be an object")
    target = _decimal(value.get("target_lufs"), "mix.target_lufs")
    peak = _decimal(value.get("true_peak_db"), "mix.true_peak_db")
    duck = _decimal(value.get("music_duck_db"), "mix.music_duck_db")
    if not Decimal("-20") <= target <= Decimal("-14"):
        raise EpisodeContractError("mix.target_lufs must be between -20 and -14")
    if not Decimal("-6") <= peak <= Decimal("-1"):
        raise EpisodeContractError("mix.true_peak_db must be between -6 and -1")
    if not Decimal("4") <= duck <= Decimal("6"):
        raise EpisodeContractError("mix.music_duck_db must be between 4 and 6")


def _validate_subtitle_cues(cues: list[tuple[Decimal, Decimal, str]], shots: list[dict[str, Any]], duration: Decimal) -> None:
    if len(cues) != len(shots):
        raise EpisodeContractError("subtitle cues must cover every shot")
    for index, ((start, end, text), shot) in enumerate(zip(cues, shots, strict=True)):
        expected_start = _decimal(shot["start_seconds"], "shot.start_seconds")
        expected_end = _decimal(shot["end_seconds"], "shot.end_seconds")
        if start != expected_start or end != expected_end or not text.strip():
            raise EpisodeContractError(f"subtitle cue {index + 1} does not match shot timing")
    if cues[-1][1] != duration:
        raise EpisodeContractError("subtitle duration does not match the episode")


def _parse_srt(path: Path) -> list[tuple[Decimal, Decimal, str]]:
    text = path.read_text(encoding="utf-8-sig")
    blocks = re.split(r"\r?\n\s*\r?\n", text.strip()) if text.strip() else []
    cues: list[tuple[Decimal, Decimal, str]] = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3 or "-->" not in lines[1]:
            raise EpisodeContractError("subtitle_asset contains an invalid SRT cue")
        left, right = (part.strip() for part in lines[1].split("-->", 1))
        cues.append((_srt_decimal(left), _srt_decimal(right), "\n".join(lines[2:])))
    return cues


def _srt_decimal(value: str) -> Decimal:
    match = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})", value)
    if not match:
        raise EpisodeContractError("subtitle_asset contains an invalid SRT timestamp")
    hours, minutes, seconds, millis = (Decimal(part) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def _probe_asset(path: Path, executable: str) -> dict[str, Any]:
    command = [
        executable, "-v", "error", "-print_format", "json",
        "-show_entries", "stream=codec_type,codec_name,duration,avg_frame_rate,width,height:format=duration",
        str(path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        raise EpisodeContractError(f"cannot inspect controlled media asset: {exc}") from exc
    if result.returncode != 0:
        raise EpisodeContractError(f"controlled media asset is not decodable: {(result.stderr or '').strip()[-500:]}")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise EpisodeContractError("ffprobe returned invalid controlled asset metadata") from exc
    if not isinstance(value, dict):
        raise EpisodeContractError("ffprobe returned invalid controlled asset metadata")
    return value


def _probe_duration(probe: dict[str, Any]) -> Decimal | None:
    format_info = probe.get("format") if isinstance(probe.get("format"), dict) else {}
    values = [format_info.get("duration")]
    for stream in probe.get("streams", []):
        if isinstance(stream, dict):
            values.append(stream.get("duration"))
    for value in values:
        try:
            if value not in {None, "N/A"}:
                return Decimal(str(value))
        except Exception:
            continue
    return None


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


def _positive_int(value: Any, label: str) -> int:
    try:
        number = int(value)
    except Exception as exc:
        raise EpisodeContractError(f"invalid integer for {label}") from exc
    if number <= 0:
        raise EpisodeContractError(f"{label} must be positive")
    return number


def _number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral() else float(value)


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""
