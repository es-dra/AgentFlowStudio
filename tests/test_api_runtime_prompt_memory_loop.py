from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from agentflow_studio.model_gateway.errors import ModelGatewayError
from apps.api.runtime_llm_enhancement import maybe_enhance_prompt_with_llm
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.openapi_export import export_openapi_schema
from apps.api.runtime_service import create_runtime_app


def test_node_prompt_optimization_returns_only_optimized_prompt_for_canvas_ui(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_libtv_prompt",
            "project_type": "short_video_campaign",
            "goal": "Create node canvas prompts.",
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
    assert trace["selected_slots"].get("subject")
    assert trace["selected_slots"].get("scene")
    assert trace["conflict_resolution"]["policy"] == "professional_knowledge_over_user_preference"
    assert trace["suppressed_context"]
    assert "Intent:" in brief["optimized_prompt"]
    assert "Subject/Character:" in brief["optimized_prompt"]
    assert "Lighting:" in brief["optimized_prompt"]
    assert "Negative Constraints:" in brief["optimized_prompt"]
    assert "provider calls remain off" in brief["optimized_prompt"].lower()
    assert payload["provider_calls_started"] is False


def test_prompt_optimizer_can_apply_gated_prompt_optimizer_enhancement(tmp_path, monkeypatch) -> None:
    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            assert capability == "llm"
            assert service_id == "prompt_optimizer"
            assert request.task_type == "prompt_enhancement"
            prompt = request.prompt
            assert "原始提示词：" in prompt
            assert "输出必须只有以下九行" in prompt
            assert "硬性要求：" in prompt
            return {"text": "\n".join(
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
            )}

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_llm_enhancement.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_relay_llm/prompt-optimizations",
        json={
            "node_id": "image-node-prompt-text",
            "node_type": "image",
            "prompt_text": "A founder stands in a night studio before a product launch.",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "cinematic",
            "node_parameters": {
                "model": "image2-keyframe",
                "llm_provider": "prompt_optimizer",
                "llm_model": "prompt-optimizer",
            },
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
    assert trace["llm_enhancement"]["model"] == "provider_configured"
    assert manifest["llm_enhancement"]["raw_response_stored"] is False
    assert brief["provider_calls_started"] is True
    assert "api_key" not in serialized
    assert "bearer " not in serialized
    assert "reasoning_content" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized


def test_studio_prompt_optimizer_uses_llm_fields_even_when_image_model_is_selected() -> None:
    from apps.api.runtime_llm_enhancement import provider_text_requested
    from apps.api.runtime_models import PromptOptimizationRequest

    request = PromptOptimizationRequest(
        node_id="image-node-studio-llm-fields",
        node_type="image",
        prompt_text="A young woman turns back on a rainy neon street.",
        generation_target="image",
        target_platform="short_video",
        style="cinematic",
        node_parameters={
            "model": "image2-keyframe",
            "llm_provider": "prompt_optimizer",
            "llm_model": "prompt-optimizer",
            "remote_optimizer_required": True,
        },
        generated_at="2026-06-14T05:20:00+08:00",
    )

    assert provider_text_requested(request) is True

def test_prompt_optimizer_falls_back_to_available_relay_llm_service(tmp_path, monkeypatch) -> None:
    class Descriptor:
        modality = "llm"

    class FakeRegistry:
        _descriptors = {"relay_llm": Descriptor()}

        def __init__(self) -> None:
            self.calls: list[str] = []

        def dispatch(self, capability, service_id, request):
            assert capability == "llm"
            self.calls.append(service_id)
            if service_id == "prompt_optimizer":
                raise ModelGatewayError("Provider service not found: prompt_optimizer")
            assert service_id == "relay_llm"
            return {"text": "\n".join(
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
            )}

    registry = FakeRegistry()
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_llm_enhancement.load_provider_registry", lambda: registry)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_relay_llm_alias/prompt-optimizations",
        json={
            "node_id": "image-node-prompt-alias",
            "node_type": "image",
            "prompt_text": "A founder stands in a night studio before a product launch.",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "cinematic",
            "node_parameters": {
                "model": "image2-keyframe",
                "llm_provider": "prompt_optimizer",
            },
            "generated_at": "2026-06-13T13:00:00+08:00",
        },
    )

    assert result.status_code == 200
    assert registry.calls[:2] == ["prompt_optimizer", "relay_llm"]
    assert result.json()["provider_calls_started"] is True


def test_prompt_optimizer_skips_incompatible_llm_endpoint_404(tmp_path, monkeypatch) -> None:
    class Descriptor:
        modality = "llm"

    class FakeRegistry:
        _descriptors = {"deepseek_llm": Descriptor()}

        def __init__(self) -> None:
            self.calls: list[str] = []

        def dispatch(self, capability, service_id, request):
            assert capability == "llm"
            self.calls.append(service_id)
            if service_id == "prompt_optimizer":
                raise ModelGatewayError(f"OpenAI-compatible HTTP error 404: unavailable {service_id}")
            assert service_id == "deepseek_llm"
            return {"text": "\n".join(
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
            )}

    registry = FakeRegistry()
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_llm_enhancement.load_provider_registry", lambda: registry)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_relay_llm_404_fallback/prompt-optimizations",
        json={
            "node_id": "image-node-prompt-404-fallback",
            "node_type": "image",
            "prompt_text": "A founder stands in a night studio before a product launch.",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "cinematic",
            "node_parameters": {"model": "image2-keyframe", "llm_provider": "prompt_optimizer"},
            "generated_at": "2026-06-13T13:10:00+08:00",
        },
    )

    assert result.status_code == 200
    assert registry.calls == ["prompt_optimizer", "deepseek_llm"]
    assert result.json()["provider_calls_started"] is True


def test_prompt_optimizer_uses_chinese_fallback_when_provider_output_is_templated(tmp_path, monkeypatch) -> None:
    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            assert capability == "llm"
            assert service_id == "prompt_optimizer"
            assert request.task_type in {"prompt_enhancement", "prompt_enhancement_retry"}
            return {"text": "\n".join(
                [
                    "Intent: generic scene.",
                    "Subject/Character: Primary character with stable identity.",
                    "Scene/Production Design: primary scene.",
                    "Camera/Framing: medium shot.",
                    "Lighting: cinematic light.",
                    "Negative Constraints: no watermark.",
                ]
            )}

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_llm_enhancement.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_relay_llm_fallback/prompt-optimizations",
        json={
            "node_id": "image-node-prompt-text-fallback",
            "node_type": "image",
            "prompt_text": "一个穿黑色风衣的年轻女导演，短发，雨夜天台，城市霓虹在湿地上反光。",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "cinematic",
            "node_parameters": {
                "model": "image2-keyframe",
                "aspect_ratio": "9:16",
                "llm_provider": "prompt_optimizer",
                "llm_model": "prompt-optimizer",
            },
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
    assert trace["llm_enhancement"]["format_retry_count"] == 1


def test_prompt_optimizer_llm_enhancement_uses_provider_registry_not_legacy_gateway() -> None:
    source = Path("apps/api/runtime_llm_enhancement.py").read_text(encoding="utf-8")

    assert "ModelGateway.from_config_path" not in source
    assert "MODEL_GATEWAY_CONFIG_ENV" not in source
    assert "load_provider_registry" in source


def test_studio_prompt_optimizer_requires_remote_llm_when_requested(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_studio_remote_optimizer/prompt-optimizations",
        json={
            "node_id": "image-node-studio",
            "node_type": "image",
            "prompt_text": "A school-uniform character sheet for a quiet young woman.",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "cinematic",
            "node_parameters": {
                "model": "image2-keyframe",
                "llm_provider": "prompt_optimizer",
                "remote_optimizer_required": True,
            },
            "generated_at": "2026-06-13T01:30:00+08:00",
        },
    )

    assert result.status_code == 422
    assert "remote LLM prompt optimization unavailable" in result.json()["detail"]


def test_studio_prompt_optimizer_does_not_fallback_when_remote_llm_output_is_rejected(tmp_path, monkeypatch) -> None:
    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            assert capability == "llm"
            assert service_id == "prompt_optimizer"
            return {"text": "Subject/Character: Primary character with stable identity."}

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_llm_enhancement.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_studio_remote_optimizer_rejected/prompt-optimizations",
        json={
            "node_id": "image-node-studio-rejected",
            "node_type": "image",
            "prompt_text": "A desert walking keyframe with a fixed character.",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "cinematic",
            "node_parameters": {
                "model": "image2-keyframe",
                "llm_provider": "prompt_optimizer",
                "remote_optimizer_required": True,
            },
            "generated_at": "2026-06-13T01:35:00+08:00",
        },
    )

    assert result.status_code == 422
    assert "enhancement missing required sections" in result.json()["detail"]


def test_studio_prompt_optimizer_accepts_common_llm_section_format_variants(tmp_path, monkeypatch) -> None:
    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            assert capability == "llm"
            assert service_id == "prompt_optimizer"
            return {"text": "\n".join(
                [
                    "1. 【意图】生成一张未来机器人屋顶观星的完整概念图。",
                    "2. [人物] 未来机器人主体清晰，金属结构和发光部件具备辨识度。",
                    "3. 场景：星际屋顶场景宽阔，远处星空和城市轮廓补足空间层次。",
                    "- 动作：机器人安静站立，像是在观察远处星空。",
                    "- 镜头：低机位中景，主体居中偏右，保留环境纵深。",
                    "- 灯光：冷色星光与柔和边缘光突出金属轮廓。",
                    "- 运动：单帧概念图，强调静态瞬间和氛围。",
                    "- 连续性：保持未来科幻主题，不漂移到其他题材。",
                    "- 负面：不要水印、乱码、畸形肢体或无关角色。",
                ]
            )}

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_llm_enhancement.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_studio_remote_optimizer_section_variants/prompt-optimizations",
        json={
            "node_id": "image-node-studio-section-variants",
            "node_type": "image",
            "prompt_text": "一个来自未来的机器人，在屋顶看星星",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "cinematic",
            "node_parameters": {
                "model": "image2-keyframe",
                "llm_provider": "prompt_optimizer",
                "remote_optimizer_required": True,
            },
            "generated_at": "2026-06-14T03:30:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    titles = [section["title"] for section in payload["user_prompt_sections"]]
    assert "人物/主体" in titles
    assert "场景/美术" in titles
    assert "镜头/构图" in titles
    assert "负面约束" in titles
    assert "【意图】" not in payload["optimized_prompt"]


def test_studio_prompt_optimizer_retries_once_when_llm_returns_chatty_article(tmp_path, monkeypatch) -> None:
    calls: list[str] = []

    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            assert capability == "llm"
            assert service_id == "prompt_optimizer"
            calls.append(request.task_type)
            if len(calls) == 1:
                return {
                    "text": "\n".join(
                        [
                            "下面为您把原始提示词扩展成适合图像生成模型的完整提示词。",
                            "## 强化版 Prompt",
                            "A cinematic rooftop scene with dramatic rain and city lights.",
                            "## Negative Prompt",
                            "low quality, watermark, bad anatomy",
                        ]
                    )
                }
            return {"text": "\n".join(
                [
                    "意图：生成一张雨夜屋顶红发人物的电影关键帧。",
                    "人物/主体：Lin Wan 站在屋顶边缘，红色长发被风吹动，神情坚定。",
                    "场景/美术：雨夜城市屋顶，远处霓虹和湿润地面形成反光。",
                    "动作/情节：人物静立在雨中，像是在等待关键时刻。",
                    "镜头/构图：低角度中景，主体位于画面中央偏右，背景保留城市纵深。",
                    "灯光：冷色雨夜环境光与暖色轮廓光共同塑造电影感。",
                    "运动/时间推进：单帧关键画面，保留雨丝和发丝的短时间动势。",
                    "连续性：保持红发人物、雨夜屋顶和电影化风格一致。",
                    "负面约束：不要水印、文字乱码、畸形肢体、身份漂移或无关角色。",
                ]
            )}

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_llm_enhancement.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_studio_remote_optimizer_retry/prompt-optimizations",
        json={
            "node_id": "image-node-studio-retry",
            "node_type": "image",
            "prompt_text": "Lin Wan stands on a rain rooftop with red long hair, cinematic keyframe.",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "cinematic",
            "node_parameters": {
                "model": "image2-keyframe",
                "llm_provider": "prompt_optimizer",
                "remote_optimizer_required": True,
            },
            "generated_at": "2026-06-14T03:40:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    assert calls == ["prompt_enhancement", "prompt_enhancement_retry"]
    assert payload["optimized_prompt"].startswith("意图：")
    trace = client.get(f"/artifacts/{payload['artifacts']['prompt_assembly_trace']['artifact_id']}").json()["payload"]
    assert trace["llm_enhancement"]["format_retry_count"] == 1


def test_prompt_optimizer_retry_instruction_is_readable_chinese() -> None:
    from apps.api.runtime_llm_enhancement_instructions import strict_format_retry_instruction

    request = PromptOptimizationRequest(
        node_id="image-node-retry-instruction",
        node_type="image",
        prompt_text="根据参考图生成电影感关键帧",
        generation_target="keyframe",
        target_platform="short_video",
        style="cinematic",
        node_parameters={"model": "image2-keyframe"},
        generated_at="2026-06-21T00:00:00+08:00",
    )

    instruction = strict_format_retry_instruction(request)

    assert "只输出九行" in instruction
    assert "人物/主体" in instruction
    assert "负面约束" in instruction
    assert "????" not in instruction


def test_studio_prompt_optimizer_salvages_repeated_chatty_llm_article(tmp_path, monkeypatch) -> None:
    chatty = "\n".join(
        [
            "下面为您把原始提示词扩展成适合图像生成模型的完整提示词。",
            "## 中文版 Prompt",
            "> **电影感关键帧，逼真的雨夜屋顶场景，林晚站在屋顶边缘，长长的红色长发随风飘动，雨滴在发丝和肩头闪烁，远处城市灯光被雾气模糊，湿润反光表面，低角度拍摄，冷暖对比灯光，体积雾和镜头雨点散射。**",
            "## Negative Prompt",
            "```",
            "low quality, blurry, watermark, deformed hands, extra limbs, bad anatomy",
            "```",
        ]
    )

    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            assert capability == "llm"
            assert service_id == "prompt_optimizer"
            return {"text": chatty}

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_llm_enhancement.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_studio_remote_optimizer_salvage/prompt-optimizations",
        json={
            "node_id": "image-node-studio-salvage",
            "node_type": "image",
            "prompt_text": "Lin Wan stands on a rain rooftop with red long hair, cinematic keyframe.",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "cinematic",
            "node_parameters": {
                "model": "image2-keyframe",
                "llm_provider": "prompt_optimizer",
                "remote_optimizer_required": True,
            },
            "generated_at": "2026-06-14T03:50:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    assert payload["optimized_prompt"].startswith("意图：")
    assert "中文版 Prompt" not in payload["optimized_prompt"]
    assert "林晚站在屋顶边缘" in payload["optimized_prompt"]
    trace = client.get(f"/artifacts/{payload['artifacts']['prompt_assembly_trace']['artifact_id']}").json()["payload"]
    assert trace["llm_enhancement"]["format_retry_count"] == 1
    assert trace["llm_enhancement"]["format_salvage_used"] is True


def test_visual_prompt_optimizer_uses_t2i_instruction_without_references(tmp_path, monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            assert capability == "llm"
            captured["prompt"] = request.prompt
            return {"text": "\n".join(
                [
                    "意图：根据一个来自未来的机器人生成一张完整概念图。",
                    "人物/主体：未来机器人主体清晰，金属结构与发光部件具有辨识度。",
                    "场景/美术：星际屋顶场景宽阔，远处星空和城市轮廓补足空间层次。",
                    "动作/情节：机器人安静站立，像是在观察远处星空。",
                    "镜头/构图：低机位中景，主体居中偏右，保留环境纵深。",
                    "灯光：冷色星光与柔和边缘光突出金属轮廓。",
                    "运动/时间推进：单帧概念图，强调静态瞬间和氛围。",
                    "连续性：保持未来科幻主题，不漂移到其他题材。",
                    "负面约束：不要水印、乱码、畸形肢体或无关角色。",
                ]
            )}

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_llm_enhancement.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_t2i_prompt_mode/prompt-optimizations",
        json={
            "node_id": "image-node-t2i",
            "node_type": "image",
            "prompt_text": "一个来自未来的机器人，在屋顶看星星",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "cinematic",
            "node_parameters": {
                "model": "image2-keyframe",
                "llm_provider": "prompt_optimizer",
                "remote_optimizer_required": True,
            },
            "generated_at": "2026-06-13T15:00:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    assert payload["optimization_mode"] == "t2i"
    assert "参考图中的同一个人物" not in captured["prompt"]
    assert "不改变参考图" not in captured["prompt"]
    assert "扩写" in captured["prompt"] or "补足" in captured["prompt"]


def test_visual_prompt_optimizer_uses_i2i_instruction_with_references(tmp_path, monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            assert capability == "llm"
            captured["prompt"] = request.prompt
            return {"text": "\n".join(
                [
                    "意图：只根据用户要求调整参考人物发型。",
                    "人物/主体：保持参考图中的同一人物身份，只将头发改为短发。",
                    "场景/美术：保留参考图原有背景和整体氛围，不新增地点。",
                    "动作/情节：人物保持原有静态姿态，仅呈现发型变化。",
                    "镜头/构图：保持参考图主体关系和构图稳定。",
                    "灯光：不改变参考图的主要光感和明暗关系。",
                    "运动/时间推进：单帧编辑画面，不制造多阶段动作。",
                    "连续性：保持脸部辨识度、服装、体型比例和整体风格。",
                    "负面约束：不要水印、乱码、身份漂移或背景大幅变化。",
                ]
            )}

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_llm_enhancement.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_i2i_prompt_mode/prompt-optimizations",
        json={
            "node_id": "image-node-i2i",
            "node_type": "image",
            "prompt_text": "将这个人物的头发改为短发",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "cinematic",
            "asset_refs": ["img_reference_001"],
            "node_parameters": {
                "model": "image2-keyframe",
                "llm_provider": "prompt_optimizer",
                "remote_optimizer_required": True,
            },
            "generated_at": "2026-06-13T15:10:00+08:00",
        },
    )

    assert result.status_code == 200
    assert result.json()["optimization_mode"] == "i2i"
    assert "参考图中的同一个人物" in captured["prompt"]
    assert "只改变用户明确要求改变的部分" in captured["prompt"]


def test_video_prompt_optimizer_uses_i2v_instruction_with_first_frame(tmp_path, monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            assert capability == "llm"
            captured["prompt"] = request.prompt
            return {"text": "\n".join(
                [
                    "意图：基于首帧生成角色在沙漠中行走的视频，保持连续运动。",
                    "人物/主体：保持首帧中的同一人物身份、蓝白校服、发型轮廓和体态比例。",
                    "场景/美术：延续首帧画风与沙漠空间，背景自然变化。",
                    "动作/情节：人物从首帧姿态开始向前行走，步伐自然克制。",
                    "镜头/构图：以首帧构图为起点，轻微跟随主体运动。",
                    "灯光：保持首帧主要光源方向、曝光和色温。",
                    "运动/时间推进：5秒连续视频，动作方向明确，节奏稳定。",
                    "连续性：首帧是强约束，保持身份、服装、体态、场景和画风一致。",
                    "负面约束：不要身份漂移、换脸、换装、静止不动、突兀转场、文字或水印。",
                ]
            )}

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_llm_enhancement.load_provider_registry", lambda: FakeRegistry())
    request = PromptOptimizationRequest(
        node_id="video-node-i2v",
        node_type="video",
        prompt_text="基于当前关键帧生成视频",
        generation_target="video",
        target_platform="short_video",
        style="cinematic",
        asset_refs=["img_first_frame"],
        node_parameters={
            "llm_provider": "prompt_optimizer",
            "remote_optimizer_required": True,
            "first_frame_image_asset_id": "img_first_frame",
            "motion": "角色在沙漠中行走",
            "connected_reference_nodes": [
                {
                    "title": "角色三视图",
                    "prompt": "意图：生成角色在沙漠中行走的图片，保持服装、发型、体态一致。",
                }
            ],
        },
        generated_at="2026-06-13T15:20:00+08:00",
    )

    payload = maybe_enhance_prompt_with_llm(request, {"selected_slots": {}})
    assert payload["optimization_mode"] == "i2v"
    assert "基于首帧生成视频" in captured["prompt"]
    assert "不要把上游节点标题或完整旧提示词当成人物名字" in captured["prompt"]
    assert "图生图编辑" not in payload["user_prompt"]
    assert "单帧图像编辑" not in payload["user_prompt"]


def test_i2i_prompt_optimizer_guardrail_uses_uploaded_image_filename_hint(tmp_path, monkeypatch) -> None:
    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            assert capability == "llm"
            return {"text": "\n".join(
                [
                    "意图：围绕“将这个人物的头发改为短发”完成本次生成。",
                    "人物/主体：保留原始提示词中的主体；若写到“这个人物”，必须理解为参考图中的同一个人物。",
                    "场景/美术：保持参考图或原提示中的场景信息；未指定时不要新增具体地点。",
                    "动作/情节：只执行“将这个人物的头发改为短发”这一项变化，不扩写新剧情。",
                    "镜头/构图：关键帧清晰呈现主体变化，构图稳定，主体可辨识。",
                    "灯光：保持自然可读的光线，不改变参考图的主要光感。",
                    "运动/时间推进：单帧关键画面，不制造多阶段动作。",
                    "连续性：保持参考图人物身份、脸部辨识度、服装、体型比例和整体风格；只改变用户明确要求改变的部分。",
                    "负面约束：不要水印、文字乱码、五官畸形、身份漂移、服装漂移、背景大幅变化。",
                ]
            )}

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_llm_enhancement.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/projects/proj_i2i_prompt_guardrail/prompt-optimizations",
        json={
            "node_id": "image-node-i2i",
            "node_type": "image",
            "prompt_text": "将这个人物的头发改为短发",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "cinematic",
            "asset_refs": ["img_reference_001"],
            "node_parameters": {
                "model": "image2-keyframe",
                "llm_provider": "prompt_optimizer",
                "remote_optimizer_required": True,
                "uploaded_images": [
                    {"asset_id": "img_reference_001", "filename": "校服周彤v1.png", "role": "reference_image"}
                ],
            },
            "generated_at": "2026-06-13T15:10:00+08:00",
        },
    )

    payload = result.json()
    assert result.status_code == 200
    assert payload["provider_calls_started"] is True
    assert payload["safe_manifest"]["llm_enhancement"]["guardrail_fallback_used"] is True
    assert "校服周彤" in payload["optimized_prompt"]
    assert "不要染发变浅" in payload["optimized_prompt"]
