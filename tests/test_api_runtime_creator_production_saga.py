from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from apps.api.runtime_episode_bootstrap import BOOTSTRAP_EPISODE_ID, BOOTSTRAP_EPISODE_VERSION_ID
from apps.api.runtime_episode_domain_contract import ProductionProjectAggregate
from apps.api.runtime_episode_domain_store import EpisodeDomainAggregateStore
from apps.api.runtime_service import create_runtime_app


PROJECT_ID = "creator-production-saga"


def _client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_AUTH_ALLOW_OPEN_SIGNUP", "true")
    return TestClient(create_runtime_app(runtime_root=tmp_path))


def _register(client: TestClient, email: str) -> dict[str, Any]:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "strong-password-123",
            "display_name": email.split("@", 1)[0],
            "invite_code": "",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _headers(session: dict[str, Any], key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {session['session_token']}"}
    if key:
        headers["Idempotency-Key"] = key
    return headers


def _create_project(client: TestClient, headers: dict[str, str], project_id: str = PROJECT_ID) -> None:
    response = client.post(
        "/projects",
        headers=headers,
        json={
            "project_id": project_id,
            "project_type": "studio_episode_production",
            "goal": "Creator production saga",
        },
    )
    assert response.status_code == 200, response.text


def _workspace(client: TestClient, headers: dict[str, str], project_id: str = PROJECT_ID) -> dict[str, Any]:
    response = client.get(
        f"/projects/{project_id}/episodes/{BOOTSTRAP_EPISODE_ID}/versions/{BOOTSTRAP_EPISODE_VERSION_ID}/workspace",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _request_body(workspace: dict[str, Any], shot_index: int = 0) -> dict[str, Any]:
    shot_ref = workspace["workspace"]["shots"][shot_index]["ref"]
    return {
        "expected_aggregate_version": workspace["aggregate"]["aggregate_version"],
        "episode_ref": workspace["workspace"]["episode_ref"],
        "shot_ref": shot_ref,
        "scope": "production_preview",
        "expected_versions": {
            "episode": workspace["workspace"]["episode_ref"]["version_id"],
            "shot": shot_ref["version_id"],
        },
    }


def _post_request(
    client: TestClient,
    headers: dict[str, str],
    body: dict[str, Any],
    key: str,
    *,
    crash_after: str | None = None,
    project_id: str = PROJECT_ID,
):
    request_headers = _headers({"session_token": headers["Authorization"].removeprefix("Bearer ")}, key)
    if crash_after:
        request_headers["X-AFS-Crash-After"] = crash_after
    return client.post(
        f"/projects/{project_id}/creator-production-requests",
        headers=request_headers,
        json=body,
    )


def _candidate_entities(tmp_path: Path, owner: dict[str, Any], project_id: str = PROJECT_ID) -> list[str]:
    aggregate = EpisodeDomainAggregateStore(tmp_path).load(
        org_id=owner["user"]["user_id"],
        project_id=project_id,
    )
    return sorted(item.entity_id for item in aggregate.asset_candidates)


def test_creator_production_request_replays_once_and_restores_workspace(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    owner = _register(client, "owner@example.com")
    headers = _headers(owner)
    _create_project(client, headers)
    workspace = _workspace(client, headers)
    body = _request_body(workspace)

    created = _post_request(client, headers, body, "preview-1")
    assert created.status_code == 200, created.text
    request = created.json()["request"]
    assert request["status"] == "done"
    assert request["status_label"] == "制作完成"
    assert request["task"]["state"] == "completed"
    assert request["run"]["state"] == "completed"
    assert request["attempt"]["state"] == "completed"
    assert request["receipt"]["episode_confirmed"] is True
    assert request["provider_dispatch_count"] == 0

    replay = _post_request(client, headers, body, "preview-1")
    assert replay.status_code == 200, replay.text
    assert replay.json()["request"]["receipt"]["receipt_id"] == request["receipt"]["receipt_id"]
    assert _candidate_entities(tmp_path, owner).count(request["candidate_ref"]["entity_id"]) == 1

    readback = _workspace(client, headers)
    shot = readback["workspace"]["shots"][0]
    assert shot["production_request"]["status_label"] == "制作完成"
    assert shot["candidates"][0]["ref"] == request["candidate_ref"]
    assert shot["candidates"][0]["artifact_present"] is True
    assert readback["workspace"]["creator_production"]["provider_dispatch_count"] == 0


def test_creator_production_crash_matrix_reconciles_exactly_once(tmp_path: Path, monkeypatch) -> None:
    crash_points = ["prepared", "artifact_prepared", "control_applied", "episode_applied", "before_confirmed"]
    for index, crash_point in enumerate(crash_points, start=1):
        root = tmp_path / crash_point
        client = _client(root, monkeypatch)
        owner = _register(client, f"owner-{index}@example.com")
        headers = _headers(owner)
        project_id = f"{PROJECT_ID}-{index}"
        _create_project(client, headers, project_id=project_id)
        workspace = _workspace(client, headers, project_id=project_id)
        body = _request_body(workspace)

        crashed = _post_request(
            client,
            headers,
            body,
            f"preview-{index}",
            crash_after=crash_point,
            project_id=project_id,
        )
        assert crashed.status_code == 500
        assert crashed.json()["detail"]["error"] == "creator_production_injected_crash"

        restarted = TestClient(create_runtime_app(runtime_root=root))
        recovered = restarted.get(
            f"/projects/{project_id}/creator-production-requests",
            headers=headers,
        )
        assert recovered.status_code == 200, recovered.text
        requests = recovered.json()["requests"]
        assert len(requests) == 1
        assert requests[0]["status"] == "done"
        assert requests[0]["receipt"]["episode_confirmed"] is True
        assert _candidate_entities(root, owner, project_id=project_id).count(
            requests[0]["candidate_ref"]["entity_id"]
        ) == 1


def test_creator_production_same_key_replay_after_episode_apply_response_failure_is_once(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client(tmp_path, monkeypatch)
    owner = _register(client, "owner@example.com")
    headers = _headers(owner)
    _create_project(client, headers)
    workspace = _workspace(client, headers)
    body = _request_body(workspace)

    crashed = _post_request(client, headers, body, "preview-1", crash_after="before_confirmed")
    assert crashed.status_code == 500

    replay = _post_request(client, headers, body, "preview-1")
    assert replay.status_code == 200, replay.text
    request = replay.json()["request"]
    assert request["status"] == "done"
    assert request["receipt"]["episode_confirmed"] is True
    assert _candidate_entities(tmp_path, owner).count(request["candidate_ref"]["entity_id"]) == 1


def test_creator_production_protected_shot_stale_before_episode_apply_fails_closed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client(tmp_path, monkeypatch)
    owner = _register(client, "owner@example.com")
    headers = _headers(owner)
    _create_project(client, headers)
    workspace = _workspace(client, headers)
    body = _request_body(workspace, shot_index=0)

    crashed = _post_request(client, headers, body, "preview-1", crash_after="control_applied")
    assert crashed.status_code == 500
    _revise_shot_directly(tmp_path, owner, shot_index=1)

    reconcile = client.get(f"/projects/{PROJECT_ID}/creator-production-requests", headers=headers)
    assert reconcile.status_code == 200, reconcile.text
    request = reconcile.json()["requests"][0]
    assert request["status"] == "failed"
    assert request["candidate_ref"] is None
    assert _candidate_entities(tmp_path, owner) == []


def test_creator_production_rejects_conflict_stale_foreign_and_corrupt_saga(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client(tmp_path, monkeypatch)
    owner = _register(client, "owner@example.com")
    other = _register(client, "other@example.com")
    headers = _headers(owner)
    _create_project(client, headers)
    workspace = _workspace(client, headers)
    body = _request_body(workspace)
    assert _post_request(client, headers, body, "preview-1").status_code == 200

    conflict = _post_request(
        client,
        headers,
        {**body, "scope": "production_preview", "expected_versions": {"shot": "different-version"}},
        "preview-1",
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["error"] == "creator_production_idempotency_conflict"

    stale = _post_request(
        client,
        headers,
        {**body, "expected_aggregate_version": body["expected_aggregate_version"]},
        "preview-2",
    )
    assert stale.status_code == 409

    foreign = client.get(f"/projects/{PROJECT_ID}/creator-production-requests", headers=_headers(other))
    assert foreign.status_code == 403

    saga_path = tmp_path / "projects" / PROJECT_ID / "creator_production_saga" / "saga.json"
    payload = json.loads(saga_path.read_text(encoding="utf-8"))
    payload["envelopes"] = payload["envelopes"][:-1]
    saga_path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    corrupt = client.get(f"/projects/{PROJECT_ID}/creator-production-requests", headers=headers)
    assert corrupt.status_code == 500
    assert corrupt.json()["detail"]["error"] == "creator_production_saga_integrity_failed"


def _revise_shot_directly(tmp_path: Path, owner: dict[str, Any], *, shot_index: int) -> None:
    store = EpisodeDomainAggregateStore(tmp_path)
    aggregate = store.load(org_id=owner["user"]["user_id"], project_id=PROJECT_ID)
    current = sorted(
        (item for item in aggregate.shots if item.scene_ref.entity_id == "scene-001"),
        key=lambda item: item.sequence,
    )[shot_index]
    payload = current.model_dump(mode="python")
    payload.update(
        {
            "version_id": f"{current.entity_id}-direct-v2",
            "revision": current.revision + 1,
            "parent_version_id": current.version_id,
            "title": f"{current.title} revised",
            "created_at": "2026-07-16T00:00:01+00:00",
            "content_digest": _digest({"shot": current.entity_id, "version": "direct-v2"}),
        }
    )
    successor = type(current).model_validate(payload)
    aggregate_payload = aggregate.model_dump(mode="python")
    aggregate_payload.update(
        {
            "aggregate_version": aggregate.aggregate_version + 1,
            "evaluated_at": "2026-07-16T00:00:01+00:00",
            "shots": (*aggregate.shots, successor),
        }
    )
    updated = ProductionProjectAggregate.model_validate(aggregate_payload)
    store.save(
        updated,
        expected_aggregate_version=aggregate.aggregate_version,
        idempotency_key="direct-protected-shot-revision",
        payload_digest=_digest(successor.model_dump(mode="json")),
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
