from __future__ import annotations

import json
import os
import subprocess
from decimal import Decimal
from pathlib import Path
from typing import Any

from agentflow_studio.production.episode_delivery import sha256_file


DURATION_TOLERANCE_SECONDS = Decimal("0.25")


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
        _check_subtitle_decode(episode, ffmpeg_executable, checks, errors)
        _check_media_decode(episode, ffmpeg_executable, checks, errors)
    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "status": "pass" if not failed else "fail",
        "evidence_layer": "technical_media_qa",
        "checks": checks,
        "errors": list(dict.fromkeys(errors)),
        "probe": probe or {},
        "artifact": {
            "episode_ref": episode.name,
            "sha256": sha256_file(episode) if episode.is_file() else None,
            "bytes": episode.stat().st_size if episode.is_file() else 0,
        },
        "non_claims": ["not_creative_media_quality", "not_human_acceptance", "not_business_validation"],
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
    _check_timeline(manifest.get("shot_timeline"), manifest.get("duration_seconds"), checks, errors)


def _check_timeline(value: Any, declared: Any, checks: list[dict[str, Any]], errors: list[str]) -> None:
    cursor = Decimal("0")
    valid = isinstance(value, list) and bool(value)
    if valid:
        for shot in value:
            required = {"shot_id", "start_seconds", "end_seconds", "asset_id", "revision_id", "asset_sha256", "lineage"}
            if not isinstance(shot, dict) or not required.issubset(shot):
                valid = False
                break
            start, end = Decimal(str(shot["start_seconds"])), Decimal(str(shot["end_seconds"]))
            lineage = shot["lineage"]
            if start != cursor or end <= start or not isinstance(lineage, dict):
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
    types = {stream.get("codec_type") for stream in streams if isinstance(stream, dict)}
    for stream_type in ("video", "audio", "subtitle"):
        present = stream_type in types
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


def _check_subtitle_decode(path: Path, executable: str, checks: list[dict[str, Any]], errors: list[str]) -> None:
    result = _run([executable, "-v", "error", "-i", path.name, "-map", "0:s:0", "-f", "srt", "-"], timeout=30, cwd=path.parent)
    passed = result.returncode == 0 and bool(result.stdout.strip())
    _add(checks, "subtitle_stream_decodes", passed)
    if not passed:
        errors.append("subtitle stream cannot be decoded")


def _check_media_decode(path: Path, executable: str, checks: list[dict[str, Any]], errors: list[str]) -> None:
    command = [executable, "-v", "error", "-i", path.name, "-map", "0:v:0", "-map", "0:a:0", "-f", "null", os.devnull]
    result = _run(command, timeout=90, cwd=path.parent)
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
