from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


PROJECT_ID = "studio-domain-crew-qa"
CREW_ID = "crew-domain-qa"
QA_EMAIL = "domain-crew-qa@local.test"
QA_PASSWORD = "Local-QA-Domain-Crew-2026!"
QA_INVITE = "domain-crew-qa-invite"
ENTITY_REF = {"entity_type": "scene", "entity_id": "scene-001", "version_id": "scene-v1"}


def prepare_provider_free_domain_crew_qa(runtime_root: Path) -> dict[str, object]:
    runtime_root = Path(runtime_root).resolve()
    runtime_root.mkdir(parents=True, exist_ok=True)
    with _qa_environment(), TestClient(create_runtime_app(runtime_root=runtime_root)) as client:
        registered = client.post(
            "/auth/register",
            json={
                "email": QA_EMAIL,
                "password": QA_PASSWORD,
                "display_name": "Domain Crew QA",
                "invite_code": QA_INVITE,
            },
        )
        registered.raise_for_status()
        headers = {"Authorization": f"Bearer {registered.json()['session_token']}"}
        client.post(
            "/projects",
            json={"project_id": PROJECT_ID, "goal": "Provider-free authenticated domain crew Studio QA"},
            headers=headers,
        ).raise_for_status()
        crew = _post(client, headers, f"/projects/{PROJECT_ID}/domain-crew", {"crew_id": CREW_ID})
        agents = {item["role"]: item["agent_id"] for item in crew["agents"]}

        crew = _post(client, headers, f"/projects/{PROJECT_ID}/domain-crew/tasks", {
            **ENTITY_REF,
            "task_id": "task-script",
            "node_id": "node-task-script",
            "expected_state_version": crew["state_version"],
            "assigned_agent_id": agents["screenwriter"],
            "action": "script.write",
            "objective": "Write the creator-reviewed episode scene.",
        })
        crew = _post(client, headers, f"/projects/{PROJECT_ID}/domain-crew/tasks/task-script/claim", {
            "expected_state_version": crew["state_version"],
            "agent_id": agents["screenwriter"],
        })
        crew = _post(client, headers, f"/projects/{PROJECT_ID}/domain-crew/messages", {
            **ENTITY_REF,
            "message_id": "message-script-storyboard",
            "expected_state_version": crew["state_version"],
            "task_id": "task-script",
            "from_agent_id": agents["screenwriter"],
            "to_agent_id": agents["storyboard"],
            "message_type": "request",
            "content": "Scene version is ready for storyboard handoff.",
        })
        crew = _handoff(
            client, headers, crew, "handoff-script-storyboard", "task-script", "task-storyboard",
            "node-task-storyboard", agents["screenwriter"], agents["storyboard"], "storyboard.compose",
        )
        crew = _post(client, headers, f"/projects/{PROJECT_ID}/domain-crew/handoffs/handoff-script-storyboard/decisions", {
            "expected_state_version": crew["state_version"],
            "receiver_agent_id": agents["storyboard"],
            "decision": "accept",
            "note": "Storyboard agent accepts the exact scene version.",
        })
        crew = _post(client, headers, f"/projects/{PROJECT_ID}/domain-crew/tasks/task-storyboard/claim", {
            "expected_state_version": crew["state_version"],
            "agent_id": agents["storyboard"],
        })
        crew = _post(client, headers, f"/projects/{PROJECT_ID}/domain-crew/messages", {
            **ENTITY_REF,
            "message_id": "message-storyboard-art",
            "expected_state_version": crew["state_version"],
            "task_id": "task-storyboard",
            "from_agent_id": agents["storyboard"],
            "to_agent_id": agents["art"],
            "message_type": "request",
            "content": "Storyboard version is ready for art production.",
        })
        crew = _handoff(
            client, headers, crew, "handoff-storyboard-art", "task-storyboard", "task-art",
            "node-task-art", agents["storyboard"], agents["art"], "art.create",
        )
        crew = _post(client, headers, f"/projects/{PROJECT_ID}/domain-crew/handoffs/handoff-storyboard-art/decisions", {
            "expected_state_version": crew["state_version"],
            "receiver_agent_id": agents["art"],
            "decision": "accept",
            "note": "Art agent accepts the exact storyboard version.",
        })
        crew = _post(client, headers, f"/projects/{PROJECT_ID}/domain-crew/tasks/task-art/claim", {
            "expected_state_version": crew["state_version"],
            "agent_id": agents["art"],
        })
        crew = _post(client, headers, f"/projects/{PROJECT_ID}/domain-crew/conflicts", {
            **ENTITY_REF,
            "conflict_id": "conflict-script-change",
            "expected_state_version": crew["state_version"],
            "task_id": "task-script",
            "raised_by_agent_id": agents["screenwriter"],
            "reason": "Creator-approved script change must propagate to storyboard and art.",
        })

        affected_work_refs = [
            {
                "downstream_task_id": "task-storyboard",
                "downstream_node_id": "node-task-storyboard",
                "responsible_agent_id": agents["storyboard"],
                "responsible_agent_role": "storyboard",
                "entity_type": "scene",
                "entity_id": "scene-001",
                "from_version_id": "scene-v1",
                "approved_version_id": "scene-v2",
            },
            {
                "downstream_task_id": "task-art",
                "downstream_node_id": "node-task-art",
                "responsible_agent_id": agents["art"],
                "responsible_agent_role": "art",
                "entity_type": "scene",
                "entity_id": "scene-001",
                "from_version_id": "scene-v1",
                "approved_version_id": "scene-v2",
            },
        ]
        saved = client.put(
            f"/projects/{PROJECT_ID}/studio-state",
            headers=headers,
            json={"state": _studio_state()},
        )
        saved.raise_for_status()
        reloaded = client.get(f"/projects/{PROJECT_ID}/domain-crew", headers=headers)
        reloaded.raise_for_status()
        persisted = reloaded.json()["crew"]
        ready = (
            len(persisted["agents"]) == 9
            and [item["task_id"] for item in persisted["tasks"]] == ["task-script", "task-storyboard", "task-art"]
            and persisted["conflicts"][-1]["status"] == "awaiting_creator"
        )
        return {
            "runtime_root": str(runtime_root),
            "project_id": PROJECT_ID,
            "email": QA_EMAIL,
            "password": QA_PASSWORD,
            "crew_id": CREW_ID,
            "state_version": persisted["state_version"],
            "agent_count": len(persisted["agents"]),
            "task_count": len(persisted["tasks"]),
            "provider_calls_started": False,
            "evidence_boundary": "domain_crew_ledger_pass",
            "non_claim": "Manual fixture/API/UI progression does not prove agent-controlled execution.",
            "browser_preflight": {
                "ready": ready,
                "desktop_viewport": {"width": 1440, "height": 960},
                "mobile_viewport": {"width": 390, "height": 844},
                "arbitration_conflict_id": "conflict-script-change",
                "selected_version_id": "scene-v2",
                "resume_agent_id": agents["screenwriter"],
                "next_action": "script.write",
                "affected_work_refs_json": json.dumps(affected_work_refs, ensure_ascii=False),
                "expected_pending_task_ids": ["task-storyboard", "task-art"],
                "flow": [
                    "login and select the prepared project",
                    "open 数字剧组 and verify nine authenticated roles",
                    "submit creator arbitration with the exact graph-validated affected work fixture",
                    "verify API-returned propagation basis and two pending reconfirmations",
                    "reconfirm storyboard then art using the responsible authenticated agent action",
                    "reload and verify the same persisted completed propagation set",
                    "repeat read/focus/scroll checks at 390x844 with zero relevant console errors",
                ],
            },
        }


def _post(client: TestClient, headers: dict[str, str], route: str, payload: dict[str, object]) -> dict[str, object]:
    response = client.post(route, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["crew"]


def _handoff(
    client: TestClient,
    headers: dict[str, str],
    crew: dict[str, object],
    handoff_id: str,
    task_id: str,
    target_task_id: str,
    target_node_id: str,
    sender: str,
    receiver: str,
    next_action: str,
) -> dict[str, object]:
    return _post(client, headers, f"/projects/{PROJECT_ID}/domain-crew/handoffs", {
        **ENTITY_REF,
        "handoff_id": handoff_id,
        "expected_state_version": crew["state_version"],
        "task_id": task_id,
        "target_task_id": target_task_id,
        "target_node_id": target_node_id,
        "from_agent_id": sender,
        "to_agent_id": receiver,
        "next_action": next_action,
        "objective": f"Continue {next_action} against the exact scene version.",
    })


def _studio_state() -> dict[str, object]:
    nodes: dict[str, object] = {}
    for index, (node_id, node_type, title) in enumerate((
        ("node-task-script", "script", "编剧 · 场景脚本"),
        ("node-task-storyboard", "text", "分镜 · 镜头编排"),
        ("node-task-art", "image", "美术 · 场景画面"),
    )):
        nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            "title": title,
            "x": 180 + index * 380,
            "y": 240,
            "w": 300,
            "h": 220,
            "prompt": "Provider-free domain crew QA fixture.",
            "content": "",
            "status": "idle",
            "result": "",
            "previewUrl": "",
            "params": {},
        }
    return {
        "meta": {"projectId": PROJECT_ID, "projectName": "数字剧组 QA", "canvasName": "编剧到美术", "seq": 1, "updated_at": ""},
        "viewport": {"x": 40, "y": 120, "scale": 0.82},
        "nodes": nodes,
        "edges": {},
        "groups": {},
        "assets": [],
        "order": list(nodes),
    }


@contextmanager
def _qa_environment() -> Iterator[None]:
    values = {
        "AFS_AUTH_ENABLED": "true",
        "AFS_INVITE_CODES": QA_INVITE,
        "AFS_ALLOW_REMOTE_LLM": "false",
        "AFS_ALLOW_REMOTE_IMAGE": "false",
        "AFS_ALLOW_REMOTE_VISION": "false",
        "AFS_ALLOW_REMOTE_VIDEO": "false",
        "AFS_ALLOW_REMOTE_ASR": "false",
    }
    before = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in before.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare provider-free authenticated Studio domain-crew browser QA.")
    parser.add_argument("--runtime-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare_provider_free_domain_crew_qa(args.runtime_root), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
