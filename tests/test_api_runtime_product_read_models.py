from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app
from tools.studio_production_delivery_browser_qa import prepare_provider_free_delivery_qa


def _register(client: TestClient, email: str, invite_code: str) -> tuple[dict, dict[str, str]]:
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
    payload = response.json()
    return payload, {"Authorization": f"Bearer {payload['session_token']}"}


def _create_project(client: TestClient, headers: dict[str, str], project_id: str, name: str) -> None:
    created = client.post(
        "/projects",
        headers=headers,
        json={"project_id": project_id, "goal": name},
    )
    assert created.status_code == 200, created.text
    state = client.put(
        f"/projects/{project_id}/studio-state",
        headers=headers,
        json={"state": {"meta": {"projectName": name, "canvasName": "制作画布"}, "nodes": {}, "order": []}},
    )
    assert state.status_code == 200, state.text


def test_product_overview_is_authenticated_owner_scoped_and_safe(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "alpha-invite,beta-invite")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    alpha, alpha_headers = _register(client, "alpha@example.com", "alpha-invite")
    _, beta_headers = _register(client, "beta@example.com", "beta-invite")
    _create_project(client, alpha_headers, "alpha-episode", "雨夜灯火")
    _create_project(client, beta_headers, "beta-secret", "Beta private project")

    crew_response = client.post(
        "/projects/alpha-episode/domain-crew",
        headers=alpha_headers,
        json={"crew_id": "rainlight-crew"},
    )
    assert crew_response.status_code == 200, crew_response.text
    crew = crew_response.json()["crew"]
    task_response = client.post(
        "/projects/alpha-episode/domain-crew/tasks",
        headers=alpha_headers,
        json={
            "task_id": "script-task",
            "node_id": "script-node",
            "expected_state_version": crew["state_version"],
            "assigned_agent_id": "rainlight-crew-screenwriter",
            "action": "script.write",
            "objective": "完成第 01 集剧本初稿",
            "entity_type": "project",
            "entity_id": "alpha-episode",
            "version_id": "episode-v1",
        },
    )
    assert task_response.status_code == 200, task_response.text

    assert client.get("/product/workspace-overview").status_code == 401
    alpha_workspace = client.get("/product/workspace-overview", headers=alpha_headers)
    assert alpha_workspace.status_code == 200, alpha_workspace.text
    payload = alpha_workspace.json()
    assert payload["locale"] == "zh-CN"
    assert [item["project_id"] for item in payload["projects"]] == ["alpha-episode"]
    assert payload["projects"][0]["name"] == "雨夜灯火"
    assert payload["projects"][0]["crew"]["registered_role_count"] == 9
    assert payload["projects"][0]["crew"]["activities"][0]["role"] == "编剧组"

    product_response = client.get("/projects/alpha-episode/product-overview", headers=alpha_headers)
    assert product_response.status_code == 200, product_response.text
    product = product_response.json()["project"]
    assert product["stages"][0] == {"key": "brief", "label": "创作简报", "state": "completed"}
    assert product["recovery"]["reload_safe"] is True
    assert product["decision_inbox"]["items"] == []
    assert product["jobs"]["cost_observability"] == "unavailable"

    encoded = json.dumps(product, ensure_ascii=False)
    assert alpha["user"]["user_id"] not in encoded
    assert "rainlight-crew-screenwriter" not in encoded
    assert "script-task" not in encoded
    assert "beta-secret" not in encoded
    assert client.get("/projects/alpha-episode/product-overview", headers=beta_headers).status_code == 403


def test_product_overview_has_chinese_empty_and_recovery_models(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "empty-invite")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    _, headers = _register(client, "empty@example.com", "empty-invite")

    payload = client.get("/product/workspace-overview", headers=headers).json()

    assert payload["workspace"] == {
        "label": "内容制作工作空间",
        "project_count": 0,
        "active_project_count": 0,
    }
    assert payload["projects"] == []
    assert payload["decision_count"] == 0
    assert payload["blocked_count"] == 0


def test_product_overview_projects_authoritative_rainlight_canon_and_reload(tmp_path, monkeypatch) -> None:
    seed = prepare_provider_free_delivery_qa(tmp_path)
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "delivery-qa-invite,canon-other-invite")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    login = client.post(
        "/auth/login",
        json={"email": seed["email"], "password": seed["password"]},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['session_token']}"}

    response = client.get(f"/projects/{seed['project_id']}/product-overview", headers=headers)
    assert response.status_code == 200, response.text
    canon = response.json()["project"]["canonical_state"]
    assert canon["status_label"] == "15/15"
    assert canon["episode_title"] == "《雨灯失窃案》第一集：最后一盏引魂灯"
    assert canon["episode_version_id"] == "ep-rainlight-001-v1"
    assert canon["duration_seconds"] == 135
    assert canon["checkpoint_version"] == 3
    assert (canon["characters"], canon["scenes"], canon["shots"], canon["audio_items"]) == (3, 3, 15, 4)
    assert len(canon["character_versions"]) == 3
    assert len(canon["scene_versions"]) == 3
    assert [item["shot_number"] for item in canon["timeline"]] == list(range(1, 16))
    assert [(item["start_seconds"], item["end_seconds"]) for item in canon["timeline"]] == [
        ((index - 1) * 9, index * 9) for index in range(1, 16)
    ]
    assert all(item["version_id"].endswith("-v1") for item in canon["timeline"])
    assert all(item["continuity"] for item in canon["timeline"])
    assert all(item["media"]["status"] == "素材待补齐" for item in canon["timeline"])
    assert all(item["audio"]["status"] == "音频待制作" for item in canon["timeline"])
    assert canon["audio"] == {
        "covered_shot_count": 15,
        "total_shot_count": 15,
        "pending_asset_count": 4,
        "all_audio_ready": False,
        "status": "音频待制作",
    }
    assert canon["pending_media_count"] == 25
    assert canon["readiness"] == "制作素材待补齐"
    encoded = json.dumps(canon, ensure_ascii=False)
    assert "required_asset_ids" not in encoded
    assert "entity_id" not in encoded
    assert "provider_needed" not in encoded
    assert "D:\\" not in encoded and "/opt/" not in encoded

    reloaded = TestClient(create_runtime_app(runtime_root=tmp_path)).get(
        f"/projects/{seed['project_id']}/product-overview",
        headers=headers,
    )
    assert reloaded.status_code == 200, reloaded.text
    assert reloaded.json()["project"]["canonical_state"] == canon

    other, other_headers = _register(client, "canon-other@example.com", "canon-other-invite")
    assert other["user"]["user_id"] not in encoded
    assert client.get(
        f"/projects/{seed['project_id']}/product-overview",
        headers=other_headers,
    ).status_code == 403
