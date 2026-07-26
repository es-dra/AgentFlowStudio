from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def _create_project(client: TestClient, project_id: str) -> None:
    response = client.post(
        "/projects",
        json={
            "project_id": project_id,
            "project_type": "short_video_campaign",
            "goal": "internal agent chat runtime test",
            "status": "in_progress",
        },
    )
    assert response.status_code == 200, response.text


def test_agent_chat_conversation_gate_closed_is_honest_unavailable(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_agent_chat_unavailable"
    _create_project(client, project_id)
    before = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]

    response = client.post(
        f"/projects/{project_id}/agent-chat/conversation",
        json={
            "message": "你好",
            "node_id": "idea_1",
            "canvas_summary": {
                "nodes": 1,
                "selected_node_type": "text",
                "selected_node_title": "雨夜想法",
                "video_readiness_status": "ready",
                "video_selected_shot_ready": 1,
                "video_shot_label": "镜头 01",
                "video_keyframe_label": "已批准关键帧",
                "video_reference_count": 3,
                "video_model": "doubao-seedance-2-0",
                "video_resolution": "720p",
                "video_duration_sec": 6,
            },
            "provider_service_id": "server_codex",
            "generated_at": "2026-07-22T08:00:00Z",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "unavailable"
    assert payload["provider_calls_started"] is False
    assert "不会用本地固定回答冒充理解" in payload["reply"]
    assert payload["graph_mutation"]["mutated"] is False
    after = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert after["version"] == before["version"]
    assert after["graph_digest"] == before["graph_digest"]


def test_agent_chat_conversation_uses_server_codex_structured_llm_and_preserves_graph(tmp_path, monkeypatch) -> None:
    calls = []

    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            calls.append((capability, service_id, request))
            return {
                "provider_calls_started": True,
                "structured_output": {
                    "reply": "你好，我会结合当前画布回答；这个想法节点还在草稿状态，下一步可以先补角色目标和场景。",
                    "intent": "greeting",
                    "suggested_actions": ["补角色目标", "补场景地点"],
                    "confidence": 0.91,
                },
            }

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_agent_chat_conversation.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_agent_chat_llm"
    _create_project(client, project_id)
    before = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]

    response = client.post(
        f"/projects/{project_id}/agent-chat/conversation",
        json={
            "message": "你好",
            "node_id": "idea_1",
            "canvas_summary": {
                "nodes": 1,
                "selected_node_type": "text",
                "selected_node_title": "雨夜想法",
                "video_readiness_status": "ready",
                "video_selected_shot_ready": 1,
                "video_shot_label": "镜头 01",
                "video_keyframe_label": "已批准关键帧",
                "video_reference_count": 3,
                "video_model": "doubao-seedance-2-0",
                "video_resolution": "720p",
                "video_duration_sec": 6,
            },
            "provider_service_id": "server_codex",
            "generated_at": "2026-07-22T08:00:00Z",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "llm"
    assert payload["provider_calls_started"] is True
    assert payload["provider_lineage"]["service_id"] == "server_codex"
    assert payload["provider_lineage"]["provider"] == "codex_local"
    assert payload["provider_lineage"]["structured_output_contract_id"] == "afs.runtime.agent_chat_conversation.v0.1"
    assert payload["cost_usd"] == 0
    assert payload["graph_mutation"]["mutated"] is False
    after = client.get(f"/projects/{project_id}/m4/production-graph").json()["graph"]
    assert after["version"] == before["version"]
    assert after["graph_digest"] == before["graph_digest"]
    assert calls and calls[0][0] == "llm"
    assert calls[0][1] == "server_codex"
    request = calls[0][2]
    assert request.structured_output_contract_id == "afs.runtime.agent_chat_conversation.v0.1"
    assert request.structured_output_schema_digest
    assert "AI 创作搭档" in request.prompt
    assert "你好" in request.prompt
    assert "不要声称已经修改画布" in request.prompt
    assert "'video_readiness_status': 'ready'" in request.prompt
    assert "'video_selected_shot_ready': 1" in request.prompt
    assert "'video_reference_count': 3" in request.prompt
    assert "'video_model': 'doubao-seedance-2-0'" in request.prompt
    assert "不要声称参考图缺失" in request.prompt
    assert "准备镜头视频" in request.prompt
