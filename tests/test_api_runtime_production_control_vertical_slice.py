from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from agentflow_studio.production_control.harness import AtomicCommitError, ProductionControlHarness
from apps.api.runtime_episode_domain_store import EpisodeDomainAggregateStore, EpisodeDomainStoreError
from apps.api.runtime_service import create_runtime_app


PROJECT_ID = "pc-vertical"
STAMP = "2026-07-15T09:00:00+00:00"


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


def _create_project(client: TestClient, headers: dict[str, str], project_id: str = PROJECT_ID) -> None:
    response = client.post(
        "/projects",
        headers=headers,
        json={
            "project_id": project_id,
            "project_type": "studio_episode_production",
            "goal": "Production control vertical slice",
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


def _action(
    client: TestClient,
    headers: dict[str, str],
    run_id: str,
    key: str,
    expected_version: int,
    action: str,
    **extra: Any,
):
    return _post(
        client,
        f"/projects/{PROJECT_ID}/production-control/runs/{run_id}/actions",
        headers,
        key,
        {"expected_version": expected_version, "action": action, "created_at": STAMP, **extra},
    )


def _approve_default_plan(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    mission = {
        "expected_version": 0,
        "objective": "制作一集可审片的故事板。",
        "constraints": ["本轮不调用外部生成服务。"],
        "created_at": STAMP,
    }
    assert _post(client, f"/projects/{PROJECT_ID}/production-control/mission", headers, "mission-1", mission).status_code == 200
    assert _post(
        client,
        f"/projects/{PROJECT_ID}/production-control/plan",
        headers,
        "plan-1",
        {"expected_version": 1, "created_at": STAMP},
    ).status_code == 200
    approved = _post(
        client,
        f"/projects/{PROJECT_ID}/production-control/plan/approve",
        headers,
        "approve-1",
        {"expected_version": 2, "created_at": STAMP},
    )
    assert approved.status_code == 200, approved.text
    return approved.json()["control"]


def test_production_control_vertical_slice_is_authenticated_recoverable_and_provider_free(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client(tmp_path, monkeypatch)
    owner = _register(client, "owner@example.com")
    other = _register(client, "other@example.com")
    headers = _headers(owner)
    _create_project(client, headers)

    mission = {
        "expected_version": 0,
        "objective": "制作一集可审片、可返工、可锁版的故事板。",
        "constraints": ["本轮不调用外部生成服务。", "未受影响镜头保持不变。"],
        "created_at": STAMP,
    }
    response = _post(client, f"/projects/{PROJECT_ID}/production-control/mission", headers, "mission-1", mission)
    assert response.status_code == 200, response.text
    first_receipt = response.json()["receipt"]["receipt_id"]
    replay = _post(client, f"/projects/{PROJECT_ID}/production-control/mission", headers, "mission-1", mission)
    assert replay.status_code == 200, replay.text
    assert replay.json()["receipt"]["receipt_id"] == first_receipt
    conflict = _post(
        client,
        f"/projects/{PROJECT_ID}/production-control/mission",
        headers,
        "mission-1",
        {**mission, "objective": "Different mission"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["error"] == "production_control_idempotency_conflict"

    plan_body = {"expected_version": 1, "created_at": STAMP}
    assert _post(client, f"/projects/{PROJECT_ID}/production-control/plan", headers, "plan-1", plan_body).status_code == 200
    assert _post(client, f"/projects/{PROJECT_ID}/production-control/plan", headers, "plan-1", plan_body).status_code == 200

    approved = _post(
        client,
        f"/projects/{PROJECT_ID}/production-control/plan/approve",
        headers,
        "approve-1",
        {"expected_version": 2, "created_at": STAMP},
    )
    assert approved.status_code == 200, approved.text
    control = approved.json()["control"]
    assert control["version"] == 3
    assert len(control["tasks"]) == 3
    assert len(control["runs"]) == 3
    assert control["event_count"] == 9
    assert control["provider_dispatch_count"] == 0
    assert _post(
        client,
        f"/projects/{PROJECT_ID}/production-control/plan/approve",
        headers,
        "approve-1",
        {"expected_version": 2, "created_at": STAMP},
    ).status_code == 200

    stale = _action(client, headers, "run-001", "stale-progress", 2, "progress")
    assert stale.status_code == 409
    assert stale.json()["detail"]["error"] == "production_control_version_conflict"

    version = control["version"]
    paused = _action(client, headers, "run-001", "pause-1", version, "pause")
    assert paused.status_code == 200, paused.text
    assert paused.json()["control"]["runs"][0]["control_state"] == "paused"
    version = paused.json()["control"]["version"]
    resumed = _action(client, headers, "run-001", "resume-1", version, "resume")
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["control"]["runs"][0]["control_state"] == "active"

    version = resumed.json()["control"]["version"]
    retried = _action(client, headers, "run-002", "retry-1", version, "retry")
    assert retried.status_code == 200, retried.text
    assert retried.json()["control"]["runs"][1]["attempt_count"] == 2

    version = retried.json()["control"]["version"]
    waiting = _action(client, headers, "run-003", "wait-1", version, "waiting_human")
    assert waiting.status_code == 200, waiting.text
    assert waiting.json()["control"]["human_decisions"]["open_run_ids"] == ["run-003"]
    version = waiting.json()["control"]["version"]
    decided = _action(
        client,
        headers,
        "run-003",
        "decide-1",
        version,
        "decide_human",
        decision_option="确认继续",
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["control"]["human_decisions"]["open_count"] == 0

    version = decided.json()["control"]["version"]
    gate = _action(client, headers, "run-001", "provider-gate-1", version, "provider_gate")
    assert gate.status_code == 200, gate.text
    assert gate.json()["control"]["provider_gate"] == "closed"
    assert gate.json()["control"]["provider_dispatch_count"] == 0

    version = gate.json()["control"]["version"]
    writeback = _action(client, headers, "run-002", "writeback-1", version, "writeback")
    assert writeback.status_code == 200, writeback.text
    control = writeback.json()["control"]
    assert len(control["artifacts"]) == 1
    assert control["artifacts"][0]["status"] == "pending_review"
    assert control["review"]["status"] == "pending_episode_review"
    assert control["review"]["delivery_readback"] == "blocked_until_episode_selection_lock"
    assert control["continuity"]["shot_local_rework_protected"] is True
    assert control["artifacts"][0]["affected_ref"]["object_id"] == "shot-002"
    assert control["artifacts"][0]["candidate_ref"]["object_id"].startswith("candidate-run-002-")
    assert control["artifacts"][0]["provenance"]["task_ref"]["object_id"] == "task-002"
    assert control["artifacts"][0]["provenance"]["run_ref"]["object_id"] == "run-002"
    assert control["artifacts"][0]["provenance"]["attempt_ref"]["object_id"] == "attempt-run-002-002"
    protected = control["artifacts"][0]["protected_refs"]
    assert {item["object_id"] for item in protected} == {"shot-001", "shot-003"}
    replay_writeback = _action(client, headers, "run-002", "writeback-1", version, "writeback")
    assert replay_writeback.status_code == 200, replay_writeback.text
    assert len(replay_writeback.json()["control"]["artifacts"]) == 1

    rebuild = client.post(f"/projects/{PROJECT_ID}/production-control/integrity/rebuild", headers=headers)
    assert rebuild.status_code == 200, rebuild.text
    assert rebuild.json()["ok"] is True
    assert rebuild.json()["provider_dispatch_count"] == 0

    workspace = client.get(
        f"/projects/{PROJECT_ID}/episodes/episode-001/versions/episode-001-v1/workspace",
        headers=headers,
    )
    assert workspace.status_code == 200, workspace.text
    assert workspace.json()["schema_version"] == "afs_episode_workspace_projection.v0.1"
    assert workspace.json()["workspace"]["truth"]["shot_count"] == 3
    assert workspace.json()["workspace"]["shots"][1]["ref"]["version_id"] == "shot-002-v1"
    assert workspace.json()["workspace"]["shots"][1]["candidates"][0]["ref"]["entity_id"].startswith("candidate-run-002-")
    assert workspace.json()["workspace"]["shots"][0]["candidates"] == []
    review_action = next(
        action
        for action in workspace.json()["workspace"]["shots"][1]["allowed_actions"]
        if action["action"] == "adopt_candidate"
    )
    assert review_action["enabled"] is False
    assert review_action["blocked_by"][0]["entity_id"] == "shot-001"

    restarted_client = TestClient(create_runtime_app(runtime_root=tmp_path))
    recovered = restarted_client.get(f"/projects/{PROJECT_ID}/production-control", headers=headers)
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["control"]["projection_digest"] == control["projection_digest"]
    assert len(recovered.json()["control"]["artifacts"]) == 1
    assert recovered.json()["control"]["artifacts"][0]["status"] == "pending_review"

    foreign = client.get(f"/projects/{PROJECT_ID}/production-control", headers=_headers(other))
    assert foreign.status_code == 403


def test_production_control_writeback_requires_episode_facts_before_ledger_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client(tmp_path, monkeypatch)
    owner = _register(client, "owner@example.com")
    headers = _headers(owner)
    _create_project(client, headers)

    snapshot = EpisodeDomainAggregateStore(tmp_path).snapshot_path(
        org_id=owner["user"]["user_id"],
        project_id=PROJECT_ID,
    )
    snapshot.unlink()

    mission = {
        "expected_version": 0,
        "objective": "制作一集可审片的故事板。",
        "constraints": ["本轮不调用外部生成服务。"],
        "created_at": STAMP,
    }
    assert _post(client, f"/projects/{PROJECT_ID}/production-control/mission", headers, "mission-1", mission).status_code == 200
    assert _post(client, f"/projects/{PROJECT_ID}/production-control/plan", headers, "plan-1", {"expected_version": 1, "created_at": STAMP}).status_code == 200
    approved = _post(
        client,
        f"/projects/{PROJECT_ID}/production-control/plan/approve",
        headers,
        "approve-1",
        {"expected_version": 2, "created_at": STAMP},
    )
    assert approved.status_code == 200, approved.text
    version = approved.json()["control"]["version"]

    writeback = _action(client, headers, "run-001", "writeback-1", version, "writeback")
    assert writeback.status_code == 409
    assert writeback.json()["detail"]["error"] == "production_control_state_conflict"

    control = client.get(f"/projects/{PROJECT_ID}/production-control", headers=headers)
    assert control.status_code == 200, control.text
    assert control.json()["control"]["version"] == version
    assert control.json()["control"]["artifacts"] == []


def test_production_control_blocked_and_cancelled_lifecycle_persists_with_typed_actions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client(tmp_path, monkeypatch)
    owner = _register(client, "owner@example.com")
    headers = _headers(owner)
    _create_project(client, headers)
    control = _approve_default_plan(client, headers)

    blocked = _action(
        client,
        headers,
        "run-001",
        "block-1",
        control["version"],
        "block",
        note="等待镜头一参考审批。",
    )
    assert blocked.status_code == 200, blocked.text
    run = blocked.json()["control"]["runs"][0]
    assert run["execution_state"] == "blocked"
    assert run["blocker"]["reason"] == "等待镜头一参考审批。"
    assert run["blocker"]["clearance_evidence_refs"] == [
        {"object_type": "plan_task", "object_id": "task-001", "revision_id": "task-001-v1"}
    ]
    actions = {item["action"]: item for item in run["allowed_actions"]}
    assert actions["retry"]["enabled"] is False
    assert actions["clear_blocker"]["enabled"] is True
    assert actions["cancel"]["enabled"] is True
    retry = _action(
        client,
        headers,
        "run-001",
        "retry-while-blocked",
        blocked.json()["control"]["version"],
        "retry",
    )
    assert retry.status_code == 409
    assert retry.json()["detail"]["error"] == "production_control_state_conflict"

    restarted = TestClient(create_runtime_app(runtime_root=tmp_path))
    recovered = restarted.get(f"/projects/{PROJECT_ID}/production-control", headers=headers)
    assert recovered.status_code == 200, recovered.text
    recovered_run = recovered.json()["control"]["runs"][0]
    assert recovered_run["execution_state"] == "blocked"
    recovered_actions = {item["action"]: item for item in recovered_run["allowed_actions"]}
    assert recovered_actions["retry"]["enabled"] is False

    cleared = _action(
        restarted,
        headers,
        "run-001",
        "clear-block-1",
        recovered.json()["control"]["version"],
        "clear_blocker",
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["control"]["runs"][0]["execution_state"] == "running"
    assert cleared.json()["control"]["runs"][0]["blocker"] is None

    cancelled = _action(
        restarted,
        headers,
        "run-003",
        "cancel-3",
        cleared.json()["control"]["version"],
        "cancel",
    )
    assert cancelled.status_code == 200, cancelled.text
    cancelled_run = cancelled.json()["control"]["runs"][2]
    assert cancelled_run["execution_state"] == "cancelled"
    cancel_actions = {item["action"]: item for item in cancelled_run["allowed_actions"]}
    assert cancel_actions["writeback"]["enabled"] is False
    assert cancel_actions["cancel"]["enabled"] is False

    after_cancel_version = cancelled.json()["control"]["version"]
    writeback = _action(
        restarted,
        headers,
        "run-003",
        "writeback-cancelled",
        after_cancel_version,
        "writeback",
    )
    assert writeback.status_code == 409
    assert writeback.json()["detail"]["error"] == "production_control_state_conflict"
    readback = restarted.get(f"/projects/{PROJECT_ID}/production-control", headers=headers)
    assert readback.status_code == 200, readback.text
    assert readback.json()["control"]["version"] == after_cancel_version
    assert readback.json()["control"]["artifacts"] == []


def test_writeback_finalize_failure_hides_artifact_and_same_key_replay_completes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client(tmp_path, monkeypatch)
    owner = _register(client, "owner@example.com")
    headers = _headers(owner)
    _create_project(client, headers)
    control = _approve_default_plan(client, headers)

    original_save = EpisodeDomainAggregateStore.save
    failures = {"remaining": 1}

    def fail_finalize_once(
        self: EpisodeDomainAggregateStore,
        aggregate,
        *,
        expected_aggregate_version: int,
        idempotency_key: str,
        payload_digest: str,
    ):
        if idempotency_key.endswith("-episode-asset-candidate-finalize") and failures["remaining"]:
            failures["remaining"] -= 1
            raise EpisodeDomainStoreError("injected finalize failure")
        return original_save(
            self,
            aggregate,
            expected_aggregate_version=expected_aggregate_version,
            idempotency_key=idempotency_key,
            payload_digest=payload_digest,
        )

    monkeypatch.setattr(EpisodeDomainAggregateStore, "save", fail_finalize_once)
    version = control["version"]
    failed = _action(client, headers, "run-001", "writeback-1", version, "writeback")
    assert failed.status_code == 409
    assert failed.json()["detail"]["error"] == "production_control_state_conflict"

    readback = client.get(f"/projects/{PROJECT_ID}/production-control", headers=headers)
    assert readback.status_code == 200, readback.text
    assert len(readback.json()["control"]["artifacts"]) == 1
    assert readback.json()["control"]["artifacts"][0]["status"] == "ledger_pending_episode_receipt"
    aggregate = EpisodeDomainAggregateStore(tmp_path).load(
        org_id=owner["user"]["user_id"],
        project_id=PROJECT_ID,
    )
    candidates = [
        item
        for item in aggregate.asset_candidates
        if item.entity_id.startswith("candidate-run-001-")
    ]
    assert len({item.entity_id for item in candidates}) == 1
    assert max(candidates, key=lambda item: item.revision).lifecycle_state == "candidate"

    replay = _action(client, headers, "run-001", "writeback-1", version, "writeback")
    assert replay.status_code == 200, replay.text
    assert len(replay.json()["control"]["artifacts"]) == 1
    aggregate = EpisodeDomainAggregateStore(tmp_path).load(
        org_id=owner["user"]["user_id"],
        project_id=PROJECT_ID,
    )
    candidates = [
        item
        for item in aggregate.asset_candidates
        if item.entity_id.startswith("candidate-run-001-")
    ]
    assert len({item.entity_id for item in candidates}) == 1
    latest = max(candidates, key=lambda item: item.revision)
    assert latest.lifecycle_state == "candidate"
    assert latest.review_state == "needs_review"
    assert latest.control_provenance is not None


def test_writeback_ledger_failure_after_episode_draft_replays_without_duplicate_candidate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client(tmp_path, monkeypatch)
    owner = _register(client, "owner@example.com")
    headers = _headers(owner)
    _create_project(client, headers)
    control = _approve_default_plan(client, headers)

    original_write_commit = ProductionControlHarness._write_commit_envelope
    failures = {"remaining": 1}

    def fail_ledger_once(self: ProductionControlHarness, *args, **kwargs):
        if failures["remaining"]:
            failures["remaining"] -= 1
            raise AtomicCommitError("injected ledger failure")
        return original_write_commit(self, *args, **kwargs)

    monkeypatch.setattr(ProductionControlHarness, "_write_commit_envelope", fail_ledger_once)
    version = control["version"]
    failed = _action(client, headers, "run-001", "writeback-1", version, "writeback")
    assert failed.status_code == 500
    assert failed.json()["detail"]["error"] == "production_control_commit_failed"

    readback = client.get(f"/projects/{PROJECT_ID}/production-control", headers=headers)
    assert readback.status_code == 200, readback.text
    assert readback.json()["control"]["artifacts"] == []
    aggregate = EpisodeDomainAggregateStore(tmp_path).load(
        org_id=owner["user"]["user_id"],
        project_id=PROJECT_ID,
    )
    candidates = [
        item
        for item in aggregate.asset_candidates
        if item.entity_id.startswith("candidate-run-001-")
    ]
    assert len({item.entity_id for item in candidates}) == 1
    latest = max(candidates, key=lambda item: item.revision)
    assert latest.lifecycle_state == "candidate"
    assert latest.job_state == "running"
    assert latest.control_provenance is None

    replay = _action(client, headers, "run-001", "writeback-1", version, "writeback")
    assert replay.status_code == 200, replay.text
    assert len(replay.json()["control"]["artifacts"]) == 1
    aggregate = EpisodeDomainAggregateStore(tmp_path).load(
        org_id=owner["user"]["user_id"],
        project_id=PROJECT_ID,
    )
    candidates = [
        item
        for item in aggregate.asset_candidates
        if item.entity_id.startswith("candidate-run-001-")
    ]
    assert len({item.entity_id for item in candidates}) == 1
    latest = max(candidates, key=lambda item: item.revision)
    assert latest.lifecycle_state == "candidate"
    assert latest.review_state == "needs_review"
    assert latest.job_state == "succeeded"
    assert latest.control_provenance is not None


def test_production_control_ledger_integrity_rejects_duplicate_sequence_and_outbox_drift(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client(tmp_path, monkeypatch)
    owner = _register(client, "owner@example.com")
    headers = _headers(owner)
    _create_project(client, headers)
    mission = {
        "expected_version": 0,
        "objective": "Mission",
        "constraints": ["Provider closed."],
        "created_at": STAMP,
    }
    assert _post(client, f"/projects/{PROJECT_ID}/production-control/mission", headers, "mission-1", mission).status_code == 200
    assert _post(client, f"/projects/{PROJECT_ID}/production-control/plan", headers, "plan-1", {"expected_version": 1, "created_at": STAMP}).status_code == 200

    ledger = tmp_path / "projects" / PROJECT_ID / "production_control" / "ledger.json"
    payload = json.loads(ledger.read_text(encoding="utf-8"))
    payload["events"][1]["project_sequence"] = 1
    ledger.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    duplicate_sequence = client.get(f"/projects/{PROJECT_ID}/production-control", headers=headers)
    assert duplicate_sequence.status_code == 500
    assert duplicate_sequence.json()["detail"]["error"] == "production_control_ledger_integrity_failed"

    client = _client(tmp_path / "outbox", monkeypatch)
    owner = _register(client, "owner2@example.com")
    headers = _headers(owner)
    _create_project(client, headers)
    assert _post(client, f"/projects/{PROJECT_ID}/production-control/mission", headers, "mission-1", mission).status_code == 200
    assert _post(client, f"/projects/{PROJECT_ID}/production-control/plan", headers, "plan-1", {"expected_version": 1, "created_at": STAMP}).status_code == 200
    ledger = tmp_path / "outbox" / "projects" / PROJECT_ID / "production_control" / "ledger.json"
    payload = json.loads(ledger.read_text(encoding="utf-8"))
    payload["outbox"] = payload["outbox"][:-1]
    ledger.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    outbox_drift = client.get(f"/projects/{PROJECT_ID}/production-control", headers=headers)
    assert outbox_drift.status_code == 500
    assert outbox_drift.json()["detail"]["error"] == "production_control_ledger_integrity_failed"
