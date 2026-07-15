from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from apps.api import runtime_creator_golden_trial
from apps.api.runtime_service import create_runtime_app


STAMP = "2026-07-15T09:00:00+00:00"


def test_creator_golden_trial_dispatch_writes_episode_candidate_and_replays_without_duplicate_provider(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client(tmp_path, monkeypatch)
    owner = _register(client, "owner@example.com")
    headers = _headers(owner)
    _create_project(client, headers, "golden-trial")
    calls: list[str] = []

    def fake_dispatch(*_args, shot_id: str, provider_attempt_id: str, **_kwargs):
        calls.append(shot_id)
        digest = hashlib.sha256(f"{shot_id}:{provider_attempt_id}".encode("utf-8")).hexdigest()
        return {
            "status": "succeeded",
            "job_id": f"fake-job-{shot_id}",
            "provider_gate": {"status": "ready", "required_gate": "AFS_ALLOW_REMOTE_IMAGE"},
            "provider_calls_started": True,
            "safe_manifest": {"status": "succeeded", "provider_raw_response_stored": False},
            "candidate_previews": [
                {
                    "candidate_id": "candidate_001",
                    "preview_url": f"/projects/golden-trial/keyframe-generations/fake-job-{shot_id}/candidates/candidate_001/preview",
                    "byte_count": 68,
                    "sha256": digest,
                    "width": 1,
                    "height": 1,
                    "aspect_ratio": "1:1",
                }
            ],
            "selected_artifact_ref": {
                "artifact_id": f"fake-artifact-{shot_id}",
                "artifact_type": "image_keyframe",
                "content_digest": digest,
            },
        }

    monkeypatch.setattr(runtime_creator_golden_trial, "_dispatch_image_keyframe", fake_dispatch)

    mission = _post(
        client,
        "/projects/golden-trial/creator-golden-trial/mission",
        headers,
        "mission-1",
        _mission(project_ceiling_amount=1.0, estimated_unit_cost_amount=0.1),
    )
    assert mission.status_code == 200, mission.text
    assert mission.json()["trial"]["status"] == "planned"

    approve = _post(
        client,
        "/projects/golden-trial/creator-golden-trial/approve",
        headers,
        "approve-1",
        {"expected_event_count": mission.json()["trial"]["event_count"], "created_at": STAMP},
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["trial"]["status"] == "approved"

    body = {
        "expected_event_count": approve.json()["trial"]["event_count"],
        "provider_service_id": "image_relay",
        "estimated_cost_amount": 0.1,
        "generated_at": STAMP,
    }
    dispatch = _post(
        client,
        "/projects/golden-trial/creator-golden-trial/dispatch-next",
        headers,
        "dispatch-1",
        body,
    )
    assert dispatch.status_code == 200, dispatch.text
    payload = dispatch.json()
    assert payload["provider_calls_started"] is True
    assert payload["receipt"]["episode_writeback"]["status"] == "written"
    assert payload["trial"]["dispatches"]["shot-001"]["episode_writeback"]["human_review_state"] == "needs_review"
    assert calls == ["shot-001"]

    replay = _post(
        client,
        "/projects/golden-trial/creator-golden-trial/dispatch-next",
        headers,
        "dispatch-1",
        {**body, "generated_at": "2026-07-15T09:00:01+00:00"},
    )
    assert replay.status_code == 200, replay.text
    assert replay.json() == payload
    assert calls == ["shot-001"]

    changed = _post(
        client,
        "/projects/golden-trial/creator-golden-trial/dispatch-next",
        headers,
        "dispatch-1",
        {**body, "provider_service_id": "different-image"},
    )
    assert changed.status_code == 409
    assert changed.json()["detail"]["error"] == "creator_golden_trial_idempotency_conflict"

    aggregate = client.get("/projects/golden-trial/episode-production-aggregate", headers=headers)
    assert aggregate.status_code == 200, aggregate.text
    candidates = aggregate.json()["aggregate"]["asset_candidates"]
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["target_ref"]["entity_id"] == "shot-001"
    assert candidate["artifact_ref"]["artifact_type"] == "image_keyframe"
    assert candidate["job_state"] == "succeeded"
    assert candidate["review_state"] == "needs_review"


def test_creator_golden_trial_budget_ceiling_blocks_without_provider_call(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client(tmp_path, monkeypatch)
    owner = _register(client, "budget-owner@example.com")
    headers = _headers(owner)
    _create_project(client, headers, "golden-budget")

    def fail_dispatch(*_args, **_kwargs):
        raise AssertionError("budget ceiling must block before provider dispatch")

    monkeypatch.setattr(runtime_creator_golden_trial, "_dispatch_image_keyframe", fail_dispatch)
    mission = _post(
        client,
        "/projects/golden-budget/creator-golden-trial/mission",
        headers,
        "mission-1",
        _mission(project_ceiling_amount=0.05, estimated_unit_cost_amount=0.1),
    )
    approve = _post(
        client,
        "/projects/golden-budget/creator-golden-trial/approve",
        headers,
        "approve-1",
        {"expected_event_count": mission.json()["trial"]["event_count"], "created_at": STAMP},
    )
    dispatch = _post(
        client,
        "/projects/golden-budget/creator-golden-trial/dispatch-next",
        headers,
        "dispatch-1",
        {
            "expected_event_count": approve.json()["trial"]["event_count"],
            "estimated_cost_amount": 0.1,
            "generated_at": STAMP,
        },
    )
    assert dispatch.status_code == 200, dispatch.text
    payload = dispatch.json()
    assert payload["provider_calls_started"] is False
    assert payload["receipt"]["status"] == "blocked"
    assert payload["trial"]["status"] == "blocked"
    assert payload["trial"]["dispatches"]["shot-001"]["reason"] == "budget_ceiling"

    aggregate = client.get("/projects/golden-budget/episode-production-aggregate", headers=headers)
    assert aggregate.status_code == 200, aggregate.text
    assert aggregate.json()["aggregate"]["asset_candidates"] == []


def test_creator_golden_trial_requires_approval_and_project_scope(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client(tmp_path, monkeypatch)
    owner = _register(client, "scope-owner@example.com")
    other = _register(client, "scope-other@example.com")
    owner_headers = _headers(owner)
    other_headers = _headers(other)
    _create_project(client, owner_headers, "golden-scope")

    mission = _post(
        client,
        "/projects/golden-scope/creator-golden-trial/mission",
        owner_headers,
        "mission-1",
        _mission(project_ceiling_amount=1.0, estimated_unit_cost_amount=0.1),
    )
    assert mission.status_code == 200, mission.text

    early_dispatch = _post(
        client,
        "/projects/golden-scope/creator-golden-trial/dispatch-next",
        owner_headers,
        "dispatch-before-approval",
        {
            "expected_event_count": mission.json()["trial"]["event_count"],
            "estimated_cost_amount": 0.1,
            "generated_at": STAMP,
        },
    )
    assert early_dispatch.status_code == 409
    assert early_dispatch.json()["detail"]["error"] == "creator_golden_trial_not_approved"

    forbidden = client.get("/projects/golden-scope/creator-golden-trial", headers=other_headers)
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["error"] == "project_access_denied"


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


def _headers(session: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['session_token']}"}


def _create_project(client: TestClient, headers: dict[str, str], project_id: str) -> None:
    response = client.post(
        "/projects",
        headers=headers,
        json={
            "project_id": project_id,
            "project_type": "studio_episode_production",
            "goal": "Creator Golden Trial",
        },
    )
    assert response.status_code == 200, response.text


def _post(
    client: TestClient,
    route: str,
    headers: dict[str, str],
    key: str,
    body: dict[str, Any],
):
    return client.post(route, headers={**headers, "Idempotency-Key": key}, json=body)


def _mission(*, project_ceiling_amount: float, estimated_unit_cost_amount: float) -> dict[str, Any]:
    return {
        "objective": "制作一个三镜头的创作者主导 AI 原生制片系统样片。",
        "constraints": ["保持三镜头连续性。", "生成后等待人类审核。"],
        "project_ceiling_amount": project_ceiling_amount,
        "estimated_unit_cost_amount": estimated_unit_cost_amount,
        "currency": "USD",
        "created_at": STAMP,
    }
