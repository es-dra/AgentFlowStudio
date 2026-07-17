from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from agentflow_studio.production.episode_delivery import sha256_file
from apps.api.runtime_real_story_production import (
    REAL_STORY_SCHEMA_VERSION,
    RealStoryProductionError,
    _read_persisted_script_authority,
    compile_story_canon,
    run_creative_media_qa,
)
from apps.api.runtime_service import create_runtime_app


def test_real_story_canon_uses_script_source_variable_pacing_and_per_shot_video_recipe() -> None:
    script = "《回声信标》小澄在旧码头收到会发光的信，沿潮汐回声修复灯塔并送达迟到多年的消息。"
    canon = compile_story_canon(brief="制作一部中文海边机器人送信短片", script_text=script)

    durations = [shot["duration_seconds"] for shot in canon["shots"]]
    script_sha = hashlib.sha256(script.encode("utf-8")).hexdigest()

    assert canon["episode"]["duration_seconds"] == 120
    assert sum(durations) == 120
    assert len(set(durations)) > 1
    assert len(canon["shots"]) == 13
    assert all(shot["script_source_sha256"] == script_sha for shot in canon["shots"])
    assert canon["production_recipe"]["requires_per_shot_keyframe"] is True
    assert canon["production_recipe"]["requires_per_shot_video"] is True
    assert canon["production_recipe"]["allows_unintentional_hash_reuse"] is False


def test_persisted_script_authority_is_read_back_and_hash_guarded(tmp_path: Path) -> None:
    script_path = tmp_path / "llm_script_body.txt"
    script_path.write_text("《回声信标》这是落盘后的权威剧本文本。", encoding="utf-8")
    public = {"script_ref": "llm_script_body.txt", "script_sha256": sha256_file(script_path)}

    authority = _read_persisted_script_authority(tmp_path, public)

    assert authority["script_text"] == "《回声信标》这是落盘后的权威剧本文本。"
    assert authority["script_sha256"] == public["script_sha256"]

    bad_public = {"script_ref": "llm_script_body.txt", "script_sha256": "0" * 64}
    try:
        _read_persisted_script_authority(tmp_path, bad_public)
    except RealStoryProductionError as exc:
        assert "hash mismatch" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected persisted script hash guard to reject drift")


def test_creative_media_qa_flags_repeated_hashes_and_static_final_media(tmp_path: Path) -> None:
    canon = compile_story_canon(
        brief="制作一部中文海边机器人送信短片",
        script_text="《回声信标》小澄修复灯塔并让迟到的消息抵达海面远处。",
    )
    subtitles = tmp_path / "subtitles.srt"
    subtitles.write_text(
        "\n\n".join(
            [
                (
                    f"{index}\n"
                    f"00:00:{int(shot['start_seconds']):02d},000 --> 00:00:{int(shot['end_seconds']):02d},000\n"
                    f"{shot['subtitle_text']}"
                )
                for index, shot in enumerate(canon["shots"], start=1)
            ]
        ),
        encoding="utf-8",
    )
    visual_assets = [
        {
            "shot_id": shot["shot_id"],
            "scene_id": shot["scene_id"],
            "path": f"assets/{shot['shot_id']}",
            "sha256": "a" * 64,
            "media_type": "image",
            "prompt": {"script_source_sha256": shot["script_source_sha256"]},
        }
        for shot in canon["shots"]
    ]

    qa = run_creative_media_qa(
        tmp_path,
        canon,
        visual_assets,
        {"provenance": {"tts_source_duration_sec": 119, "dialogue_repeated": False}},
        {"status": "pass"},
    )

    finding_ids = {finding["id"] for finding in qa["findings"]}
    assert qa["status"] == "fail"
    assert "DUPLICATE-HASH" in finding_ids
    assert "VIDEO-COVERAGE" in finding_ids


def test_creative_media_qa_flags_exact_subtitle_mismatch(tmp_path: Path) -> None:
    canon = compile_story_canon(
        brief="制作一部中文海边机器人送信短片",
        script_text="《回声信标》小澄修复灯塔并让迟到的消息抵达海面远处。",
    )
    wrong_shots = [dict(shot) for shot in canon["shots"]]
    wrong_shots[1]["subtitle_text"] = wrong_shots[0]["subtitle_text"]
    _write_test_subtitles(tmp_path / "subtitles.srt", wrong_shots)
    visual_assets = _video_assets_for(canon)

    qa = run_creative_media_qa(
        tmp_path,
        canon,
        visual_assets,
        {"provenance": {"tts_source_duration_sec": 119}},
        {"status": "pass"},
    )

    assert "SUBTITLES" in {finding["id"] for finding in qa["findings"]}


def test_creative_media_qa_flags_repeated_dialogue_source(tmp_path: Path) -> None:
    canon = compile_story_canon(
        brief="制作一部中文海边机器人送信短片",
        script_text="《回声信标》小澄修复灯塔并让迟到的消息抵达海面远处。",
    )
    canon["shots"][1]["subtitle_text"] = canon["shots"][0]["subtitle_text"]
    _write_test_subtitles(tmp_path / "subtitles.srt", canon["shots"])
    visual_assets = _video_assets_for(canon)

    qa = run_creative_media_qa(
        tmp_path,
        canon,
        visual_assets,
        {
            "provenance": {
                "tts_source_duration_sec": 119,
                "dialogue_source_line_count": len(canon["shots"]),
                "dialogue_source_unique_line_count": len({shot["subtitle_text"] for shot in canon["shots"]}),
            }
        },
        {"status": "pass"},
    )

    assert "AUDIO-REPEAT" in {finding["id"] for finding in qa["findings"]}


def test_real_story_production_route_persists_safe_manifest_and_preview(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_AUTH_ALLOW_OPEN_SIGNUP", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    registered = client.post(
        "/auth/register",
        json={
            "email": "creator@example.com",
            "password": "strong-password-123",
            "display_name": "Creator",
        },
    )
    assert registered.status_code == 200, registered.text
    headers = {"Authorization": f"Bearer {registered.json()['session_token']}"}
    created = client.post(
        "/projects",
        json={"project_id": "owned-project", "goal": "Real story route"},
        headers=headers,
    )
    assert created.status_code == 200, created.text
    run_response = client.post(
        "/projects/owned-project/production-runs",
        json={
            "schema_version": "afs_runtime_production_run.v0.1",
            "run_id": "production-run-real-story",
            "idempotency_key": "create-real-story-run",
            "subject_digest": "b" * 64,
            "candidates": [
                {
                    "candidate_id": "candidate-001",
                    "canonical_digest": "c" * 64,
                    "parent_job_id": "job-keyframe-001",
                    "shot_id": "shot-001",
                    "safe_artifact_refs": [],
                }
            ],
        },
        headers=headers,
    )
    assert run_response.status_code == 200, run_response.text
    run = run_response.json()["production_run"]

    def fake_execute(store, project_id, run_id, request, root, **_kwargs):
        delivery = root / "delivery"
        delivery.mkdir(parents=True)
        episode = delivery / "episode.mp4"
        episode.write_bytes(b"fake-mp4-bytes")
        return {
            "schema_version": REAL_STORY_SCHEMA_VERSION,
            "project_id": project_id,
            "run_id": run_id,
            "status": "creative_qa_passed",
            "story_canon_digest": "c" * 64,
            "production_sha256": "d" * 64,
            "delivery": {
                "episode_asset_ref": "delivery_episode",
                "episode_sha256": sha256_file(episode),
                "preview_url": f"/projects/{project_id}/production-runs/{run_id}/real-story-production/delivery/preview",
            },
            "media_provenance": {
                "visual_assets": [
                    {"shot_id": "shot-001", "media_type": "video", "sha256": "e" * 64}
                ]
            },
        }

    monkeypatch.setattr("apps.api.runtime_production_runs.execute_real_story_production", fake_execute)
    produced = client.post(
        "/projects/owned-project/production-runs/production-run-real-story/real-story-production",
        json={
            "schema_version": REAL_STORY_SCHEMA_VERSION,
            "idempotency_key": "real-story-once",
            "expected_checkpoint_version": run["checkpoint"]["version"],
            "brief": "一部 120 秒中文动画短片：小型邮差机器人小澄修复灯塔并送达迟到多年的消息。",
        },
        headers=headers,
    )
    assert produced.status_code == 200, produced.text
    production = produced.json()["production_run"]["real_story_production"]
    serialized = json.dumps(production, ensure_ascii=False)
    assert production["schema_version"] == REAL_STORY_SCHEMA_VERSION
    assert ".mp4" not in serialized
    assert "delivery_episode" in serialized

    preview = client.get(production["delivery"]["preview_url"], headers=headers)
    assert preview.status_code == 200, preview.text
    assert preview.content == b"fake-mp4-bytes"


def _video_assets_for(canon: dict) -> list[dict]:
    return [
        {
            "shot_id": shot["shot_id"],
            "scene_id": shot["scene_id"],
            "path": f"assets/{shot['shot_id']}",
            "sha256": hashlib.sha256(shot["shot_id"].encode("utf-8")).hexdigest(),
            "media_type": "video",
            "prompt": {"script_source_sha256": shot["script_source_sha256"]},
        }
        for shot in canon["shots"]
    ]


def _write_test_subtitles(path: Path, shots: list[dict]) -> None:
    blocks = []
    for index, shot in enumerate(shots, start=1):
        blocks.append(
            f"{index}\n{_srt_time(int(shot['start_seconds']))} --> {_srt_time(int(shot['end_seconds']))}\n"
            f"{shot['subtitle_text']}"
        )
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def _srt_time(seconds: int) -> str:
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d},000"
