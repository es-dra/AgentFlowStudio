from __future__ import annotations

import json
import os
import re
import subprocess
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

from agentflow_studio.production.episode_delivery import sha256_file


DURATION_TOLERANCE_SECONDS = Decimal("0.25")
CUT_TOLERANCE_SECONDS = Decimal("0.15")


def run_episode_technical_qa(
    episode_path: str | Path,
    manifest_path: str | Path,
    *,
    ffprobe_executable: str = "ffprobe",
    ffmpeg_executable: str = "ffmpeg",
) -> dict[str, Any]:
    episode = Path(episode_path).resolve()
    manifest_file = Path(manifest_path).resolve()
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    manifest = _load_manifest(manifest_file, checks, errors)
    probe = _probe(episode, ffprobe_executable, checks, errors)

    if manifest:
        _check_manifest(episode, manifest, checks, errors)
    if probe:
        _check_probe(probe, manifest, checks, errors)
        _check_subtitle_bounds(episode, manifest, ffmpeg_executable, checks, errors)
        _check_cut_timing(episode, manifest, ffprobe_executable, checks, errors)
        _check_visual_signals(episode, ffmpeg_executable, checks, errors)
        _check_audio_signals(episode, manifest, ffmpeg_executable, checks, errors)
        _check_media_decode(episode, ffmpeg_executable, checks, errors)
    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "status": "pass" if not failed else "fail",
        "evidence_label": "representative_episode_assembly_engine_pass" if not failed else "technical_media_qa_fail",
        "evidence_layer": "technical_media_qa",
        "checks": checks,
        "errors": list(dict.fromkeys(errors)),
        "probe": probe or {},
        "artifact": {
            "episode_ref": episode.name,
            "sha256": sha256_file(episode) if episode.is_file() else None,
            "bytes": episode.stat().st_size if episode.is_file() else 0,
        },
        "non_claims": [
            "not_representative_content_proof",
            "not_creative_media_quality",
            "not_human_acceptance",
            "not_business_validation",
            "not_release_evidence",
        ],
    }


def _load_manifest(path: Path, checks: list[dict[str, Any]], errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        _add(checks, "assembly_manifest_present", False)
        errors.append("assembly manifest is missing")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _add(checks, "assembly_manifest_valid", False)
        errors.append("assembly manifest is invalid")
        return None
    valid = isinstance(value, dict)
    _add(checks, "assembly_manifest_valid", valid)
    return value if valid else None


def _probe(path: Path, executable: str, checks: list[dict[str, Any]], errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file() or path.stat().st_size == 0:
        _add(checks, "episode_file_present", False)
        errors.append("episode MP4 is missing or empty")
        return None
    _add(checks, "episode_file_present", True)
    command = [executable, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path.name]
    result = _run(command, timeout=30, cwd=path.parent)
    if result.returncode != 0:
        _add(checks, "ffprobe_openable", False)
        errors.append((result.stderr or "ffprobe failed").strip())
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        _add(checks, "ffprobe_openable", False)
        errors.append("ffprobe returned invalid JSON")
        return None
    _add(checks, "ffprobe_openable", True)
    return payload


def _check_manifest(path: Path, manifest: dict[str, Any], checks: list[dict[str, Any]], errors: list[str]) -> None:
    expected_hash = str(manifest.get("episode_sha256") or "")
    hash_ok = len(expected_hash) == 64 and expected_hash == sha256_file(path)
    _add(checks, "episode_sha256_exact", hash_ok)
    if not hash_ok:
        errors.append("episode sha256 does not match assembly manifest")
    provider_ok = manifest.get("provider_calls_started") == 0
    _add(checks, "provider_calls_zero", provider_ok)
    if not provider_ok:
        errors.append("provider call count is not zero")
    label_ok = manifest.get("evidence_label") == "representative_episode_assembly_engine_pass"
    _add(checks, "evidence_label_bounded", label_ok)
    if not label_ok:
        errors.append("assembly evidence label is missing or overclaimed")
    _check_timeline(manifest.get("shot_timeline"), manifest.get("duration_seconds"), checks, errors)
    stems = manifest.get("audio_stem_lineage")
    stems_ok = isinstance(stems, dict) and set(stems) == {"dialogue", "music", "sfx"}
    _add(checks, "three_stem_lineage_complete", stems_ok)
    if not stems_ok:
        errors.append("dialogue, music, and sfx lineage is incomplete")


def _check_timeline(value: Any, declared: Any, checks: list[dict[str, Any]], errors: list[str]) -> None:
    cursor = Decimal("0")
    valid = isinstance(value, list) and bool(value)
    if valid:
        for shot in value:
            required = {
                "shot_id", "start_seconds", "end_seconds", "media_type", "asset_id",
                "revision_id", "asset_sha256", "lineage",
            }
            if not isinstance(shot, dict) or not required.issubset(shot):
                valid = False
                break
            start, end = Decimal(str(shot["start_seconds"])), Decimal(str(shot["end_seconds"]))
            lineage = shot["lineage"]
            if start != cursor or end <= start or shot["media_type"] not in {"image", "video"} or not isinstance(lineage, dict):
                valid = False
                break
            if any(lineage.get(key) != shot.get(key) for key in ("shot_id", "asset_id", "revision_id")):
                valid = False
                break
            cursor = end
    try:
        valid = valid and cursor == Decimal(str(declared)) and Decimal("120") <= cursor <= Decimal("180")
    except Exception:
        valid = False
    _add(checks, "timeline_and_lineage_exact", valid)
    if not valid:
        errors.append("shot timeline or lineage is incomplete")


def _check_probe(probe: dict[str, Any], manifest: dict[str, Any] | None, checks: list[dict[str, Any]], errors: list[str]) -> None:
    streams = probe.get("streams") if isinstance(probe.get("streams"), list) else []
    typed = {stream.get("codec_type"): stream for stream in streams if isinstance(stream, dict)}
    for stream_type in ("video", "audio", "subtitle"):
        present = stream_type in typed
        _add(checks, f"{stream_type}_stream_present", present)
        if not present:
            errors.append(f"{stream_type} stream is missing")
    actual = _duration(probe)
    declared = Decimal(str(manifest.get("duration_seconds"))) if manifest else None
    duration_ok = actual is not None and Decimal("120") <= actual <= Decimal("180")
    exact = duration_ok and declared is not None and abs(actual - declared) <= DURATION_TOLERANCE_SECONDS
    _add(checks, "duration_120_to_180_seconds", duration_ok, {"actual_seconds": float(actual) if actual else None})
    _add(checks, "duration_matches_manifest", exact)
    if not duration_ok or not exact:
        errors.append("episode duration is invalid or differs from the manifest")

    profile = manifest.get("output_profile") if manifest and isinstance(manifest.get("output_profile"), dict) else {}
    video = typed.get("video") or {}
    width_ok = video.get("width") == profile.get("width")
    height_ok = video.get("height") == profile.get("height")
    _add(checks, "resolution_matches_profile", width_ok and height_ok, {"width": video.get("width"), "height": video.get("height")})
    fps = _fraction_decimal(video.get("avg_frame_rate"))
    expected_fps = _decimal_or_none(profile.get("frame_rate"))
    fps_ok = fps is not None and expected_fps is not None and abs(fps - expected_fps) <= Decimal("0.01")
    _add(checks, "frame_rate_matches_profile", fps_ok, {"fps": float(fps) if fps is not None else None})
    bitrate = _int_or_zero(video.get("bit_rate")) or _int_or_zero((probe.get("format") or {}).get("bit_rate"))
    floor = _int_or_zero(profile.get("minimum_video_bitrate"))
    bitrate_ok = bitrate >= floor > 0
    _add(checks, "video_bitrate_floor", bitrate_ok, {"bitrate": bitrate, "minimum": floor})
    if not width_ok or not height_ok or not fps_ok or not bitrate_ok:
        errors.append("video resolution, frame rate, or bitrate is outside the frozen output profile")

    audio = typed.get("audio") or {}
    audio_ok = audio.get("sample_rate") == str(profile.get("audio_sample_rate")) and audio.get("channels") == profile.get("audio_channels")
    _add(checks, "audio_sample_rate_and_channels", audio_ok)
    if not audio_ok:
        errors.append("audio sample rate or channel count differs from the mix profile")


def _check_subtitle_bounds(
    path: Path, manifest: dict[str, Any] | None, executable: str,
    checks: list[dict[str, Any]], errors: list[str],
) -> None:
    result = _run([executable, "-v", "error", "-i", path.name, "-map", "0:s:0", "-f", "srt", "-"], timeout=30, cwd=path.parent)
    if result.returncode != 0 or not result.stdout.strip():
        _add(checks, "subtitle_stream_decodes", False)
        errors.append("subtitle stream cannot be decoded")
        return
    _add(checks, "subtitle_stream_decodes", True)
    cues = _parse_srt(result.stdout)
    timeline = manifest.get("shot_timeline") if manifest and isinstance(manifest.get("shot_timeline"), list) else []
    valid = len(cues) == len(timeline)
    if valid:
        for cue, shot in zip(cues, timeline, strict=True):
            start, end, text = cue
            valid = (
                start == Decimal(str(shot["start_seconds"]))
                and end == Decimal(str(shot["end_seconds"]))
                and bool(text.strip())
            )
            if not valid:
                break
    _add(checks, "subtitle_bounds_and_shot_sync", valid, {"cue_count": len(cues)})
    if not valid:
        errors.append("subtitle cues are out of bounds or not synchronized to the shot plan")


def _check_cut_timing(
    path: Path, manifest: dict[str, Any] | None, executable: str,
    checks: list[dict[str, Any]], errors: list[str],
) -> None:
    expected = manifest.get("expected_cut_seconds") if manifest and isinstance(manifest.get("expected_cut_seconds"), list) else []
    result = _run(
        [
            executable, "-v", "error", "-select_streams", "v:0", "-skip_frame", "nokey",
            "-show_entries", "frame=pts_time", "-of", "csv=p=0", path.name,
        ],
        timeout=45,
        cwd=path.parent,
    )
    keyframes = []
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            try:
                keyframes.append(Decimal(line.strip().split(",", 1)[0]))
            except Exception:
                continue
    valid = bool(expected) and all(
        any(abs(actual - Decimal(str(cut))) <= CUT_TOLERANCE_SECONDS for actual in keyframes)
        for cut in expected
    )
    _add(checks, "shot_cut_keyframes_match_plan", valid, {"expected": len(expected), "keyframes": len(keyframes)})
    if not valid:
        errors.append("encoded keyframes do not cover every planned shot cut")


def _check_visual_signals(path: Path, executable: str, checks: list[dict[str, Any]], errors: list[str]) -> None:
    result = _run(
        [
            executable, "-hide_banner", "-v", "info", "-i", path.name,
            "-vf", "blackdetect=d=1.0:pix_th=0.10,freezedetect=n=-45dB:d=2.0",
            "-an", "-f", "null", os.devnull,
        ],
        timeout=150,
        cwd=path.parent,
    )
    black_ranges = len(re.findall(r"black_start:", result.stderr or ""))
    freeze_ranges = len(re.findall(r"freeze_start:", result.stderr or ""))
    decoded = result.returncode == 0
    _add(checks, "visual_signal_scan_decodes", decoded)
    _add(checks, "no_long_black_segments", decoded and black_ranges == 0, {"signals": black_ranges})
    _add(checks, "no_long_frozen_segments", decoded and freeze_ranges == 0, {"signals": freeze_ranges})
    if not decoded or black_ranges or freeze_ranges:
        errors.append("black or frozen-frame technical signals exceed the engine-proof bounds")


def _check_audio_signals(
    path: Path, manifest: dict[str, Any] | None, executable: str,
    checks: list[dict[str, Any]], errors: list[str],
) -> None:
    result = _run(
        [
            executable, "-hide_banner", "-v", "info", "-i", path.name, "-map", "0:a:0",
            "-af", "ebur128=peak=true,silencedetect=noise=-45dB:d=2.0", "-f", "null", os.devnull,
        ],
        timeout=150,
        cwd=path.parent,
    )
    stderr = result.stderr or ""
    loudness_matches = re.findall(r"\bI:\s*(-?\d+(?:\.\d+)?)\s+LUFS", stderr)
    peak_matches = re.findall(r"\bPeak:\s*(-?\d+(?:\.\d+)?)\s+dBFS", stderr)
    integrated = Decimal(loudness_matches[-1]) if loudness_matches else None
    peak = Decimal(peak_matches[-1]) if peak_matches else None
    mix = manifest.get("mix") if manifest and isinstance(manifest.get("mix"), dict) else {}
    target = _decimal_or_none(mix.get("target_lufs"))
    true_peak_bound = _decimal_or_none(mix.get("true_peak_db"))
    loudness_ok = integrated is not None and target is not None and abs(integrated - target) <= Decimal("1.5")
    peak_ok = peak is not None and true_peak_bound is not None and peak <= true_peak_bound + Decimal("0.2")
    silence_ranges = len(re.findall(r"silence_start:", stderr))
    silence_ok = result.returncode == 0 and silence_ranges == 0
    _add(checks, "audio_integrated_loudness_bound", loudness_ok, {"lufs": float(integrated) if integrated is not None else None})
    _add(checks, "audio_true_peak_bound", peak_ok, {"peak_dbfs": float(peak) if peak is not None else None})
    _add(checks, "no_long_audio_silence", silence_ok, {"signals": silence_ranges})
    if not loudness_ok or not peak_ok or not silence_ok:
        errors.append("audio loudness, peak, or silence signals exceed the mix bounds")


def _check_media_decode(path: Path, executable: str, checks: list[dict[str, Any]], errors: list[str]) -> None:
    command = [executable, "-v", "error", "-i", path.name, "-map", "0:v:0", "-map", "0:a:0", "-f", "null", os.devnull]
    result = _run(command, timeout=150, cwd=path.parent)
    passed = result.returncode == 0
    _add(checks, "video_audio_decode_complete", passed)
    if not passed:
        errors.append((result.stderr or "media decode failed").strip())


def _duration(probe: dict[str, Any]) -> Decimal | None:
    format_info = probe.get("format") if isinstance(probe.get("format"), dict) else {}
    try:
        return Decimal(str(format_info.get("duration")))
    except Exception:
        return None


def _fraction_decimal(value: Any) -> Decimal | None:
    try:
        fraction = Fraction(str(value))
        return Decimal(fraction.numerator) / Decimal(fraction.denominator)
    except Exception:
        return None


def _decimal_or_none(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _parse_srt(text: str) -> list[tuple[Decimal, Decimal, str]]:
    blocks = re.split(r"\r?\n\s*\r?\n", text.strip()) if text.strip() else []
    cues: list[tuple[Decimal, Decimal, str]] = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3 or "-->" not in lines[1]:
            return []
        left, right = (part.strip() for part in lines[1].split("-->", 1))
        start, end = _srt_decimal(left), _srt_decimal(right)
        if start is None or end is None:
            return []
        cues.append((start, end, "\n".join(lines[2:])))
    return cues


def _srt_decimal(value: str) -> Decimal | None:
    match = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})", value)
    if not match:
        return None
    hours, minutes, seconds, millis = (Decimal(part) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def _run(command: list[str], *, timeout: int, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False, cwd=cwd)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return subprocess.CompletedProcess(command, 127, stdout="", stderr=str(exc))


def _add(checks: list[dict[str, Any]], name: str, passed: bool, details: dict[str, Any] | None = None) -> None:
    check: dict[str, Any] = {"name": name, "status": "pass" if passed else "fail"}
    if details is not None:
        check["details"] = details
    checks.append(check)
