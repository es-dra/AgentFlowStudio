from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from agentflow_studio.production.vertical_slice import CharacterSeed, DeterministicProductionSlice, ProjectIP
from apps.api.runtime_production_models import canonical_json_digest
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


def _create_run(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.post(
        "/projects/owned-project/production-runs",
        json=_create_payload(),
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["production_run"]


def _creator_decision(run: dict, **updates) -> dict:
    candidate = run["candidates"][0]
    payload = {
        "schema_version": "afs_creator_decision.v0.1",
        "decision_id": "decision-001",
        "idempotency_key": "creator-decision-001",
        "expected_checkpoint_version": run["checkpoint"]["version"],
        "subject_digest": run["subject_digest"],
        "decision": "select",
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["canonical_digest"],
        "parent_revision_id": None,
        "revision_intent": "Select the clarity-first treatment without content changes.",
    }
    return {**payload, **updates}


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
    assert created.json()["studio_binding"] == {
        "schema_version": "afs_studio_production_binding.v0.1",
        "authoritative_source": "runtime_production_run",
        "compatibility_mode": "backend_authoritative_summary_only",
        "active_run_id": "production-run-001",
        "checkpoint_version": 1,
        "checkpoint_digest": run["checkpoint"]["state_digest"],
        "subject_digest": run["subject_digest"],
    }
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


def test_creator_decision_enforces_checkpoint_subject_candidate_and_idempotency(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    run = _create_run(client, headers)
    route = "/projects/owned-project/production-runs/production-run-001/creator-decisions"

    stale = client.post(route, json=_creator_decision(run, expected_checkpoint_version=2), headers=headers)
    changed_subject = client.post(route, json=_creator_decision(run, subject_digest=_digest("changed")), headers=headers)
    changed_candidate = client.post(route, json=_creator_decision(run, candidate_digest=_digest("changed")), headers=headers)
    selected = client.post(route, json=_creator_decision(run), headers=headers)
    replayed = client.post(route, json=_creator_decision(run), headers=headers)
    idempotency_conflict = client.post(
        route,
        json=_creator_decision(run, revision_intent="A changed request with a reused key."),
        headers=headers,
    )

    assert stale.status_code == 409
    assert stale.json()["detail"]["error"] == "stale_production_checkpoint"
    assert changed_subject.status_code == 409
    assert "subject digest changed" in changed_subject.text
    assert changed_candidate.status_code == 409
    assert "candidate digest changed" in changed_candidate.text
    assert selected.status_code == 200, selected.text
    selected_run = selected.json()["production_run"]
    revision = selected_run["selected_revision"]
    assert selected_run["checkpoint"]["version"] == 2
    assert selected_run["checkpoint"]["previous_digest"] == run["checkpoint"]["state_digest"]
    assert revision["candidate_id"] == run["candidates"][0]["candidate_id"]
    assert revision["candidate_digest"] == run["candidates"][0]["canonical_digest"]
    assert revision["creator_decision_id"] == "decision-001"
    assert revision["parent_job_id"] == "job-keyframe-001"
    assert len(revision["canonical_digest"]) == 64
    assert len(revision["subject_digest"]) == 64
    assert replayed.status_code == 200
    assert replayed.json()["idempotent_replay"] is True
    assert replayed.json()["production_run"] == selected_run
    assert idempotency_conflict.status_code == 409
    assert "idempotency conflict" in idempotency_conflict.text


def test_selected_revision_lineage_supports_creator_revision_and_reload_recovery(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    run = _create_run(client, headers)
    route = "/projects/owned-project/production-runs/production-run-001/creator-decisions"
    selected = client.post(route, json=_creator_decision(run), headers=headers).json()["production_run"]
    first_revision = selected["selected_revision"]
    revised_payload = _creator_decision(
        selected,
        decision_id="decision-002",
        idempotency_key="creator-decision-002",
        decision="revise",
        parent_revision_id=first_revision["revision_id"],
        revision_intent="Keep the chosen composition and strengthen the character reaction.",
    )

    revised_response = client.post(route, json=revised_payload, headers=headers)

    assert revised_response.status_code == 200, revised_response.text
    revised = revised_response.json()["production_run"]
    second_revision = revised["selected_revision"]
    assert revised["checkpoint"]["version"] == 3
    assert second_revision["parent_revision_id"] == first_revision["revision_id"]
    assert second_revision["revision_id"] != first_revision["revision_id"]
    assert {
        "source_ref": first_revision["revision_id"],
        "target_ref": second_revision["revision_id"],
        "relation": "revision_revised_to_revision",
    } in revised["lineage"]

    restarted_client = TestClient(create_runtime_app(runtime_root=tmp_path))
    recovered = restarted_client.get(
        "/projects/owned-project/production-runs/production-run-001",
        headers=headers,
    )
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["production_run"] == revised


def test_quality_review_and_export_bind_selected_revision_with_hash_readback(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    created = _create_run(client, headers)
    decision_route = "/projects/owned-project/production-runs/production-run-001/creator-decisions"
    selected = client.post(decision_route, json=_creator_decision(created), headers=headers).json()["production_run"]
    revision = selected["selected_revision"]
    review_payload = {
        "schema_version": "afs_production_quality_review.v0.1",
        "review_id": "quality-review-001",
        "idempotency_key": "quality-review-001",
        "expected_checkpoint_version": selected["checkpoint"]["version"],
        "reviewed_subject_digest": revision["subject_digest"],
        "selected_revision_id": revision["revision_id"],
        "selected_revision_digest": revision["canonical_digest"],
        "decision": "approve",
        "checklist": {
            "story_intent_preserved": True,
            "character_continuity_checked": True,
            "shot_coverage_checked": True,
            "revision_addressed": True,
        },
        "note": "Deterministic contract review only; not human acceptance.",
    }
    review_route = "/projects/owned-project/production-runs/production-run-001/quality-reviews"
    reviewed_response = client.post(review_route, json=review_payload, headers=headers)
    assert reviewed_response.status_code == 200, reviewed_response.text
    reviewed = reviewed_response.json()["production_run"]
    assert reviewed["checkpoint"]["version"] == 3
    assert reviewed["quality_reviews"][-1]["human_acceptance_claimed"] is False

    export_payload = {
        "schema_version": "afs_production_export.v0.1",
        "export_id": "export-001",
        "idempotency_key": "export-001",
        "expected_checkpoint_version": reviewed["checkpoint"]["version"],
        "selected_revision_id": revision["revision_id"],
        "selected_revision_digest": revision["canonical_digest"],
    }
    export_route = "/projects/owned-project/production-runs/production-run-001/exports"
    changed_export = client.post(
        export_route,
        json={**export_payload, "selected_revision_digest": _digest("changed")},
        headers=headers,
    )
    exported_response = client.post(export_route, json=export_payload, headers=headers)
    replayed = client.post(export_route, json=export_payload, headers=headers)

    assert changed_export.status_code == 409
    assert exported_response.status_code == 200, exported_response.text
    exported = exported_response.json()
    run = exported["production_run"]
    export = exported["export"]
    assert run["status"] == "exported"
    assert run["checkpoint"]["version"] == 4
    assert export["selected_revision_id"] == revision["revision_id"]
    assert export["selected_revision_digest"] == revision["canonical_digest"]
    assert len(export["delivery_sha256"]) == 64
    assert exported["studio_binding"]["last_export_id"] == "export-001"
    assert exported["studio_binding"]["selected_revision_id"] == revision["revision_id"]
    assert replayed.status_code == 200
    assert replayed.json()["idempotent_replay"] is True
    assert replayed.json()["export"] == export

    artifact = client.get(f"/artifacts/{export['artifact']['artifact_id']}", headers=headers)
    assert artifact.status_code == 200, artifact.text
    delivery = artifact.json()["payload"]
    assert delivery["selected_revision"]["revision_id"] == revision["revision_id"]
    assert delivery["selected_revision"]["canonical_digest"] == revision["canonical_digest"]
    assert delivery["quality_review_ref"] == "quality-review-001"
    delivery_path = (
        tmp_path
        / "projects"
        / "owned-project"
        / "production_runs"
        / "production-run-001"
        / "exports"
        / "export-001"
        / "production_delivery.json"
    )
    assert hashlib.sha256(delivery_path.read_bytes()).hexdigest() == export["delivery_sha256"]

    restarted_client = TestClient(create_runtime_app(runtime_root=tmp_path))
    recovered = restarted_client.get(
        "/projects/owned-project/production-runs/production-run-001",
        headers=headers,
    )
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["production_run"]["exports"] == [export]

    delivery_path.write_text(json.dumps({**delivery, "quality_review_ref": "tampered"}), encoding="utf-8")
    tampered_readback = restarted_client.get(
        "/projects/owned-project/production-runs/production-run-001",
        headers=headers,
    )
    assert tampered_readback.status_code == 409
    assert "export artifact integrity mismatch" in tampered_readback.text


def test_checkpoint_tampering_fails_closed_on_readback(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    _create_run(client, headers)
    state_path = (
        tmp_path / "projects" / "owned-project" / "production_runs" / "production-run-001" / "production_run.json"
    )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["subject_digest"] = _digest("tampered")
    state_path.write_text(json.dumps(state), encoding="utf-8")

    response = client.get(
        "/projects/owned-project/production-runs/production-run-001",
        headers=headers,
    )

    assert response.status_code == 409
    assert "checkpoint integrity mismatch" in response.text


def test_pr127_deterministic_candidates_bridge_into_authenticated_project_run(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path / "runtime", monkeypatch)
    project = ProjectIP(
        project_id="owned-project",
        title="Deterministic bridge",
        premise="A creator compares governed shot treatments.",
        audience="internal creator",
        format="short-form storyboard",
        tone="cinematic",
        characters=[
            CharacterSeed(
                character_id="hero-001",
                name="Hero",
                role="lead",
                visual_anchor="red scarf and dark jacket",
            )
        ],
    )
    deterministic = DeterministicProductionSlice(project, tmp_path / "deterministic")
    deterministic.advance_to_candidates()
    candidates = deterministic.state["artifacts"]["candidates"]
    payload = {
        "schema_version": "afs_runtime_production_run.v0.1",
        "run_id": "production-run-pr127-bridge",
        "idempotency_key": "create-pr127-bridge",
        "subject_digest": canonical_json_digest(project.model_dump(mode="json")),
        "candidates": [
            {
                "candidate_id": item["candidate_id"],
                "canonical_digest": canonical_json_digest(item),
                "parent_job_id": deterministic.state["run_id"],
                "shot_id": item["shot_id"],
                "safe_artifact_refs": [],
            }
            for item in candidates
        ],
    }

    created = client.post(
        "/projects/owned-project/production-runs",
        json=payload,
        headers=headers,
    )

    assert created.status_code == 200, created.text
    run = created.json()["production_run"]
    assert len(run["candidates"]) == 6
    assert {item["shot_id"] for item in run["candidates"]} == {"shot_001", "shot_002", "shot_003"}
    assert all(item["parent_job_id"] == deterministic.state["run_id"] for item in run["candidates"])


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
