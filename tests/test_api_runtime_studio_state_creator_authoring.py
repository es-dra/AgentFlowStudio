from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def _project(client: TestClient, project_id: str) -> dict[str, object]:
    created = client.post(
        "/projects",
        json={"project_id": project_id, "goal": "恢复测试", "project_type": "studio_creator_authoring"},
    )
    assert created.status_code == 200, created.text
    return client.get(f"/projects/{project_id}/creator-workspace").json()["project"]["ref"]


def test_creator_pending_command_round_trips_through_server_state(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "creator-state-roundtrip"
    project_ref = _project(client, project_id)
    pending = {
        "schema_version": "afs_creator_pending_command.v0.1",
        "idempotency_key": "creator-project-edit-1",
        "status": "pending",
        "command": {
            "action": "authoring.revise",
            "expected_aggregate_version": 1,
            "target_ref": project_ref,
            "new_version_id": "creator-state-roundtrip-v2",
            "created_at": "2026-07-16T00:00:01+00:00",
            "changes": {"entity_type": "project", "title": "恢复后的项目"},
        },
    }
    response = client.put(
        f"/projects/{project_id}/studio-state",
        json={
            "state": {
                "creator_authoring": {
                    "mode": "canvas",
                    "selected_episode": "",
                    "selected_shot": "",
                    "selected_section": f"project:{project_id}",
                    "mobile_inspector_open": False,
                    "technical_open": False,
                    "pending_command": pending,
                    "pending_failure": "",
                }
            }
        },
    )
    assert response.status_code == 200, response.text
    saved = response.json()["state"]["creator_authoring"]
    assert saved["mode"] == "canvas"
    assert saved["pending_command"] == pending

    restarted = TestClient(create_runtime_app(runtime_root=tmp_path))
    recovered = restarted.get(f"/projects/{project_id}/studio-state")
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["state"]["creator_authoring"]["pending_command"] == pending


def test_creator_state_rejects_truncated_envelope_and_domain_facts(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "creator-state-reject"
    _project(client, project_id)
    route = f"/projects/{project_id}/studio-state"

    truncated = client.put(
        route,
        json={"state": {"creator_authoring": {"pending_command": {"status": "pending"}}}},
    )
    domain_fact = client.put(
        route,
        json={"state": {"creator_authoring": {"episodes": [{"title": "不应写入"}]}}},
    )
    assert truncated.status_code == 400
    assert domain_fact.status_code == 400


def test_studio_state_cas_is_atomic_and_corrupt_state_cannot_be_overwritten(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "creator-state-cas"
    _project(client, project_id)
    route = f"/projects/{project_id}/studio-state"
    creator_ui = {
        "creator_authoring": {
            "mode": "storyboard",
            "selected_episode": "",
            "selected_shot": "",
            "selected_section": f"project:{project_id}",
            "mobile_inspector_open": False,
            "technical_open": False,
            "pending_command": None,
            "pending_failure": "",
        }
    }
    first = client.put(route, json={"expected_version": "", "state": creator_ui})
    assert first.status_code == 200, first.text
    version = first.json()["state_version"]

    stale = client.put(route, json={"expected_version": "", "state": creator_ui})
    current = client.put(route, json={"expected_version": version, "state": creator_ui})
    assert stale.status_code == 409
    assert current.status_code == 200

    state_path = tmp_path / "projects" / project_id / "studio_state.json"
    state_path.write_text('{"state_version":', encoding="utf-8")
    corrupt = client.put(
        route,
        json={"expected_version": current.json()["state_version"], "state": creator_ui},
    )
    assert corrupt.status_code == 409
    assert state_path.read_text(encoding="utf-8") == '{"state_version":'


def test_studio_state_same_version_concurrent_writers_have_one_winner(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "creator-state-double-write"
    _project(client, project_id)
    route = f"/projects/{project_id}/studio-state"
    first = client.put(route, json={"state": {"creator_authoring": {"selected_section": f"project:{project_id}"}}})
    assert first.status_code == 200, first.text
    version = first.json()["state_version"]
    payloads = [
        {"expected_version": version, "state": {"creator_authoring": {"selected_section": f"project:{project_id}", "mode": mode}}}
        for mode in ("storyboard", "canvas")
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda payload: client.put(route, json=payload), payloads))
    assert sorted(response.status_code for response in responses) == [200, 409]


def test_semantically_truncated_pending_envelope_cannot_be_silently_overwritten(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "creator-state-semantic-corrupt"
    _project(client, project_id)
    state_path = tmp_path / "projects" / project_id / "studio_state.json"
    state_path.write_text(
        json.dumps(
            {
                "state_version": "studio_state:corrupt-v1",
                "saved_at": "2026-07-16T00:00:01+00:00",
                "state": {
                    "creator_authoring": {
                        "schema_version": "afs_creator_authoring_ui.v0.1",
                        "selected_section": f"project:{project_id}",
                        "pending_command": {
                            "schema_version": "afs_creator_pending_command.v0.1",
                            "idempotency_key": "truncated-1",
                            "status": "pending",
                        },
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    response = client.put(
        f"/projects/{project_id}/studio-state",
        json={
            "expected_version": "studio_state:corrupt-v1",
            "state": {"creator_authoring": {"selected_section": f"project:{project_id}"}},
        },
    )
    assert response.status_code == 409
    assert "truncated-1" in state_path.read_text(encoding="utf-8")
