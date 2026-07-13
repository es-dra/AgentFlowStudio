from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from agentflow_studio.production.episode_delivery import (
    EpisodeContractError,
    assemble_episode,
    sha256_file,
    validate_episode_spec,
)
from agentflow_studio.production.episode_media_quality import run_episode_technical_qa
from tools.afs_episode_delivery_harness import run_harness, write_controlled_episode_fixture


FFMPEG_READY = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def test_provider_free_harness_builds_real_132_second_mp4_with_exact_evidence(tmp_path: Path) -> None:
    if not FFMPEG_READY:
        pytest.skip("ffmpeg and ffprobe are required for real episode evidence")

    result = run_harness(tmp_path)
    episode = Path(result["episode_path"])
    manifest_path = Path(result["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result["status"] == "pass"
    assert episode.is_file() and episode.stat().st_size > 0
    assert result["duration_seconds"] == 132
    assert result["stream_types"] == ["audio", "subtitle", "video"]
    assert result["shot_count"] == 12
    assert result["provider_calls_started"] == 0
    assert manifest["episode_sha256"] == sha256_file(episode)
    assert result["manifest_sha256"] == sha256_file(manifest_path)
    assert len(manifest["shot_timeline"]) == 12
    assert all(shot["lineage"]["revision_id"] == shot["revision_id"] for shot in manifest["shot_timeline"])
    assert result["evidence_layers"]["creative_media_quality"] == "not_evaluated"
    assert result["evidence_layers"]["human_acceptance"] == "not_evaluated"


def test_replay_of_identical_controlled_inputs_has_identical_mp4_hash(tmp_path: Path) -> None:
    if not FFMPEG_READY:
        pytest.skip("ffmpeg and ffprobe are required for deterministic replay")
    first = run_harness(tmp_path / "first")
    second = run_harness(tmp_path / "second")

    first_manifest = json.loads(Path(first["manifest_path"]).read_text(encoding="utf-8"))
    second_manifest = json.loads(Path(second["manifest_path"]).read_text(encoding="utf-8"))
    assert first["episode_sha256"] == second["episode_sha256"]
    assert first_manifest["input_spec_sha256"] == second_manifest["input_spec_sha256"]
    assert first_manifest["deterministic_replay"]["command_sha256"] == second_manifest["deterministic_replay"]["command_sha256"]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing_visual", "file is missing"),
        ("tampered_visual", "sha256 mismatch"),
        ("stale_visual", "stale revision"),
        ("missing_audio", "file is missing"),
        ("tampered_subtitle", "sha256 mismatch"),
        ("broken_lineage", "lineage mismatch"),
        ("provider_call", "provider calls must remain zero"),
    ],
)
def test_contract_fails_closed_for_missing_tampered_stale_or_uncontrolled_inputs(
    tmp_path: Path, mutation: str, message: str,
) -> None:
    spec_path = write_controlled_episode_fixture(tmp_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if mutation == "missing_visual":
        (tmp_path / spec["shots"][0]["visual_asset"]["path"]).unlink()
    elif mutation == "tampered_visual":
        (tmp_path / spec["shots"][0]["visual_asset"]["path"]).write_bytes(b"tampered")
    elif mutation == "stale_visual":
        spec["shots"][0]["visual_asset"]["current_revision_id"] = "visual-001-rev-002"
    elif mutation == "missing_audio":
        (tmp_path / spec["audio_asset"]["path"]).unlink()
    elif mutation == "tampered_subtitle":
        (tmp_path / spec["subtitle_asset"]["path"]).write_text("tampered", encoding="utf-8")
    elif mutation == "broken_lineage":
        spec["shots"][0]["lineage"]["revision_id"] = "unapproved-revision"
    elif mutation == "provider_call":
        spec["provider_calls_started"] = 1
    spec_path.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(EpisodeContractError, match=message):
        validate_episode_spec(spec_path)


def test_contract_rejects_timeline_gap_overlap_and_short_episode(tmp_path: Path) -> None:
    spec_path = write_controlled_episode_fixture(tmp_path)
    original = json.loads(spec_path.read_text(encoding="utf-8"))
    cases = [
        ({"shot": 1, "field": "start_seconds", "value": 12}, "gap or overlap"),
        ({"shot": 1, "field": "start_seconds", "value": 10}, "gap or overlap"),
        ({"duration": 119}, "between 120 and 180"),
    ]
    for index, (patch, message) in enumerate(cases):
        spec = json.loads(json.dumps(original))
        if "duration" in patch:
            spec["shots"] = spec["shots"][:10]
            spec["duration_seconds"] = 110
        else:
            spec["shots"][patch["shot"]][patch["field"]] = patch["value"]
        candidate = tmp_path / f"invalid-{index}.json"
        candidate.write_text(json.dumps(spec), encoding="utf-8")
        with pytest.raises(EpisodeContractError, match=message):
            validate_episode_spec(candidate)


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


def test_source_files_state_nonclaims_and_no_generated_binary_contract() -> None:
    delivery_source = Path("agentflow_studio/production/episode_delivery.py").read_text(encoding="utf-8")
    qa_source = Path("agentflow_studio/production/episode_media_quality.py").read_text(encoding="utf-8")
    harness_source = Path("tools/afs_episode_delivery_harness.py").read_text(encoding="utf-8")
    combined = "\n".join((delivery_source, qa_source, harness_source))

    assert "provider_calls_started" in combined
    assert "not_creative_media_quality" in combined
    assert "not_human_acceptance" in combined
    assert "not_business_validation" in combined
    assert "openai" not in combined.lower()
    assert "requests." not in combined
    assert "http://" not in combined and "https://" not in combined
