from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.openapi_export import export_openapi_schema
from apps.api.runtime_service import create_runtime_app


def test_node_prompt_optimization_returns_only_optimized_prompt_for_canvas_ui(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_libtv_prompt",
            "project_type": "short_video_campaign",
            "goal": "Create LibTV-like node canvas prompts.",
        },
    )

    result = client.post(
        "/projects/proj_libtv_prompt/prompt-optimizations",
        json={
            "node_id": "script-node-001",
            "node_type": "script",
            "prompt_text": "A calm founder walks through a rainy neon street and introduces an AI video tool.",
            "generation_target": "script",
            "target_platform": "short_video",
            "style": "cinematic noir",
            "generated_at": "2026-06-11T10:00:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    brief = client.get(f"/artifacts/{payload['artifacts']['creative_brief']['artifact_id']}").json()["payload"]
    trace = client.get(f"/artifacts/{payload['artifacts']['prompt_assembly_trace']['artifact_id']}").json()["payload"]
    manifest = client.get(f"/artifacts/{payload['artifacts']['prompt_optimization_safe_manifest']['artifact_id']}").json()["payload"]
    serialized = json.dumps({"payload": payload, "brief": brief, "trace": trace, "manifest": manifest}, ensure_ascii=False).lower()

    assert payload["job"]["action"] == "prompt_optimization"
    assert payload["job"]["status"] == "succeeded"
    assert payload["ui_surface"] == "node_prompt_optimizer"
    assert payload["original_prompt"].startswith("A calm founder")
    assert payload["optimized_prompt"] == brief["optimized_prompt"]
    assert "lighting" in payload["optimized_prompt"].lower()
    assert "candidate_memory" not in serialized
    assert "memory_decision" not in serialized
    assert "creative_memory" not in payload
    assert trace["context_priority"] == [
        "professional_knowledge_base",
        "script_character_scene_assets",
        "user_preferences",
    ]
    assert {rule["rule_id"] for rule in trace["knowledge_rules"]} >= {
        "cinematography_shot_intent_v1",
        "lighting_mood_v1",
        "character_consistency_v1",
    }
    assert trace["background_context_refs"] == []
    assert trace["extracted_context_refs"]
    assert manifest["provider_calls_started"] is False
    assert manifest["raw_provider_response_stored"] is False
    assert manifest["generated_media_bytes_stored"] is False
    assert payload["provider_calls_started"] is False
    assert payload["writes_long_term_memory"] is False
    assert payload["writes_company_kb"] is False
    assert "not durable memory" in payload["non_claims"]
    assert "api_key" not in serialized
    assert "bearer " not in serialized
    assert "signed_url" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized
    assert "data/processed/runs" not in serialized


def test_second_node_prompt_optimization_uses_background_assets_without_user_memory_review(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_libtv_background_context",
            "project_type": "short_video_campaign",
            "goal": "Optimize repeated node prompts with hidden context.",
        },
    )
    first = client.post(
        "/projects/proj_libtv_background_context/prompt-optimizations",
        json={
            "node_id": "text-node-001",
            "node_type": "text",
            "prompt_text": "A silver-haired detective searches an abandoned observatory at blue hour.",
            "generation_target": "image",
            "target_platform": "short_video",
            "style": "moody cinematic",
            "generated_at": "2026-06-11T10:10:00+08:00",
        },
    ).json()
    second = client.post(
        "/projects/proj_libtv_background_context/prompt-optimizations",
        json={
            "node_id": "image-node-002",
            "node_type": "image",
            "prompt_text": "The recurring detective finds a hidden map under the observatory floor.",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "controlled mystery",
            "asset_refs": [first["artifacts"]["creative_brief"]["artifact_id"]],
            "generated_at": "2026-06-11T10:20:00+08:00",
        },
    ).json()

    trace = client.get(f"/artifacts/{second['artifacts']['prompt_assembly_trace']['artifact_id']}").json()["payload"]
    brief = client.get(f"/artifacts/{second['artifacts']['creative_brief']['artifact_id']}").json()["payload"]
    serialized = json.dumps({"trace": trace, "brief": brief, "response": second}, ensure_ascii=False).lower()

    assert trace["background_context_refs"]
    assert any(ref["memory_type"] == "character" for ref in trace["background_context_refs"])
    assert any(ref["memory_type"] == "scene" for ref in trace["background_context_refs"])
    assert trace["asset_refs"] == [first["artifacts"]["creative_brief"]["artifact_id"]]
    assert "Silver-haired detective" in brief["optimized_prompt"]
    assert "Abandoned observatory" in brief["optimized_prompt"]
    assert "candidate_memory" not in serialized
    assert "memory_decision" not in serialized
    assert trace["provider_calls_started"] is False
    assert "not durable memory" in trace["non_claims"]


def test_prompt_memory_mvp_openapi_exposes_optimizer_but_not_memory_review_surfaces(tmp_path) -> None:
    output_path = tmp_path / "frontend" / "afs-runtime-service.openapi.json"
    exported_path = export_openapi_schema(output_path, runtime_root=tmp_path / "openapi_runtime")
    schema = json.loads(exported_path.read_text(encoding="utf-8"))
    serialized = json.dumps(schema, ensure_ascii=False).lower()

    assert "/projects/{project_id}/prompt-optimizations" in schema["paths"]
    assert "/projects/{project_id}/creative-memory" not in schema["paths"]
    assert "/projects/{project_id}/memory-decisions" not in schema["paths"]
    assert "promptoptimizationrequest" in serialized
    assert "memorydecisionrequest" not in serialized
    assert "api_key" not in serialized
    assert "signed_url" not in serialized


def test_prompt_optimizer_uses_professional_knowledgebase_trace_and_chinese_slots(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_zh_prompt_knowledge",
            "project_type": "short_video_campaign",
            "goal": "中文节点提示词优化。",
        },
    )

    result = client.post(
        "/projects/proj_zh_prompt_knowledge/prompt-optimizations",
        json={
            "node_id": "video-node-zh-001",
            "node_type": "video",
            "prompt_text": "一个男孩坐在昏暗房间里，墙上有海报，情绪低落，镜头缓慢推进。",
            "generation_target": "video",
            "target_platform": "short_video",
            "style": "用户偏好：高饱和、夸张炫光、快速甩镜；项目风格：克制、真实、电影感、低照度室内光线",
            "generated_at": "2026-06-11T11:00:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    trace = client.get(f"/artifacts/{payload['artifacts']['prompt_assembly_trace']['artifact_id']}").json()["payload"]
    manifest = client.get(f"/artifacts/{payload['artifacts']['prompt_optimization_safe_manifest']['artifact_id']}").json()["payload"]
    brief = client.get(f"/artifacts/{payload['artifacts']['creative_brief']['artifact_id']}").json()["payload"]

    assert manifest["knowledgebase_version"] == "creative_prompt_knowledgebase_v1"
    assert manifest["knowledgebase_rules_count"] >= 40
    assert manifest["knowledgebase_registry_hash"]
    assert all("match_reason" in rule for rule in trace["knowledge_rules"])
    assert all("weight" in rule for rule in trace["knowledge_rules"])
    assert {rule["rule_id"] for rule in trace["knowledge_rules"]} >= {
        "video_motion_temporal_progression_v1",
        "lighting_motivated_low_key_v1",
        "negative_no_provider_claim_v1",
    }
    assert trace["selected_slots"]["language"] == "zh"
    assert trace["selected_slots"]["subject"] == "一个男孩"
    assert "昏暗房间" in trace["selected_slots"]["scene"]
    assert trace["conflict_resolution"]["policy"] == "professional_knowledge_over_user_preference"
    assert trace["suppressed_context"]
    assert "Intent:" in brief["optimized_prompt"]
    assert "Subject/Character:" in brief["optimized_prompt"]
    assert "Lighting:" in brief["optimized_prompt"]
    assert "Negative Constraints:" in brief["optimized_prompt"]
    assert "provider calls remain off" in brief["optimized_prompt"].lower()
    assert payload["provider_calls_started"] is False
