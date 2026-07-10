from __future__ import annotations

import json
import base64
from pathlib import Path


PNG_B64 = base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
).decode("ascii")


def test_model_call_context_feedback_overlay_sanitizer_is_split() -> None:
    root = Path(__file__).resolve().parents[1]
    main_source = root / "agentflow" / "algorithms" / "model_call_context" / "__init__.py"
    helper_source = root / "agentflow" / "algorithms" / "model_call_context" / "feedback_context.py"
    main_text = main_source.read_text(encoding="utf-8")
    helper_text = helper_source.read_text(encoding="utf-8")

    assert len(main_text.splitlines()) <= 240
    assert len(helper_text.splitlines()) <= 120
    assert "from agentflow.algorithms.model_call_context.feedback_context import" in main_text
    assert "def _bundle_feedback_context_overlays" not in main_text
    assert "def bundle_feedback_context_overlays" in helper_text


def test_model_call_context_maps_operations_and_blocks_unsafe_boundaries() -> None:
    from agentflow.algorithms.model_call_context import OPERATION_INTENT_TARGETS, build_model_call_context

    prompt_path = "C:" + "\\secret\\asset.png"
    feedback_path = "D:" + "\\private\\run.png"
    bearer = "Bear" + "er abc123"
    key_value = "api" + "_key=123"
    for operation_intent, generation_target in OPERATION_INTENT_TARGETS.items():
        context = build_model_call_context(
            project_id="proj_context_contract",
            node_ref={"node_id": f"node-{operation_intent}", "node_type": "image"},
            operation_intent=operation_intent,
            generation_target=generation_target,
            input_prompt=f"Use {prompt_path} and https://example.test/signed?token=abc with {bearer}",
            context_bundle={
                "included_assets": [{"asset_id": "asset_fixed_1"}],
                "excluded_assets": [{"asset_id": "asset_draft_1", "reason": "draft_asset_rejected"}],
                "reference_image_channel": [{"asset_id": "img_context_1"}],
                "warnings": [{"warning_id": "best_effort_lock_conflict"}],
            },
            fixed_assets=[{"asset_id": "asset_fixed_1", "status": "fixed"}],
            draft_assets=[{"asset_id": "asset_draft_1", "status": "draft"}],
            rejected_assets=[{"asset_id": "asset_rejected_1", "status": "rejected"}],
            retired_assets=[{"asset_id": "asset_retired_1", "status": "retired"}],
            reference_image_refs=["img_user_1"],
            user_preferences={"style": "cinematic"},
            expert_rule_ids=["lighting_mood_v1"],
            provider_constraints={"capability": "image", "reference_image_slots": 1},
            feedback_events=[
                {
                    "kind": "studio_quality_feedback",
                    "ratings": {"identity_similarity": 5, "unknown_metric": 2},
                    "drift_notes": f"bad path {feedback_path} and {key_value}",
                }
            ],
        )
        serialized = json.dumps(context, ensure_ascii=False).lower()

        assert context["schema_version"] == "afs_model_call_context.v0.1"
        assert context["context_id"].startswith("mctx_")
        assert context["operation_intent"] == operation_intent
        assert context["generation_target"] == generation_target
        assert context["asset_context"]["context_eligible_asset_ids"] == ["asset_fixed_1"]
        assert context["asset_context"]["draft_asset_ids"] == ["asset_draft_1"]
        assert context["asset_context"]["rejected_asset_ids"] == ["asset_rejected_1"]
        assert context["asset_context"]["retired_asset_ids"] == ["asset_retired_1"]
        assert context["reference_context"]["reference_image_refs"] == ["img_context_1", "img_user_1"]
        assert context["preference_context"]["expert_rule_ids"] == ["lighting_mood_v1"]
        assert context["feedback_context"]["events"][0]["feedback_is_memory"] is False
        assert context["trace_summary"]["context_bundle_present"] is True
        assert context["safety_boundary"]["no_provider_raw"] is True
        assert context["safety_boundary"]["no_local_path"] is True
        assert "c:\\secret" not in serialized
        assert "d:\\private" not in serialized
        assert "token=abc" not in serialized
        assert "bearer abc123" not in serialized
        assert key_value not in serialized


def test_request_projection_infers_provider_neutral_modes_from_model_call_context() -> None:
    from agentflow.algorithms.model_call_context import build_model_call_context
    from agentflow.algorithms.request_projection import build_request_plan

    image_t2i = build_model_call_context(
        project_id="proj_projection",
        node_ref={"node_id": "image-1", "node_type": "image"},
        operation_intent="image_generate",
        generation_target="image",
        input_prompt="Generate a clean keyframe.",
    )
    image_i2i = build_model_call_context(
        project_id="proj_projection",
        node_ref={"node_id": "image-2", "node_type": "image"},
        operation_intent="image_generate",
        generation_target="image",
        input_prompt="Adjust the reference keyframe.",
        reference_image_refs=["img_reference_1"],
    )
    video_t2v = build_model_call_context(
        project_id="proj_projection",
        node_ref={"node_id": "video-1", "node_type": "video"},
        operation_intent="video_generate",
        generation_target="video",
        input_prompt="Generate a five second establishing shot.",
    )
    video_i2v = build_model_call_context(
        project_id="proj_projection",
        node_ref={"node_id": "video-2", "node_type": "video"},
        operation_intent="video_generate",
        generation_target="video",
        input_prompt="Animate the first frame.",
        reference_image_refs=["img_first_frame"],
    )

    assert build_request_plan(model_call_context=image_t2i)["request_mode"] == "t2i"
    assert build_request_plan(model_call_context=image_i2i)["request_mode"] == "i2i"
    assert build_request_plan(model_call_context=video_t2v)["request_mode"] == "t2v"
    i2v_plan = build_request_plan(model_call_context=video_i2v)

    assert i2v_plan["request_mode"] == "i2v"
    assert i2v_plan["context_id"] == video_i2v["context_id"]
    assert i2v_plan["provider_neutral"] is True
    assert i2v_plan["provider_request"]["reference_image_refs"] == ["img_first_frame"]
    assert i2v_plan["safety_boundary"]["no_provider_raw"] is True


def test_visual_understanding_normalizes_observation_before_asset_card_drafting() -> None:
    from agentflow.algorithms.visual_understanding import normalize_visual_observation

    observation = normalize_visual_observation(
        project_id="proj_visual",
        observation_id="vision_obs_1",
        source_refs={"image_asset_refs": ["img_1"], "video_artifact_id": "video_artifact_1"},
        provider_observation={
            "description": "Character in a rainy alley. Provider raw URL https://example.test/raw?token=abc",
            "labels": ["character", "scene", "unrelated-provider-label"],
            "raw_json": {"secret": "do not store"},
            "local_path": "D:\\private\\frame.png",
        },
        project_need={"asset_types": ["character", "scene"], "focus": "reusable asset card"},
    )
    serialized = json.dumps(observation, ensure_ascii=False).lower()

    assert observation["artifact_type"] == "agentflow_visual_understanding_observation"
    assert observation["project_relevance"]["selected_asset_types"] == ["character", "scene"]
    assert observation["safe_evidence"]["image_asset_ref_count"] == 1
    assert observation["asset_card_policy"]["default_status"] == "draft"
    assert observation["asset_card_policy"]["requires_human_confirmation"] is True
    assert "token=abc" not in serialized
    assert "d:\\private" not in serialized
    assert "raw_json" not in serialized


def test_asset_continuity_context_keeps_only_fixed_assets_eligible() -> None:
    from agentflow.algorithms.fixed_asset_memory import asset_continuity_context

    context = asset_continuity_context(
        {
            "fixed_1": {"asset_id": "fixed_1", "status": "fixed", "asset_type": "character"},
            "draft_1": {"asset_id": "draft_1", "status": "draft", "asset_type": "scene"},
            "rejected_1": {"asset_id": "rejected_1", "status": "rejected", "asset_type": "character"},
            "retired_1": {"asset_id": "retired_1", "status": "retired", "asset_type": "video"},
        },
        locked_asset_ids=["fixed_1", "draft_1"],
        excluded_asset_ids=["retired_1"],
    )

    assert context["algorithm_id"] == "afs.fixed_asset_memory.v0.1"
    assert context["context_eligible_asset_ids"] == ["fixed_1"]
    assert context["locked_fixed_asset_ids"] == ["fixed_1"]
    assert context["blocked_lock_asset_ids"] == ["draft_1"]
    assert context["excluded_asset_ids"] == ["retired_1"]
    assert context["continuity_policy"]["draft_assets_enter_context"] is False


def test_algorithm_library_taxonomy_separates_core_algorithms_from_auxiliary_guards() -> None:
    from agentflow import algorithms

    assert algorithms.CORE_AGENT_ALGORITHMS == (
        "prompt_intelligence_optimization",
        "context_intelligence_scheduling",
        "visual_understanding_assetization",
        "asset_memory_continuity",
        "model_request_projection",
        "quality_feedback_drift_control",
    )
    assert "provider_gate_manifest" not in algorithms.CORE_AGENT_ALGORITHM_MODULES
    assert "skill_action_selection" not in algorithms.CORE_AGENT_ALGORITHM_MODULES
    assert "provider_gate_manifest" in algorithms.AUXILIARY_ENGINEERING_MODULES
    assert "skill_action_selection" in algorithms.AUXILIARY_ENGINEERING_MODULES


def test_runtime_prompt_optimization_registers_model_call_context_artifact(tmp_path) -> None:
    from fastapi.testclient import TestClient

    from apps.api.runtime_service import create_runtime_app

    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    result = client.post(
        "/projects/proj_prompt_model_context/prompt-optimizations",
        json={
            "node_id": "script-node-001",
            "node_type": "script",
            "prompt_text": "A founder introduces an AI video tool.",
            "generation_target": "script",
            "target_platform": "short_video",
            "style": "cinematic",
            "generated_at": "2026-06-18T10:00:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    context_ref = payload["artifacts"]["model_call_context"]
    context = client.get(f"/artifacts/{context_ref['artifact_id']}").json()["payload"]

    assert payload["model_call_context_id"] == context["context_id"]
    assert payload["model_call_context_summary"]["context_id"] == context["context_id"]
    assert payload["model_call_context_summary"]["artifact"]["artifact_id"] == context_ref["artifact_id"]
    assert payload["model_call_context_summary"]["operation_intent"] == "prompt_optimize"
    assert payload["model_call_context_summary"]["context_sources"]["context_bundle_present"] is False
    assert payload["model_call_context_summary"]["asset_context"]["context_eligible_asset_count"] == 0
    assert payload["model_call_context_summary"]["provider_constraints"]["provider_gate"] == "AFS_ALLOW_REMOTE_LLM"
    assert payload["model_call_context_summary"]["safety_boundary"]["no_provider_raw"] is True
    assert "feedback_context" not in payload["model_call_context_summary"]
    assert context["operation_intent"] == "prompt_optimize"
    assert context["generation_target"] == "prompt"
    assert context["asset_context"]["context_eligible_asset_ids"] == []
    assert context["preference_context"]["expert_rule_ids"]
    assert context["safety_boundary"]["no_provider_raw"] is True


def test_runtime_keyframe_request_plan_is_projected_from_model_call_context(tmp_path, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from apps.api.runtime_service import create_runtime_app

    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    uploaded = client.post(
        "/projects/proj_keyframe_model_context/image-assets",
        json={
            "node_id": "reference-node",
            "filename": "reference.png",
            "mime_type": "image/png",
            "data_base64": PNG_B64,
            "role": "reference_image",
            "generated_at": "2026-06-18T10:09:00+08:00",
        },
    )
    assert uploaded.status_code == 200
    image_asset_id = uploaded.json()["asset"]["asset_id"]
    result = client.post(
        "/projects/proj_keyframe_model_context/keyframe-generations",
        json={
            "node_id": "image-node-001",
            "prompt_text": "A clean concept keyframe.",
            "optimized_prompt": "A clean concept keyframe.",
            "target_platform": "short_video",
            "style": "cinematic",
            "asset_refs": [image_asset_id],
            "generated_at": "2026-06-18T10:10:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    context = client.get(f"/artifacts/{payload['artifacts']['model_call_context']['artifact_id']}").json()["payload"]
    projection = client.get(f"/artifacts/{payload['artifacts']['model_request_plan']['artifact_id']}").json()["payload"]
    legacy_plan = client.get(f"/artifacts/{payload['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]

    assert payload["model_call_context_id"] == context["context_id"]
    assert context["operation_intent"] == "image_generate"
    assert projection["context_id"] == context["context_id"]
    assert projection["request_mode"] == "i2i"
    assert projection["provider_request"]["reference_image_refs"] == [image_asset_id]
    assert legacy_plan["model_call_context_id"] == context["context_id"]
    assert legacy_plan["model_request_plan_ref"] == "model_request_plan.json"
