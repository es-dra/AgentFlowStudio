from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from apps.api.runtime_creative_agent import build_creative_agent_decision
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_script_generation_body import deterministic_script_body
from apps.api.runtime_storyboard_local import local_storyboard_shots


SAFE_EXECUTION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")


class ExecutionDriftError(RuntimeError):
    """The persisted authority no longer matches this deterministic execution."""


class HttpResponse(Protocol):
    status_code: int
    text: str

    def json(self) -> Any: ...


class AuthenticatedHttpTransport(Protocol):
    """An already authenticated, user-delegated Runtime Service transport."""

    def request(self, method: str, path: str, *, json: Mapping[str, Any] | None = None) -> HttpResponse: ...


@dataclass(frozen=True)
class ExecutionIds:
    execution_id: str

    def value(self, label: str) -> str:
        return f"{self.execution_id}-{label}"


class DomainCrewExecution:
    """Resumable provider-free screenwriter -> storyboard -> art execution."""

    def __init__(self, transport: AuthenticatedHttpTransport, *, project_id: str, crew_id: str,
                 execution_id: str, source_idea: str) -> None:
        if not SAFE_EXECUTION_ID.fullmatch(execution_id):
            raise ValueError("execution_id must be a safe deterministic identifier")
        self.transport = transport
        self.project_id = project_id
        self.crew_id = crew_id
        self.ids = ExecutionIds(execution_id)
        self.source_idea = source_idea.strip()
        if not self.source_idea:
            raise ValueError("source_idea is required")

    def run_phase_a(self) -> dict[str, Any]:
        crew = self._crew()
        self._validate_crew(crew)
        version = self.ids.value("scene-v1")
        script = self._work("screenwriter", version)
        crew = self._ensure_initial_task(crew, version)
        crew = self._ensure_claim(crew, "script", "screenwriter")
        crew = self._ensure_message(crew, "script-v1", "script", "screenwriter", "storyboard", version, script)
        crew = self._ensure_handoff(crew, "script-storyboard", "script", "storyboard", "storyboard", version)
        crew = self._ensure_accept(crew, "script-storyboard", "storyboard")
        storyboard = self._work("storyboard", version)
        crew = self._ensure_claim(crew, "storyboard", "storyboard")
        crew = self._ensure_message(crew, "storyboard-v1", "storyboard", "storyboard", "art", version, storyboard)
        crew = self._ensure_handoff(crew, "storyboard-art", "storyboard", "art", "art", version)
        crew = self._ensure_accept(crew, "storyboard-art", "art")
        art = self._work("art", version)
        crew = self._ensure_claim(crew, "art", "art")
        crew = self._ensure_message(crew, "art-v1", "art", "art", "screenwriter", version, art)
        crew = self._ensure_conflict(crew, version)
        self._validate_phase_a(crew, version)
        return self._evidence(crew, "awaiting_creator")

    def run_phase_b(self, *, approved_version_id: str) -> dict[str, Any]:
        crew = self._crew()
        self._validate_phase_b_boundary(crew, approved_version_id)
        script = self._work("screenwriter", approved_version_id)
        crew = self._ensure_claim(crew, "script", "screenwriter")
        crew = self._ensure_message(
            crew, "script-approved", "script", "screenwriter", "storyboard", approved_version_id, script,
        )
        storyboard = self._work("storyboard", approved_version_id)
        crew = self._ensure_reconfirm(crew, "storyboard", approved_version_id)
        crew = self._ensure_message(
            crew, "storyboard-approved", "storyboard", "storyboard", "art", approved_version_id, storyboard,
        )
        art = self._work("art", approved_version_id)
        crew = self._ensure_reconfirm(crew, "art", approved_version_id)
        crew = self._ensure_message(crew, "art-approved", "art", "art", "screenwriter", approved_version_id, art)
        self._validate_final(crew, approved_version_id)
        return self._evidence(crew, "propagation_complete")

    def expected_affected_work(self, approved_version_id: str) -> list[dict[str, str]]:
        version = self.ids.value("scene-v1")
        return [
            {"downstream_task_id": self.ids.value(f"task-{role}"),
             "downstream_node_id": self.ids.value(f"node-{role}"),
             "responsible_agent_id": self._agent_id(role), "responsible_agent_role": role,
             "entity_type": "scene", "entity_id": self.ids.value("scene"),
             "from_version_id": version, "approved_version_id": approved_version_id}
            for role in ("storyboard", "art")
        ]

    def _crew(self) -> dict[str, Any]:
        return self._request("GET", self._path())["crew"]

    def _request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        response = self.transport.request(method, path, json=payload)
        if response.status_code != 200:
            raise ExecutionDriftError(f"runtime request failed closed: {method} {path} status={response.status_code}")
        value = response.json()
        if not isinstance(value, dict):
            raise ExecutionDriftError("runtime response is not an object")
        return value

    def _post(self, suffix: str, crew: dict[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
        body = {**payload, "expected_state_version": crew["state_version"]}
        return self._request("POST", self._path(suffix), body)["crew"]

    def _ensure_initial_task(self, crew: dict[str, Any], version: str) -> dict[str, Any]:
        expected = self._task_record("script", "screenwriter", version, "ready")
        existing = self._find(crew["tasks"], "task_id", expected["task_id"])
        if existing:
            existing = self._named(crew["tasks"], "task_id", expected["task_id"], "initial task")
            self._match(existing, {key: value for key, value in expected.items() if key != "status"}, "initial task")
            return crew
        return self._post("/tasks", crew, {key: expected[key] for key in (
            "task_id", "node_id", "assigned_agent_id", "action", "objective", "entity_type", "entity_id", "version_id")})

    def _ensure_claim(self, crew: dict[str, Any], label: str, role: str) -> dict[str, Any]:
        task = self._task(crew, label)
        agent = self._agent_id(role)
        if task["claimed_by_agent_id"] == agent and task["status"] in {"claimed", "completed", "blocked_human"}:
            return crew
        if task["status"] != "ready" or task["assigned_agent_id"] != agent:
            raise ExecutionDriftError(f"{label} task is not claimable by expected adapter")
        return self._post(f"/tasks/{task['task_id']}/claim", crew, {"agent_id": agent})

    def _ensure_message(self, crew: dict[str, Any], label: str, task_label: str, sender: str, receiver: str,
                        version: str, work: dict[str, Any]) -> dict[str, Any]:
        message = {"message_id": self.ids.value(f"message-{label}"), "task_id": self.ids.value(f"task-{task_label}"),
                   "from_agent_id": self._agent_id(sender), "to_agent_id": self._agent_id(receiver),
                   "message_type": "request", "entity_type": "scene", "entity_id": self.ids.value("scene"),
                   "version_id": version, "content": self._message(sender, task_label, version, work)}
        existing = self._find(crew["messages"], "message_id", message["message_id"])
        if existing:
            existing = self._named(crew["messages"], "message_id", message["message_id"], "adapter message")
            self._match(existing, message, "adapter message")
            return crew
        return self._post("/messages", crew, message)

    def _ensure_handoff(self, crew: dict[str, Any], label: str, source: str, target: str, receiver: str,
                        version: str) -> dict[str, Any]:
        handoff = {"handoff_id": self.ids.value(f"handoff-{label}"), "task_id": self.ids.value(f"task-{source}"),
                   "target_task_id": self.ids.value(f"task-{target}"), "target_node_id": self.ids.value(f"node-{target}"),
                   "from_agent_id": self._agent_id(source if source != "script" else "screenwriter"),
                   "to_agent_id": self._agent_id(receiver), "next_action": self._action(receiver),
                   "objective": self.ids.value(f"objective-{target}"), "entity_type": "scene",
                   "entity_id": self.ids.value("scene"), "version_id": version}
        existing = self._find(crew["handoffs"], "handoff_id", handoff["handoff_id"])
        if existing:
            existing = self._named(crew["handoffs"], "handoff_id", handoff["handoff_id"], "handoff")
            self._match(existing, handoff, "handoff")
            return crew
        return self._post("/handoffs", crew, handoff)

    def _ensure_accept(self, crew: dict[str, Any], label: str, receiver: str) -> dict[str, Any]:
        handoff = self._named(crew["handoffs"], "handoff_id", self.ids.value(f"handoff-{label}"), "handoff")
        if handoff["status"] == "accepted":
            return crew
        if handoff["status"] != "pending_receiver":
            raise ExecutionDriftError("handoff decision drift")
        return self._post(f"/handoffs/{handoff['handoff_id']}/decisions", crew,
                          {"receiver_agent_id": self._agent_id(receiver), "decision": "accept",
                           "note": self.ids.value("adapter-accept")})

    def _ensure_conflict(self, crew: dict[str, Any], version: str) -> dict[str, Any]:
        conflict_id = self.ids.value("conflict-creator")
        existing = self._find(crew["conflicts"], "conflict_id", conflict_id)
        if existing:
            existing = self._named(crew["conflicts"], "conflict_id", conflict_id, "conflict")
            self._match(existing, {"task_id": self.ids.value("task-script"),
                "raised_by_agent_id": self._agent_id("screenwriter"), "entity_type": "scene",
                "entity_id": self.ids.value("scene"), "version_id": version}, "conflict")
            return crew
        return self._post("/conflicts", crew, {"conflict_id": conflict_id,
            "task_id": self.ids.value("task-script"), "raised_by_agent_id": self._agent_id("screenwriter"),
            "reason": self.ids.value("creator-version-change"), "entity_type": "scene",
            "entity_id": self.ids.value("scene"), "version_id": version})

    def _ensure_reconfirm(self, crew: dict[str, Any], role: str, version: str) -> dict[str, Any]:
        task_id = self.ids.value(f"task-{role}")
        record = self._named(crew["propagation_reconfirmations"], "downstream_task_id", task_id, "pending ref")
        if record["reconfirmation_status"] == "reconfirmed":
            self._match(record, {"approved_version_id": version,
                "confirmed_by_agent_id": self._agent_id(role)}, "reconfirmation")
            return crew
        if record["reconfirmation_status"] != "required_pending":
            raise ExecutionDriftError("reconfirmation status drift")
        return self._post(f"/propagation-reconfirmations/{record['affected_ref_id']}/actions", crew,
                          {"responsible_agent_id": self._agent_id(role), "action": "acknowledge_reconfirm",
                           "observed_version_id": version})

    def _work(self, role: str, version: str) -> dict[str, Any]:
        script = deterministic_script_body(f"{self.source_idea} [{version}]")
        if role == "screenwriter":
            output: Any = script
        else:
            shots = local_storyboard_shots(script, shot_count_hint=3)
            if role == "storyboard":
                output = shots
            else:
                request = PromptOptimizationRequest(node_id=self.ids.value("node-art"), node_type="image",
                    prompt_text=shots[0]["description"], generation_target="keyframe", generated_at="deterministic")
                output = build_creative_agent_decision(request,
                    sections=[{"title": "Storyboard", "text": shots[0]["description"]}], rules=[], slots={},
                    background=[], suppressed_context=[])
        return {"work_digest": self._digest(output), "input_digest": self._digest({"idea": self.source_idea,
                "version_id": version}), "provider_dispatch_count": 0}

    def _message(self, role: str, task: str, version: str, work: dict[str, Any]) -> str:
        return json.dumps({"action": self._action(role), "agent_id": self._agent_id(role),
            "entity_ref": {"entity_type": "scene", "entity_id": self.ids.value("scene"), "version_id": version},
            "execution_id": self.ids.execution_id, "input_digest": work["input_digest"], "project_id": self.project_id,
            "provider_dispatch_count": 0, "role": role, "schema_version": "afs_domain_crew_execution.v0.1",
            "task_id": self.ids.value(f"task-{task}"), "work_digest": work["work_digest"]},
            sort_keys=True, separators=(",", ":"))

    def _validate_crew(self, crew: dict[str, Any]) -> None:
        if crew.get("project_id") != self.project_id or crew.get("crew_id") != self.crew_id:
            raise ExecutionDriftError("project or crew identity drift")
        roles = {item.get("role"): item.get("agent_id") for item in crew.get("agents", [])}
        if any(roles.get(role) != self._agent_id(role) for role in ("screenwriter", "storyboard", "art")):
            raise ExecutionDriftError("domain agent identity drift")

    def _validate_phase_a(self, crew: dict[str, Any], version: str) -> None:
        self._validate_crew(crew)
        conflict = self._named(crew["conflicts"], "conflict_id", self.ids.value("conflict-creator"), "conflict")
        if conflict["status"] != "awaiting_creator" or conflict["version_id"] != version:
            raise ExecutionDriftError("phase A did not stop at creator boundary")

    def _validate_phase_b_boundary(self, crew: dict[str, Any], version: str) -> None:
        self._validate_crew(crew)
        arbitration = self._named(crew["arbitrations"], "conflict_id", self.ids.value("conflict-creator"), "arbitration")
        if arbitration["selected_version_id"] != version:
            raise ExecutionDriftError("creator arbitration version drift")
        expected = self.expected_affected_work(version)
        try:
            actual = [{key: item[key] for key in expected[0]} for item in arbitration["affected_work_refs"]]
            records = [{key: item[key] for key in expected[0]} for item in crew["propagation_reconfirmations"]
                       if item.get("arbitration_conflict_id") == self.ids.value("conflict-creator")]
            basis = arbitration["propagation_basis"]
        except (KeyError, TypeError) as exc:
            raise ExecutionDriftError("API-authoritative affected graph is incomplete") from exc
        if actual != expected:
            raise ExecutionDriftError("API-authoritative affected graph drift")
        if records != expected or basis.get("from_version_id") != self.ids.value("scene-v1") \
                or basis.get("approved_version_id") != version:
            raise ExecutionDriftError("propagation basis or pending set drift")

    def _validate_final(self, crew: dict[str, Any], version: str) -> None:
        arbitration = self._named(crew["arbitrations"], "conflict_id", self.ids.value("conflict-creator"), "arbitration")
        if not arbitration["propagation_complete"] or arbitration["propagation_status"] != "reconfirmed":
            raise ExecutionDriftError("propagation is not complete")
        records = [item for item in crew["propagation_reconfirmations"]
                   if item.get("arbitration_conflict_id") == self.ids.value("conflict-creator")]
        if len(records) != 2 or any(item.get("reconfirmation_status") != "reconfirmed" for item in records):
            raise ExecutionDriftError("final reconfirmation set drift")
        for role in ("screenwriter", "storyboard", "art"):
            task = self._task(crew, "script" if role == "screenwriter" else role)
            if task["version_id"] != version or task["claimed_by_agent_id"] != self._agent_id(role):
                raise ExecutionDriftError("final ownership or entity version drift")

    def _task_record(self, label: str, role: str, version: str, status: str) -> dict[str, str]:
        return {"task_id": self.ids.value(f"task-{label}"), "node_id": self.ids.value(f"node-{label}"),
                "assigned_agent_id": self._agent_id(role), "action": self._action(role),
                "objective": self.ids.value(f"objective-{label}"), "entity_type": "scene",
                "entity_id": self.ids.value("scene"), "version_id": version, "status": status}

    def _task(self, crew: dict[str, Any], label: str) -> dict[str, Any]:
        return self._named(crew["tasks"], "task_id", self.ids.value(f"task-{label}"), "task")

    def _agent_id(self, role: str) -> str:
        return f"{self.crew_id}-{role}"

    @staticmethod
    def _action(role: str) -> str:
        return {"screenwriter": "script.write", "storyboard": "storyboard.compose", "art": "art.create"}[role]

    def _path(self, suffix: str = "") -> str:
        return f"/projects/{self.project_id}/domain-crew{suffix}"

    @staticmethod
    def _digest(value: Any) -> str:
        return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
            separators=(",", ":")).encode("utf-8")).hexdigest()

    @staticmethod
    def _find(items: list[dict[str, Any]], key: str, value: str) -> dict[str, Any] | None:
        return next((item for item in items if item.get(key) == value), None)

    def _named(self, items: list[dict[str, Any]], key: str, value: str, label: str) -> dict[str, Any]:
        matches = [item for item in items if item.get(key) == value]
        if len(matches) != 1:
            raise ExecutionDriftError(f"{label} identity is missing or duplicated")
        return matches[0]

    @staticmethod
    def _match(actual: Mapping[str, Any], expected: Mapping[str, Any], label: str) -> None:
        if any(actual.get(key) != value for key, value in expected.items()):
            raise ExecutionDriftError(f"{label} content drift")

    def _evidence(self, crew: dict[str, Any], status: str) -> dict[str, Any]:
        return {"schema_version": "afs_domain_crew_execution_evidence.v0.1", "execution_id": self.ids.execution_id,
                "project_id": self.project_id, "status": status, "state_version": crew["state_version"],
                "adapter_action_message_ids": [item["message_id"] for item in crew["messages"]
                    if item["message_id"].startswith(self.ids.value("message-"))],
                "provider_dispatch_count": 0, "auth_boundary": "user_delegated_authenticated_transport"}


__all__ = ("AuthenticatedHttpTransport", "DomainCrewExecution", "ExecutionDriftError")
