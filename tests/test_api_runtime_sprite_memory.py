from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def _create_project(client: TestClient, project_id: str) -> None:
    response = client.post(
        "/projects",
        json={
            "project_id": project_id,
            "project_type": "short_video_campaign",
            "goal": "internal sprite memory test",
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


def _write_memory(
    client: TestClient,
    project_id: str,
    *,
    memory_type: str = "style_preference",
    label: str = "low-key cinematic color",
    summary: str = "User prefers restrained cyan accents and dark storybook lighting.",
    source_message_id: str = "msg-001",
    created_at: str = "2026-06-23T10:00:00+08:00",
) -> dict:
    response = client.post(
        f"/projects/{project_id}/sprite/memory",
        json={
            "memory_type": memory_type,
            "label": label,
            "summary": summary,
            "source_message_id": source_message_id,
            "scope": "project",
            "confidence": 0.92,
            "user_confirmed": True,
            "created_at": created_at,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["memory"]


def test_sprite_memory_writes_only_user_confirmed_project_preference(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_sprite_memory_confirmed"
    _create_project(client, project_id)

    memory = _write_memory(client, project_id)

    assert memory["memory_type"] == "style_preference"
    assert memory["user_confirmed"] is True
    assert memory["scope"] == "project"
    assert memory["writes_company_kb"] is False
    assert memory["writes_long_term_memory"] is False

    listed = client.get(f"/projects/{project_id}/sprite/memory")
    assert listed.status_code == 200, listed.text
    state = listed.json()
    assert state["schema_version"] == "afs_sprite_project_memory.v0.1"
    assert state["writes_company_kb"] is False
    assert state["writes_long_term_memory"] is False
    assert state["memory_count"] == 1
    assert state["memories"][0]["memory_id"] == memory["memory_id"]


def test_sprite_memory_delete_removes_only_selected_memory(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_sprite_memory_delete"
    _create_project(client, project_id)
    first = _write_memory(client, project_id, label="quiet suggestions", created_at="2026-06-23T10:00:00+08:00")
    second = _write_memory(
        client,
        project_id,
        memory_type="workflow_preference",
        label="storyboard first",
        summary="User prefers reviewing storyboard cards before keyframe generation.",
        source_message_id="msg-002",
        created_at="2026-06-23T10:01:00+08:00",
    )

    response = client.delete(f"/projects/{project_id}/sprite/memory/{first['memory_id']}")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["deleted"] is True
    assert payload["memory_id"] == first["memory_id"]
    assert payload["state"]["memory_count"] == 1
    assert payload["state"]["memories"][0]["memory_id"] == second["memory_id"]


def test_sprite_memory_clear_removes_all_project_memories(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_sprite_memory_clear"
    _create_project(client, project_id)
    _write_memory(client, project_id, label="quiet suggestions", created_at="2026-06-23T10:00:00+08:00")
    _write_memory(
        client,
        project_id,
        memory_type="negative_preference",
        label="avoid dashboard-looking frames",
        summary="User repeatedly rejects dashboard-like generated images.",
        source_message_id="msg-003",
        created_at="2026-06-23T10:02:00+08:00",
    )

    response = client.post(f"/projects/{project_id}/sprite/memory/clear")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["cleared"] is True
    assert payload["state"]["memory_count"] == 0
    assert payload["state"]["memories"] == []
    assert payload["state"]["writes_company_kb"] is False
    assert payload["state"]["writes_long_term_memory"] is False


def test_sprite_memory_rejects_private_customer_content_even_when_confirmed(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_sprite_memory_private_customer"
    _create_project(client, project_id)

    response = client.post(
        f"/projects/{project_id}/sprite/memory",
        json={
            "memory_type": "workflow_preference",
            "label": "Customer Acme launch",
            "summary": "Customer Acme confidential launch plan should never be stored as sprite memory.",
            "source_message_id": "msg-private",
            "scope": "project",
            "confidence": 0.99,
            "user_confirmed": True,
            "created_at": "2026-06-23T10:03:00+08:00",
        },
    )

    assert response.status_code == 422, response.text
    listed = client.get(f"/projects/{project_id}/sprite/memory")
    assert listed.status_code == 200, listed.text
    assert listed.json()["memory_count"] == 0


@pytest.mark.parametrize(
    "unsafe_summary",
    [
        "Remember provider raw response payload for the next run.",
        "Remember this signed_url for the generated image.",
        r"Remember C:\Users\demo\private\clip.mp4 as the local media path.",
        "Remember api_key=abc123 as the provider setting.",
    ],
)
def test_sprite_memory_rejects_secret_provider_and_media_references(tmp_path, unsafe_summary: str) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_sprite_memory_secret_refs"
    _create_project(client, project_id)

    response = client.post(
        f"/projects/{project_id}/sprite/memory",
        json={
            "memory_type": "style_preference",
            "label": "unsafe reference",
            "summary": unsafe_summary,
            "source_message_id": "msg-unsafe",
            "scope": "project",
            "confidence": 0.99,
            "user_confirmed": True,
            "created_at": "2026-06-23T10:04:30+08:00",
        },
    )

    assert response.status_code == 422, response.text
    assert client.get(f"/projects/{project_id}/sprite/memory").json()["memory_count"] == 0


def test_sprite_memory_rejects_unconfirmed_preference(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_sprite_memory_unconfirmed"
    _create_project(client, project_id)

    response = client.post(
        f"/projects/{project_id}/sprite/memory",
        json={
            "memory_type": "collaboration_preference",
            "label": "more proactive reminders",
            "summary": "User may want TuanTuan to remind more proactively, but did not confirm storage.",
            "source_message_id": "msg-unconfirmed",
            "scope": "project",
            "confidence": 0.7,
            "user_confirmed": False,
            "created_at": "2026-06-23T10:04:00+08:00",
        },
    )

    assert response.status_code == 422, response.text
    listed = client.get(f"/projects/{project_id}/sprite/memory")
    assert listed.status_code == 200, listed.text
    assert listed.json()["memory_count"] == 0


def test_sprite_memory_respects_auth_project_scope(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "alpha-invite,beta-invite")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    alpha = _register(client, invite_code="alpha-invite", email="alpha@example.com")
    beta = _register(client, invite_code="beta-invite", email="beta@example.com")
    alpha_headers = _auth_headers(alpha["session_token"])
    beta_headers = _auth_headers(beta["session_token"])

    created = client.post(
        "/projects",
        json={"project_id": "alpha-sprite-memory", "goal": "Alpha sprite memory project"},
        headers=alpha_headers,
    )
    assert created.status_code == 200, created.text
    request_body = {
        "memory_type": "style_preference",
        "label": "soft cyan accents",
        "summary": "User prefers soft cyan accents for TuanTuan suggestions.",
        "source_message_id": "msg-auth",
        "scope": "project",
        "confidence": 0.8,
        "user_confirmed": True,
        "created_at": "2026-06-23T10:05:00+08:00",
    }

    assert client.post("/projects/alpha-sprite-memory/sprite/memory", json=request_body).status_code == 401
    assert client.post(
        "/projects/alpha-sprite-memory/sprite/memory",
        json=request_body,
        headers=beta_headers,
    ).status_code == 403
    assert client.post(
        "/projects/alpha-sprite-memory/sprite/memory",
        json=request_body,
        headers=alpha_headers,
    ).status_code == 200
