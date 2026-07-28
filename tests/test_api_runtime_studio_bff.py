from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.runtime_production_graph import ProductionGraphStore
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore


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
        for surface in (
            "overview",
            "canvas",
            "script",
            "storyboard",
            "asset-bible",
            "review",
            "delivery",
        )
    }

    assert {payload["authority_mode"] for payload in payloads.values()} == {"graph_v1"}
    assert {payload["schema_version"] for payload in payloads.values()} == {
        "afs.studio_bff.v0.2"
    }
    assert {payload["project_version"] for payload in payloads.values()} == {1}
    assert len({payload["graph_digest"] for payload in payloads.values()}) == 1
    assert len({payload["event_cursor"] for payload in payloads.values()}) == 1
    assert all(payload["provider_dispatch_count"] == 0 for payload in payloads.values())
    assert payloads["overview"]["resume_target"]["surface"] == "review"
    assert payloads["overview"]["resume_target"]["entity_id"] == "delivery-main"
    assert payloads["overview"]["agent_summary"]["based_on_project_version"] == 1
    assert {item["entity_type"] for item in payloads["script"]["entities"]} == {"input", "revision"}
    assert "unit" in {item["entity_type"] for item in payloads["storyboard"]["entities"]}
    assert {"entity", "location", "resource"} <= {
        item["entity_type"] for item in payloads["asset-bible"]["entities"]
    }
    assert payloads["review"]["review_queue"][0]["state"] == "pending"
    assert "delivery" in {item["entity_type"] for item in payloads["delivery"]["entities"]}
    assert payloads["delivery"]["cost_summary"]["available"] is False
    assert payloads["delivery"]["delivery_summary"]["state"] == "blocked"
    assert payloads["delivery"]["delivery_summary"]["blocker_count"] == 2
    assert payloads["review"]["rework_preview"]["available"] is False
    assert next(
        item
        for item in payloads["review"]["allowed_actions"]
        if item["action"] == "preview_rework"
    )["enabled"] is False
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
    assert response.json()["event_cursor"] == 0
    assert response.json()["surface_summary"]["state"] == "empty"
    assert response.json()["resume_target"]["available"] is False
    assert response.json()["delivery_summary"]["state"] == "empty"
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

    assert unknown_surface.status_code == 422
    assert missing_project.status_code == 404


def test_studio_bff_recursively_removes_private_metadata_and_refs(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "safe-projection"
    assert client.post(
        "/projects",
        json={"project_id": project_id, "goal": "Safe projection"},
    ).status_code == 200
    graph_store = ProductionGraphStore(RuntimeStore(tmp_path))
    graph_store.append(
        project_id,
        expected_version=0,
        idempotency_key="unsafe-synthetic-input",
        semantic_digest="b" * 64,
        events=[
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "character-safe",
                    "category": "entity",
                    "metadata": {
                        "display_name": "林晚",
                        "lineage": {
                            "source": "creator_input",
                            "api_key": "synthetic-not-a-real-key",
                            "token": "synthetic-secret-token-value",
                            "path": "/opt/afs/AgentFlowStudio/private/asset.png",
                            "sas": "https://blob.example.invalid/a?sv=1&sig=synthetic",
                            "nested": {
                                "signed_url": "https://example.invalid/media?signature=synthetic",
                                "private_path": r"C:\private\asset.png",
                            },
                        },
                    },
                },
            },
            {
                "type": "node_upserted",
                "node": {
                    "node_id": r"C:\private\unsafe-node",
                    "category": "entity",
                    "metadata": {"display_name": "must not project"},
                },
            },
            {
                "type": "review_recorded",
                "review_id": "review-safe",
                "target_id": "character-safe",
                "state": "pending",
                "evidence_refs": ["evidence-safe", r"C:\private\evidence.json"],
            },
        ],
    )

    response = client.get(
        f"/api/v1/projects/{project_id}/studio",
        params={"surface": "canvas"},
    )
    serialized = response.text.lower()

    assert response.status_code == 200
    assert "creator_input" in serialized
    assert "api_key" not in serialized
    assert "signed_url" not in serialized
    assert "signature=" not in serialized
    assert "synthetic-secret-token-value" not in serialized
    assert "/opt/afs/" not in serialized
    assert "sig=" not in serialized
    assert "c:\\\\" not in serialized
    assert "unsafe-node" not in serialized
    assert response.json()["review_queue"][0]["evidence_refs"] == ["evidence-safe"]


def test_studio_bff_openapi_contract_is_typed(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    operation = client.get("/openapi.json").json()["paths"][
        "/api/v1/projects/{project_id}/studio"
    ]["get"]
    surface = next(
        item for item in operation["parameters"]
        if item["name"] == "surface"
    )
    response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]

    assert surface["schema"]["enum"] == [
        "overview",
        "canvas",
        "script",
        "storyboard",
        "asset-bible",
        "review",
        "delivery",
    ]
    assert response_schema["$ref"].endswith("/StudioSurfaceEnvelope")
