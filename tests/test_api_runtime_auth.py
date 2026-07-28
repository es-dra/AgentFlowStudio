from __future__ import annotations

import base64
import json
import logging

from fastapi.testclient import TestClient

from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


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


def test_admin_invites_are_hash_only_listable_and_revocable(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    auth = RuntimeAuthStore(RuntimeStore(tmp_path))
    invite = auth.create_invite_code("private-alpha-code", batch_id="wave-1", note="Alice")

    invites_text = (tmp_path / "auth" / "invites.json").read_text(encoding="utf-8")
    assert "private-alpha-code" not in invites_text
    assert invite["status"] == "available"
    assert invite["batch_id"] == "wave-1"
    assert auth.list_invites()[0]["invite_id"] == invite["invite_id"]

    revoked = auth.revoke_invite(invite["invite_id"])
    assert revoked["status"] == "revoked"

    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    response = client.post(
        "/auth/register",
        json={
            "email": "alpha@example.com",
            "password": "strong-password-123",
            "display_name": "Alpha",
            "invite_code": "private-alpha-code",
        },
    )
    assert response.status_code == 400


def test_unsafe_static_env_invites_are_skipped(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "123456,valid-alpha-code")

    auth = RuntimeAuthStore(RuntimeStore(tmp_path))
    invites = auth.list_invites()

    assert len(invites) == 1
    assert invites[0]["source"] == "env"
    assert "123456" not in (tmp_path / "auth" / "invites.json").read_text(encoding="utf-8")


def test_login_failures_are_rate_limited_and_audited(tmp_path, monkeypatch, caplog) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "alpha-invite")
    monkeypatch.setenv("AFS_AUTH_RATE_LIMIT_MAX_FAILURES", "2")
    caplog.set_level(logging.INFO, logger="afs.runtime.audit")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    _register(client, invite_code="alpha-invite", email="alpha@example.com")

    bad_login = {"email": "alpha@example.com", "password": "wrong-password"}
    assert client.post("/auth/login", json=bad_login).status_code == 401
    assert client.post("/auth/login", json=bad_login).status_code == 401
    limited = client.post("/auth/login", json=bad_login)

    assert limited.status_code == 429
    rate_limits = json.loads((tmp_path / "auth" / "rate_limits.json").read_text(encoding="utf-8"))
    assert rate_limits["buckets"]
    audit_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "auth.login.failed" in audit_text
    assert "wrong-password" not in audit_text
    assert "alpha@example.com" not in audit_text


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


def test_protected_request_reuses_middleware_user_lookup(tmp_path, monkeypatch) -> None:
    client = _auth_client(tmp_path, monkeypatch)
    alpha = _register(client, invite_code="alpha-invite", email="alpha@example.com")
    headers = _auth_headers(alpha["session_token"])
    original = RuntimeAuthStore.user_from_request
    calls = 0

    def counted(self, request):
        nonlocal calls
        calls += 1
        return original(self, request)

    monkeypatch.setattr(RuntimeAuthStore, "user_from_request", counted)

    response = client.get("/projects", headers=headers)

    assert response.status_code == 200
    assert calls == 1


def test_auth_scope_covers_studio_state_assets_jobs_and_artifacts(tmp_path, monkeypatch) -> None:
    client = _auth_client(tmp_path, monkeypatch)
    alpha = _register(client, invite_code="alpha-invite", email="alpha@example.com")
    beta = _register(client, invite_code="beta-invite", email="beta@example.com")
    alpha_headers = _auth_headers(alpha["session_token"])
    beta_headers = _auth_headers(beta["session_token"])

    created = client.post(
        "/projects",
        json={"project_id": "alpha-project", "goal": "Alpha owned project"},
        headers=alpha_headers,
    )
    assert created.status_code == 200
    manifest_artifact_id = created.json()["artifact"]["artifact_id"]

    state = {
        "meta": {"projectName": "Alpha Project", "canvasName": "Board"},
        "nodes": {"image_1": {"type": "image", "title": "First frame"}},
        "order": ["image_1"],
    }
    assert client.put(
        "/projects/alpha-project/studio-state",
        json={"state": state},
        headers=alpha_headers,
    ).status_code == 200
    assert client.get("/projects/alpha-project/studio-state", headers=alpha_headers).status_code == 200
    assert client.get("/projects/alpha-project/studio-state", headers=beta_headers).status_code == 403

    upload = client.post(
        "/projects/alpha-project/image-assets",
        json={
            "node_id": "image_1",
            "filename": "first-frame.png",
            "mime_type": "image/png",
            "data_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
            "role": "reference_image",
            "generated_at": "2026-06-19T12:00:00+08:00",
        },
        headers=alpha_headers,
    )
    assert upload.status_code == 200, upload.text
    asset_id = upload.json()["asset"]["asset_id"]
    asset_artifact_id = upload.json()["artifact"]["artifact_id"]
    assert client.get("/projects/alpha-project/image-assets", headers=alpha_headers).status_code == 200
    assert client.get("/projects/alpha-project/image-assets", headers=beta_headers).status_code == 403
    assert client.get(f"/projects/alpha-project/image-assets/{asset_id}/preview").status_code == 401
    assert client.get(f"/projects/alpha-project/image-assets/{asset_id}/preview", headers=alpha_headers).status_code == 200
    assert client.get(f"/projects/alpha-project/image-assets/{asset_id}/preview", headers=beta_headers).status_code == 403

    feedback = client.post(
        "/feedback",
        json={
            "project_id": "alpha-project",
            "feedback": {"rating": 4, "notes": "Alpha-only feedback"},
            "generated_at": "2026-06-19T12:01:00+08:00",
        },
        headers=alpha_headers,
    )
    assert feedback.status_code == 200
    job_id = feedback.json()["job"]["job_id"]
    assert client.get(f"/runs/{job_id}", headers=alpha_headers).status_code == 200
    assert client.get(f"/runs/{job_id}", headers=beta_headers).status_code == 403

    assert client.get(f"/artifacts/{manifest_artifact_id}", headers=alpha_headers).status_code == 200
    assert client.get(f"/artifacts/{manifest_artifact_id}", headers=beta_headers).status_code == 403
    assert client.get(f"/artifacts/{asset_artifact_id}", headers=alpha_headers).status_code == 200
    assert client.get(f"/artifacts/{asset_artifact_id}", headers=beta_headers).status_code == 403
