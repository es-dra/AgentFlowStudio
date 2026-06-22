from __future__ import annotations

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


def test_social_square_public_list_is_safe_and_mutations_require_auth(tmp_path, monkeypatch) -> None:
    client = _auth_client(tmp_path, monkeypatch)

    empty = client.get("/community/requests")
    assert empty.status_code == 200
    assert empty.json() == {"requests": []}

    blocked = client.post(
        "/community/requests",
        json={
            "title": "需要一个雨夜开场脚本",
            "body": "想找人帮忙把侦探短片开头整理成 30 秒短视频脚本。",
            "need_type": "script",
            "deliverable_hint": "三段式脚本和关键画面说明",
        },
    )
    assert blocked.status_code == 401

    alpha = _register(client, invite_code="alpha-invite", email="alpha@example.com")
    created = client.post(
        "/community/requests",
        headers=_auth_headers(alpha["session_token"]),
        json={
            "title": "需要一个雨夜开场脚本",
            "body": "想找人帮忙把侦探短片开头整理成 30 秒短视频脚本。",
            "need_type": "script",
            "deliverable_hint": "三段式脚本和关键画面说明",
        },
    )

    assert created.status_code == 200, created.text
    item = created.json()["request"]
    assert item["status"] == "open"
    assert item["title"] == "需要一个雨夜开场脚本"
    assert item["author_display_name"] == "alpha"
    assert item["safe_public_summary"]
    assert "author_user_id" not in item
    assert "alpha@example.com" not in created.text

    listed = client.get("/community/requests").json()["requests"]
    assert [entry["request_id"] for entry in listed] == [item["request_id"]]
    assert "author_user_id" not in listed[0]
    assert "session" not in str(listed[0]).lower()


def test_social_square_request_lifecycle_is_role_gated(tmp_path, monkeypatch) -> None:
    client = _auth_client(tmp_path, monkeypatch)
    alpha = _register(client, invite_code="alpha-invite", email="alpha@example.com")
    beta = _register(client, invite_code="beta-invite", email="beta@example.com")
    alpha_headers = _auth_headers(alpha["session_token"])
    beta_headers = _auth_headers(beta["session_token"])

    created = client.post(
        "/community/requests",
        headers=alpha_headers,
        json={
            "title": "寻找角色设定板协作者",
            "body": "需要把机器人角色整理成多视图设定板，方便后续关键帧复用。",
            "need_type": "image",
            "deliverable_hint": "角色正面、侧面、背面和材质细节说明",
        },
    ).json()["request"]
    request_id = created["request_id"]

    own_accept = client.post(f"/community/requests/{request_id}/accept", headers=alpha_headers)
    assert own_accept.status_code == 403

    accepted = client.post(f"/community/requests/{request_id}/accept", headers=beta_headers)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["request"]["status"] == "accepted"
    assert accepted.json()["request"]["accepted_by_display_name"] == "beta"

    author_submit = client.post(
        f"/community/requests/{request_id}/submit",
        headers=alpha_headers,
        json={"text": "我先自己提交一个版本。"},
    )
    assert author_submit.status_code == 403

    submitted = client.post(
        f"/community/requests/{request_id}/submit",
        headers=beta_headers,
        json={"text": "已完成角色设定说明，包含四视图和材质备注。", "project_id": "demo-project"},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["request"]["status"] == "submitted"
    assert submitted.json()["request"]["submission"]["text"].startswith("已完成角色设定说明")
    assert "accepted_by_user_id" not in submitted.json()["request"]

    beta_complete = client.post(f"/community/requests/{request_id}/complete", headers=beta_headers)
    assert beta_complete.status_code == 403

    completed = client.post(f"/community/requests/{request_id}/complete", headers=alpha_headers)
    assert completed.status_code == 200, completed.text
    assert completed.json()["request"]["status"] == "completed"

    report = client.post(
        f"/community/requests/{request_id}/report",
        headers=beta_headers,
        json={"reason": "成果已经关闭，但测试举报事件仍应安全记录。"},
    )
    assert report.status_code == 200
    assert report.json()["request"]["report_count"] == 1
    assert "beta@example.com" not in report.text
