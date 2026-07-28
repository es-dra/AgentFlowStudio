from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def _candidate() -> dict:
    return {
        "schema_version": "afs.film_domain_pack.v0.1",
        "trusted_candidate": True,
        "source_digest": "a" * 64,
        "brief": {"brief_id": "brief-main"},
        "script_revision": {"revision_id": "revision-v1"},
        "sequence": {"sequence_id": "sequence-main", "name": "第一集"},
        "characters": [{"character_id": "character-lin", "display_name": "林晚"}],
        "scenes": [{"scene_id": "scene-rooftop", "name": "屋顶"}],
        "assets": [{"asset_id": "prop-letter", "name": "旧信", "kind": "prop"}],
        "shots": [
            {
                "shot_id": "shot-001",
                "scene_id": "scene-rooftop",
                "character_refs": ["character-lin"],
                "asset_refs": ["prop-letter"],
                "duration_seconds": 6,
                "intent": "林晚打开旧信。",
            }
        ],
        "delivery_id": "delivery-main",
    }


def _client_with_graph(tmp_path) -> tuple[TestClient, str]:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-bff-project"
    created = client.post(
        "/projects",
        json={"project_id": project_id, "goal": "Studio BFF real project projection"},
    )
    assert created.status_code == 200
    confirmed = client.post(
        f"/projects/{project_id}/m4/film-candidates/confirm",
        json={
            "expected_graph_version": 0,
            "idempotency_key": "confirm-bff",
            "candidate": _candidate(),
        },
    )
    assert confirmed.status_code == 200
    return client, project_id


def test_studio_bff_surfaces_share_one_graph_version_and_digest(tmp_path) -> None:
    client, project_id = _client_with_graph(tmp_path)
    payloads = {
        surface: client.get(
            f"/api/v1/projects/{project_id}/studio",
            params={"surface": surface},
        ).json()
        for surface in ("canvas", "script", "storyboard", "asset-bible", "review", "delivery")
    }

    assert {payload["authority_mode"] for payload in payloads.values()} == {"graph_v1"}
    assert {payload["project_version"] for payload in payloads.values()} == {1}
    assert len({payload["graph_digest"] for payload in payloads.values()}) == 1
    assert all(payload["provider_dispatch_count"] == 0 for payload in payloads.values())
    assert {item["entity_type"] for item in payloads["script"]["entities"]} == {"input", "revision"}
    assert "unit" in {item["entity_type"] for item in payloads["storyboard"]["entities"]}
    assert {"entity", "location", "resource"} <= {
        item["entity_type"] for item in payloads["asset-bible"]["entities"]
    }
    assert payloads["review"]["review_queue"][0]["state"] == "pending"
    assert "delivery" in {item["entity_type"] for item in payloads["delivery"]["entities"]}
    assert payloads["delivery"]["cost_summary"]["available"] is False
    assert payloads["canvas"]["recovery_summary"]["safe_to_repeat_provider_dispatch"] is False


def test_studio_bff_defaults_to_canvas(tmp_path) -> None:
    client, project_id = _client_with_graph(tmp_path)

    response = client.get(f"/api/v1/projects/{project_id}/studio")

    assert response.status_code == 200
    assert response.json()["surface"] == "canvas"


def test_studio_bff_read_does_not_mutate_graph(tmp_path) -> None:
    client, project_id = _client_with_graph(tmp_path)
    path = tmp_path / "projects" / project_id / "production_graph" / "graph.json"
    before = path.read_bytes()

    response = client.get(
        f"/api/v1/projects/{project_id}/studio",
        params={"surface": "canvas"},
    )

    assert response.status_code == 200
    assert path.read_bytes() == before


def test_studio_bff_legacy_project_is_explicit_and_does_not_create_graph(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "legacy-project"
    assert client.post(
        "/projects",
        json={"project_id": project_id, "goal": "Legacy project"},
    ).status_code == 200
    path = tmp_path / "projects" / project_id / "production_graph" / "graph.json"

    response = client.get(
        f"/api/v1/projects/{project_id}/studio",
        params={"surface": "canvas"},
    )

    assert response.status_code == 200
    assert response.json()["authority_mode"] == "legacy_file"
    assert response.json()["entities"] == []
    assert path.exists() is False


def test_studio_bff_rejects_unknown_surface_and_missing_project(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    assert client.post(
        "/projects",
        json={"project_id": "known", "goal": "Known project"},
    ).status_code == 200

    unknown_surface = client.get(
        "/api/v1/projects/known/studio",
        params={"surface": "nodes"},
    )
    missing_project = client.get(
        "/api/v1/projects/missing/studio",
        params={"surface": "canvas"},
    )

    assert unknown_surface.status_code == 404
    assert missing_project.status_code == 404
