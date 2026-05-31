from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agentflow.memory.video_pipeline import (
    build_memory_video_pipeline_plan,
    write_memory_video_pipeline_plan,
)
from apps.cli.main import app


EXAMPLE_PROTOCOL = Path("examples/agentflow/memory_video_pipeline_protocol.example.json")


def test_protocol_example_builds_no_call_plan_without_provider_or_secret_side_effects(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_IMAGE", raising=False)
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_VIDEO", raising=False)
    protocol = _protocol()

    plan = build_memory_video_pipeline_plan(protocol)
    paths = write_memory_video_pipeline_plan(plan, tmp_path / "plan")

    assert plan["artifact_type"] == "agentflow_memory_video_pipeline_plan"
    assert plan["provider_calls_started"] is False
    assert plan["writes_long_term_memory"] is False
    assert plan["claim_boundaries"]["human_acceptance"] == "not_reviewed"
    assert plan["claim_boundaries"]["business_validation"] == "not_validated"
    assert [lane["lane_id"] for lane in plan["lane_plans"]] == ["baseline", "memory_backed"]
    assert plan["lane_parity"]["same_user_task"] is True
    assert plan["lane_parity"]["same_source_assets"] is True
    assert plan["lane_parity"]["same_provider_route"] is True
    assert _lane(plan, "baseline")["memory_sources_loaded"] == []
    assert _lane(plan, "memory_backed")["memory_sources_loaded"] == [
        "character_card_yiqi_v1",
        "scene_card_neon_rain_v1",
        "feedback_patch_occlusion_recovery_v1",
    ]
    assert _lane(plan, "memory_backed")["request_projection"]["provider_calls_started"] is False
    assert plan["review_plan"]["cross_run_stability"]["status"] == "available_when_repeated_runs_exist"

    assert {path.name for path in paths} == {
        "protocol_summary.json",
        "request_plan.json",
        "review_plan.json",
        "run_plan.json",
        "memory_video_pipeline_report.md",
    }
    serialized = _read_outputs(paths)
    assert "D:\\Projects" not in serialized
    assert "Bearer " not in serialized
    assert "data:image/" not in serialized
    assert "signed_url" not in serialized
    assert "secret" not in serialized.lower()


def test_rejected_or_expired_memory_cannot_enter_context() -> None:
    protocol = _protocol()
    protocol["memory_context"]["cards"][0]["promotion_status"] = "rejected"

    with pytest.raises(ValueError, match="not reusable"):
        build_memory_video_pipeline_plan(protocol)

    protocol = _protocol()
    protocol["memory_context"]["cards"][0]["promotion_status"] = "expired"

    with pytest.raises(ValueError, match="not reusable"):
        build_memory_video_pipeline_plan(protocol)


def test_baseline_and_memory_backed_lanes_must_keep_same_task_and_provider_route() -> None:
    protocol = _protocol()
    protocol["lanes"][1]["user_task"] = "Make a different video"

    with pytest.raises(ValueError, match="same user_task"):
        build_memory_video_pipeline_plan(protocol)

    protocol = _protocol()
    protocol["lanes"][1]["provider_route"] = {"video_service_id": "other_i2v"}

    with pytest.raises(ValueError, match="same provider route"):
        build_memory_video_pipeline_plan(protocol)


def test_protocol_rejects_absolute_paths_signed_urls_and_data_urls() -> None:
    protocol = _protocol()
    protocol["source_assets"][0]["display_ref"] = "D:\\Projects\\AgentFlowStudio\\data\\raw\\secret.png"

    with pytest.raises(ValueError, match="unsafe"):
        build_memory_video_pipeline_plan(protocol)

    protocol = _protocol()
    protocol["source_assets"][0]["display_ref"] = "https://cdn.example.com/a.png?signed_url=abc"

    with pytest.raises(ValueError, match="unsafe"):
        build_memory_video_pipeline_plan(protocol)

    protocol = _protocol()
    protocol["source_assets"][0]["display_ref"] = "data:image/png;base64,abc"

    with pytest.raises(ValueError, match="unsafe"):
        build_memory_video_pipeline_plan(protocol)


def test_cli_writes_no_call_plan_from_protocol(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_IMAGE", raising=False)
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_VIDEO", raising=False)
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(json.dumps(_protocol(), ensure_ascii=False), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "memory-video-pipeline-plan",
            "--protocol",
            str(protocol_path),
            "--output",
            str(tmp_path / "plan"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Memory video pipeline plan" in result.output
    assert "Provider calls: not started" in result.output
    assert "Lanes planned: 2" in result.output
    assert (tmp_path / "plan" / "request_plan.json").is_file()
    assert str(protocol_path) not in result.output


def test_committed_protocol_example_is_sanitized_and_accepted() -> None:
    protocol = json.loads(EXAMPLE_PROTOCOL.read_text(encoding="utf-8"))

    plan = build_memory_video_pipeline_plan(protocol)

    assert protocol["artifact_type"] == "agentflow_memory_video_pipeline_protocol"
    assert plan["protocol_id"] == protocol["protocol_id"]
    assert plan["provider_calls_started"] is False
    serialized = json.dumps(protocol, ensure_ascii=False)
    assert "D:\\Projects" not in serialized
    assert "Bearer " not in serialized
    assert "data:image/" not in serialized


def _protocol() -> dict:
    return {
        "schema_version": "0.1.0",
        "artifact_type": "agentflow_memory_video_pipeline_protocol",
        "protocol_id": "memory_video_pipeline_neon_rain_turnback_v1",
        "project_brief": {
            "project_id": "memory_advantage_recording_016",
            "title": "Neon rain turnback I2V memory advantage",
            "user_task": (
                "Create a 15 second vertical 3D anime cinematic video where the same young woman "
                "crosses a neon rain street, turns back to camera, and stops under a flickering neon sign."
            ),
            "target_format": "vertical_9_16",
            "style": "3D anime cinematic",
        },
        "source_assets": [
            {
                "asset_id": "source_keyframe_yiqi_neon_rain",
                "asset_kind": "image_keyframe",
                "role": "same_source_keyframe_for_all_lanes",
                "display_ref": "demo_012_memory_neon_rain_candidate_001.jpg",
                "path_persisted": False,
            }
        ],
        "provider_route": {
            "image_service_id": "minimax_image",
            "video_service_id": "kling_i2v",
            "image_model": "image-01",
            "video_model": "kling-v3",
            "duration_sec": 15,
            "mode": "pro",
            "aspect_ratio": "9:16",
        },
        "memory_context": {
            "cards": [
                {
                    "memory_id": "character_card_yiqi_v1",
                    "memory_type": "character",
                    "promotion_status": "promoted",
                    "summary": "same face shape, high ponytail, white T-shirt, blue jeans, white sneakers",
                    "source_refs": ["DEMO-012:accepted_character_asset"],
                    "writes_long_term_memory": False,
                },
                {
                    "memory_id": "scene_card_neon_rain_v1",
                    "memory_type": "scene",
                    "promotion_status": "merged",
                    "summary": "neon rain street, wet asphalt reflections, blue-magenta signage glow",
                    "source_refs": ["RECORDING-016:run_1", "RECORDING-016:run_2"],
                    "writes_long_term_memory": False,
                },
                {
                    "memory_id": "feedback_patch_occlusion_recovery_v1",
                    "memory_type": "feedback_patch",
                    "promotion_status": "promoted",
                    "summary": "recover same face and outfit after rain or light occlusion",
                    "source_refs": ["DEMO-015:review_notes"],
                    "writes_long_term_memory": False,
                },
            ]
        },
        "lanes": [
            {
                "lane_id": "baseline",
                "production_mode": "stateless_generation",
                "user_task": "{project_brief.user_task}",
                "provider_route": "{provider_route}",
                "source_asset_refs": ["source_keyframe_yiqi_neon_rain"],
                "memory_refs": [],
                "prompt_instructions": "Use the current task and source keyframe only.",
            },
            {
                "lane_id": "memory_backed",
                "production_mode": "memory_backed_generation",
                "user_task": "{project_brief.user_task}",
                "provider_route": "{provider_route}",
                "source_asset_refs": ["source_keyframe_yiqi_neon_rain"],
                "memory_refs": [
                    "character_card_yiqi_v1",
                    "scene_card_neon_rain_v1",
                    "feedback_patch_occlusion_recovery_v1",
                ],
                "prompt_instructions": "Project selected memory cards into the provider prompt.",
            },
        ],
        "storyboard": {
            "scene_id": "neon_rain_turnback",
            "shot_checkpoints": [
                "0-3s front three-quarter readable character",
                "3-6s walking through neon rain",
                "6-10s light sweep and rain partially obscure face and torso",
                "10-13s turn back toward camera",
                "13-15s stop under flickering abstract neon sign",
            ],
        },
        "review_rubric": {
            "criteria": [
                "identity_retention",
                "wardrobe_retention",
                "scene_anchor_retention",
                "motion_physics",
                "occlusion_recovery",
                "cross_run_stability",
            ]
        },
        "claim_boundaries": {
            "structure_verification": "protocol_plan_only",
            "runtime_verification": "not_run",
            "human_acceptance": "not_reviewed",
            "business_validation": "not_validated",
            "quality_improvement_claim": "not_claimed",
            "durable_memory_runtime": "not_implemented",
        },
    }


def _lane(plan: dict, lane_id: str) -> dict:
    for lane in plan["lane_plans"]:
        if lane["lane_id"] == lane_id:
            return lane
    raise AssertionError(f"lane not found: {lane_id}")


def _read_outputs(paths: list[Path]) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)
