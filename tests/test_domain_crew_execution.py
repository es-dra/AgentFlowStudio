from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

import pytest
from fastapi.testclient import TestClient

from agentflow_studio.domain_crew_execution import DomainCrewExecution, ExecutionDriftError
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore
from tools.afs_domain_crew_execution import main as cli_main


EXECUTION_ID = "adapter-cycle-001"
PROJECT_ID = "episode-agent-cycle"
CREW_ID = "crew-agent-cycle"
SOURCE_IDEA = "A courier discovers a hidden signal and chooses to protect the city."


@dataclass
class ClientTransport:
    client: TestClient
    token: str

    def request(self, method: str, path: str, *, json: Mapping[str, Any] | None = None):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        return self.client.request(method, path, json=json, headers=headers)


class StaleWriteTransport(ClientTransport):
    stale_next_write = True

    def request(self, method: str, path: str, *, json: Mapping[str, Any] | None = None):
        payload = dict(json or {})
        if method == "POST" and self.stale_next_write and "expected_state_version" in payload:
            self.stale_next_write = False
            payload["expected_state_version"] += 1
        return super().request(method, path, json=payload)


def _fixture(tmp_path, monkeypatch):
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "adapter-owner,adapter-other")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "false")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "false")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    owner = client.post("/auth/register", json={"email": "adapter-owner@example.com",
        "password": "strong-password-123", "display_name": "Owner", "invite_code": "adapter-owner"}).json()
    other = client.post("/auth/register", json={"email": "adapter-other@example.com",
        "password": "strong-password-123", "display_name": "Other", "invite_code": "adapter-other"}).json()
    owner_token, other_token = owner["session_token"], other["session_token"]
    headers = {"Authorization": f"Bearer {owner_token}"}
    assert client.post("/projects", json={"project_id": PROJECT_ID, "goal": "Agent-driven episode"},
                       headers=headers).status_code == 200
    response = client.post(f"/projects/{PROJECT_ID}/domain-crew", json={"crew_id": CREW_ID}, headers=headers)
    assert response.status_code == 200, response.text
    return client, owner_token, other_token


def _execution(client: TestClient, token: str) -> DomainCrewExecution:
    return DomainCrewExecution(ClientTransport(client, token), project_id=PROJECT_ID, crew_id=CREW_ID,
                               execution_id=EXECUTION_ID, source_idea=SOURCE_IDEA)


def _arbitrate(client: TestClient, token: str, execution: DomainCrewExecution, approved: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    crew = client.get(f"/projects/{PROJECT_ID}/domain-crew", headers=headers).json()["crew"]
    response = client.post(
        f"/projects/{PROJECT_ID}/domain-crew/conflicts/{EXECUTION_ID}-conflict-creator/arbitrations",
        headers=headers,
        json={"entity_type": "scene", "entity_id": f"{EXECUTION_ID}-scene",
              "from_version_id": f"{EXECUTION_ID}-scene-v1", "selected_version_id": approved,
              "expected_state_version": crew["state_version"],
              "resume_agent_id": f"{CREW_ID}-screenwriter", "next_action": "script.write",
              "rationale": "Creator selected the approved script version in Studio.",
              "affected_work_refs": execution.expected_affected_work(approved)},
    )
    assert response.status_code == 200, response.text
    return response.json()["crew"]


def _crew(client: TestClient, token: str) -> dict[str, Any]:
    return client.get(f"/projects/{PROJECT_ID}/domain-crew",
                      headers={"Authorization": f"Bearer {token}"}).json()["crew"]


def test_provider_free_adapters_drive_and_reload_exact_authenticated_cycle(tmp_path, monkeypatch) -> None:
    client, token, _ = _fixture(tmp_path, monkeypatch)
    execution = _execution(client, token)
    phase_a = execution.run_phase_a()
    assert phase_a["status"] == "awaiting_creator"
    assert phase_a["provider_dispatch_count"] == 0
    assert phase_a["auth_boundary"] == "user_delegated_authenticated_transport"
    assert execution.run_phase_a()["state_version"] == phase_a["state_version"]

    approved = f"{EXECUTION_ID}-scene-v2"
    pending = _arbitrate(client, token, execution, approved)
    assert [item["downstream_task_id"] for item in pending["propagation_reconfirmations"]] == [
        f"{EXECUTION_ID}-task-storyboard", f"{EXECUTION_ID}-task-art"]
    assert all(item["reconfirmation_status"] == "required_pending"
               for item in pending["propagation_reconfirmations"])

    final_evidence = execution.run_phase_b(approved_version_id=approved)
    assert final_evidence["status"] == "propagation_complete"
    assert final_evidence["provider_dispatch_count"] == 0
    assert len(final_evidence["adapter_action_message_ids"]) == 6
    assert execution.run_phase_b(approved_version_id=approved)["state_version"] == final_evidence["state_version"]

    reloaded = TestClient(create_runtime_app(runtime_root=tmp_path))
    restored = _crew(reloaded, token)
    arbitration = restored["arbitrations"][0]
    assert arbitration["propagation_complete"] is True
    assert arbitration["propagation_status"] == "reconfirmed"
    assert [item["sequence"] for item in restored["events"]] == list(range(1, len(restored["events"]) + 1))
    for role, task_label in (("screenwriter", "script"), ("storyboard", "storyboard"), ("art", "art")):
        task = next(item for item in restored["tasks"] if item["task_id"] == f"{EXECUTION_ID}-task-{task_label}")
        assert task["claimed_by_agent_id"] == f"{CREW_ID}-{role}"
        assert task["version_id"] == approved
    for message in restored["messages"]:
        action = json.loads(message["content"])
        assert action["execution_id"] == EXECUTION_ID
        assert action["agent_id"] == message["from_agent_id"]
        assert action["entity_ref"]["version_id"] == message["version_id"]
        assert len(action["work_digest"]) == 64
        assert action["provider_dispatch_count"] == 0


def test_missing_and_foreign_auth_fail_without_progress_or_secret_echo(tmp_path, monkeypatch) -> None:
    client, token, other_token = _fixture(tmp_path, monkeypatch)
    for supplied in ("", other_token):
        with pytest.raises(ExecutionDriftError) as caught:
            _execution(client, supplied).run_phase_a()
        assert token not in str(caught.value)
        assert other_token not in str(caught.value)
    assert _crew(client, token)["tasks"] == []


def test_stale_version_fails_closed_before_adapter_progress_continues(tmp_path, monkeypatch) -> None:
    client, token, _ = _fixture(tmp_path, monkeypatch)
    execution = DomainCrewExecution(StaleWriteTransport(client, token), project_id=PROJECT_ID, crew_id=CREW_ID,
                                    execution_id=EXECUTION_ID, source_idea=SOURCE_IDEA)
    with pytest.raises(ExecutionDriftError, match="status=409"):
        execution.run_phase_a()
    assert _crew(client, token)["tasks"] == []


@pytest.mark.parametrize("mutation", ("wrong-agent", "wrong-version", "duplicate-message"))
def test_resume_rejects_identity_content_and_duplicate_drift(tmp_path, monkeypatch, mutation) -> None:
    client, token, _ = _fixture(tmp_path, monkeypatch)
    execution = _execution(client, token)
    execution.run_phase_a()
    store = RuntimeStore(tmp_path)
    crew = store.load_domain_crew(PROJECT_ID)
    if mutation == "wrong-agent":
        crew["tasks"][0]["assigned_agent_id"] = f"{CREW_ID}-art"
    elif mutation == "wrong-version":
        crew["tasks"][0]["version_id"] = f"{EXECUTION_ID}-foreign-version"
    else:
        crew["messages"].append(dict(crew["messages"][0]))
    store.write_domain_crew(PROJECT_ID, crew)
    with pytest.raises(ExecutionDriftError):
        execution.run_phase_a()


@pytest.mark.parametrize("mutation", ("omitted-pending", "graph-node-drift", "approved-version-drift"))
def test_phase_b_rejects_omitted_pending_and_authority_graph_drift(tmp_path, monkeypatch, mutation) -> None:
    client, token, _ = _fixture(tmp_path, monkeypatch)
    execution = _execution(client, token)
    execution.run_phase_a()
    approved = f"{EXECUTION_ID}-scene-v2"
    _arbitrate(client, token, execution, approved)
    store = RuntimeStore(tmp_path)
    crew = store.load_domain_crew(PROJECT_ID)
    if mutation == "omitted-pending":
        crew["propagation_reconfirmations"] = crew["propagation_reconfirmations"][:1]
    elif mutation == "graph-node-drift":
        crew["arbitrations"][0]["affected_work_refs"][0]["downstream_node_id"] = "foreign-node"
    else:
        crew["arbitrations"][0]["selected_version_id"] = f"{EXECUTION_ID}-scene-v3"
    store.write_domain_crew(PROJECT_ID, crew)
    with pytest.raises(ExecutionDriftError):
        execution.run_phase_b(approved_version_id=approved)


def test_cli_rejects_argv_token_and_never_echoes_it(monkeypatch, capsys) -> None:
    secret = "sensitive-runtime-token-value"
    monkeypatch.setenv("AFS_RUNTIME_BEARER_TOKEN", secret)
    result = cli_main(["--token", secret])
    captured = capsys.readouterr()
    assert result == 2
    assert secret not in captured.out
    assert secret not in captured.err
    assert "AFS_RUNTIME_BEARER_TOKEN" in captured.err
