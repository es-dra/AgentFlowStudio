from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore


def _client(tmp_path, monkeypatch) -> tuple[TestClient, dict[str, str], dict[str, str]]:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "owner-invite,other-invite")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    owner = client.post("/auth/register", json={"email": "owner@example.com", "password": "strong-password-123",
        "display_name": "Owner", "invite_code": "owner-invite"}).json()
    other = client.post("/auth/register", json={"email": "other@example.com", "password": "strong-password-123",
        "display_name": "Other", "invite_code": "other-invite"}).json()
    owner_headers = {"Authorization": f"Bearer {owner['session_token']}"}
    other_headers = {"Authorization": f"Bearer {other['session_token']}"}
    created = client.post("/projects", json={"project_id": "episode-001", "goal": "Produce episode"}, headers=owner_headers)
    assert created.status_code == 200
    return client, owner_headers, other_headers


def _ref() -> dict[str, str]:
    return {"entity_type": "scene", "entity_id": "scene-001", "version_id": "scene-v1"}


def _arbitration_ref() -> dict[str, str]:
    return {"entity_type": "scene", "entity_id": "scene-001", "from_version_id": "scene-v1"}


def _bootstrap(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.post("/projects/episode-001/domain-crew", json={"crew_id": "crew-001"}, headers=headers)
    assert response.status_code == 200, response.text
    crew = response.json()["crew"]
    assert [agent["role"] for agent in crew["agents"]] == [
        "screenwriter", "storyboard", "art", "director", "continuity", "qa", "audio", "edit", "export",
    ]
    assert all(agent["owner_user_id"] == crew["owner_user_id"] for agent in crew["agents"])
    return crew


def _create_task(client: TestClient, headers: dict[str, str], *, version: int, task_id: str, agent: str, action: str) -> dict:
    response = client.post("/projects/episode-001/domain-crew/tasks", headers=headers, json={**_ref(),
        "task_id": task_id, "node_id": f"node-{task_id}", "expected_state_version": version, "assigned_agent_id": agent,
        "action": action, "objective": f"Complete {action}"})
    assert response.status_code == 200, response.text
    return response.json()["crew"]


def _claim(client: TestClient, headers: dict[str, str], *, task_id: str, agent: str, version: int) -> dict:
    response = client.post(f"/projects/episode-001/domain-crew/tasks/{task_id}/claim", headers=headers,
                           json={"expected_state_version": version, "agent_id": agent})
    assert response.status_code == 200, response.text
    return response.json()["crew"]


def _handoff(client: TestClient, headers: dict[str, str], *, version: int, handoff_id: str, task_id: str,
             target_task_id: str, sender: str, receiver: str, next_action: str) -> dict:
    created = client.post("/projects/episode-001/domain-crew/handoffs", headers=headers, json={**_ref(),
        "handoff_id": handoff_id, "expected_state_version": version, "task_id": task_id,
        "target_task_id": target_task_id, "target_node_id": f"node-{target_task_id}",
        "from_agent_id": sender, "to_agent_id": receiver,
        "next_action": next_action, "objective": f"Continue with {next_action}"})
    assert created.status_code == 200, created.text
    return created.json()["crew"]


def _decide(client: TestClient, headers: dict[str, str], *, version: int, handoff_id: str,
            receiver: str, decision: str) -> dict:
    response = client.post(f"/projects/episode-001/domain-crew/handoffs/{handoff_id}/decisions", headers=headers,
        json={"expected_state_version": version, "receiver_agent_id": receiver, "decision": decision,
              "note": f"Receiver chose {decision}"})
    assert response.status_code == 200, response.text
    return response.json()["crew"]


def test_authenticated_script_storyboard_art_vertical_persists_and_reloads(tmp_path, monkeypatch) -> None:
    client, headers, other_headers = _client(tmp_path, monkeypatch)
    crew = _bootstrap(client, headers)
    screenwriter, storyboard, art = (f"crew-001-{role}" for role in ("screenwriter", "storyboard", "art"))
    crew = _create_task(client, headers, version=1, task_id="task-script", agent=screenwriter, action="script.write")
    crew = _claim(client, headers, task_id="task-script", agent=screenwriter, version=crew["state_version"])

    message = client.post("/projects/episode-001/domain-crew/messages", headers=headers, json={**_ref(),
        "message_id": "message-script-ready", "expected_state_version": crew["state_version"],
        "task_id": "task-script", "from_agent_id": screenwriter, "to_agent_id": storyboard,
        "message_type": "request", "content": "Script version is ready for storyboard handoff."})
    assert message.status_code == 200, message.text
    crew = message.json()["crew"]
    linked = message.json()["message"]
    assert (linked["project_id"], linked["task_id"], linked["entity_id"], linked["version_id"]) == (
        "episode-001", "task-script", "scene-001", "scene-v1")

    crew = _handoff(client, headers, version=crew["state_version"], handoff_id="handoff-script-storyboard",
                    task_id="task-script", target_task_id="task-storyboard", sender=screenwriter,
                    receiver=storyboard, next_action="storyboard.compose")
    crew = _decide(client, headers, version=crew["state_version"], handoff_id="handoff-script-storyboard",
                   receiver=storyboard, decision="accept")
    crew = _claim(client, headers, task_id="task-storyboard", agent=storyboard, version=crew["state_version"])
    crew = _handoff(client, headers, version=crew["state_version"], handoff_id="handoff-storyboard-art",
                    task_id="task-storyboard", target_task_id="task-art", sender=storyboard,
                    receiver=art, next_action="art.create")
    crew = _decide(client, headers, version=crew["state_version"], handoff_id="handoff-storyboard-art",
                   receiver=art, decision="accept")
    crew = _claim(client, headers, task_id="task-art", agent=art, version=crew["state_version"])

    conflict = client.post("/projects/episode-001/domain-crew/conflicts", headers=headers, json={**_ref(),
        "conflict_id": "conflict-script-change", "expected_state_version": crew["state_version"],
        "task_id": "task-script", "raised_by_agent_id": screenwriter,
        "reason": "Creator-approved script change affects downstream scene work."})
    assert conflict.status_code == 200, conflict.text
    crew = conflict.json()["crew"]
    assert conflict.json()["conflict"]["escalation"] == "human_creator"

    affected = [
        {"downstream_task_id": "task-storyboard", "downstream_node_id": "node-task-storyboard",
         "responsible_agent_id": storyboard, "responsible_agent_role": "storyboard", "entity_type": "scene",
         "entity_id": "scene-001", "from_version_id": "scene-v1", "approved_version_id": "scene-v2"},
        {"downstream_task_id": "task-art", "downstream_node_id": "node-task-art",
         "responsible_agent_id": art, "responsible_agent_role": "art", "entity_type": "scene",
         "entity_id": "scene-001", "from_version_id": "scene-v1", "approved_version_id": "scene-v2"},
    ]

    stale = client.post("/projects/episode-001/domain-crew/conflicts/conflict-script-change/arbitrations", headers=headers,
        json={**_arbitration_ref(), "selected_version_id": "scene-v2", "expected_state_version": crew["state_version"] - 1,
              "resume_agent_id": screenwriter, "next_action": "script.write", "rationale": "Use approved version.",
              "affected_work_refs": affected})
    assert stale.status_code == 409
    foreign_node = [{**affected[0], "downstream_node_id": "foreign-node"}]
    foreign = client.post("/projects/episode-001/domain-crew/conflicts/conflict-script-change/arbitrations", headers=headers,
        json={**_arbitration_ref(), "selected_version_id": "scene-v2", "expected_state_version": crew["state_version"],
              "resume_agent_id": screenwriter, "next_action": "script.write", "rationale": "Use approved version.",
              "affected_work_refs": foreign_node})
    assert foreign.status_code == 409
    omitted = client.post("/projects/episode-001/domain-crew/conflicts/conflict-script-change/arbitrations", headers=headers,
        json={**_arbitration_ref(), "selected_version_id": "scene-v2", "expected_state_version": crew["state_version"],
              "resume_agent_id": screenwriter, "next_action": "script.write", "rationale": "Use approved version.",
              "affected_work_refs": affected[:1]})
    assert omitted.status_code == 409
    duplicate = client.post("/projects/episode-001/domain-crew/conflicts/conflict-script-change/arbitrations", headers=headers,
        json={**_arbitration_ref(), "selected_version_id": "scene-v2", "expected_state_version": crew["state_version"],
              "resume_agent_id": screenwriter, "next_action": "script.write", "rationale": "Use approved version.",
              "affected_work_refs": [affected[0], affected[0]]})
    assert duplicate.status_code == 422
    arbitrated = client.post("/projects/episode-001/domain-crew/conflicts/conflict-script-change/arbitrations", headers=headers,
        json={**_arbitration_ref(), "selected_version_id": "scene-v2", "expected_state_version": crew["state_version"],
              "resume_agent_id": screenwriter, "next_action": "script.write", "rationale": "Use approved version.",
              "affected_work_refs": affected})
    assert arbitrated.status_code == 200, arbitrated.text
    pending = arbitrated.json()["crew"]
    assert arbitrated.json()["arbitration"]["creator_user_id"] == pending["owner_user_id"]
    assert arbitrated.json()["arbitration"]["propagation_complete"] is False
    assert arbitrated.json()["task"]["status"] == "ready"
    assert arbitrated.json()["task"]["version_id"] == "scene-v2"
    refs = arbitrated.json()["arbitration"]["affected_work_refs"]
    assert [item["downstream_task_id"] for item in refs] == ["task-storyboard", "task-art"]
    assert all(item["reconfirmation_status"] == "required_pending" for item in refs)
    assert refs[0]["propagation_basis"] == {"arbitration_state_version": crew["state_version"],
        "arbitration_event_sequence": len(crew["events"]) + 1, "from_version_id": "scene-v1",
        "approved_version_id": "scene-v2"}
    pending_reload = TestClient(create_runtime_app(runtime_root=tmp_path)).get(
        "/projects/episode-001/domain-crew", headers=headers).json()["crew"]
    assert pending_reload["propagation_reconfirmations"] == pending["propagation_reconfirmations"]

    stale_reconfirm = client.post(
        f"/projects/episode-001/domain-crew/propagation-reconfirmations/{refs[0]['affected_ref_id']}/actions",
        headers=headers, json={"expected_state_version": pending["state_version"] - 1,
                              "responsible_agent_id": storyboard, "action": "acknowledge_reconfirm",
                              "observed_version_id": "scene-v2"})
    assert stale_reconfirm.status_code == 409

    unauthorized = client.post(f"/projects/episode-001/domain-crew/propagation-reconfirmations/{refs[0]['affected_ref_id']}/actions",
        headers=headers, json={"expected_state_version": pending["state_version"],
                              "responsible_agent_id": art, "action": "acknowledge_reconfirm",
                              "observed_version_id": "scene-v2"})
    assert unauthorized.status_code == 409
    first = client.post(f"/projects/episode-001/domain-crew/propagation-reconfirmations/{refs[0]['affected_ref_id']}/actions",
        headers=headers, json={"expected_state_version": pending["state_version"],
                              "responsible_agent_id": storyboard, "action": "acknowledge_reconfirm",
                              "observed_version_id": "scene-v2"})
    assert first.status_code == 200, first.text
    assert first.json()["arbitration"]["propagation_complete"] is False
    reconfirmed = client.post(f"/projects/episode-001/domain-crew/propagation-reconfirmations/{refs[1]['affected_ref_id']}/actions",
        headers=headers, json={"expected_state_version": first.json()["crew"]["state_version"],
                              "responsible_agent_id": art, "action": "acknowledge_reconfirm",
                              "observed_version_id": "scene-v2"})
    assert reconfirmed.status_code == 200, reconfirmed.text
    final = reconfirmed.json()["crew"]
    assert reconfirmed.json()["reconfirmation"]["reconfirmation_status"] == "reconfirmed"
    assert reconfirmed.json()["arbitration"]["propagation_complete"] is True
    assert reconfirmed.json()["task"]["status"] == "ready"

    leaf = _claim(client, headers, task_id="task-art", agent=art, version=final["state_version"])
    leaf_conflict = client.post("/projects/episode-001/domain-crew/conflicts", headers=headers, json={
        "entity_type": "scene", "entity_id": "scene-001", "version_id": "scene-v2",
        "conflict_id": "conflict-art-leaf", "expected_state_version": leaf["state_version"],
        "task_id": "task-art", "raised_by_agent_id": art, "reason": "Leaf art needs creator arbitration."})
    assert leaf_conflict.status_code == 200, leaf_conflict.text
    leaf_crew = leaf_conflict.json()["crew"]
    leaf_arbitration = client.post("/projects/episode-001/domain-crew/conflicts/conflict-art-leaf/arbitrations",
        headers=headers, json={"entity_type": "scene", "entity_id": "scene-001", "from_version_id": "scene-v2",
            "selected_version_id": "scene-v3", "expected_state_version": leaf_crew["state_version"],
            "resume_agent_id": art, "next_action": "art.create", "rationale": "Use creator-approved leaf version.",
            "affected_work_refs": []})
    assert leaf_arbitration.status_code == 200, leaf_arbitration.text
    assert leaf_arbitration.json()["arbitration"]["propagation_complete"] is True
    final = leaf_arbitration.json()["crew"]

    assert client.get("/projects/episode-001/domain-crew", headers=other_headers).status_code == 403
    reloaded_client = TestClient(create_runtime_app(runtime_root=tmp_path))
    reloaded = reloaded_client.get("/projects/episode-001/domain-crew", headers=headers)
    assert reloaded.status_code == 200, reloaded.text
    restored = reloaded.json()["crew"]
    assert restored == final
    assert [event["sequence"] for event in restored["events"]] == list(range(1, len(restored["events"]) + 1))
    assert all(item["owner_user_id"] == restored["owner_user_id"] for item in restored["tasks"])


def test_receiver_reject_and_identity_ref_authorization_fail_closed(tmp_path, monkeypatch) -> None:
    client, headers, other_headers = _client(tmp_path, monkeypatch)
    crew = _bootstrap(client, headers)
    writer, storyboard = "crew-001-screenwriter", "crew-001-storyboard"
    crew = _create_task(client, headers, version=1, task_id="task-script", agent=writer, action="script.write")

    wrong_claim = client.post("/projects/episode-001/domain-crew/tasks/task-script/claim", headers=headers,
                              json={"expected_state_version": crew["state_version"], "agent_id": storyboard})
    assert wrong_claim.status_code == 409
    crew = _claim(client, headers, task_id="task-script", agent=writer, version=crew["state_version"])
    mismatched = client.post("/projects/episode-001/domain-crew/messages", headers=headers, json={**_ref(),
        "version_id": "scene-v2", "message_id": "bad-version", "expected_state_version": crew["state_version"],
        "task_id": "task-script", "from_agent_id": writer, "to_agent_id": storyboard,
        "message_type": "request", "content": "Wrong version."})
    assert mismatched.status_code == 409
    crew = _handoff(client, headers, version=crew["state_version"], handoff_id="handoff-reject",
                    task_id="task-script", target_task_id="task-storyboard", sender=writer,
                    receiver=storyboard, next_action="storyboard.compose")
    wrong_receiver = client.post("/projects/episode-001/domain-crew/handoffs/handoff-reject/decisions", headers=headers,
        json={"expected_state_version": crew["state_version"], "receiver_agent_id": "crew-001-art", "decision": "accept"})
    assert wrong_receiver.status_code == 409
    rejected = _decide(client, headers, version=crew["state_version"], handoff_id="handoff-reject",
                       receiver=storyboard, decision="reject")
    task = next(item for item in rejected["tasks"] if item["task_id"] == "task-script")
    assert task["status"] == "revision_required"
    assert not any(item["task_id"] == "task-storyboard" for item in rejected["tasks"])

    other_project = client.post("/projects", json={"project_id": "other-project", "goal": "Other"}, headers=other_headers)
    assert other_project.status_code == 200
    hidden = client.get("/projects/episode-001/domain-crew", headers=other_headers)
    missing = client.get("/projects/missing/domain-crew", headers=headers)
    assert hidden.status_code == 403 and "crew-001" not in hidden.text
    assert missing.status_code in {403, 404} and "crew-001" not in missing.text


def test_message_and_handoff_target_identities_are_unique_under_current_and_concurrent_state(tmp_path, monkeypatch) -> None:
    client, headers, _ = _client(tmp_path, monkeypatch)
    _bootstrap(client, headers)
    writer, storyboard = "crew-001-screenwriter", "crew-001-storyboard"
    crew = _create_task(client, headers, version=1, task_id="task-script", agent=writer, action="script.write")
    crew = _claim(client, headers, task_id="task-script", agent=writer, version=crew["state_version"])
    message_payload = {**_ref(), "message_id": "message-unique", "expected_state_version": crew["state_version"],
        "task_id": "task-script", "from_agent_id": writer, "to_agent_id": storyboard,
        "message_type": "request", "content": "Concurrency-safe message identity."}
    clients = [TestClient(create_runtime_app(runtime_root=tmp_path)) for _ in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        message_statuses = list(pool.map(
            lambda concurrent_client: concurrent_client.post(
                "/projects/episode-001/domain-crew/messages", headers=headers, json=message_payload).status_code,
            clients,
        ))
    assert sorted(message_statuses) == [200, 409]
    crew = client.get("/projects/episode-001/domain-crew", headers=headers).json()["crew"]
    assert [item["message_id"] for item in crew["messages"]] == ["message-unique"]

    current_duplicate = client.post("/projects/episode-001/domain-crew/messages", headers=headers,
        json={**message_payload, "expected_state_version": crew["state_version"]})
    assert current_duplicate.status_code == 409
    assert len(client.get("/projects/episode-001/domain-crew", headers=headers).json()["crew"]["messages"]) == 1

    handoff_payload = {**_ref(), "expected_state_version": crew["state_version"], "task_id": "task-script",
        "target_task_id": "task-storyboard", "target_node_id": "node-task-storyboard", "from_agent_id": writer,
        "to_agent_id": storyboard, "next_action": "storyboard.compose", "objective": "Compose storyboard."}
    with ThreadPoolExecutor(max_workers=2) as pool:
        handoff_statuses = list(pool.map(
            lambda pair: pair[0].post("/projects/episode-001/domain-crew/handoffs", headers=headers,
                json={**handoff_payload, "handoff_id": pair[1]}).status_code,
            zip(clients, ("handoff-a", "handoff-b")),
        ))
    assert sorted(handoff_statuses) == [200, 409]
    crew = client.get("/projects/episode-001/domain-crew", headers=headers).json()["crew"]
    assert len(crew["handoffs"]) == 1
    winning_handoff_id = crew["handoffs"][0]["handoff_id"]

    current_handoff_duplicate = client.post("/projects/episode-001/domain-crew/handoffs", headers=headers,
        json={**handoff_payload, "handoff_id": "handoff-current", "expected_state_version": crew["state_version"]})
    assert current_handoff_duplicate.status_code == 409
    reserved_task = client.post("/projects/episode-001/domain-crew/tasks", headers=headers, json={**_ref(),
        "task_id": "task-storyboard", "node_id": "node-reserved", "expected_state_version": crew["state_version"],
        "assigned_agent_id": storyboard, "action": "storyboard.compose", "objective": "Must remain reserved."})
    assert reserved_task.status_code == 409

    store = RuntimeStore(tmp_path)
    collision = store.load_domain_crew("episode-001")
    collision["tasks"].append({"task_id": "task-storyboard", "node_id": "node-collision",
        "project_id": "episode-001", "owner_user_id": collision["owner_user_id"],
        "assigned_agent_id": storyboard, "action": "storyboard.compose", "objective": "Concurrent collision",
        **_ref(), "status": "ready", "claimed_by_agent_id": ""})
    store.write_domain_crew("episode-001", collision)
    raced_decision = client.post(
        f"/projects/episode-001/domain-crew/handoffs/{winning_handoff_id}/decisions", headers=headers,
        json={"expected_state_version": collision["state_version"], "receiver_agent_id": storyboard,
              "decision": "accept", "note": "Must revalidate target uniqueness."})
    assert raced_decision.status_code == 409
    reloaded = RuntimeStore(tmp_path).load_domain_crew("episode-001")
    assert [item["task_id"] for item in reloaded["tasks"]].count("task-storyboard") == 1
    assert len({item["message_id"] for item in reloaded["messages"]}) == len(reloaded["messages"])
