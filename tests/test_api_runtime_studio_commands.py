from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_film_production_graph import compile_film_candidate
from apps.api.runtime_production_graph import (
    ProductionGraphStore,
    canonical_digest,
    graph_path,
)
from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_studio_commands import register_runtime_studio_command_routes


def _candidate() -> dict:
    return {
        "schema_version": "afs.film_domain_pack.v0.1",
        "trusted_candidate": True,
        "source_digest": "a" * 64,
        "brief": {"brief_id": "brief-main"},
        "script_revision": {"revision_id": "revision-v1"},
        "sequence": {"sequence_id": "sequence-main", "name": "第一集"},
        "characters": [
            {"character_id": "character-lin", "display_name": "林晚"}
        ],
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


def _client_with_candidate(tmp_path) -> tuple[TestClient, RuntimeStore, dict]:
    store = RuntimeStore(tmp_path)
    store.create_project_manifest(
        project_id="studio-command-project",
        project_type="short_film",
        goal="Studio command preview and receipt",
        status="in_progress",
    )
    graph_store = ProductionGraphStore(store)
    graph = graph_store.append(
        "studio-command-project",
        expected_version=0,
        idempotency_key="confirm-candidate",
        semantic_digest=canonical_digest(_candidate()),
        events=compile_film_candidate("studio-command-project", _candidate()),
    )
    graph = graph_store.append(
        "studio-command-project",
        expected_version=graph["version"],
        idempotency_key="pending-video",
        semantic_digest=canonical_digest({"pending": "shot-001"}),
        events=[
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "video-candidate-001",
                    "category": "artifact",
                    "state": "active",
                    "metadata": {"kind": "video_candidate"},
                },
            },
            {
                "type": "relation_upserted",
                "from_id": "shot-001",
                "to_id": "video-candidate-001",
                "relation_type": "pending_video_candidate",
            },
        ],
    )
    app = FastAPI()
    auth = RuntimeAuthStore(store, env={"AFS_AUTH_ENABLED": "false"})
    register_runtime_studio_command_routes(app, store, auth)
    return TestClient(app), store, graph


def test_studio_rework_preview_is_read_only_and_confirm_creates_planned_task(
    tmp_path,
) -> None:
    client, store, graph = _client_with_candidate(tmp_path)
    path = graph_path(store, "studio-command-project")
    before = path.read_bytes()
    request = {
        "target_entity_id": "shot-001",
        "expected_graph_version": graph["version"],
        "expected_graph_digest": graph["graph_digest"],
    }

    preview_response = client.post(
        "/api/v1/projects/studio-command-project/studio/commands/rework/preview",
        json=request,
    )

    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["status"] == "preview"
    assert preview["requires_confirmation"] is True
    assert preview["provider_dispatch_count"] == 0
    assert set(preview["impact_refs"]) == {
        "delivery-main",
        "video-candidate-001",
    }
    assert path.read_bytes() == before

    confirm_response = client.post(
        "/api/v1/projects/studio-command-project/studio/commands/rework/confirm",
        json={
            **request,
            "preview_id": preview["preview_id"],
            "idempotency_key": "confirm-local-rework",
        },
    )

    assert confirm_response.status_code == 200
    receipt = confirm_response.json()
    assert receipt["dispatch_state"] == "planned_not_dispatched"
    assert receipt["provider_dispatch_count"] == 0
    assert receipt["graph_version"] == graph["version"] + 1
    updated = ProductionGraphStore(store).load("studio-command-project")
    assert updated["work"][receipt["task_id"]]["state"] == "planned"
    assert updated["nodes"]["delivery-main"]["state"] == "invalidated"

    replay = client.post(
        "/api/v1/projects/studio-command-project/studio/commands/rework/confirm",
        json={
            **request,
            "preview_id": preview["preview_id"],
            "idempotency_key": "confirm-local-rework",
        },
    )
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True
    assert replay.json()["receipt_id"] == receipt["receipt_id"]
    assert replay.json()["provider_dispatch_count"] == 0


def test_studio_rework_preview_fails_closed_on_stale_or_invalid_target(
    tmp_path,
) -> None:
    client, _store, graph = _client_with_candidate(tmp_path)

    stale = client.post(
        "/api/v1/projects/studio-command-project/studio/commands/rework/preview",
        json={
            "target_entity_id": "shot-001",
            "expected_graph_version": graph["version"] - 1,
            "expected_graph_digest": graph["graph_digest"],
        },
    )
    invalid = client.post(
        "/api/v1/projects/studio-command-project/studio/commands/rework/preview",
        json={
            "target_entity_id": "delivery-main",
            "expected_graph_version": graph["version"],
            "expected_graph_digest": graph["graph_digest"],
        },
    )

    assert stale.status_code == 409
    assert invalid.status_code == 409


def test_studio_rework_command_openapi_is_typed(tmp_path) -> None:
    client, _store, _graph = _client_with_candidate(tmp_path)

    paths = client.get("/openapi.json").json()["paths"]

    preview = paths[
        "/api/v1/projects/{project_id}/studio/commands/rework/preview"
    ]["post"]
    confirm = paths[
        "/api/v1/projects/{project_id}/studio/commands/rework/confirm"
    ]["post"]
    assert preview["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/StudioReworkPreviewReceipt")
    assert confirm["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/StudioReworkConfirmReceipt")
