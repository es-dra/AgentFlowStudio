import hashlib
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from agentflow.harness.json_io import exclusive_file_lock
from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_domain_crew_models import (
    ArbitrationRequest, ConflictCreateRequest, CrewCreateRequest, HandoffCreateRequest,
    HandoffDecisionRequest, MessageCreateRequest, ReconfirmationRequest, TaskClaimRequest, TaskCreateRequest,
)
from apps.api.runtime_store import RuntimeStore


ROLE_CAPABILITIES = {
    "screenwriter": ("script.write",), "storyboard": ("storyboard.compose",), "art": ("art.create",),
    "director": ("direction.review",), "continuity": ("continuity.review",), "qa": ("quality.review",),
    "audio": ("audio.produce",), "edit": ("edit.assemble",), "export": ("export.deliver",),
}


def register_runtime_domain_crew_routes(app: FastAPI, store: RuntimeStore, auth: RuntimeAuthStore) -> None:
    @app.post("/projects/{project_id}/domain-crew")
    def create_crew(project_id: str, body: CrewCreateRequest, request: Request) -> dict[str, Any]:
        owner_id = _require_owner(store, auth, request, project_id)
        with exclusive_file_lock(store.domain_crew_lock_path(project_id)):
            try:
                current = store.load_domain_crew(project_id)
            except KeyError:
                current = None
            if current:
                _require_crew_owner(current, owner_id)
                if current["crew_id"] != body.crew_id:
                    raise HTTPException(status_code=409, detail="project domain crew already exists")
                return {"crew": current, "idempotent_replay": True}
            agents = [
                {"agent_id": f"{body.crew_id}-{role}", "role": role, "owner_user_id": owner_id,
                 "capabilities": list(capabilities), "status": "registered"}
                for role, capabilities in ROLE_CAPABILITIES.items()
            ]
            crew = {"artifact_type": "afs_runtime_domain_crew", "schema_version": "afs_domain_crew.v0.1",
                    "project_id": project_id, "crew_id": body.crew_id, "owner_user_id": owner_id,
                    "state_version": 1, "agents": agents, "tasks": [], "messages": [], "handoffs": [],
                    "conflicts": [], "arbitrations": [], "propagation_reconfirmations": [],
                    "events": [], "updated_at": _now()}
            _event(crew, "crew_registered", creator_user_id=owner_id)
            store.write_domain_crew(project_id, crew)
            return {"crew": crew, "idempotent_replay": False}

    @app.get("/projects/{project_id}/domain-crew")
    def get_crew(project_id: str, request: Request) -> dict[str, Any]:
        owner_id = _require_owner(store, auth, request, project_id)
        crew = _load(store, project_id)
        _require_crew_owner(crew, owner_id)
        return {"crew": crew}

    @app.post("/projects/{project_id}/domain-crew/tasks")
    def create_task(project_id: str, body: TaskCreateRequest, request: Request) -> dict[str, Any]:
        owner_id = _require_owner(store, auth, request, project_id)
        with exclusive_file_lock(store.domain_crew_lock_path(project_id)):
            crew = _mutable(store, project_id, owner_id, body.expected_state_version)
            if _task_id_reserved(crew, body.task_id):
                raise HTTPException(status_code=409, detail="domain task id already exists")
            agent = _agent(crew, body.assigned_agent_id)
            _require_capability(agent, body.action)
            task = {**_dump(body, "expected_state_version"), "project_id": project_id,
                    "owner_user_id": owner_id, "status": "ready", "claimed_by_agent_id": ""}
            crew["tasks"].append(task)
            _commit(store, crew, "task_created", actor_agent_id=agent["agent_id"], task_id=body.task_id)
            return {"crew": crew, "task": task}

    @app.post("/projects/{project_id}/domain-crew/tasks/{task_id}/claim")
    def claim_task(project_id: str, task_id: str, body: TaskClaimRequest, request: Request) -> dict[str, Any]:
        owner_id = _require_owner(store, auth, request, project_id)
        with exclusive_file_lock(store.domain_crew_lock_path(project_id)):
            crew = _mutable(store, project_id, owner_id, body.expected_state_version)
            task, agent = _task(crew, task_id), _agent(crew, body.agent_id)
            if task["assigned_agent_id"] != agent["agent_id"] or task["status"] != "ready":
                raise HTTPException(status_code=409, detail="task is not claimable by this agent")
            task.update(status="claimed", claimed_by_agent_id=agent["agent_id"])
            _commit(store, crew, "task_claimed", actor_agent_id=agent["agent_id"], task_id=task_id)
            return {"crew": crew, "task": task}

    @app.post("/projects/{project_id}/domain-crew/messages")
    def create_message(project_id: str, body: MessageCreateRequest, request: Request) -> dict[str, Any]:
        owner_id = _require_owner(store, auth, request, project_id)
        with exclusive_file_lock(store.domain_crew_lock_path(project_id)):
            crew = _mutable(store, project_id, owner_id, body.expected_state_version)
            task = _task(crew, body.task_id)
            sender, receiver = _agent(crew, body.from_agent_id), _agent(crew, body.to_agent_id)
            _same_ref(task, body)
            if (_find(crew["messages"], "message_id", body.message_id)
                    or task["claimed_by_agent_id"] != sender["agent_id"] or sender == receiver):
                raise HTTPException(status_code=409, detail="message identity or sender ownership is invalid")
            message = {**_dump(body, "expected_state_version"), "project_id": project_id,
                       "owner_user_id": owner_id, "sent_at": _now()}
            crew["messages"].append(message)
            _commit(store, crew, "message_sent", actor_agent_id=sender["agent_id"], task_id=body.task_id)
            return {"crew": crew, "message": message}

    @app.post("/projects/{project_id}/domain-crew/handoffs")
    def create_handoff(project_id: str, body: HandoffCreateRequest, request: Request) -> dict[str, Any]:
        owner_id = _require_owner(store, auth, request, project_id)
        with exclusive_file_lock(store.domain_crew_lock_path(project_id)):
            crew = _mutable(store, project_id, owner_id, body.expected_state_version)
            task = _task(crew, body.task_id)
            sender, receiver = _agent(crew, body.from_agent_id), _agent(crew, body.to_agent_id)
            _same_ref(task, body)
            if task["claimed_by_agent_id"] != sender["agent_id"]:
                raise HTTPException(status_code=409, detail="handoff sender does not own the claimed task")
            if _find(crew["handoffs"], "handoff_id", body.handoff_id) or _task_id_reserved(crew, body.target_task_id):
                raise HTTPException(status_code=409, detail="handoff or target task id already exists")
            _require_capability(receiver, body.next_action)
            handoff = {**_dump(body, "expected_state_version"), "project_id": project_id,
                       "owner_user_id": owner_id, "status": "pending_receiver", "created_at": _now()}
            crew["handoffs"].append(handoff)
            _commit(store, crew, "handoff_requested", actor_agent_id=sender["agent_id"], task_id=body.task_id)
            return {"crew": crew, "handoff": handoff}

    @app.post("/projects/{project_id}/domain-crew/handoffs/{handoff_id}/decisions")
    def decide_handoff(project_id: str, handoff_id: str, body: HandoffDecisionRequest, request: Request) -> dict[str, Any]:
        owner_id = _require_owner(store, auth, request, project_id)
        with exclusive_file_lock(store.domain_crew_lock_path(project_id)):
            crew = _mutable(store, project_id, owner_id, body.expected_state_version)
            handoff, receiver = _required(crew["handoffs"], "handoff_id", handoff_id, "handoff"), _agent(crew, body.receiver_agent_id)
            if handoff["status"] != "pending_receiver" or handoff["to_agent_id"] != receiver["agent_id"]:
                raise HTTPException(status_code=409, detail="handoff is not decidable by this receiver")
            if _task_id_reserved(crew, handoff["target_task_id"], exclude_handoff_id=handoff_id):
                raise HTTPException(status_code=409, detail="handoff target task id is no longer unique")
            source = _task(crew, handoff["task_id"])
            handoff.update(status="accepted" if body.decision == "accept" else "rejected", decision_note=body.note, decided_at=_now())
            if body.decision == "accept":
                source["status"] = "completed"
                crew["tasks"].append({"task_id": handoff["target_task_id"], "project_id": project_id,
                    "node_id": handoff["target_node_id"],
                    "owner_user_id": owner_id, "assigned_agent_id": receiver["agent_id"], "action": handoff["next_action"],
                    "objective": handoff["objective"], "entity_type": handoff["entity_type"], "entity_id": handoff["entity_id"],
                    "version_id": handoff["version_id"], "status": "ready", "claimed_by_agent_id": ""})
            else:
                source["status"] = "revision_required"
            _commit(store, crew, f"handoff_{body.decision}ed", actor_agent_id=receiver["agent_id"], task_id=source["task_id"])
            return {"crew": crew, "handoff": handoff}

    @app.post("/projects/{project_id}/domain-crew/conflicts")
    def create_conflict(project_id: str, body: ConflictCreateRequest, request: Request) -> dict[str, Any]:
        owner_id = _require_owner(store, auth, request, project_id)
        with exclusive_file_lock(store.domain_crew_lock_path(project_id)):
            crew = _mutable(store, project_id, owner_id, body.expected_state_version)
            task, agent = _task(crew, body.task_id), _agent(crew, body.raised_by_agent_id)
            _same_ref(task, body)
            if (task["claimed_by_agent_id"] != agent["agent_id"]
                    or task["status"] not in {"claimed", "completed"}
                    or _find(crew["conflicts"], "conflict_id", body.conflict_id)):
                raise HTTPException(status_code=409, detail="conflict identity or task ownership is invalid")
            conflict = {**_dump(body, "expected_state_version"), "project_id": project_id,
                        "owner_user_id": owner_id, "status": "awaiting_creator", "escalation": "human_creator", "created_at": _now()}
            crew["conflicts"].append(conflict)
            task["status"] = "blocked_human"
            _commit(store, crew, "conflict_escalated", actor_agent_id=agent["agent_id"], task_id=body.task_id)
            return {"crew": crew, "conflict": conflict}

    @app.post("/projects/{project_id}/domain-crew/conflicts/{conflict_id}/arbitrations")
    def arbitrate(project_id: str, conflict_id: str, body: ArbitrationRequest, request: Request) -> dict[str, Any]:
        owner_id = _require_owner(store, auth, request, project_id)
        with exclusive_file_lock(store.domain_crew_lock_path(project_id)):
            crew = _mutable(store, project_id, owner_id, body.expected_state_version)
            conflict = _required(crew["conflicts"], "conflict_id", conflict_id, "conflict")
            task, agent = _task(crew, conflict["task_id"]), _agent(crew, body.resume_agent_id)
            _same_arbitration_ref(conflict, body)
            _require_capability(agent, body.next_action)
            if conflict["status"] != "awaiting_creator" or task["status"] != "blocked_human":
                raise HTTPException(status_code=409, detail="conflict is not awaiting creator arbitration")
            expected_affected = _derived_affected_work(crew, conflict, body.selected_version_id)
            submitted_affected = [item.model_dump(mode="json") for item in body.affected_work_refs]
            if submitted_affected != expected_affected:
                raise HTTPException(status_code=409, detail="affected downstream work set is incomplete or foreign")
            basis = {"arbitration_state_version": crew["state_version"],
                     "arbitration_event_sequence": len(crew["events"]) + 1,
                     "from_version_id": conflict["version_id"], "approved_version_id": body.selected_version_id}
            arbitration = {**_dump(body, "expected_state_version", "affected_work_refs"), "conflict_id": conflict_id,
                           "project_id": project_id, "creator_user_id": owner_id,
                           "propagation_status": "reconfirmation_pending" if expected_affected else "reconfirmed",
                           "propagation_complete": not expected_affected,
                           "propagation_basis": basis,
                           "recorded_at": _now()}
            reconfirmations = []
            for affected in expected_affected:
                downstream_task = _task(crew, affected["downstream_task_id"])
                ref_id = "affected-" + hashlib.sha256(
                    f"{project_id}:{conflict_id}:{downstream_task['task_id']}".encode("utf-8")
                ).hexdigest()[:20]
                reconfirmation = {**affected, "affected_ref_id": ref_id, "project_id": project_id,
                                  "arbitration_conflict_id": conflict_id, "reconfirmation_status": "required_pending",
                                  "required_action": "acknowledge_reconfirm", "propagation_basis": basis,
                                  "confirmed_at": ""}
                reconfirmations.append(reconfirmation)
                downstream_task.update(status="reconfirmation_required",
                                       pending_version_id=affected["approved_version_id"])
            arbitration["affected_work_refs"] = reconfirmations
            crew["arbitrations"].append(arbitration)
            crew["propagation_reconfirmations"].extend(reconfirmations)
            conflict.update(status="resolved_by_creator", arbitration_version_id=body.selected_version_id)
            task.update(version_id=body.selected_version_id, assigned_agent_id=agent["agent_id"],
                        action=body.next_action, status="ready", claimed_by_agent_id="")
            if any(item["downstream_task_id"] == task["task_id"] for item in reconfirmations):
                task.update(status="reconfirmation_required", pending_version_id=body.selected_version_id)
            _commit(store, crew, "creator_arbitrated", creator_user_id=owner_id, task_id=task["task_id"])
            return {"crew": crew, "arbitration": arbitration, "task": task}

    @app.post("/projects/{project_id}/domain-crew/propagation-reconfirmations/{affected_ref_id}/actions")
    def reconfirm_propagation(project_id: str, affected_ref_id: str, body: ReconfirmationRequest,
                              request: Request) -> dict[str, Any]:
        owner_id = _require_owner(store, auth, request, project_id)
        with exclusive_file_lock(store.domain_crew_lock_path(project_id)):
            crew = _mutable(store, project_id, owner_id, body.expected_state_version)
            record = _required(crew["propagation_reconfirmations"], "affected_ref_id", affected_ref_id,
                               "propagation reconfirmation")
            agent = _agent(crew, body.responsible_agent_id)
            task = _task(crew, record["downstream_task_id"])
            if (record["reconfirmation_status"] != "required_pending"
                    or record["responsible_agent_id"] != agent["agent_id"]
                    or record["responsible_agent_role"] != agent["role"]
                    or record["approved_version_id"] != body.observed_version_id
                    or task["node_id"] != record["downstream_node_id"]
                    or task.get("pending_version_id") != body.observed_version_id):
                raise HTTPException(status_code=409, detail="propagation reconfirmation identity or version changed")
            record.update(reconfirmation_status="reconfirmed", confirmed_at=_now(),
                          confirmed_by_agent_id=agent["agent_id"], action=body.action)
            task.update(version_id=body.observed_version_id, pending_version_id="", status="ready")
            pending = {item["affected_ref_id"] for item in crew["propagation_reconfirmations"]
                       if item["arbitration_conflict_id"] == record["arbitration_conflict_id"]
                       and item["reconfirmation_status"] == "required_pending"}
            arbitration = _required(crew["arbitrations"], "conflict_id", record["arbitration_conflict_id"], "arbitration")
            arbitration_ref = _required(arbitration["affected_work_refs"], "affected_ref_id", affected_ref_id,
                                        "arbitration affected work")
            arbitration_ref.update(reconfirmation_status="reconfirmed", confirmed_at=record["confirmed_at"],
                                   confirmed_by_agent_id=agent["agent_id"], action=body.action)
            arbitration.update(propagation_status="reconfirmation_pending" if pending else "reconfirmed",
                               propagation_complete=not pending)
            _commit(store, crew, "downstream_reconfirmed", actor_agent_id=agent["agent_id"], task_id=task["task_id"])
            return {"crew": crew, "reconfirmation": record, "arbitration": arbitration, "task": task}


def _require_owner(store: RuntimeStore, auth: RuntimeAuthStore, request: Request, project_id: str) -> str:
    if not auth.enabled():
        raise HTTPException(status_code=403, detail="authenticated domain crew requires runtime auth")
    if store.is_project_deleted(project_id) or not store.project_manifest_path(project_id).is_file():
        raise HTTPException(status_code=404, detail="project not found")
    user_id = str(auth.require_user(request).get("user_id") or "")
    if not user_id or not auth.user_can_access_project(user_id, project_id):
        raise HTTPException(status_code=403, detail="project access denied")
    return user_id


def _load(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    try:
        return store.load_domain_crew(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="domain crew not found") from exc


def _mutable(store: RuntimeStore, project_id: str, owner_id: str, expected: int) -> dict[str, Any]:
    crew = _load(store, project_id)
    _require_crew_owner(crew, owner_id)
    if crew["state_version"] != expected: raise HTTPException(409, "domain crew state version changed")
    return crew


def _require_crew_owner(crew: dict[str, Any], owner_id: str) -> None:
    if crew.get("owner_user_id") != owner_id: raise HTTPException(403, "domain crew access denied")


def _find(items: list[dict[str, Any]], key: str, value: str) -> dict[str, Any] | None:
    return next((item for item in items if item.get(key) == value), None)


def _task_id_reserved(crew: dict[str, Any], task_id: str, exclude_handoff_id: str = "") -> bool:
    return bool(_find(crew["tasks"], "task_id", task_id)) or any(
        item["target_task_id"] == task_id and item["handoff_id"] != exclude_handoff_id
        and item["status"] in {"pending_receiver", "accepted"} for item in crew["handoffs"])


def _required(items: list[dict[str, Any]], key: str, value: str, label: str) -> dict[str, Any]:
    item = _find(items, key, value)
    if not item: raise HTTPException(404, f"{label} not found")
    return item


def _agent(crew: dict[str, Any], agent_id: str) -> dict[str, Any]: return _required(crew["agents"], "agent_id", agent_id, "domain agent")


def _task(crew: dict[str, Any], task_id: str) -> dict[str, Any]: return _required(crew["tasks"], "task_id", task_id, "domain task")


def _require_capability(agent: dict[str, Any], action: str) -> None:
    if action not in agent["capabilities"]: raise HTTPException(409, "agent capability does not authorize task action")


def _same_ref(record: dict[str, Any], body: Any) -> None:
    if any(record[key] != getattr(body, key) for key in ("entity_type", "entity_id", "version_id")): raise HTTPException(409, "entity version reference changed")


def _same_arbitration_ref(conflict: dict[str, Any], body: ArbitrationRequest) -> None:
    if (conflict["entity_type"], conflict["entity_id"], conflict["version_id"]) != (body.entity_type, body.entity_id, body.from_version_id):
        raise HTTPException(409, "conflict entity version reference changed")


def _derived_affected_work(crew: dict[str, Any], conflict: dict[str, Any], approved_version_id: str) -> list[dict[str, Any]]:
    reached, ordered, changed = {conflict["task_id"]}, [], True
    while changed:
        changed = False
        for handoff in crew["handoffs"]:
            target_id = handoff["target_task_id"]
            if handoff["status"] == "accepted" and handoff["task_id"] in reached and target_id not in reached:
                reached.add(target_id)
                ordered.append(target_id)
                changed = True
    affected = []
    for task_id in ordered:
        task = _task(crew, task_id)
        agent = _agent(crew, task["assigned_agent_id"])
        if (task["entity_type"], task["entity_id"], task["version_id"]) != (
                conflict["entity_type"], conflict["entity_id"], conflict["version_id"]):
            raise HTTPException(status_code=409, detail="persisted downstream dependency version changed")
        affected.append({"downstream_task_id": task_id, "downstream_node_id": task["node_id"],
                         "responsible_agent_id": agent["agent_id"], "responsible_agent_role": agent["role"],
                         "entity_type": task["entity_type"], "entity_id": task["entity_id"],
                         "from_version_id": task["version_id"], "approved_version_id": approved_version_id})
    return affected


def _dump(body: Any, *exclude: str) -> dict[str, Any]:
    return body.model_dump(mode="json", exclude=set(exclude))


def _event(crew: dict[str, Any], event_type: str, **refs: str) -> None:
    crew["events"].append({"sequence": len(crew["events"]) + 1, "event_type": event_type,
                           "project_id": crew["project_id"], **refs, "recorded_at": _now()})


def _commit(store: RuntimeStore, crew: dict[str, Any], event_type: str, **refs: str) -> None:
    _event(crew, event_type, **refs)
    crew["state_version"] += 1
    crew["updated_at"] = _now()
    store.write_domain_crew(crew["project_id"], crew)


def _now() -> str: return datetime.now(timezone.utc).isoformat()
