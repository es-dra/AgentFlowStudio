from __future__ import annotations

import json
from pathlib import Path

import yaml


def test_project_manifest_example_has_schema_version() -> None:
    payload = json.loads(Path("examples/contracts/project_manifest.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1"
    assert payload["project_type"] == "short_video_distribution"
    assert isinstance(payload["runs"], list)
    assert isinstance(payload["packages"], list)


def test_feedback_example_jsonl_has_schema_version() -> None:
    lines = Path("examples/contracts/feedback.example.jsonl").read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines if line.strip()]

    assert events
    assert all(event["schema_version"] == "0.1" for event in events)
    assert {event["target_type"] for event in events} <= {"clip", "candidate", "package", "run"}


def test_platform_profile_examples_have_schema_version() -> None:
    profile_paths = sorted(Path("configs/platform_profiles").glob("*.yaml"))

    assert {path.name for path in profile_paths} >= {
        "douyin.yaml",
        "xiaohongshu.yaml",
        "youtube_shorts.yaml",
    }
    for path in profile_paths:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "0.1"
        assert payload["platform_id"]
        assert payload["recommended_duration_sec"]["min"] > 0
        assert payload["aspect_ratio"]
