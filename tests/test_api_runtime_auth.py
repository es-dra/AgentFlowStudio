from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def _auth_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "alpha-invite,beta-invite")
    return TestClient(create_runtime_app(runtime_root=tmp_path))


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


def test_invite_registration_creates_session_and_consumes_code(tmp_path, monkeypatch) -> None:
    client = _auth_client(tmp_path, monkeypatch)

    status = client.get("/auth/status").json()
    assert status["auth_required"] is True
    assert status["authenticated"] is False
    assert status["invite_registration_available"] is True
    assert status["session_ttl_hours"] == 168
    health = client.get("/health").json()
    assert health["auth_required"] is True
    assert health["boundaries"]["no_account_system"] is False

    registered = _register(client, invite_code="alpha-invite", email="alpha@example.com")
    assert registered["user"]["email"] == "alpha@example.com"
    assert registered["session_token"]
    assert "password_hash" not in registered

    me = client.get("/auth/me", headers=_auth_headers(registered["session_token"]))
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "alpha@example.com"

    reused = client.post(
        "/auth/register",
        json={
            "email": "other@example.com",
            "password": "strong-password-123",
            "display_name": "Other",
            "invite_code": "alpha-invite",
        },
    )
    assert reused.status_code == 400
    assert "invite" in reused.text.lower()


def test_expired_session_is_rejected_and_removed(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "alpha-invite")
    monkeypatch.setenv("AFS_AUTH_SESSION_TTL_HOURS", "1")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    registered = _register(client, invite_code="alpha-invite", email="alpha@example.com")

    sessions_path = tmp_path / "auth" / "sessions.json"
    sessions = json.loads(sessions_path.read_text(encoding="utf-8"))
    token_hash = next(iter(sessions["sessions"]))
    sessions["sessions"][token_hash]["created_at"] = "2026-01-01T00:00:00+00:00"
    sessions_path.write_text(json.dumps(sessions), encoding="utf-8")

    me = client.get("/auth/me", headers=_auth_headers(registered["session_token"]))
    assert me.status_code == 401
    cleaned = json.loads(sessions_path.read_text(encoding="utf-8"))
    assert cleaned["sessions"] == {}


def test_login_returns_new_session_without_exposing_password_hash(tmp_path, monkeypatch) -> None:
    client = _auth_client(tmp_path, monkeypatch)
    _register(client, invite_code="alpha-invite", email="alpha@example.com")

    response = client.post(
        "/auth/login",
        json={"email": "alpha@example.com", "password": "strong-password-123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["email"] == "alpha@example.com"
    assert payload["session_token"]
    assert "password_hash" not in response.text
    assert "strong-password-123" not in response.text


def test_auth_enabled_projects_are_owner_scoped(tmp_path, monkeypatch) -> None:
    client = _auth_client(tmp_path, monkeypatch)
    alpha = _register(client, invite_code="alpha-invite", email="alpha@example.com")
    beta = _register(client, invite_code="beta-invite", email="beta@example.com")
    alpha_headers = _auth_headers(alpha["session_token"])
    beta_headers = _auth_headers(beta["session_token"])

    assert client.get("/projects").status_code == 401

    created = client.post(
        "/projects",
        json={"project_id": "alpha-project", "goal": "Alpha owned project"},
        headers=alpha_headers,
    )
    assert created.status_code == 200

    alpha_projects = client.get("/projects", headers=alpha_headers).json()["projects"]
    beta_projects = client.get("/projects", headers=beta_headers).json()["projects"]

    assert [item["project_id"] for item in alpha_projects] == ["alpha-project"]
    assert beta_projects == []
    assert client.get("/projects/alpha-project/manifest", headers=alpha_headers).status_code == 200
    assert client.get("/projects/alpha-project/manifest", headers=beta_headers).status_code == 403
