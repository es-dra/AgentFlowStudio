from __future__ import annotations

import json


def test_algorithm_library_exports_runtime_algorithm_contracts() -> None:
    from agentflow import algorithms
    from agentflow.algorithms import (
        asset_card_drafting,
        context_resolver,
        creative_intent_control,
        fixed_asset_memory,
        provider_gate_manifest,
        quality_feedback_scoring,
        revision_drift_control,
        skill_action_selection,
    )

    assert algorithms.ALGORITHM_LIBRARY_VERSION.startswith("afs_algorithm_library_")
    for module in (
        asset_card_drafting,
        context_resolver,
        creative_intent_control,
        fixed_asset_memory,
        provider_gate_manifest,
        quality_feedback_scoring,
        revision_drift_control,
        skill_action_selection,
    ):
        assert module.ALGORITHM_ID.startswith("afs.")
        assert module.INPUT_CONTRACT
        assert module.OUTPUT_CONTRACT
        assert module.FAILURE_MODES
        assert module.EVIDENCE_BOUNDARY


def test_fixed_asset_memory_rejects_draft_assets_for_context_candidates() -> None:
    from agentflow.algorithms.fixed_asset_memory import fixed_context_assets

    assets = {
        "draft_1": {"asset_id": "draft_1", "status": "draft", "asset_type": "character", "label": "Draft"},
        "fixed_1": {"asset_id": "fixed_1", "status": "fixed", "asset_type": "character", "label": "Fixed"},
        "rejected_1": {"asset_id": "rejected_1", "status": "rejected", "asset_type": "scene", "label": "Rejected"},
    }

    assert list(fixed_context_assets(assets)) == ["fixed_1"]


def test_provider_safe_manifest_redacts_unsafe_boundaries() -> None:
    from agentflow.algorithms.provider_gate_manifest import blocked_manifest, provider_gate_status

    gate = provider_gate_status("vision", enabled=False)
    manifest = blocked_manifest(
        action="asset_card_draft",
        capability="vision",
        required_gate=gate.required_gate,
        failure_class="remote_vision_gate_closed",
    )
    serialized = json.dumps(manifest, ensure_ascii=False).lower()

    assert gate.status == "blocked"
    assert manifest["provider_raw_response_stored"] is False
    assert manifest["media_bytes_returned_by_api"] is False
    assert "api_key" not in serialized
    assert "signed_url" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized


def test_asset_card_drafting_uses_animal_role_defaults_for_cat_prompt() -> None:
    from agentflow.algorithms.asset_card_drafting import draft_asset_card

    draft = draft_asset_card(
        asset_type="character",
        project_id="proj_cat_asset",
        draft_id="draft_cat",
        source_image_asset_refs=["img_cat_ref"],
        sampled_image_asset_refs=[],
        source_video_artifact_id=None,
        prompt_text="生成一只清晰自然的黑色狸花猫，保留虎斑纹、额头 M 字纹、短毛和明亮眼睛。",
        provider_service_id="vision_image",
    )

    assert draft["asset_type"] == "character"
    assert draft["label_suggestion"] == "黑色狸花猫"
    assert "reference animal subject" in draft["signature"]
    assert "reference character" not in draft["signature"]
    assert "keep fur color and markings" in draft["candidate_locks"]
    assert "keep reference-sheet views consistent" in draft["candidate_locks"]
    assert "reference_views" in draft["feature_card"]
    assert "only add human hair clothing or anthropomorphic traits when explicitly requested" in draft["candidate_locks"]
    assert "用户明确要求" in draft["feature_card"]["wardrobe"]


def test_quality_feedback_scoring_sanitizes_raw_evidence_without_memory_promotion() -> None:
    from agentflow.algorithms.quality_feedback_scoring import sanitize_quality_feedback

    payload = sanitize_quality_feedback(
        {
            "kind": "studio_quality_feedback",
            "node_id": "node-1",
            "node_type": "video",
            "ratings": {"identity_similarity": 5, "unknown_metric": 3},
            "target_change_success": 4,
            "drift_notes": r"bad url https://example.test/signed?token=abc and C:\\secret\\asset.png",
            "safe_preview_ref": "runtime_preview_endpoint",
        }
    )
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert payload["ratings"] == {"identity_similarity": 5}
    assert payload["feedback_is_memory"] is False
    assert payload["writes_long_term_memory"] is False
    assert "token=abc" not in serialized
    assert "c:\\secret" not in serialized


def test_creative_intent_video_prompt_algorithm_handles_i2v_contract() -> None:
    from agentflow.algorithms.creative_intent_control import (
        deterministic_video_fallback_prompt,
        has_visual_reference,
        prompt_optimization_mode,
        video_enhancement_instruction,
    )

    params = {
        "first_frame_image_asset_id": "img_first",
        "motion": "角色在沙漠中行走",
        "connected_reference_nodes": [{"title": "角色三视图"}],
    }

    assert has_visual_reference(asset_refs=[], node_parameters=params, node_id="video-1") is True
    assert prompt_optimization_mode(node_type="video", generation_target="video", has_visual_reference=True) == "i2v"
    fallback = deterministic_video_fallback_prompt(
        prompt_text="基于当前关键帧生成视频",
        node_parameters=params,
        slots={},
    )
    instruction = video_enhancement_instruction(
        prompt_text="基于当前关键帧生成视频",
        style="cinematic",
        node_parameters=params,
        mode="i2v",
    )

    assert "基于首帧生成视频" in fallback
    assert "单帧图像编辑" not in fallback
    assert "不要把上游节点标题或完整旧提示词当成角色名字" in instruction


def test_provider_gate_video_prompt_algorithm_strips_image_edit_language() -> None:
    from agentflow.algorithms.provider_gate_manifest import video_provider_prompt

    prompt = video_provider_prompt(
        prompt_text="基于当前关键帧生成视频",
        optimized_prompt="意图：本次只做这一项图生图编辑。运动/时间推进：单帧图像编辑，不制造多阶段动作或剧情。",
        duration_sec=5,
        motion="角色在沙漠中行走",
        last_frame_image_asset_id=None,
        context_bundle={"text_channel": {"asset_identity_segment": "保持周彤身份"}},
    )

    assert "图生图编辑" not in prompt
    assert "单帧图像编辑" not in prompt
    assert "first frame as a strict visual anchor" in prompt
    assert "保持周彤身份" in prompt


def test_context_resolver_reference_algorithm_merges_bundle_and_request_refs() -> None:
    from agentflow.algorithms.context_resolver import merged_reference_image_refs

    refs = merged_reference_image_refs(
        request_asset_refs=["img_uploaded_ref", "img_context_ref"],
        context_bundle={"reference_image_channel": [{"asset_id": "img_context_ref"}]},
    )

    assert refs == ["img_context_ref", "img_uploaded_ref"]


def test_video_generation_plan_algorithm_returns_second_level_motion_beats() -> None:
    from agentflow.algorithms.provider_gate_manifest import video_generation_plan

    plan = video_generation_plan(
        prompt_text="A future robot watches stars on a rural rooftop.",
        optimized_prompt=None,
        duration_sec=5,
        motion="The robot slowly raises its glowing face toward the sky.",
        last_frame_image_asset_id=None,
        context_bundle=None,
    )

    assert plan["motion_plan"]["time_beats"][0]["time"] == "0.0s-1.0s"
    assert plan["motion_plan"]["time_beats"][1]["time"] == "1.0s-3.5s"
    assert plan["motion_plan"]["time_beats"][2]["time"] == "3.5s-5.0s"
    assert "rooftop platform and sky relationship" in plan["editing_plan"]["continuity_locks"]
    assert "unrequested chair" in plan["editing_plan"]["forbidden_changes"]


def test_video_generation_plan_includes_professional_reference_and_prompt_guidance() -> None:
    from agentflow.algorithms.provider_gate_manifest import video_generation_plan, video_provider_prompt

    plan = video_generation_plan(
        prompt_text="A future robot watches stars on a rural rooftop platform.",
        optimized_prompt="Generate a continuous 5s video from the first frame.",
        duration_sec=5,
        motion="The robot slowly raises its glowing face toward the sky.",
        last_frame_image_asset_id=None,
        context_bundle=None,
    )
    prompt = video_provider_prompt(
        prompt_text="A future robot watches stars on a rural rooftop platform.",
        optimized_prompt="Generate a continuous 5s video from the first frame.",
        duration_sec=5,
        motion="The robot slowly raises its glowing face toward the sky.",
        last_frame_image_asset_id=None,
        context_bundle=None,
    )

    reference = plan["professional_reference"]
    assert {"night", "rooftop", "video"} <= set(reference["tags"])
    assert "moderate-to-deep" in reference["depth_of_field"]["decision"]
    assert "0-1s" in reference["pacing"]["must_include"][0]
    assert "Professional video reference:" in prompt
    assert "motivated night exterior" in prompt
    assert "conflicting" not in prompt.lower()
    assert "conflict" not in prompt.lower()

    neutral_prompt = video_provider_prompt(
        prompt_text="Generate a continuous video from the first frame.",
        optimized_prompt=None,
        duration_sec=5,
        motion="fixed camera",
        last_frame_image_asset_id=None,
        context_bundle=None,
    )
    assert "conflicting" not in neutral_prompt.lower()
    assert "conflict" not in neutral_prompt.lower()
    assert "inconsistent motion directions" in neutral_prompt


def test_video_generation_plan_includes_director_scenario_and_prompt_guidance() -> None:
    from agentflow.algorithms.provider_gate_manifest import video_generation_plan, video_provider_prompt

    plan = video_generation_plan(
        prompt_text="A podcast interview quote becomes a short visual clip with a warm studio microphone.",
        optimized_prompt="Generate a continuous 5s video from the first frame.",
        duration_sec=5,
        motion="The speaker subtly reacts while the microphone light glows.",
        last_frame_image_asset_id=None,
        context_bundle=None,
    )
    prompt = video_provider_prompt(
        prompt_text="A podcast interview quote becomes a short visual clip with a warm studio microphone.",
        optimized_prompt="Generate a continuous 5s video from the first frame.",
        duration_sec=5,
        motion="The speaker subtly reacts while the microphone light glows.",
        last_frame_image_asset_id=None,
        context_bundle=None,
    )

    scenario = plan["director_scenario"]
    assert scenario["primary_scenario"] == "podcast_visual"
    assert "quote focus is clear" in scenario["quality_checks"]
    assert plan["prompt_contract"]["director_scenario_selected"] is True
    assert "Director scenario video guidance:" in prompt
    assert "Podcast Visual" in prompt
