from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agentflow.memory.video_pipeline_presentation import (
    build_memory_video_pipeline_presentation,
    write_memory_video_pipeline_presentation,
)
from apps.cli.main import app


PROTOCOL_PATH = Path("examples/agentflow/memory_video_pipeline_protocol.example.json")
REVIEW_PATH = Path("examples/agentflow/memory_video_pipeline_review.example.json")
OBSERVATION_PATH = Path("examples/agentflow/memory_video_pipeline_human_observation.example.json")
PRESENTATION_PATH = Path("examples/agentflow/memory_video_pipeline_presentation_package.example.json")


def test_presentation_package_summarizes_demo_without_copying_media_or_overclaiming(tmp_path) -> None:
    package = build_memory_video_pipeline_presentation(_protocol(), _review(), _observation())
    paths = write_memory_video_pipeline_presentation(package, tmp_path / "presentation")

    assert package["artifact_type"] == "agentflow_memory_video_pipeline_presentation_package"
    assert package["provider_calls_started_by_package"] is False
    assert package["writes_long_term_memory"] is False
    assert package["demo_title"] == "Neon rain turnback I2V memory advantage"
    assert package["one_sentence_takeaway"] == (
        "Under the same keyframe, task, model, duration, and storyboard, the memory-backed lane showed "
        "more stable repeat behavior while remaining a bounded visual signal."
    )
    assert package["experiment_setup"]["same_for_both_lanes"] == [
        "user_task",
        "source_keyframe",
        "provider_route",
        "video_model",
        "duration_sec",
        "storyboard_checkpoints",
    ]
    assert package["experiment_setup"]["intended_difference"] == "memory_context_only"
    assert package["input_difference"]["baseline"] == "current task plus source keyframe only"
    assert package["input_difference"]["memory_backed"] == [
        "character_card_yiqi_v1",
        "scene_card_neon_rain_v1",
        "feedback_patch_occlusion_recovery_v1",
    ]
    assert package["result_summary"]["baseline_more_variable"] is True
    assert package["result_summary"]["memory_backed_more_stable"] is True
    assert package["claim_boundaries"]["quality_improvement_claim"] == "bounded_visual_signal_only"
    assert package["slidev_outline"][0]["title"] == "\u5b9e\u9a8c\u95ee\u9898"
    assert package["slidev_outline"][1]["title"] == "\u8f93\u5165\u5dee\u5f02"
    assert package["speaker_notes"][0].startswith(
        "\u8fd9\u4e0d\u662f\u4e00\u6b21\u63d0\u793a\u8bcd\u70ab\u6280"
    )

    assert {path.name for path in paths} == {
        "memory_video_pipeline_presentation_package.json",
        "memory_video_pipeline_presentation_brief.md",
        "slidev_insert.md",
    }
    serialized = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    assert "\u5b9e\u9a8c\u95ee\u9898" in serialized
    assert "\u8f93\u5165\u5dee\u5f02" in serialized
    assert "\u89c2\u5bdf\u7ed3\u679c" in serialized
    assert "\u8fd9\u4e0d\u662f\u4e00\u6b21\u63d0\u793a\u8bcd\u70ab\u6280" in serialized
    for mojibake in ["瀹", "杈", "瑙", "鍙", "杩", "銆", "€"]:
        assert mojibake not in serialized
    assert "final proof" not in serialized.lower()
    assert "business validation" in serialized.lower()
    assert "D:\\Projects" not in serialized
    assert "https://" not in serialized
    assert ".mp4" not in serialized
    assert "Bearer " not in serialized


def test_presentation_requires_protocol_review_and_observation_alignment() -> None:
    protocol = _protocol()
    review = _review()
    observation = _observation()
    observation["protocol_id"] = "other_protocol"

    with pytest.raises(ValueError, match="same protocol_id"):
        build_memory_video_pipeline_presentation(protocol, review, observation)

    observation = _observation()
    observation["claim_boundaries"]["human_acceptance"] = "accepted"

    with pytest.raises(ValueError, match="not_acceptance"):
        build_memory_video_pipeline_presentation(protocol, review, observation)


def test_committed_presentation_example_contains_readable_slidev_chinese() -> None:
    package = json.loads(PRESENTATION_PATH.read_text(encoding="utf-8"))
    serialized = json.dumps(package, ensure_ascii=False)

    assert package["slidev_outline"][0]["title"] == "\u5b9e\u9a8c\u95ee\u9898"
    assert package["slidev_outline"][1]["title"] == "\u8f93\u5165\u5dee\u5f02"
    assert package["slidev_outline"][2]["title"] == "\u89c2\u5bdf\u7ed3\u679c"
    assert package["speaker_notes"][0].startswith(
        "\u8fd9\u4e0d\u662f\u4e00\u6b21\u63d0\u793a\u8bcd\u70ab\u6280"
    )
    for mojibake in ["瀹", "杈", "瑙", "鍙", "杩", "銆", "€"]:
        assert mojibake not in serialized


def test_cli_writes_presentation_package_from_three_inputs(tmp_path) -> None:
    protocol_path = tmp_path / "protocol.json"
    review_path = tmp_path / "review.json"
    observation_path = tmp_path / "observation.json"
    protocol_path.write_text(json.dumps(_protocol(), ensure_ascii=False), encoding="utf-8")
    review_path.write_text(json.dumps(_review(), ensure_ascii=False), encoding="utf-8")
    observation_path.write_text("\ufeff" + json.dumps(_observation(), ensure_ascii=False), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "memory-video-pipeline-present",
            "--protocol",
            str(protocol_path),
            "--review",
            str(review_path),
            "--observation",
            str(observation_path),
            "--output",
            str(tmp_path / "presentation"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Memory video pipeline presentation package" in result.output
    assert "Provider calls: not started" in result.output
    assert str(protocol_path) not in result.output
    assert str(review_path) not in result.output
    assert str(observation_path) not in result.output
    slidev_insert = tmp_path / "presentation" / "slidev_insert.md"
    assert slidev_insert.is_file()
    rendered = slidev_insert.read_text(encoding="utf-8")
    assert "\u5b9e\u9a8c\u95ee\u9898" in rendered
    assert "\u8f93\u5165\u5dee\u5f02" in rendered
    assert "\u53ef\u8bb2\u6e05\u695a\u7684\u8fb9\u754c" in rendered
    for mojibake in ["瀹", "杈", "瑙", "鍙", "杩", "銆", "€"]:
        assert mojibake not in rendered


def _protocol() -> dict:
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def _review() -> dict:
    return json.loads(REVIEW_PATH.read_text(encoding="utf-8"))


def _observation() -> dict:
    return json.loads(OBSERVATION_PATH.read_text(encoding="utf-8"))
