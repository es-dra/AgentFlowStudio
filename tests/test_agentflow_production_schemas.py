from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from agentflow_studio.production import (
    CostQualityTrace,
    CreativeBrief,
    FeedbackSignalLog,
    MemoryCandidateStore,
    ProductionHandoff,
)


def test_creative_brief_example_validates_with_semver_schema_version() -> None:
    payload = json.loads(Path("examples/agentflow_production/creative_brief.example.json").read_text(encoding="utf-8"))

    brief = CreativeBrief.model_validate(payload)

    assert brief.schema_version == "0.1.0"
    assert brief.content_mode == "episodic_story_production"
    assert brief.project_title


def test_agentflow_production_contracts_reject_extra_fields_but_allow_metadata() -> None:
    payload = json.loads(Path("examples/agentflow_production/creative_brief.example.json").read_text(encoding="utf-8"))
    payload["metadata"] = {"source": "unit_test"}
    assert CreativeBrief.model_validate(payload).metadata == {"source": "unit_test"}

    payload["unexpected"] = "not allowed"
    with pytest.raises(ValidationError):
        CreativeBrief.model_validate(payload)


def test_schema_version_must_be_semver() -> None:
    payload = json.loads(Path("examples/agentflow_production/creative_brief.example.json").read_text(encoding="utf-8"))
    payload["schema_version"] = "0.1"

    with pytest.raises(ValidationError):
        CreativeBrief.model_validate(payload)


def test_memory_candidates_are_candidate_only() -> None:
    store = MemoryCandidateStore.model_validate(
        {
            "schema_version": "0.1.0",
            "artifact_type": "memory_candidates",
            "run_id": "run_test",
            "candidates": [
                {
                    "id": "mem_001",
                    "promotion_status": "candidate",
                    "memory_type": "style_preference",
                    "statement": "Prefer restrained suspense hooks.",
                    "evidence_refs": ["story_bible.json"],
                    "confidence": 0.7,
                }
            ],
        }
    )

    assert store.candidates[0].promotion_status == "candidate"

    bad = store.model_dump(mode="json")
    bad["candidates"][0]["promotion_status"] = "promoted"
    with pytest.raises(ValidationError):
        MemoryCandidateStore.model_validate(bad)


def test_agent_native_auxiliary_contracts_are_explicitly_scoped() -> None:
    trace = CostQualityTrace.model_validate(
        {
            "schema_version": "0.1.0",
            "artifact_type": "cost_quality_trace",
            "run_id": "run_test",
            "provider": "local_deterministic",
            "execution_mode": "local_deterministic",
            "estimated_cost": 0,
            "currency": "USD",
            "input_artifacts": ["creative_brief.json"],
            "output_artifacts": ["production_handoff.json"],
            "quality_proxy": {"shot_prompt_alignment": 1.0},
            "applicable_scenario": "episodic_story_production",
        }
    )
    feedback = FeedbackSignalLog.model_validate(
        {
            "schema_version": "0.1.0",
            "artifact_type": "feedback_signal_log",
            "run_id": "run_test",
            "source_of_truth": "feedback.jsonl",
            "is_primary_feedback_store": False,
            "signals": [],
        }
    )

    assert trace.execution_mode == "local_deterministic"
    assert trace.estimated_cost == 0
    assert feedback.is_primary_feedback_store is False


def test_production_handoff_references_prompt_pack() -> None:
    handoff = ProductionHandoff.model_validate(
        {
            "schema_version": "0.1.0",
            "artifact_type": "production_handoff",
            "handoff_id": "handoff_test",
            "project_title": "Test",
            "content_mode": "episodic_story_production",
            "source_brief_id": "brief_test",
            "story_bible_id": "bible_test",
            "episode_outline_id": "outline_test",
            "scene_plan_id": "scene_plan_test",
            "shot_plan_id": "shot_plan_test",
            "prompt_pack_id": "prompt_pack_test",
            "ready_for": ["visual_generation"],
            "open_risks": [],
            "artifact_refs": {
                "prompt_pack": "prompt_pack.json",
            },
        }
    )

    assert handoff.artifact_refs["prompt_pack"] == "prompt_pack.json"
