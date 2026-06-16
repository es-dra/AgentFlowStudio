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
    assert "不要把上游节点标题或完整旧提示词当成人物名字" in instruction


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
