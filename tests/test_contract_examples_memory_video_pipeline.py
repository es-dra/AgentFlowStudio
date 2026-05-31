from __future__ import annotations

import json
from pathlib import Path


def test_agentflow_memory_video_pipeline_protocol_example_is_no_call_plan() -> None:
    payload = json.loads(
        Path("examples/agentflow/memory_video_pipeline_protocol.example.json").read_text(encoding="utf-8")
    )

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_memory_video_pipeline_protocol"
    assert payload["provider_route"]["image_service_id"] == "minimax_image"
    assert payload["provider_route"]["video_service_id"] == "kling_i2v"
    assert [lane["lane_id"] for lane in payload["lanes"]] == ["baseline", "memory_backed"]
    assert payload["lanes"][0]["memory_refs"] == []
    assert payload["lanes"][1]["memory_refs"]
    assert {card["promotion_status"] for card in payload["memory_context"]["cards"]} <= {"promoted", "merged"}
    assert all(card["writes_long_term_memory"] is False for card in payload["memory_context"]["cards"])
    assert payload["claim_boundaries"]["human_acceptance"] == "not_reviewed"
    assert payload["claim_boundaries"]["business_validation"] == "not_validated"


def test_agentflow_memory_video_pipeline_review_example_is_review_only() -> None:
    payload = json.loads(
        Path("examples/agentflow/memory_video_pipeline_review.example.json").read_text(encoding="utf-8")
    )

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_memory_video_pipeline_review"
    assert payload["provider_calls_started_by_review"] is False
    assert payload["writes_long_term_memory"] is False
    assert payload["lane_parity"]["only_memory_context_differs"] is True
    assert payload["lane_parity"]["same_source_image_sha256"] is True
    assert payload["cross_run_stability"]["status"] == "ready_for_human_visual_review"
    assert payload["cross_run_stability"]["machine_judgement"] == "not_performed"
    assert payload["claim_boundaries"]["human_acceptance"] == "not_reviewed"
    assert payload["claim_boundaries"]["business_validation"] == "not_validated"
    assert payload["claim_boundaries"]["quality_improvement_claim"] == "not_claimed"


def test_agentflow_memory_video_pipeline_human_observation_example_is_bounded_signal() -> None:
    payload = json.loads(
        Path("examples/agentflow/memory_video_pipeline_human_observation.example.json").read_text(encoding="utf-8")
    )

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_memory_video_pipeline_human_observation"
    assert payload["source_review_artifact_type"] == "agentflow_memory_video_pipeline_review"
    assert payload["provider_calls_started_by_observation"] is False
    assert payload["writes_long_term_memory"] is False
    assert payload["observation_status"] == "visual_observation_recorded"
    assert payload["observed_signal_summary"]["memory_backed_more_stable"] is True
    assert payload["observed_signal_summary"]["residual_risk"] == "subjective_visual_review"
    assert payload["claim_boundaries"]["human_acceptance"] == "not_acceptance"
    assert payload["claim_boundaries"]["business_validation"] == "not_validated"
    assert payload["claim_boundaries"]["quality_improvement_claim"] == "bounded_visual_signal_only"


def test_agentflow_memory_video_pipeline_presentation_package_example_is_safe_summary() -> None:
    payload = json.loads(
        Path("examples/agentflow/memory_video_pipeline_presentation_package.example.json").read_text(encoding="utf-8")
    )

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_memory_video_pipeline_presentation_package"
    assert payload["provider_calls_started_by_package"] is False
    assert payload["writes_long_term_memory"] is False
    assert payload["experiment_setup"]["intended_difference"] == "memory_context_only"
    assert payload["input_difference"]["baseline"] == "current task plus source keyframe only"
    assert payload["result_summary"]["memory_backed_more_stable"] is True
    assert payload["claim_boundaries"]["human_acceptance"] == "not_acceptance"
    assert payload["claim_boundaries"]["business_validation"] == "not_validated"
    assert payload["claim_boundaries"]["quality_improvement_claim"] == "bounded_visual_signal_only"


def test_agentflow_memory_video_pipeline_package_example_links_no_call_outputs() -> None:
    payload = json.loads(
        Path("examples/agentflow/memory_video_pipeline_package.example.json").read_text(encoding="utf-8")
    )

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_memory_video_pipeline_package"
    assert payload["provider_calls_started"] is False
    assert payload["writes_long_term_memory"] is False
    assert payload["plan_ref"] == "plan/run_plan.json"
    assert payload["review_ref"] == "review/memory_video_pipeline_review.json"
    assert payload["observation_ref"] == "observation/memory_video_pipeline_human_observation.json"
    assert payload["presentation_ref"] == "presentation/memory_video_pipeline_presentation_package.json"
    assert payload["feedback_event_draft_ref"] == "feedback/memory_video_pipeline_feedback_event_draft.json"
    assert payload["claim_boundaries"]["human_acceptance"] == "not_acceptance"
    assert payload["claim_boundaries"]["business_validation"] == "not_validated"
    assert payload["claim_boundaries"]["quality_improvement_claim"] == "bounded_visual_signal_only"
