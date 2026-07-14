from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol


SAFE_EXECUTION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
ROLE_ORDER = (
    "screenwriter", "storyboard", "art", "director", "continuity", "qa", "audio", "edit", "export",
)
ROLE_ACTIONS = {
    "screenwriter": "script.write",
    "storyboard": "storyboard.compose",
    "art": "art.create",
    "director": "direction.review",
    "continuity": "continuity.review",
    "qa": "quality.review",
    "audio": "audio.produce",
    "edit": "edit.assemble",
    "export": "export.deliver",
}
ROLE_RESPONSIBILITIES = {
    "screenwriter": "确认剧本选择与本集叙事意图",
    "storyboard": "更新十五镜分镜与节奏责任",
    "art": "校准角色、场景与镜头画面责任",
    "director": "复核表演、镜头与叙事方向",
    "continuity": "检查角色、空间、灯光与雨势连续性",
    "qa": "执行叙事、一致性和技术质量门禁",
    "audio": "更新对白、音乐、音效与混音计划",
    "edit": "重组镜头、字幕与音频时间线",
    "export": "核对交付就绪与精确导出证据",
}


class EpisodeExecutionDriftError(RuntimeError):
    """Persisted project authority no longer matches the deterministic episode execution."""


class HttpResponse(Protocol):
    status_code: int
    text: str

    def json(self) -> Any: ...


class AuthenticatedHttpTransport(Protocol):
    """An already authenticated Runtime Service HTTP transport."""

    def request(self, method: str, path: str, *, json: Mapping[str, Any] | None = None) -> HttpResponse: ...


@dataclass(frozen=True)
class EpisodeExecutionIds:
    execution_id: str

    def value(self, label: str) -> str:
        return f"{self.execution_id}-{label}"


class RepresentativeEpisodeExecution:
    """Provider-free nine-role Rainlight execution over authenticated public Runtime APIs."""

    def __init__(
        self,
        transport: AuthenticatedHttpTransport,
        *,
        project_id: str,
        crew_id: str,
        run_id: str,
        execution_id: str,
        revision: Mapping[str, Any],
    ) -> None:
        if not SAFE_EXECUTION_ID.fullmatch(execution_id):
            raise ValueError("execution_id must be a safe deterministic identifier")
        self.transport = transport
        self.project_id = project_id
        self.crew_id = crew_id
        self.run_id = run_id
        self.ids = EpisodeExecutionIds(execution_id)
        self.revision = copy.deepcopy(dict(revision))
        self._validate_revision_contract()

    @classmethod
    def from_revision_path(
        cls,
        transport: AuthenticatedHttpTransport,
        *,
        project_id: str,
        crew_id: str,
        run_id: str,
        execution_id: str,
        revision_path: str | Path,
    ) -> "RepresentativeEpisodeExecution":
        try:
            revision = json.loads(Path(revision_path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError("episode revision fixture is unreadable") from exc
        return cls(
            transport,
            project_id=project_id,
            crew_id=crew_id,
            run_id=run_id,
            execution_id=execution_id,
            revision=revision,
        )

    def run_phase_a(self) -> dict[str, Any]:
        run = self._run()
        self._validate_v1_binding(run)
        crew = self._crew()
        self._validate_crew(crew)
        crew = self._ensure_initial_task(crew)
        for index, role in enumerate(ROLE_ORDER):
            crew = self._ensure_claim(crew, role)
            receiver = ROLE_ORDER[index + 1] if index + 1 < len(ROLE_ORDER) else "screenwriter"
            crew = self._ensure_message(crew, role, receiver, phase="v1")
            if index + 1 < len(ROLE_ORDER):
                crew = self._ensure_handoff(crew, role, receiver)
                crew = self._ensure_accept(crew, role, receiver)
        crew = self._ensure_conflict(crew)
        self._validate_phase_a(crew)
        return self._evidence(crew, run, "awaiting_creator_revision")

    def record_creator_revision(self) -> dict[str, Any]:
        crew = self._crew()
        existing = self._find(crew.get("arbitrations") or [], "conflict_id", self.ids.value("conflict-creator-v2"))
        if existing:
            self._validate_arbitration_boundary(crew)
            return self._evidence(crew, self._run(), "reconfirmation_pending")
        self._validate_phase_a(crew)
        affected = self._derive_authoritative_affected_work(crew, require_source_version=True)
        if [item["responsible_agent_role"] for item in affected] != list(ROLE_ORDER[1:]):
            raise EpisodeExecutionDriftError("persisted dependency graph does not cover the exact downstream crew")
        response = self._post(
            f"/conflicts/{self.ids.value('conflict-creator-v2')}/arbitrations",
            crew,
            {
                "entity_type": "project",
                "entity_id": self.project_id,
                "from_version_id": self.from_version,
                "selected_version_id": self.approved_version,
                "resume_agent_id": self._agent_id("screenwriter"),
                "next_action": ROLE_ACTIONS["screenwriter"],
                "rationale": self.revision["creator_rationale"],
                # The caller cannot supply this list. It is reconstructed from the persisted accepted handoff graph,
                # and the Runtime API independently derives and validates completeness before mutation.
                "affected_work_refs": affected,
            },
        )
        self._validate_arbitration_boundary(response)
        return self._evidence(response, self._run(), "reconfirmation_pending")

    def reconfirm_next(self, role: str) -> dict[str, Any]:
        if role not in ROLE_ORDER[1:]:
            raise ValueError("role is not a downstream reconfirmation responsibility")
        crew = self._crew()
        self._validate_arbitration_boundary(crew)
        records = self._execution_reconfirmations(crew)
        requested = self._record_for_role(records, role)
        if requested.get("reconfirmation_status") == "reconfirmed":
            return crew
        pending = [item for item in records if item.get("reconfirmation_status") == "required_pending"]
        expected = next((item for item in ROLE_ORDER[1:] if any(
            record.get("responsible_agent_role") == item for record in pending
        )), None)
        if expected is None:
            if requested.get("reconfirmation_status") != "reconfirmed":
                raise EpisodeExecutionDriftError("reconfirmation set is incomplete")
            return crew
        if role != expected:
            raise EpisodeExecutionDriftError("downstream reconfirmation order changed")
        record = requested
        crew = self._post(
            f"/propagation-reconfirmations/{record['affected_ref_id']}/actions",
            crew,
            {
                "responsible_agent_id": self._agent_id(role),
                "action": "acknowledge_reconfirm",
                "observed_version_id": self.approved_version,
            },
        )
        return self._ensure_message(crew, role, ROLE_ORDER[(ROLE_ORDER.index(role) + 1) % len(ROLE_ORDER)], phase="v2")

    def run_phase_b(self) -> dict[str, Any]:
        crew = self._crew()
        self._validate_arbitration_boundary(crew)
        crew = self._ensure_claim(crew, "screenwriter")
        crew = self._ensure_message(crew, "screenwriter", "storyboard", phase="v2")
        for role in ROLE_ORDER[1:]:
            crew = self.reconfirm_next(role)
        self._validate_propagation_complete(crew)
        run = self.finalize_binding()
        return self._evidence(crew, run, "episode_v2_bound")

    def finalize_binding(self) -> dict[str, Any]:
        crew = self._crew()
        self._validate_propagation_complete(crew)
        run = self._run()
        binding = self._binding(run)
        expected_package = self._v2_package_digest(binding)
        if binding.get("episode_version_id") == self.approved_version:
            if binding.get("package_sha256") != expected_package:
                raise EpisodeExecutionDriftError("approved episode binding content drift")
            self._validate_v2_binding(binding)
            return run
        self._validate_v1_binding(run)
        payload = self._binding_payload(run, crew)
        response = self._request(
            "PUT",
            f"/projects/{self.project_id}/production-runs/{self.run_id}/representative-episode-binding",
            payload,
        )
        updated = response["production_run"]
        self._validate_v2_binding(self._binding(updated))
        return updated

    @property
    def from_version(self) -> str:
        return str(self.revision["from_episode_version_id"])

    @property
    def approved_version(self) -> str:
        return str(self.revision["approved_episode_version_id"])

    def _crew(self) -> dict[str, Any]:
        return self._request("GET", self._crew_path())["crew"]

    def _run(self) -> dict[str, Any]:
        return self._request(
            "GET", f"/projects/{self.project_id}/production-runs/{self.run_id}"
        )["production_run"]

    def _request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        response = self.transport.request(method, path, json=payload)
        if response.status_code != 200:
            raise EpisodeExecutionDriftError(f"runtime request failed closed: {method} {path} status={response.status_code}")
        value = response.json()
        if not isinstance(value, dict):
            raise EpisodeExecutionDriftError("runtime response is not an object")
        return value

    def _post(self, suffix: str, crew: dict[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
        body = {**payload, "expected_state_version": crew["state_version"]}
        return self._request("POST", self._crew_path(suffix), body)["crew"]

    def _ensure_initial_task(self, crew: dict[str, Any]) -> dict[str, Any]:
        expected = self._task_record("screenwriter")
        existing = self._find(crew.get("tasks") or [], "task_id", expected["task_id"])
        if existing:
            self._match(existing, expected, "screenwriter task", ignored=("status", "claimed_by_agent_id"))
            return crew
        return self._post("/tasks", crew, expected)

    def _ensure_claim(self, crew: dict[str, Any], role: str) -> dict[str, Any]:
        task = self._task(crew, role)
        agent = self._agent_id(role)
        if task.get("claimed_by_agent_id") == agent and task.get("status") in {
            "claimed", "completed", "blocked_human", "reconfirmation_required", "ready",
        }:
            return crew
        if task.get("status") != "ready" or task.get("assigned_agent_id") != agent:
            raise EpisodeExecutionDriftError(f"{role} task is not claimable by its responsible adapter")
        return self._post(f"/tasks/{task['task_id']}/claim", crew, {"agent_id": agent})

    def _ensure_message(self, crew: dict[str, Any], role: str, receiver: str, *, phase: str) -> dict[str, Any]:
        message = {
            "message_id": self.ids.value(f"message-{role}-{phase}"),
            "task_id": self.ids.value(f"task-{role}"),
            "from_agent_id": self._agent_id(role),
            "to_agent_id": self._agent_id(receiver),
            "message_type": "status" if phase == "v2" else "request",
            "entity_type": "project",
            "entity_id": self.project_id,
            "version_id": self.approved_version if phase == "v2" else self.from_version,
            "content": self._message_content(role, phase),
        }
        existing = self._find(crew.get("messages") or [], "message_id", message["message_id"])
        if existing:
            self._match(existing, message, f"{role} structured message")
            return crew
        return self._post("/messages", crew, message)

    def _ensure_handoff(self, crew: dict[str, Any], role: str, receiver: str) -> dict[str, Any]:
        handoff = {
            "handoff_id": self.ids.value(f"handoff-{role}-{receiver}"),
            "task_id": self.ids.value(f"task-{role}"),
            "target_task_id": self.ids.value(f"task-{receiver}"),
            "target_node_id": self.ids.value(f"node-{receiver}"),
            "from_agent_id": self._agent_id(role),
            "to_agent_id": self._agent_id(receiver),
            "next_action": ROLE_ACTIONS[receiver],
            "objective": ROLE_RESPONSIBILITIES[receiver],
            "entity_type": "project",
            "entity_id": self.project_id,
            "version_id": self.from_version,
        }
        existing = self._find(crew.get("handoffs") or [], "handoff_id", handoff["handoff_id"])
        if existing:
            self._match(existing, handoff, f"{role} handoff")
            return crew
        return self._post("/handoffs", crew, handoff)

    def _ensure_accept(self, crew: dict[str, Any], role: str, receiver: str) -> dict[str, Any]:
        handoff = self._named(
            crew.get("handoffs") or [], "handoff_id", self.ids.value(f"handoff-{role}-{receiver}"), "handoff",
        )
        if handoff.get("status") == "accepted":
            return crew
        if handoff.get("status") != "pending_receiver":
            raise EpisodeExecutionDriftError("handoff decision drift")
        return self._post(
            f"/handoffs/{handoff['handoff_id']}/decisions",
            crew,
            {
                "receiver_agent_id": self._agent_id(receiver),
                "decision": "accept",
                "note": f"{ROLE_RESPONSIBILITIES[receiver]}，接受第 1 版责任交接。",
            },
        )

    def _ensure_conflict(self, crew: dict[str, Any]) -> dict[str, Any]:
        conflict_id = self.ids.value("conflict-creator-v2")
        existing = self._find(crew.get("conflicts") or [], "conflict_id", conflict_id)
        if existing:
            self._match(existing, {
                "task_id": self.ids.value("task-screenwriter"),
                "raised_by_agent_id": self._agent_id("screenwriter"),
                "entity_type": "project",
                "entity_id": self.project_id,
                "version_id": self.from_version,
            }, "creator revision conflict")
            return crew
        return self._post(
            "/conflicts",
            crew,
            {
                "conflict_id": conflict_id,
                "task_id": self.ids.value("task-screenwriter"),
                "raised_by_agent_id": self._agent_id("screenwriter"),
                "reason": "第 11 镜共同守护动作需要主创确认并传播到下游责任。",
                "entity_type": "project",
                "entity_id": self.project_id,
                "version_id": self.from_version,
            },
        )

    def _derive_authoritative_affected_work(
        self, crew: dict[str, Any], *, require_source_version: bool,
    ) -> list[dict[str, str]]:
        reached = {self.ids.value("task-screenwriter")}
        ordered: list[str] = []
        changed = True
        while changed:
            changed = False
            for handoff in crew.get("handoffs") or []:
                target_id = str(handoff.get("target_task_id") or "")
                if handoff.get("status") == "accepted" and handoff.get("task_id") in reached and target_id not in reached:
                    reached.add(target_id)
                    ordered.append(target_id)
                    changed = True
        result = []
        for task_id in ordered:
            task = self._named(crew.get("tasks") or [], "task_id", task_id, "downstream task")
            role = next((item for item in ROLE_ORDER if self._agent_id(item) == task.get("assigned_agent_id")), "")
            expected_identity = {"entity_type": "project", "entity_id": self.project_id}
            if require_source_version:
                expected_identity["version_id"] = self.from_version
            if not role or any(task.get(key) != value for key, value in expected_identity.items()):
                raise EpisodeExecutionDriftError("persisted downstream task authority drift")
            result.append({
                "downstream_task_id": task_id,
                "downstream_node_id": str(task["node_id"]),
                "responsible_agent_id": self._agent_id(role),
                "responsible_agent_role": role,
                "entity_type": "project",
                "entity_id": self.project_id,
                "from_version_id": self.from_version,
                "approved_version_id": self.approved_version,
            })
        return result

    def _binding_payload(self, run: dict[str, Any], crew: dict[str, Any]) -> dict[str, Any]:
        binding = self._binding(run)
        canon = copy.deepcopy(binding["episode_canon"])
        for item in canon.get("shots") or []:
            item.pop("asset_readiness", None)
            item.pop("audio_coverage", None)
        if isinstance(canon.get("audio"), dict):
            canon["audio"].pop("readiness", None)
        canon["episode_version_id"] = self.approved_version
        changed = self.revision["changed_shot"]
        shot = self._named(canon["shots"], "entity_id", changed["shot_id"], "changed canon shot")
        if shot.get("current_approved_version_id") != changed["from_version_id"]:
            raise EpisodeExecutionDriftError("changed shot source version drift")
        if shot.get(changed["field"]) != changed["from_value"]:
            raise EpisodeExecutionDriftError("changed shot source content drift")
        shot["current_approved_version_id"] = changed["approved_version_id"]
        shot[changed["field"]] = changed["approved_value"]
        shot_refs = copy.deepcopy(binding["shot_refs"])
        ref = self._named(shot_refs, "entity_id", changed["shot_id"], "changed shot inventory ref")
        if ref.get("current_approved_version_id") != changed["from_version_id"]:
            raise EpisodeExecutionDriftError("changed shot inventory version drift")
        ref["current_approved_version_id"] = changed["approved_version_id"]
        records = self._execution_reconfirmations(crew)
        return {
            "schema_version": "afs_representative_episode_binding.v0.1",
            "idempotency_key": self.ids.value("bind-episode-v2"),
            "expected_checkpoint_version": run["checkpoint"]["version"],
            "expected_subject_digest": run["subject_digest"],
            "expected_package_sha256": binding["package_sha256"],
            "package_sha256": self._v2_package_digest(binding),
            "package_project_id": self.project_id,
            "episode_id": self.revision["episode_id"],
            "episode_version_id": self.approved_version,
            "character_refs": copy.deepcopy(binding["character_refs"]),
            "scene_refs": copy.deepcopy(binding["scene_refs"]),
            "shot_refs": shot_refs,
            "asset_refs": copy.deepcopy(binding["asset_refs"]),
            "episode_canon": canon,
            "pending_media_count": int(binding["asset_readiness"]["pending_media_count"]),
            "creator_decision_ref": self.revision["creator_decision_ref"],
            "authoritative_affected_task_refs": [str(item["downstream_task_id"]) for item in records],
            "downstream_reconfirmations": [
                {
                    "task_id": str(item["downstream_task_id"]),
                    "status": "reconfirmed",
                    "approved_version_id": self.approved_version,
                }
                for item in records
            ],
        }

    def _validate_revision_contract(self) -> None:
        changed = self.revision.get("changed_shot")
        preservation = self.revision.get("preservation_contract")
        if (
            self.revision.get("schema_version") != "afs.representative_episode_revision.v0.1"
            or self.revision.get("project_id") != self.project_id
            or not isinstance(changed, dict)
            or not isinstance(preservation, dict)
            or changed.get("field") != "visual_action"
            or preservation.get("shot_count") != 15
            or preservation.get("unchanged_shot_count") != 14
            or self.revision.get("media_status") != "media_assets_pending"
            or self.revision.get("provider_dispatch_count") != 0
        ):
            raise ValueError("episode revision fixture violates the one-shot provider-free contract")

    def _validate_crew(self, crew: dict[str, Any]) -> None:
        if crew.get("project_id") != self.project_id or crew.get("crew_id") != self.crew_id:
            raise EpisodeExecutionDriftError("project or crew identity drift")
        roles = {item.get("role"): item.get("agent_id") for item in crew.get("agents") or []}
        if any(roles.get(role) != self._agent_id(role) for role in ROLE_ORDER):
            raise EpisodeExecutionDriftError("nine-role domain agent registry drift")

    def _validate_v1_binding(self, run: dict[str, Any]) -> None:
        binding = self._binding(run)
        if (
            binding.get("package_project_id") != self.project_id
            or binding.get("episode_id") != self.revision["episode_id"]
            or binding.get("episode_version_id") != self.from_version
            or binding.get("package_sha256") != self.revision["from_package_sha256"]
            or len(binding.get("shot_refs") or []) != 15
            or len((binding.get("episode_canon") or {}).get("shots") or []) != 15
        ):
            raise EpisodeExecutionDriftError("authoritative v1 episode binding drift")
        changed = self.revision["changed_shot"]
        shot = self._named(binding["episode_canon"]["shots"], "entity_id", changed["shot_id"], "v1 changed shot")
        if (
            shot.get("current_approved_version_id") != changed["from_version_id"]
            or shot.get(changed["field"]) != changed["from_value"]
        ):
            raise EpisodeExecutionDriftError("authoritative v1 changed-shot source drift")

    def _validate_phase_a(self, crew: dict[str, Any]) -> None:
        self._validate_crew(crew)
        tasks = [item for item in crew.get("tasks") or [] if str(item.get("task_id") or "").startswith(self.ids.value("task-"))]
        handoffs = [item for item in crew.get("handoffs") or [] if str(item.get("handoff_id") or "").startswith(self.ids.value("handoff-"))]
        messages = [item for item in crew.get("messages") or [] if str(item.get("message_id") or "").startswith(self.ids.value("message-"))]
        conflict = self._named(crew.get("conflicts") or [], "conflict_id", self.ids.value("conflict-creator-v2"), "creator conflict")
        if (
            len(tasks) != 9
            or len(handoffs) != 8
            or any(item.get("status") != "accepted" for item in handoffs)
            or len(messages) != 9
            or conflict.get("status") != "awaiting_creator"
        ):
            raise EpisodeExecutionDriftError("phase A did not establish the exact accepted nine-role graph")
        for role in ROLE_ORDER:
            task = self._task(crew, role)
            if task.get("claimed_by_agent_id") != self._agent_id(role) or task.get("version_id") != self.from_version:
                raise EpisodeExecutionDriftError("role ownership or episode version drift")

    def _validate_arbitration_boundary(self, crew: dict[str, Any]) -> None:
        arbitration = self._named(
            crew.get("arbitrations") or [], "conflict_id", self.ids.value("conflict-creator-v2"), "creator arbitration",
        )
        expected = self._derive_authoritative_affected_work(crew, require_source_version=False)
        actual = arbitration.get("affected_work_refs") or []
        keys = tuple(expected[0]) if expected else ()
        if (
            arbitration.get("selected_version_id") != self.approved_version
            or [{key: item.get(key) for key in keys} for item in actual] != expected
            or [item.get("responsible_agent_role") for item in actual] != list(ROLE_ORDER[1:])
        ):
            raise EpisodeExecutionDriftError("API-authoritative affected work set drift")
        records = self._execution_reconfirmations(crew)
        if len(records) != 8 or any(item.get("approved_version_id") != self.approved_version for item in records):
            raise EpisodeExecutionDriftError("propagation pending set is incomplete or stale")

    def _validate_propagation_complete(self, crew: dict[str, Any]) -> None:
        self._validate_arbitration_boundary(crew)
        arbitration = self._named(
            crew.get("arbitrations") or [], "conflict_id", self.ids.value("conflict-creator-v2"), "creator arbitration",
        )
        records = self._execution_reconfirmations(crew)
        if (
            arbitration.get("propagation_complete") is not True
            or arbitration.get("propagation_status") != "reconfirmed"
            or any(item.get("reconfirmation_status") != "reconfirmed" for item in records)
        ):
            raise EpisodeExecutionDriftError("episode binding cannot advance before complete downstream reconfirmation")

    def _validate_v2_binding(self, binding: dict[str, Any]) -> None:
        changed = self.revision["changed_shot"]
        shots = binding.get("episode_canon", {}).get("shots") or []
        shot = self._named(shots, "entity_id", changed["shot_id"], "v2 changed shot")
        if (
            binding.get("episode_version_id") != self.approved_version
            or binding.get("propagation_complete") is not True
            or binding.get("asset_readiness", {}).get("pending_media_count") != 25
            or shot.get("current_approved_version_id") != changed["approved_version_id"]
            or shot.get(changed["field"]) != changed["approved_value"]
        ):
            raise EpisodeExecutionDriftError("v2 episode binding failed exact readback")

    def _execution_reconfirmations(self, crew: dict[str, Any]) -> list[dict[str, Any]]:
        conflict_id = self.ids.value("conflict-creator-v2")
        records = [
            item for item in crew.get("propagation_reconfirmations") or []
            if item.get("arbitration_conflict_id") == conflict_id
        ]
        role_index = {role: index for index, role in enumerate(ROLE_ORDER)}
        records.sort(key=lambda item: role_index.get(str(item.get("responsible_agent_role") or ""), 99))
        return records

    def _v2_package_digest(self, binding: dict[str, Any]) -> str:
        return self._digest({
            "schema_version": "afs.representative_episode_revision_binding.v0.1",
            "base_package_sha256": self.revision["from_package_sha256"],
            "revision": self.revision,
        })

    def _message_content(self, role: str, phase: str) -> str:
        payload = {
            "schema_version": "afs_representative_episode_execution.v0.1",
            "execution_id": self.ids.execution_id,
            "project_id": self.project_id,
            "episode_id": self.revision["episode_id"],
            "episode_version_id": self.approved_version if phase == "v2" else self.from_version,
            "shot_ref": self.revision["changed_shot"]["shot_id"],
            "role": role,
            "agent_id": self._agent_id(role),
            "task_id": self.ids.value(f"task-{role}"),
            "action": ROLE_ACTIONS[role],
            "responsibility": ROLE_RESPONSIBILITIES[role],
            "phase": "downstream_reconfirmed" if phase == "v2" else "responsibility_handoff",
            "work_digest": self._digest({"revision": self.revision, "role": role, "phase": phase}),
            "provider_dispatch_count": 0,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def _task_record(self, role: str) -> dict[str, Any]:
        return {
            "task_id": self.ids.value(f"task-{role}"),
            "node_id": self.ids.value(f"node-{role}"),
            "assigned_agent_id": self._agent_id(role),
            "action": ROLE_ACTIONS[role],
            "objective": ROLE_RESPONSIBILITIES[role],
            "entity_type": "project",
            "entity_id": self.project_id,
            "version_id": self.from_version,
        }

    def _task(self, crew: dict[str, Any], role: str) -> dict[str, Any]:
        return self._named(crew.get("tasks") or [], "task_id", self.ids.value(f"task-{role}"), f"{role} task")

    def _record_for_role(self, records: list[dict[str, Any]], role: str) -> dict[str, Any]:
        return self._named(records, "responsible_agent_role", role, f"{role} reconfirmation")

    def _agent_id(self, role: str) -> str:
        return f"{self.crew_id}-{role}"

    def _crew_path(self, suffix: str = "") -> str:
        return f"/projects/{self.project_id}/domain-crew{suffix}"

    @staticmethod
    def _binding(run: dict[str, Any]) -> dict[str, Any]:
        binding = run.get("representative_episode_binding")
        if not isinstance(binding, dict):
            raise EpisodeExecutionDriftError("representative episode binding is missing")
        return binding

    @staticmethod
    def _digest(value: Any) -> str:
        return hashlib.sha256(json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")).hexdigest()

    @staticmethod
    def _find(items: list[dict[str, Any]], key: str, value: str) -> dict[str, Any] | None:
        return next((item for item in items if item.get(key) == value), None)

    @staticmethod
    def _named(items: list[dict[str, Any]], key: str, value: str, label: str) -> dict[str, Any]:
        matches = [item for item in items if item.get(key) == value]
        if len(matches) != 1:
            raise EpisodeExecutionDriftError(f"{label} identity is missing or duplicated")
        return matches[0]

    @staticmethod
    def _match(
        actual: Mapping[str, Any], expected: Mapping[str, Any], label: str, *, ignored: tuple[str, ...] = (),
    ) -> None:
        if any(actual.get(key) != value for key, value in expected.items() if key not in ignored):
            raise EpisodeExecutionDriftError(f"{label} content drift")

    def _evidence(self, crew: dict[str, Any], run: dict[str, Any], status: str) -> dict[str, Any]:
        binding = self._binding(run)
        records = self._execution_reconfirmations(crew)
        return {
            "schema_version": "afs_representative_episode_execution_evidence.v0.1",
            "evidence_label": "provider_free_episode_crew_execution_pass" if status == "episode_v2_bound" else "provider_free_episode_crew_execution_progress",
            "execution_id": self.ids.execution_id,
            "project_id": self.project_id,
            "episode_version_id": binding.get("episode_version_id"),
            "status": status,
            "crew_state_version": crew.get("state_version"),
            "production_checkpoint_version": run.get("checkpoint", {}).get("version"),
            "role_count": 9,
            "accepted_handoff_count": len([
                item for item in crew.get("handoffs") or []
                if str(item.get("handoff_id") or "").startswith(self.ids.value("handoff-")) and item.get("status") == "accepted"
            ]),
            "reconfirmed_count": sum(item.get("reconfirmation_status") == "reconfirmed" for item in records),
            "propagation_complete": len(records) == 8 and all(item.get("reconfirmation_status") == "reconfirmed" for item in records),
            "media_status": "media_assets_pending",
            "provider_dispatch_count": 0,
            "auth_boundary": "user_delegated_authenticated_http_transport",
            "non_claims": ["media_quality", "human_acceptance", "business_validation", "deploy_or_release"],
        }


__all__ = (
    "AuthenticatedHttpTransport",
    "EpisodeExecutionDriftError",
    "RepresentativeEpisodeExecution",
    "ROLE_ACTIONS",
    "ROLE_ORDER",
    "ROLE_RESPONSIBILITIES",
)
