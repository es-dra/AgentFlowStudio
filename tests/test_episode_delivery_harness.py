from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from agentflow_studio.production.episode_delivery import (
    EpisodeContractError,
    assemble_episode,
    build_ffmpeg_command,
    sha256_file,
    validate_episode_spec,
)
from agentflow_studio.production.episode_media_quality import run_episode_technical_qa
from tools.afs_episode_delivery_harness import run_harness, write_controlled_episode_fixture


FFMPEG_READY = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def test_provider_free_harness_builds_mixed_media_135_second_mp4_with_exact_evidence(tmp_path: Path) -> None:
    if not FFMPEG_READY:
        pytest.skip("ffmpeg and ffprobe are required for real assembly-engine evidence")

    result = run_harness(tmp_path)
    episode = Path(result["episode_path"])
    manifest_path = Path(result["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    qa = json.loads(Path(result["technical_qa_path"]).read_text(encoding="utf-8"))
    checks = {check["name"]: check["status"] for check in qa["checks"]}

    assert result["status"] == "pass", qa["errors"]
    assert result["evidence_label"] == "representative_episode_assembly_engine_pass"
    assert episode.is_file() and episode.stat().st_size > 0
    assert result["duration_seconds"] == 135
    assert result["stream_types"] == ["audio", "subtitle", "video"]
    assert result["shot_count"] == 15
    assert result["visual_input_types"] == ["image", "video"]
    assert result["audio_stems"] == ["dialogue", "music", "sfx"]
    assert result["provider_calls_started"] == 0
    assert manifest["source_contract"] == "agentflow_studio.production.episode_delivery.v0.1"
    assert manifest["episode_sha256"] == sha256_file(episode)
    assert result["manifest_sha256"] == sha256_file(manifest_path)
    assert len(manifest["shot_timeline"]) == 15
    assert all(shot["lineage"]["revision_id"] == shot["revision_id"] for shot in manifest["shot_timeline"])
    for required in (
        "resolution_matches_profile", "frame_rate_matches_profile", "video_bitrate_floor",
        "no_long_black_segments", "no_long_frozen_segments", "audio_integrated_loudness_bound",
        "audio_true_peak_bound", "no_long_audio_silence", "subtitle_bounds_and_shot_sync",
        "shot_cut_keyframes_match_plan", "video_audio_decode_complete",
    ):
        assert checks[required] == "pass"
    assert result["evidence_layers"]["representative_content_proof"] == "not_evaluated"
    assert result["evidence_layers"]["creative_media_quality"] == "not_evaluated"
    assert result["evidence_layers"]["human_acceptance"] == "not_evaluated"


def test_replay_of_identical_controlled_inputs_has_identical_hashes_on_same_toolchain(tmp_path: Path) -> None:
    if not FFMPEG_READY:
        pytest.skip("ffmpeg and ffprobe are required for deterministic replay")
    first = run_harness(tmp_path / "first")
    second = run_harness(tmp_path / "second")

    first_manifest = json.loads(Path(first["manifest_path"]).read_text(encoding="utf-8"))
    second_manifest = json.loads(Path(second["manifest_path"]).read_text(encoding="utf-8"))
    assert first["episode_sha256"] == second["episode_sha256"]
    assert first_manifest["input_spec_sha256"] == second_manifest["input_spec_sha256"]
    assert first_manifest["deterministic_replay"]["command_sha256"] == second_manifest["deterministic_replay"]["command_sha256"]
    assert "exact ffmpeg build" in first_manifest["deterministic_replay"]["scope"]
    assert "not promised across" in first_manifest["deterministic_replay"]["codec_limit"]


def test_command_trims_mixed_visuals_and_mixes_three_audio_stems(tmp_path: Path) -> None:
    if not FFMPEG_READY:
        pytest.skip("ffmpeg and ffprobe are required for controlled media inspection")
    spec_path = write_controlled_episode_fixture(tmp_path)
    frozen = validate_episode_spec(spec_path)
    command = build_ffmpeg_command(frozen, tmp_path / "episode.mp4")
    joined = " ".join(command)

    assert "-loop 1" in joined
    assert "-ss 0" in joined
    assert "concat=n=15" in joined
    assert "sidechaincompress" in joined
    assert "amix=inputs=3" in joined
    assert "loudnorm=I=-16" in joined
    assert "-force_key_frames 0,9,18" in joined


def test_contract_fails_closed_for_controlled_input_and_timing_failures(tmp_path: Path) -> None:
    if not FFMPEG_READY:
        pytest.skip("ffmpeg and ffprobe are required for negative controlled-media probes")
    base = tmp_path / "base"
    spec_path = write_controlled_episode_fixture(base)
    original = json.loads(spec_path.read_text(encoding="utf-8"))

    def candidate(name: str) -> tuple[Path, dict]:
        root = tmp_path / name
        shutil.copytree(base, root)
        path = root / "episode_spec.json"
        return path, json.loads(path.read_text(encoding="utf-8"))

    cases: list[tuple[Path, str]] = []

    path, spec = candidate("missing")
    (path.parent / spec["shots"][0]["visual_asset"]["path"]).unlink()
    cases.append((path, "file is missing"))

    path, spec = candidate("tampered")
    asset_path = path.parent / spec["shots"][0]["visual_asset"]["path"]
    asset_path.write_bytes(b"tampered")
    cases.append((path, "sha256 mismatch"))

    path, spec = candidate("stale")
    spec["shots"][0]["visual_asset"]["current_revision_id"] = "newer-revision"
    _write(path, spec)
    cases.append((path, "stale revision"))

    path, spec = candidate("unsupported-stream")
    audio = spec["audio_stems"]["dialogue"]
    visual = spec["shots"][1]["visual_asset"]
    visual.update({"path": audio["path"], "sha256": audio["sha256"], "media_type": "video"})
    _repair_lineage(spec, 1)
    _write(path, spec)
    cases.append((path, "unsupported streams"))

    path, spec = candidate("short-video")
    spec["shots"][1]["source_start_seconds"] = 5
    _write(path, spec)
    cases.append((path, "shorter than the requested trim"))

    path, spec = candidate("stale-subtitle")
    subtitle_path = path.parent / spec["subtitle_asset"]["path"]
    subtitle_path.write_text(subtitle_path.read_text(encoding="utf-8").replace("00:00:09,000", "00:00:08,000", 1), encoding="utf-8")
    spec["subtitle_asset"]["sha256"] = sha256_file(subtitle_path)
    _write(path, spec)
    cases.append((path, "does not match shot timing"))

    path, spec = candidate("lineage")
    spec["shots"][0]["lineage"]["revision_id"] = "foreign-revision"
    _write(path, spec)
    cases.append((path, "lineage mismatch"))

    path, spec = candidate("gap")
    spec["shots"][1]["start_seconds"] = 10
    _write(path, spec)
    cases.append((path, "gap or overlap"))

    path, spec = candidate("provider")
    spec["provider_calls_started"] = 1
    _write(path, spec)
    cases.append((path, "provider calls must remain zero"))

    short_audio_root = tmp_path / "short-audio"
    path, spec = candidate("audio-duration")
    short_audio = short_audio_root / "short.wav"
    short_audio.parent.mkdir(parents=True)
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", str(short_audio)],
        check=True,
    )
    copied = path.parent / "inputs" / "short.wav"
    shutil.copy2(short_audio, copied)
    spec["audio_stems"]["dialogue"].update({"path": "inputs/short.wav", "sha256": sha256_file(copied)})
    _write(path, spec)
    cases.append((path, "duration does not match"))

    for invalid_path, message in cases:
        with pytest.raises(EpisodeContractError, match=message):
            validate_episode_spec(invalid_path)


def test_contract_rejects_short_episode_and_mix_outside_bounds(tmp_path: Path) -> None:
    if not FFMPEG_READY:
        pytest.skip("ffmpeg and ffprobe are required for controlled media inspection")
    spec_path = write_controlled_episode_fixture(tmp_path)
    original = json.loads(spec_path.read_text(encoding="utf-8"))

    short = json.loads(json.dumps(original))
    short["shots"] = short["shots"][:13]
    short["shot_count"] = 13
    short["duration_seconds"] = 117
    short_path = tmp_path / "short.json"
    _write(short_path, short)
    with pytest.raises(EpisodeContractError, match="between 120 and 180"):
        validate_episode_spec(short_path)

    bad_mix = json.loads(json.dumps(original))
    bad_mix["mix"]["music_duck_db"] = 9
    bad_mix_path = tmp_path / "bad-mix.json"
    _write(bad_mix_path, bad_mix)
    with pytest.raises(EpisodeContractError, match="between 4 and 6"):
        validate_episode_spec(bad_mix_path)


def test_technical_qa_fails_when_episode_bytes_are_tampered(tmp_path: Path) -> None:
    if not FFMPEG_READY:
        pytest.skip("ffmpeg and ffprobe are required for tamper QA")
    spec_path = write_controlled_episode_fixture(tmp_path)
    delivery = assemble_episode(spec_path, tmp_path / "delivery")
    with delivery["episode"].open("ab") as stream:
        stream.write(b"tampered-after-manifest")

    qa = run_episode_technical_qa(delivery["episode"], delivery["manifest"])
    checks = {check["name"]: check["status"] for check in qa["checks"]}
    assert qa["status"] == "fail"
    assert checks["episode_sha256_exact"] == "fail"


def test_source_files_preserve_provider_free_nonclaims_and_no_repo_media_contract() -> None:
    delivery_source = Path("agentflow_studio/production/episode_delivery.py").read_text(encoding="utf-8")
    qa_source = Path("agentflow_studio/production/episode_media_quality.py").read_text(encoding="utf-8")
    harness_source = Path("tools/afs_episode_delivery_harness.py").read_text(encoding="utf-8")
    combined = "\n".join((delivery_source, qa_source, harness_source))

    assert "provider_calls_started" in combined
    assert "representative_episode_assembly_engine_pass" in combined
    assert "not_representative_content_proof" in combined
    assert "not_creative_media_quality" in combined
    assert "not_human_acceptance" in combined
    assert "not_business_validation" in combined
    assert "not_release_evidence" in combined
    assert "openai" not in combined.lower()
    assert "requests." not in combined
    assert "http://" not in combined and "https://" not in combined


def _repair_lineage(spec: dict, index: int) -> None:
    shot = spec["shots"][index]
    shot["lineage"]["asset_id"] = shot["visual_asset"]["asset_id"]
    shot["lineage"]["revision_id"] = shot["visual_asset"]["revision_id"]


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
