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


def test_prompt_optimizer_can_apply_gated_minimax_m3_enhancement(tmp_path, monkeypatch) -> None:
    class FakeGateway:
        def generate(self, prompt, *, task_type=None, provider_name=None):
            assert task_type == "prompt_enhancement"
            assert provider_name == "minimax_m3"
            assert "Canonical brief:" in prompt
            assert "不要替换成" in prompt
            assert "最终展示给用户的内容必须以中文为主" in prompt
            return "\n".join(
                [
                    "意图：为安静的创始人场景生成一张可控关键帧。",
                    "人物/主体：保持创始人的身份、服装和神态稳定清晰。",
                    "场景/美术：夜间工作室、玻璃墙、克制道具，避免杂乱背景。",
                    "动作/情节：创始人在发言前短暂停顿，情绪内敛但有压力。",
                    "镜头/构图：竖构图中景，主体位置明确，背景信息服务叙事。",
                    "灯光：低调实景窗光，柔和反差，保留面部可读性。",
                    "运动/时间推进：静态关键帧，暗示缓慢推进但不制造运动模糊。",
                    "连续性：延续服装、空间方位和主光方向。",
                    "负面约束：不要水印，不要手部畸形，不要身份漂移。",
                ]
            )

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setenv("AFS_MODEL_CONFIG", str(tmp_path / "models.yaml"))
    monkeypatch.setattr(
        "apps.api.runtime_llm_enhancement.ModelGateway.from_config_path",
        lambda path: FakeGateway(),
    )
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_minimax_llm/prompt-optimizations",
        json={
            "node_id": "image-node-minimax-text",
            "node_type": "image",
            "prompt_text": "A founder stands in a night studio before a product launch.",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "cinematic",
            "node_parameters": {"model": "minimax-image-01"},
            "generated_at": "2026-06-12T13:00:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    trace = client.get(f"/artifacts/{payload['artifacts']['prompt_assembly_trace']['artifact_id']}").json()["payload"]
    brief = client.get(f"/artifacts/{payload['artifacts']['creative_brief']['artifact_id']}").json()["payload"]
    manifest = client.get(f"/artifacts/{payload['artifacts']['prompt_optimization_safe_manifest']['artifact_id']}").json()["payload"]
    serialized = json.dumps({"payload": payload, "trace": trace, "brief": brief, "manifest": manifest}, ensure_ascii=False).lower()

    assert payload["provider_calls_started"] is True
    assert payload["optimized_prompt"].startswith("意图：为安静的创始人场景生成")
    assert "Intent:" not in payload["optimized_prompt"]
    assert payload["user_prompt"] == payload["optimized_prompt"]
    assert trace["llm_enhancement"]["status"] == "applied"
    assert trace["llm_enhancement"]["model"] == "MiniMax-M3"
    assert manifest["llm_enhancement"]["raw_response_stored"] is False
    assert brief["provider_calls_started"] is True
    assert "api_key" not in serialized
    assert "bearer " not in serialized
    assert "reasoning_content" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized


def test_prompt_optimizer_uses_chinese_fallback_when_minimax_output_is_templated(tmp_path, monkeypatch) -> None:
    class FakeGateway:
        def generate(self, prompt, *, task_type=None, provider_name=None):
            assert task_type == "prompt_enhancement"
            return "\n".join(
                [
                    "Intent: generic scene.",
                    "Subject/Character: Primary character with stable identity.",
                    "Scene/Production Design: primary scene.",
                    "Camera/Framing: medium shot.",
                    "Lighting: cinematic light.",
                    "Negative Constraints: no watermark.",
                ]
            )

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setenv("AFS_MODEL_CONFIG", str(tmp_path / "models.yaml"))
    monkeypatch.setattr(
        "apps.api.runtime_llm_enhancement.ModelGateway.from_config_path",
        lambda path: FakeGateway(),
    )
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_minimax_llm_fallback/prompt-optimizations",
        json={
            "node_id": "image-node-minimax-text-fallback",
            "node_type": "image",
            "prompt_text": "一个穿黑色风衣的年轻女导演，短发，雨夜天台，城市霓虹在湿地上反光。",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "cinematic",
            "node_parameters": {"model": "minimax-image-01", "aspect_ratio": "9:16"},
            "generated_at": "2026-06-12T13:10:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    trace = client.get(f"/artifacts/{payload['artifacts']['prompt_assembly_trace']['artifact_id']}").json()["payload"]

    assert payload["provider_calls_started"] is True
    assert payload["optimized_prompt"].startswith("意图：")
    assert "人物/主体：" in payload["optimized_prompt"]
    assert "Primary character" not in payload["optimized_prompt"]
    assert trace["llm_enhancement"]["status"] == "discarded"
    assert trace["llm_enhancement"]["discard_reason"] == "enhancement missing required sections"
