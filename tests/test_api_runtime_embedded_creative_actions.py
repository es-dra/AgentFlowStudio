from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def _create_project(client: TestClient, project_id: str) -> None:
    response = client.post(
        "/projects",
        json={
            "project_id": project_id,
            "project_type": "freeform_canvas",
            "goal": "embedded creative action test",
            "status": "in_progress",
        },
    )
    assert response.status_code == 200, response.text


def _creative_action_request(**overrides) -> dict:
    payload = {
        "action_type": "script_revision",
        "node_id": "idea_node_1",
        "node_type": "text",
        "source_text": "孙悟空大战猪八戒。",
        "mode": "professional_expansion",
        "context_summary": {
            "project_name": "节点内创作测试",
            "selected_node_title": "短想法",
            "selected_node_type": "text",
            "selected_node_status": "draft",
            "counts": {"nodes": 1, "scenes": 0, "shots": 0},
            "section": "canvas",
        },
        "constraints": ["普通优化必须保持同一节点身份。", "确认前不改动画布。"],
        "provider_service_id": "server_codex",
        "generated_at": "2026-07-22T12:00:00Z",
    }
    payload.update(overrides)
    return payload


def test_embedded_creative_action_gate_closed_is_preview_only_unavailable(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "embedded-action-unavailable"
    _create_project(client, project_id)
    before = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]

    response = client.post(
        f"/projects/{project_id}/embedded-creative-actions/preview",
        json=_creative_action_request(),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "unavailable"
    assert payload["provider_calls_started"] is False
    assert "不会使用本地模板冒充专业改写" in payload["preview"]["rationale"]
    assert payload["graph_mutation"]["mutated"] is False
    after = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert after["version"] == before["version"]
    assert after["graph_digest"] == before["graph_digest"]


def test_embedded_script_revision_uses_server_codex_schema_and_preserves_graph(tmp_path, monkeypatch) -> None:
    calls = []

    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            calls.append((capability, service_id, request))
            return {
                "provider_calls_started": True,
                "structured_output": {
                    "action_type": "script_revision",
                    "mode": "professional_expansion",
                    "revised_text": (
                        "花果山傍晚，孙悟空误以为猪八戒偷吃了给师父准备的供果，举棒逼问。"
                        "猪八戒一边躲闪一边护着篮子，嘴上求饶却仍惦记最后一口甜桃。"
                        "两人的打斗从玩笑升级到真怒，又在发现妖怪踪迹时转成默契联手。"
                    ),
                    "change_summary": ["补足冲突起因和人物目标", "加入动作、对白节奏和关系变化"],
                    "rationale": "这版把短想法扩写成可继续拆分的戏剧场面，同时保留同一节点身份。",
                    "unresolved_decisions": ["是否加入唐僧旁观反应"],
                    "quality_flags": ["preview_only"],
                },
            }

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_embedded_creative_actions.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "embedded-action-llm"
    _create_project(client, project_id)
    before = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]

    response = client.post(
        f"/projects/{project_id}/embedded-creative-actions/preview",
        json=_creative_action_request(),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "llm"
    assert payload["provider_calls_started"] is True
    assert payload["provider_lineage"]["service_id"] == "server_codex"
    assert payload["provider_lineage"]["provider"] == "codex_local"
    assert payload["provider_lineage"]["structured_output_contract_id"] == "afs.runtime.embedded_creative_action.v0.1"
    assert payload["preview"]["revised_text"].startswith("花果山傍晚")
    assert payload["graph_mutation"]["mutated"] is False
    after = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert after["version"] == before["version"]
    assert after["graph_digest"] == before["graph_digest"]
    assert calls and calls[0][0] == "llm"
    assert calls[0][1] == "server_codex"
    request = calls[0][2]
    assert request.structured_output_contract_id == "afs.runtime.embedded_creative_action.v0.1"
    assert request.structured_output_schema_digest
    assert "不修改画布" in request.prompt
    assert "孙悟空大战猪八戒" in request.prompt
    assert "固定4x15/10x6" in request.prompt


def test_embedded_shot_breakdown_returns_dynamic_preview_without_creating_shots(tmp_path, monkeypatch) -> None:
    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            return {
                "provider_calls_started": True,
                "structured_output": {
                    "action_type": "shot_breakdown",
                    "mode": "dynamic_shot_breakdown",
                    "revised_text": (
                        "这一场可拆成三段动作：误会、追打、共同发现妖怪踪迹。"
                        "悟空的压迫、八戒的闪躲和两人突然停手的节奏都需要明确镜头目的，"
                        "每个镜头时长由动作节拍和信息揭示决定，不套用固定数量模板。"
                    ),
                    "change_summary": ["按内容拆为三段", "每个镜头都有叙事目的"],
                    "rationale": "分镜草案只作为当前节点预览，等待用户确认后再派生具体镜头。",
                    "unresolved_decisions": [],
                    "quality_flags": ["dynamic_count"],
                    "shot_plan": {
                        "total_shots": 3,
                        "estimated_duration_sec": 21,
                        "scenes": [{
                            "title": "花果山误会",
                            "purpose": "从误会推进到联手",
                            "shots": [
                                {
                                    "title": "供果空篮",
                                    "duration_sec": 5,
                                    "shot_size": "中近景",
                                    "camera_angle": "略低机位",
                                    "movement": "缓慢推进到空篮",
                                    "blocking": "悟空压近，八戒后退护篮",
                                    "sound": "风声与桃核落地声",
                                    "transition": "动作切",
                                    "narrative_purpose": "建立误会证据",
                                },
                                {
                                    "title": "棍耙交错",
                                    "duration_sec": 9,
                                    "shot_size": "全景转近景",
                                    "camera_angle": "侧向跟拍",
                                    "movement": "横移追随两人绕树",
                                    "blocking": "悟空追打，八戒躲闪解释",
                                    "sound": "金属碰撞和急促喘息",
                                    "transition": "节奏切",
                                    "narrative_purpose": "把冲突推到最高点",
                                },
                            ],
                        }],
                    },
                },
            }

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_embedded_creative_actions.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "embedded-action-shot-plan"
    _create_project(client, project_id)
    before = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]

    response = client.post(
        f"/projects/{project_id}/embedded-creative-actions/preview",
        json=_creative_action_request(
            action_type="shot_breakdown",
            mode="dynamic_shot_breakdown",
            node_type="script",
            source_text="悟空和八戒因为供果争执，最后发现妖怪踪迹。",
        ),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "llm"
    assert payload["preview"]["shot_plan"]["total_shots"] == 2
    assert payload["preview"]["shot_plan"]["estimated_duration_sec"] == 21
    assert payload["graph_mutation"]["mutated"] is False
    after = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert after["version"] == before["version"]
    assert after["graph_digest"] == before["graph_digest"]
