from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


REPO_ROOT = Path(__file__).resolve().parents[1]


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _registered_client(tmp_path, monkeypatch):
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_AUTH_ALLOW_OPEN_SIGNUP", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    registered = client.post(
        "/auth/register",
        json={
            "email": "creator@example.com",
            "password": "strong-password-123",
            "display_name": "Creator",
        },
    )
    assert registered.status_code == 200, registered.text
    headers = {"Authorization": f"Bearer {registered.json()['session_token']}"}
    created = client.post(
        "/projects",
        json={"project_id": "owned-project", "goal": "Authenticated production lifecycle"},
        headers=headers,
    )
    assert created.status_code == 200, created.text
    return client, headers


def _create_payload() -> dict:
    return {
        "schema_version": "afs_runtime_production_run.v0.1",
        "run_id": "production-run-001",
        "idempotency_key": "create-production-run-001",
        "subject_digest": _digest("project-subject-v1"),
        "candidates": [
            {
                "candidate_id": "candidate-001",
                "canonical_digest": _digest("candidate-one"),
                "parent_job_id": "job-keyframe-001",
                "shot_id": "shot-001",
                "safe_artifact_refs": [
                    {
                        "artifact_id": "artifact-candidate-001",
                        "artifact_type": "candidate-manifest",
                        "role": "candidate_manifest",
                        "media_type": "application/json",
                    }
                ],
            },
            {
                "candidate_id": "candidate-002",
                "canonical_digest": _digest("candidate-two"),
                "parent_job_id": "job-keyframe-001",
                "shot_id": "shot-001",
                "safe_artifact_refs": [],
            },
        ],
    }


def test_production_run_requires_authenticated_project_owner(tmp_path, monkeypatch) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post("/projects", json={"project_id": "local-project", "goal": "Local dev project"})

    response = client.post("/projects/local-project/production-runs", json=_create_payload())

    assert response.status_code == 403
    assert "runtime auth" in response.text

    owner_client, owner_headers = _registered_client(tmp_path / "authenticated", monkeypatch)
    other = owner_client.post(
        "/auth/register",
        json={
            "email": "other@example.com",
            "password": "strong-password-456",
            "display_name": "Other",
        },
    )
    other_headers = {"Authorization": f"Bearer {other.json()['session_token']}"}

    created = owner_client.post(
        "/projects/owned-project/production-runs",
        json=_create_payload(),
        headers=owner_headers,
    )
    denied = owner_client.get(
        "/projects/owned-project/production-runs/production-run-001",
        headers=other_headers,
    )

    assert created.status_code == 200, created.text
    assert denied.status_code == 403


def test_create_list_get_and_idempotent_replay_persist_checkpoint(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    payload = _create_payload()

    created = client.post(
        "/projects/owned-project/production-runs",
        json=payload,
        headers=headers,
    )
    replayed = client.post(
        "/projects/owned-project/production-runs",
        json=payload,
        headers=headers,
    )
    listed = client.get("/projects/owned-project/production-runs", headers=headers)
    loaded = client.get(
        "/projects/owned-project/production-runs/production-run-001",
        headers=headers,
    )

    assert created.status_code == 200, created.text
    assert created.json()["idempotent_replay"] is False
    run = created.json()["production_run"]
    assert run["project_id"] == "owned-project"
    assert run["run_id"] == "production-run-001"
    assert run["status"] == "candidates_ready"
    assert run["subject_digest"] == payload["subject_digest"]
    assert run["candidates"][0]["canonical_digest"] == payload["candidates"][0]["canonical_digest"]
    assert run["selected_revision"] is None
    assert run["checkpoint"]["schema_version"] == "afs_runtime_production_checkpoint.v0.1"
    assert run["checkpoint"]["version"] == 1
    assert len(run["checkpoint"]["state_digest"]) == 64
    assert replayed.status_code == 200
    assert replayed.json()["idempotent_replay"] is True
    assert replayed.json()["production_run"] == run
    assert [item["run_id"] for item in listed.json()["production_runs"]] == ["production-run-001"]
    assert loaded.json()["production_run"] == run

    persisted = json.loads(
        (tmp_path / "projects" / "owned-project" / "production_runs" / "production-run-001" / "production_run.json")
        .read_text(encoding="utf-8")
    )
    assert persisted == run
    manifest = json.loads(
        (tmp_path / "projects" / "owned-project" / "project_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["runs"] == [
        {
            "run_id": "production-run-001",
            "artifact_type": "afs_runtime_production_run",
            "schema_version": "afs_runtime_production_run.v0.1",
            "status": "candidates_ready",
        }
    ]


def test_create_idempotency_key_rejects_changed_subject(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    payload = _create_payload()
    assert client.post(
        "/projects/owned-project/production-runs",
        json=payload,
        headers=headers,
    ).status_code == 200
    payload["subject_digest"] = _digest("changed-subject")

    conflict = client.post(
        "/projects/owned-project/production-runs",
        json=payload,
        headers=headers,
    )

    assert conflict.status_code == 409
    assert "idempotency conflict" in conflict.text


def test_studio_state_keeps_only_backend_authoritative_production_binding(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-production-binding"
    client.post("/projects", json={"project_id": project_id, "goal": "Production binding"})
    digest = _digest("binding")

    response = client.put(
        f"/projects/{project_id}/studio-state",
        json={
            "state": {
                "production": {
                    "schema_version": "client-invented-version",
                    "authoritative_source": "client",
                    "compatibility_mode": "client_can_overwrite",
                    "active_run_id": "production-run-001",
                    "checkpoint_version": 4,
                    "checkpoint_digest": digest,
                    "subject_digest": digest,
                    "selected_candidate_id": "candidate-001",
                    "selected_candidate_digest": digest,
                    "selected_revision_id": "revision-001",
                    "selected_revision_digest": digest,
                    "last_export_id": "export-001",
                    "provider_response": "must not persist",
                }
            }
        },
    )

    assert response.status_code == 200, response.text
    binding = response.json()["state"]["production"]
    assert binding == {
        "schema_version": "afs_studio_production_binding.v0.1",
        "authoritative_source": "runtime_production_run",
        "compatibility_mode": "backend_authoritative_summary_only",
        "active_run_id": "production-run-001",
        "checkpoint_version": 4,
        "checkpoint_digest": digest,
        "subject_digest": digest,
        "selected_candidate_id": "candidate-001",
        "selected_candidate_digest": digest,
        "selected_revision_id": "revision-001",
        "selected_revision_digest": digest,
        "last_export_id": "export-001",
    }
    assert "provider_response" not in json.dumps(binding)


def test_studio_client_and_store_expose_frozen_production_contract() -> None:
    runtime_client = (REPO_ROOT / "apps" / "studio" / "src" / "runtime-client.js").read_text(encoding="utf-8")
    store_state = (REPO_ROOT / "apps" / "studio" / "src" / "store-state.js").read_text(encoding="utf-8")

    for method in (
        "createProductionRun",
        "listProductionRuns",
        "getProductionRun",
        "submitCreatorDecision",
        "recordProductionQualityReview",
        "exportProductionRun",
    ):
        assert f"{method}(" in runtime_client
    assert 'authoritative_source: "runtime_production_run"' in store_state
    assert 'compatibility_mode: "backend_authoritative_summary_only"' in store_state
