from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agentflow.memory.video_pipeline_observation import (
    build_memory_video_pipeline_observation,
    write_memory_video_pipeline_observation,
)
from apps.cli.main import app


REVIEW_PATH = Path("examples/agentflow/memory_video_pipeline_review.example.json")


def test_observation_captures_human_visual_notes_without_upgrading_claims(tmp_path) -> None:
    review = _review()
    notes = _notes()

    observation = build_memory_video_pipeline_observation(review, notes)
    paths = write_memory_video_pipeline_observation(observation, tmp_path / "observation")

    assert observation["artifact_type"] == "agentflow_memory_video_pipeline_human_observation"
    assert observation["source_review_artifact_type"] == "agentflow_memory_video_pipeline_review"
    assert observation["provider_calls_started_by_observation"] is False
    assert observation["writes_long_term_memory"] is False
    assert observation["observation_status"] == "visual_observation_recorded"
    assert observation["claim_boundaries"]["human_acceptance"] == "not_acceptance"
    assert observation["claim_boundaries"]["quality_improvement_claim"] == "bounded_visual_signal_only"
    assert observation["claim_boundaries"]["business_validation"] == "not_validated"
    assert observation["observed_signal_summary"]["memory_backed_more_stable"] is True
    assert observation["observed_signal_summary"]["baseline_more_variable"] is True
    assert observation["observed_signal_summary"]["residual_risk"] == "subjective_visual_review"
    assert [item["criterion"] for item in observation["observations"]] == [
        "shot_structure_consistency",
        "identity_anchor_retention",
        "wardrobe_anchor_retention",
        "scene_anchor_retention",
        "occlusion_recovery_repeatability",
        "motion_physics_repeatability",
    ]

    assert {path.name for path in paths} == {
        "memory_video_pipeline_human_observation.json",
        "memory_video_pipeline_human_observation.md",
    }
    serialized = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    assert "final proof" not in serialized.lower()
    assert "business validation" in serialized.lower()
    assert "D:\\Projects" not in serialized
    assert "https://" not in serialized
    assert ".mp4" not in serialized


def test_observation_requires_all_review_fields_and_known_verdicts() -> None:
    review = _review()
    notes = _notes()
    notes["observations"].pop()

    with pytest.raises(ValueError, match="missing observation criteria"):
        build_memory_video_pipeline_observation(review, notes)

    notes = _notes()
    notes["observations"][0]["verdict"] = "decisive_proof"

    with pytest.raises(ValueError, match="unsupported observation verdict"):
        build_memory_video_pipeline_observation(review, notes)


def test_observation_rejects_private_paths_provider_urls_and_acceptance_claims() -> None:
    review = _review()
    notes = _notes()
    notes["observations"][0]["note"] = "See D:\\Projects\\AgentFlowStudio\\data\\processed\\run.mp4"

    with pytest.raises(ValueError, match="unsafe"):
        build_memory_video_pipeline_observation(review, notes)

    notes = _notes()
    notes["claim_boundaries"]["human_acceptance"] = "accepted"

    with pytest.raises(ValueError, match="not_acceptance"):
        build_memory_video_pipeline_observation(review, notes)


def test_cli_writes_human_observation_from_review_and_notes(tmp_path) -> None:
    review_path = tmp_path / "review.json"
    notes_path = tmp_path / "notes.json"
    review_path.write_text(json.dumps(_review(), ensure_ascii=False), encoding="utf-8")
    notes_path.write_text("\ufeff" + json.dumps(_notes(), ensure_ascii=False), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "memory-video-pipeline-observe",
            "--review",
            str(review_path),
            "--notes",
            str(notes_path),
            "--output",
            str(tmp_path / "observation"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Memory video pipeline human observation" in result.output
    assert "Observation status: visual_observation_recorded" in result.output
    assert "Provider calls: not started" in result.output
    assert str(review_path) not in result.output
    assert str(notes_path) not in result.output
    assert (tmp_path / "observation" / "memory_video_pipeline_human_observation.json").is_file()


def _review() -> dict:
    return json.loads(REVIEW_PATH.read_text(encoding="utf-8"))


def _notes() -> dict:
    return {
        "schema_version": "0.1.0",
        "artifact_type": "agentflow_memory_video_pipeline_human_observation_notes",
        "reviewer": "operator_visual_review",
        "source_review_id": "memory_video_pipeline_neon_rain_turnback_v1",
        "observations": [
            {
                "criterion": "shot_structure_consistency",
                "verdict": "memory_backed_stronger",
                "note": "Baseline repeats varied more in camera path; memory-backed repeats kept the five checkpoints closer.",
            },
            {
                "criterion": "identity_anchor_retention",
                "verdict": "memory_backed_stronger",
                "note": "Memory-backed repeats recovered the same face and high ponytail more consistently after motion.",
            },
            {
                "criterion": "wardrobe_anchor_retention",
                "verdict": "memory_backed_stronger",
                "note": "Memory-backed repeats retained the white top, blue jeans, and white sneakers with less drift.",
            },
            {
                "criterion": "scene_anchor_retention",
                "verdict": "mixed",
                "note": "Both lanes kept neon rain, but memory-backed repeats aligned reflections and sign-light timing more closely.",
            },
            {
                "criterion": "occlusion_recovery_repeatability",
                "verdict": "memory_backed_stronger",
                "note": "After rain and light sweep occlusion, memory-backed repeats returned to a more similar readable character.",
            },
            {
                "criterion": "motion_physics_repeatability",
                "verdict": "mixed",
                "note": "Both lanes have model drift; memory-backed repeats were steadier, but this remains subjective visual evidence.",
            },
        ],
        "observed_signal_summary": {
            "baseline_more_variable": True,
            "memory_backed_more_stable": True,
            "residual_risk": "subjective_visual_review",
        },
        "claim_boundaries": {
            "human_acceptance": "not_acceptance",
            "business_validation": "not_validated",
            "quality_improvement_claim": "bounded_visual_signal_only",
            "durable_memory_runtime": "not_implemented",
        },
    }
