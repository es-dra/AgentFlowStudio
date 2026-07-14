from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import pytest
from fastapi.testclient import TestClient

from agentflow_studio.representative_episode_execution import (
    EpisodeExecutionDriftError,
    RepresentativeEpisodeExecution,
    ROLE_ORDER,
)
from apps.api.runtime_service import create_runtime_app
from tools.afs_representative_episode_execution import main as cli_main
from tools.studio_production_delivery_browser_qa import (
    CREW_ID,
    EPISODE_EXECUTION_ID,
    PROJECT_ID,
    QA_EMAIL,
    QA_PASSWORD,
    RUN_ID,
    prepare_provider_free_delivery_qa,
)


REVISION = Path(__file__).parents[1] / "examples" / "representative_episode" / "episode_revision_v2.json"


@dataclass
class ClientTransport:
    client: TestClient
    token: str

    def request(self, method: str, path: str, *, json: Mapping[str, Any] | None = None):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        return self.client.request(method, path, json=json, headers=headers)


def _setup(tmp_path: Path, monkeypatch):
    seed = prepare_provider_free_delivery_qa(tmp_path, run_episode_execution=False)
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "delivery-qa-invite,crew-foreign-invite")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "false")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "false")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "false")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    login = client.post("/auth/login", json={"email": QA_EMAIL, "password": QA_PASSWORD})
    assert login.status_code == 200, login.text
    token = login.json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}
    crew = client.post(f"/projects/{PROJECT_ID}/domain-crew", headers=headers, json={"crew_id": CREW_ID})
    assert crew.status_code == 200, crew.text
    execution = RepresentativeEpisodeExecution.from_revision_path(
        ClientTransport(client, token),
        project_id=PROJECT_ID,
        crew_id=CREW_ID,
        run_id=RUN_ID,
        execution_id=EPISODE_EXECUTION_ID,
        revision_path=REVISION,
    )
    return seed, client, token, headers, execution


def _crew(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    response = client.get(f"/projects/{PROJECT_ID}/domain-crew", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["crew"]


def _run(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    response = client.get(f"/projects/{PROJECT_ID}/production-runs/{RUN_ID}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["production_run"]


def test_nine_role_execution_reloads_and_advances_one_shot_only_after_complete_propagation(
    tmp_path: Path, monkeypatch,
) -> None:
    _, client, _, headers, execution = _setup(tmp_path, monkeypatch)
    v1 = copy.deepcopy(_run(client, headers)["representative_episode_binding"])

    phase_a = execution.run_phase_a()
    assert phase_a["status"] == "awaiting_creator_revision"
    assert phase_a["role_count"] == 9
    assert phase_a["accepted_handoff_count"] == 8
    assert phase_a["provider_dispatch_count"] == 0
    assert execution.run_phase_a()["crew_state_version"] == phase_a["crew_state_version"]
    crew = _crew(client, headers)
    tasks = [item for item in crew["tasks"] if item["task_id"].startswith(f"{EPISODE_EXECUTION_ID}-task-")]
    assert [item["assigned_agent_id"].removeprefix(f"{CREW_ID}-") for item in tasks] == list(ROLE_ORDER)
    assert all(item["claimed_by_agent_id"] == item["assigned_agent_id"] for item in tasks)
    assert all(item["version_id"] == "ep-rainlight-001-v1" for item in tasks)
    assert len([item for item in crew["messages"] if item["message_id"].endswith("-v1")]) == 9

    pending_evidence = execution.record_creator_revision()
    assert pending_evidence["status"] == "reconfirmation_pending"
    pending = _crew(client, headers)["propagation_reconfirmations"]
    assert [item["responsible_agent_role"] for item in pending] == list(ROLE_ORDER[1:])
    assert all(item["reconfirmation_status"] == "required_pending" for item in pending)
    assert _run(client, headers)["representative_episode_binding"] == v1
    pending_projection = client.get(
        f"/projects/{PROJECT_ID}/product-overview", headers=headers,
    ).json()["project"]["crew"]["episode_execution"]
    assert pending_projection["role_count"] == 9
    assert pending_projection["pending_reconfirmation_count"] == 8
    assert pending_projection["reconfirmed_count"] == 0
    assert pending_projection["propagation_complete"] is False

    execution.reconfirm_next("storyboard")
    partial_projection = client.get(
        f"/projects/{PROJECT_ID}/product-overview", headers=headers,
    ).json()["project"]["crew"]["episode_execution"]
    assert partial_projection["pending_reconfirmation_count"] == 7
    assert partial_projection["reconfirmed_count"] == 1
    assert partial_projection["propagation_complete"] is False
    with pytest.raises(EpisodeExecutionDriftError, match="cannot advance"):
        execution.finalize_binding()
    assert _run(client, headers)["representative_episode_binding"] == v1

    final = execution.run_phase_b()
    assert final == execution.run_phase_b()
    assert final["status"] == "episode_v2_bound"
    assert final["reconfirmed_count"] == 8
    assert final["propagation_complete"] is True
    assert final["media_status"] == "media_assets_pending"
    assert final["provider_dispatch_count"] == 0

    v2 = _run(client, headers)["representative_episode_binding"]
    assert v2["episode_version_id"] == "ep-rainlight-001-v2"
    assert v2["package_sha256"] != v1["package_sha256"]
    assert v2["previous_binding_digest"] == v1["binding_digest"]
    assert v2["propagation_complete"] is True
    assert v2["asset_readiness"]["pending_media_count"] == 25
    assert len(v2["episode_canon"]["shots"]) == 15
    changed = []
    for before, after in zip(v1["episode_canon"]["shots"], v2["episode_canon"]["shots"], strict=True):
        if before != after:
            changed.append((before, after))
    assert len(changed) == 1
    before, after = changed[0]
    assert before["entity_id"] == after["entity_id"] == "shot-011"
    assert before["current_approved_version_id"] == "shot-011-v1"
    assert after["current_approved_version_id"] == "shot-011-v2"
    assert {key: value for key, value in before.items() if key not in {"current_approved_version_id", "visual_action"}} == {
        key: value for key, value in after.items() if key not in {"current_approved_version_id", "visual_action"}
    }
    assert all(
        left == right
        for left, right in zip(v1["shot_refs"], v2["shot_refs"], strict=True)
        if left["entity_id"] != "shot-011"
    )

    restored_client = TestClient(create_runtime_app(runtime_root=tmp_path))
    restored = _run(restored_client, headers)
    assert restored["representative_episode_binding"] == v2
    restored_crew = _crew(restored_client, headers)
    assert restored_crew["arbitrations"][-1]["propagation_complete"] is True
    for item in restored_crew["messages"]:
        if item["message_id"].startswith(f"{EPISODE_EXECUTION_ID}-message-"):
            action = json.loads(item["content"])
            assert action["agent_id"] == item["from_agent_id"]
            assert action["project_id"] == PROJECT_ID
            assert action["episode_id"] == "ep-rainlight-001"
            assert action["provider_dispatch_count"] == 0


def test_wrong_order_omitted_duplicate_foreign_and_stale_authority_fail_closed(tmp_path: Path, monkeypatch) -> None:
    _, client, token, headers, execution = _setup(tmp_path, monkeypatch)
    execution.run_phase_a()
    crew = _crew(client, headers)
    affected = execution._derive_authoritative_affected_work(crew, require_source_version=True)
    arbitration_path = (
        f"/projects/{PROJECT_ID}/domain-crew/conflicts/"
        f"{EPISODE_EXECUTION_ID}-conflict-creator-v2/arbitrations"
    )
    base = {
        "entity_type": "project",
        "entity_id": PROJECT_ID,
        "from_version_id": "ep-rainlight-001-v1",
        "selected_version_id": "ep-rainlight-001-v2",
        "expected_state_version": crew["state_version"],
        "resume_agent_id": f"{CREW_ID}-screenwriter",
        "next_action": "script.write",
        "rationale": "Creator approved the exact Rainlight v2 revision.",
    }
    omitted = client.post(arbitration_path, headers=headers, json={**base, "affected_work_refs": affected[:-1]})
    duplicate = client.post(arbitration_path, headers=headers, json={**base, "affected_work_refs": [*affected, affected[-1]]})
    assert omitted.status_code == 409
    assert duplicate.status_code == 422
    assert _crew(client, headers)["arbitrations"] == []

    execution.record_creator_revision()
    with pytest.raises(EpisodeExecutionDriftError, match="order changed"):
        execution.reconfirm_next("art")
    crew = _crew(client, headers)
    first = crew["propagation_reconfirmations"][0]
    wrong_role = client.post(
        f"/projects/{PROJECT_ID}/domain-crew/propagation-reconfirmations/{first['affected_ref_id']}/actions",
        headers=headers,
        json={
            "expected_state_version": crew["state_version"],
            "responsible_agent_id": f"{CREW_ID}-art",
            "action": "acknowledge_reconfirm",
            "observed_version_id": "ep-rainlight-001-v2",
        },
    )
    stale_version = client.post(
        f"/projects/{PROJECT_ID}/domain-crew/propagation-reconfirmations/{first['affected_ref_id']}/actions",
        headers=headers,
        json={
            "expected_state_version": crew["state_version"] + 1,
            "responsible_agent_id": f"{CREW_ID}-storyboard",
            "action": "acknowledge_reconfirm",
            "observed_version_id": "ep-rainlight-001-v1",
        },
    )
    assert wrong_role.status_code == 409
    assert stale_version.status_code == 409
    assert _run(client, headers)["representative_episode_binding"]["episode_version_id"] == "ep-rainlight-001-v1"

    foreign = client.post(
        "/auth/register",
        json={
            "email": "crew-foreign@example.com",
            "password": "strong-password-123",
            "display_name": "Foreign",
            "invite_code": "crew-foreign-invite",
        },
    ).json()["session_token"]
    with pytest.raises(EpisodeExecutionDriftError, match="status=403"):
        RepresentativeEpisodeExecution.from_revision_path(
            ClientTransport(client, foreign),
            project_id=PROJECT_ID,
            crew_id=CREW_ID,
            run_id=RUN_ID,
            execution_id=EPISODE_EXECUTION_ID,
            revision_path=REVISION,
        ).run_phase_a()
    assert token not in json.dumps(_crew(client, headers))


def test_cli_rejects_token_argument_without_echo(monkeypatch, capsys) -> None:
    secret = "sensitive-runtime-token-value"
    monkeypatch.setenv("AFS_RUNTIME_BEARER_TOKEN", secret)
    result = cli_main(["--token", secret])
    captured = capsys.readouterr()
    assert result == 2
    assert secret not in captured.out
    assert secret not in captured.err
