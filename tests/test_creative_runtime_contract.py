from __future__ import annotations

import json

import pytest


def test_creative_runtime_contract_connects_intent_memory_knowledge_assets_and_gates() -> None:
    from agentflow.algorithms.creative_runtime_contract import (
        SCHEMA_VERSION,
        build_creative_runtime_contract,
        public_creative_runtime_contract_summary,
    )
    from agentflow.algorithms.model_call_context import build_model_call_context

    local_path = "D:" + "\\private\\raw\\frame.png"
    bearer = "Bear" + "er abc123"
    key_value = "api" + "_key=123"
    model_context = build_model_call_context(
        project_id="proj_creative_runtime",
        node_ref={"node_id": "storyboard-node-1", "node_type": "text"},
        operation_intent="prompt_optimize",
        generation_target="prompt",
        input_prompt=f"Build a storyboard from {local_path} using {bearer}",
        context_bundle={
            "included_assets": [{"asset_id": "asset_fixed_hero"}],
            "warnings": [{"warning_id": "context_budget_trimmed"}],
        },
        fixed_assets=[{"asset_id": "asset_fixed_hero", "status": "fixed"}],
        expert_rule_ids=["rule_storyboard_beats"],
        provider_constraints={"capability": "llm", "provider_gate": "AFS_ALLOW_REMOTE_LLM"},
    )

    contract = build_creative_runtime_contract(
        project_id="proj_creative_runtime",
        request_id="req_storyboard_001",
        operation="storyboard_breakdown",
        owner_intent={
            "current_request": f"Turn script into shots. Avoid leaking https://example.test/signed?token=abc",
            "goal_state": "structured storyboard with reusable character and scene continuity",
            "hard_constraints": [f"do not read {local_path}", key_value],
            "soft_preferences": ["cinematic, restrained motion"],
            "explicit_non_goals": ["provider execution"],
        },
        model_call_context=model_context,
        memory_context={
            "characters": [
                {
                    "memory_id": "mem_char_hero",
                    "memory_type": "character",
                    "label": "Lin Wan",
                    "source": "prompt_optimization_background",
                    "raw_json": {"do_not_store": True},
                }
            ],
            "scenes": [{"memory_id": "mem_scene_lab", "memory_type": "scene", "label": "Underground Lab"}],
            "style_preferences": [
                {"memory_id": "mem_pref_no_flash", "memory_type": "style_preference", "label": "avoid flashy lighting"}
            ],
            "promotion_candidate_ids": ["cand_pref_001"],
            "writes_long_term_memory": True,
        },
        knowledge_context={
            "knowledgebase_version": "2026.07",
            "knowledgebase_registry_hash": "kb_hash_001",
            "knowledge_rules": [
                {"rule_id": "storyboard_source_span_required"},
                {"rule_id": "asset_reuse_character_scene_only"},
            ],
            "director_scenario": {"selected_packs": [{"scenario_id": "detective_reveal"}]},
            "professional_reference": {"references": [{"reference_id": "cinematography_continuity"}]},
            "conflict_resolution": {"policy": "professional_knowledge_over_user_preference"},
        },
        asset_context={
            "fixed_assets": [{"asset_id": "asset_fixed_hero", "status": "fixed"}],
            "draft_assets": [{"asset_id": "asset_draft_prop", "status": "draft"}],
            "rejected_assets": [{"asset_id": "asset_rejected_scene", "status": "rejected"}],
            "retired_assets": [{"asset_id": "asset_retired_look", "status": "retired"}],
            "unresolved_assets": [{"graph_asset_id": "graph:scene:unresolved"}],
            "identity_registry_refs": ["asset_identity_registry:proj_creative_runtime"],
            "binding_decision_refs": ["binding:asset_fixed_hero:shot_001"],
        },
        provider_context={
            "capability": "llm",
            "provider_gate": "AFS_ALLOW_REMOTE_LLM",
            "gate_status": "blocked",
            "provider_calls_started": True,
            "provider_service_id": "fake-provider",
        },
        evidence_context={
            "model_call_context_ref": "model_call_context.json",
            "safe_manifest_ref": "safe_manifest.json",
            "run_trace_ref": "creative_runtime_trace.json",
        },
    )
    repeat = build_creative_runtime_contract(
        project_id="proj_creative_runtime",
        request_id="req_storyboard_001",
        operation="storyboard_breakdown",
        owner_intent={
            "current_request": f"Turn script into shots. Avoid leaking https://example.test/signed?token=abc",
            "goal_state": "structured storyboard with reusable character and scene continuity",
            "hard_constraints": [f"do not read {local_path}", key_value],
            "soft_preferences": ["cinematic, restrained motion"],
            "explicit_non_goals": ["provider execution"],
        },
        model_call_context=model_context,
        memory_context={
            "characters": [
                {
                    "memory_id": "mem_char_hero",
                    "memory_type": "character",
                    "label": "Lin Wan",
                    "source": "prompt_optimization_background",
                    "raw_json": {"do_not_store": True},
                }
            ],
            "scenes": [{"memory_id": "mem_scene_lab", "memory_type": "scene", "label": "Underground Lab"}],
            "style_preferences": [
                {"memory_id": "mem_pref_no_flash", "memory_type": "style_preference", "label": "avoid flashy lighting"}
            ],
            "promotion_candidate_ids": ["cand_pref_001"],
            "writes_long_term_memory": True,
        },
        knowledge_context={
            "knowledgebase_version": "2026.07",
            "knowledgebase_registry_hash": "kb_hash_001",
            "knowledge_rules": [
                {"rule_id": "storyboard_source_span_required"},
                {"rule_id": "asset_reuse_character_scene_only"},
            ],
            "director_scenario": {"selected_packs": [{"scenario_id": "detective_reveal"}]},
            "professional_reference": {"references": [{"reference_id": "cinematography_continuity"}]},
            "conflict_resolution": {"policy": "professional_knowledge_over_user_preference"},
        },
        asset_context={
            "fixed_assets": [{"asset_id": "asset_fixed_hero", "status": "fixed"}],
            "draft_assets": [{"asset_id": "asset_draft_prop", "status": "draft"}],
            "rejected_assets": [{"asset_id": "asset_rejected_scene", "status": "rejected"}],
            "retired_assets": [{"asset_id": "asset_retired_look", "status": "retired"}],
            "unresolved_assets": [{"graph_asset_id": "graph:scene:unresolved"}],
            "identity_registry_refs": ["asset_identity_registry:proj_creative_runtime"],
            "binding_decision_refs": ["binding:asset_fixed_hero:shot_001"],
        },
        provider_context={
            "capability": "llm",
            "provider_gate": "AFS_ALLOW_REMOTE_LLM",
            "gate_status": "blocked",
            "provider_calls_started": True,
            "provider_service_id": "fake-provider",
        },
        evidence_context={
            "model_call_context_ref": "model_call_context.json",
            "safe_manifest_ref": "safe_manifest.json",
            "run_trace_ref": "creative_runtime_trace.json",
        },
    )
    serialized = json.dumps(contract, ensure_ascii=False).lower()
    summary = public_creative_runtime_contract_summary(contract)

    assert contract["schema_version"] == SCHEMA_VERSION
    assert contract["contract_id"].startswith("crtc_")
    assert repeat["contract_id"] == contract["contract_id"]
    assert contract["operation"] == "storyboard_breakdown"
    assert contract["generation_target"] == "storyboard"
    assert contract["model_call_context"]["context_id"] == model_context["context_id"]
    assert contract["memory_context"]["writes_long_term_memory"] is False
    assert contract["memory_context"]["promotion_candidates_only"] is True
    assert contract["knowledge_context"]["rule_ids"] == [
        "storyboard_source_span_required",
        "asset_reuse_character_scene_only",
    ]
    assert contract["knowledge_context"]["director_scenario_ids"] == ["director_scenario:detective_reveal"]
    assert contract["asset_context"]["context_eligible_asset_ids"] == ["asset_fixed_hero"]
    assert contract["asset_context"]["draft_assets_enter_context"] is False
    assert contract["provider_context"]["required_gate"] == "AFS_ALLOW_REMOTE_LLM"
    assert contract["provider_context"]["provider_calls_started"] is False
    assert contract["provider_context"]["source_reported_provider_calls_started"] is True
    assert contract["runtime_policy"]["requires_evaluator_before_quality_claim"] is True
    assert "not_durable_memory_promotion" in contract["non_claims"]
    assert "not_generated_media_qa" in contract["non_claims"]
    assert summary["memory_context"]["project_memory_count"] == 2
    assert summary["memory_context"]["user_preference_count"] == 1
    assert summary["knowledge_context"]["rule_count"] == 2
    assert summary["asset_context"]["fixed_asset_count"] == 1
    assert summary["provider_context"]["provider_calls_started"] is False
    assert "token=abc" not in serialized
    assert "d:\\private" not in serialized
    assert "bearer abc123" not in serialized
    assert key_value not in serialized
    assert "raw_json" not in serialized
    assert "do_not_store" not in serialized


def test_creative_runtime_contract_infers_provider_gate_for_media_operations() -> None:
    from agentflow.algorithms.creative_runtime_contract import build_creative_runtime_contract

    image_contract = build_creative_runtime_contract(
        project_id="proj_creative_runtime",
        request_id="req_image_001",
        operation="image_generation",
    )
    video_contract = build_creative_runtime_contract(
        project_id="proj_creative_runtime",
        request_id="req_video_001",
        operation="video_generation",
    )

    assert image_contract["provider_context"]["capability"] == "image"
    assert image_contract["provider_context"]["required_gate"] == "AFS_ALLOW_REMOTE_IMAGE"
    assert video_contract["provider_context"]["capability"] == "video"
    assert video_contract["provider_context"]["required_gate"] == "AFS_ALLOW_REMOTE_VIDEO"
    assert image_contract["runtime_policy"]["provider_calls_started"] is False
    assert video_contract["runtime_policy"]["provider_calls_started"] is False


def test_creative_runtime_contract_rejects_unknown_operation_and_is_registered() -> None:
    from agentflow import algorithms
    from agentflow.algorithms.creative_runtime_contract import build_creative_runtime_contract

    assert "creative_runtime_contract" in algorithms.CORE_AGENT_ALGORITHM_MODULES
    with pytest.raises(ValueError, match="unknown creative runtime operation"):
        build_creative_runtime_contract(
            project_id="proj_creative_runtime",
            request_id="req_bad",
            operation="direct_provider_upload",
        )
