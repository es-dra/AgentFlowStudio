from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def _create_project(client: TestClient, project_id: str) -> None:
    response = client.post(
        "/projects",
        json={
            "project_id": project_id,
            "project_type": "short_video_campaign",
            "goal": "internal sprite test",
            "status": "in_progress",
        },
    )
    assert response.status_code == 200, response.text


def _register(client: TestClient, *, invite_code: str, email: str) -> dict:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "strong-password-123",
            "display_name": email.split("@", 1)[0],
            "invite_code": invite_code,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _auth_headers(session_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {session_token}"}


def test_sprite_chat_falls_back_to_local_rules_when_llm_gate_closed(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_sprite_local"
    _create_project(client, project_id)

    response = client.post(
        f"/projects/{project_id}/sprite/chat",
        json={
            "message": "下一步应该做什么?",
            "node_id": "image_1",
            "canvas_summary": {"nodes": 2, "assets": 1},
            "generated_at": "2026-06-19T10:00:00Z",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["project_id"] == project_id
    assert payload["mode"] == "local_rules"
    assert payload["provider_calls_started"] is False
    assert payload["provider_gate"] == {
        "capability": "llm",
        "env": "AFS_ALLOW_REMOTE_LLM",
        "status": "blocked",
    }
    assert "下一步" in payload["reply"]
    assert payload["safe_manifest"]["provider_raw_response_stored"] is False
    assert payload["safe_manifest"]["local_paths_returned_by_api"] is False


def test_sprite_chat_uses_unified_llm_dispatch_when_gate_is_open(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, str, str]] = []

    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            calls.append((capability, service_id, request.prompt))
            return {"text": "先确认首帧参考图，再生成视频。"}

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_sprite.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_sprite_llm"
    _create_project(client, project_id)

    response = client.post(
        f"/projects/{project_id}/sprite/chat",
        json={
            "message": "我现在怎么继续?",
            "node_id": "video_1",
            "canvas_summary": {"nodes": 3, "assets": 2, "selected_node_type": "video"},
            "generated_at": "2026-06-19T10:00:00Z",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "llm"
    assert payload["provider_calls_started"] is True
    assert payload["reply"] == "先确认首帧参考图，再生成视频。"
    assert calls and calls[0][0] == "llm"
    assert calls[0][1] == "prompt_optimizer"
    assert "我现在怎么继续?" in calls[0][2]
    assert "Do not include local paths" in calls[0][2]
    assert "你是团团" in calls[0][2]
    assert "不要把用户称为 AFS Studio" in calls[0][2]


def test_sprite_chat_constrains_long_llm_reply_to_two_sentences(tmp_path, monkeypatch) -> None:
    class VerboseRegistry:
        def dispatch(self, capability, service_id, request):
            return {
                "text": (
                    "我先看当前画布，建议你确认关键帧节点。"
                    "然后检查素材是否已经固定。"
                    "第三步再进入生成队列，避免上下文漂移。"
                )
            }

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_sprite.load_provider_registry", lambda: VerboseRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_sprite_concise"
    _create_project(client, project_id)

    response = client.post(
        f"/projects/{project_id}/sprite/chat",
        json={
            "message": "你看到了什么?",
            "node_id": "image_1",
            "canvas_summary": {"nodes": 1, "assets": 0, "selected_node_type": "image"},
            "generated_at": "2026-06-21T00:00:00+08:00",
        },
    )

    assert response.status_code == 200, response.text
    reply = response.json()["reply"]
    assert reply == "我先看当前画布，建议你确认关键帧节点。然后检查素材是否已经固定。"
    assert "第三步" not in reply


def test_sprite_chat_falls_back_when_llm_reply_is_unsafe(tmp_path, monkeypatch) -> None:
    class UnsafeRegistry:
        def dispatch(self, capability, service_id, request):
            return {"text": "Use this signed_url and provider raw response."}

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_sprite.load_provider_registry", lambda: UnsafeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_sprite_unsafe"
    _create_project(client, project_id)

    response = client.post(
        f"/projects/{project_id}/sprite/chat",
        json={
            "message": "下一步怎么做?",
            "canvas_summary": {"nodes": 1, "assets": 0},
            "generated_at": "2026-06-19T10:00:00Z",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "local_rules"
    assert payload["provider_calls_started"] is False
    assert payload["safe_manifest"]["fallback_reason"] == "unsafe_llm_reply"
    assert "signed_url" not in payload["reply"]


def test_sprite_chat_does_not_send_unsafe_user_message_to_llm(tmp_path, monkeypatch) -> None:
    calls: list[str] = []

    class FakeRegistry:
        def dispatch(self, capability, service_id, request):
            calls.append(request.prompt)
            return {"text": "should not run"}

    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setattr("apps.api.runtime_sprite.load_provider_registry", lambda: FakeRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_sprite_unsafe_user"
    _create_project(client, project_id)

    response = client.post(
        f"/projects/{project_id}/sprite/chat",
        json={
            "message": r"请看 C:\Users\demo\secret.png 下一步怎么做?",
            "canvas_summary": {"nodes": "two", "assets": []},
            "generated_at": "2026-06-19T10:00:00Z",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "local_rules"
    assert payload["provider_calls_started"] is False
    assert payload["safe_manifest"]["fallback_reason"] == "unsafe_user_message"
    assert calls == []
    assert "0 个节点" in payload["reply"]


def test_sprite_chat_respects_auth_project_scope(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "alpha-invite,beta-invite")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    alpha = _register(client, invite_code="alpha-invite", email="alpha@example.com")
    beta = _register(client, invite_code="beta-invite", email="beta@example.com")
    alpha_headers = _auth_headers(alpha["session_token"])
    beta_headers = _auth_headers(beta["session_token"])

    created = client.post(
        "/projects",
        json={"project_id": "alpha-sprite-project", "goal": "Alpha sprite project"},
        headers=alpha_headers,
    )
    assert created.status_code == 200, created.text
    request_body = {
        "message": "下一步怎么做?",
        "canvas_summary": {"nodes": 1, "assets": 0},
        "generated_at": "2026-06-19T10:00:00Z",
    }

    assert client.post("/projects/alpha-sprite-project/sprite/chat", json=request_body).status_code == 401
    assert client.post(
        "/projects/alpha-sprite-project/sprite/chat",
        json=request_body,
        headers=beta_headers,
    ).status_code == 403
    assert client.post(
        "/projects/alpha-sprite-project/sprite/chat",
        json=request_body,
        headers=alpha_headers,
    ).status_code == 200
