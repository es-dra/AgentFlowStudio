from __future__ import annotations

import json
from pathlib import Path

import yaml

from narratostudio import CreativeBrief


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


def test_narratostudio_creative_brief_example_has_schema_version() -> None:
    payload = json.loads(Path("examples/narratostudio/creative_brief.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert CreativeBrief.model_validate(payload).artifact_type == "creative_brief"


def test_agentflow_project_manifest_example_has_schema_version() -> None:
    payload = json.loads(Path("examples/agentflow/project_manifest.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_project_manifest"
    assert {module["module_id"] for module in payload["modules"]} == {"narratostudio", "narratocut"}


def test_agentflow_artifact_map_example_has_schema_version() -> None:
    payload = json.loads(Path("examples/agentflow/artifact_map.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_artifact_map"
    assert {artifact["module_owner"] for artifact in payload["artifacts"]} == {"NarratoStudio", "NarratoCut"}


def test_agentflow_feedback_event_example_jsonl_has_schema_version() -> None:
    lines = Path("examples/agentflow/feedback_event.example.jsonl").read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines if line.strip()]

    assert events
    assert all(event["schema_version"] == "0.1.0" for event in events)
    assert {event["artifact_type"] for event in events} == {"agentflow_feedback_event"}
    assert {event["decision"] for event in events} <= {"accepted", "rejected", "needs_revision", "note", "published"}


def test_agentflow_memory_candidate_example_is_candidate_only() -> None:
    payload = json.loads(Path("examples/agentflow/memory_candidate.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_memory_candidate"
    assert payload["promotion_status"] == "candidate"
    assert payload["source_artifact"] == "memory_candidates.json"
    assert payload["source_of_truth"] == "feedback.jsonl"
    assert payload["evidence_refs"]


def test_agentflow_memory_promotion_decision_example_is_explicit_review() -> None:
    payload = json.loads(Path("examples/agentflow/memory_promotion_decision.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_memory_promotion_decision"
    assert payload["source_candidate_id"]
    assert payload["decision"] in {"promoted", "rejected", "merged", "expired"}
    assert payload["promotion_mode"] == "human_reviewed"
    assert payload["writes_long_term_memory"] is False
