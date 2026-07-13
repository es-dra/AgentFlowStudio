from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SAFE_ID = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$"
EntityType = Literal["project", "character", "scene", "shot"]
AgentRole = Literal["screenwriter", "storyboard", "art", "director", "continuity", "qa", "audio", "edit", "export"]
TaskAction = Literal[
    "script.write", "storyboard.compose", "art.create", "direction.review", "continuity.review",
    "quality.review", "audio.produce", "edit.assemble", "export.deliver",
]


class DomainCrewModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VersionRef(DomainCrewModel):
    entity_type: EntityType
    entity_id: str = Field(pattern=SAFE_ID)
    version_id: str = Field(pattern=SAFE_ID)


class CrewCreateRequest(DomainCrewModel):
    crew_id: str = Field(pattern=SAFE_ID)


class TaskCreateRequest(VersionRef):
    task_id: str = Field(pattern=SAFE_ID)
    node_id: str = Field(pattern=SAFE_ID)
    expected_state_version: int = Field(ge=1, strict=True)
    assigned_agent_id: str = Field(pattern=SAFE_ID)
    action: TaskAction
    objective: str = Field(min_length=1, max_length=500)


class TaskClaimRequest(DomainCrewModel):
    expected_state_version: int = Field(ge=1, strict=True)
    agent_id: str = Field(pattern=SAFE_ID)


class MessageCreateRequest(VersionRef):
    message_id: str = Field(pattern=SAFE_ID)
    expected_state_version: int = Field(ge=1, strict=True)
    task_id: str = Field(pattern=SAFE_ID)
    from_agent_id: str = Field(pattern=SAFE_ID)
    to_agent_id: str = Field(pattern=SAFE_ID)
    message_type: Literal["request", "response", "status", "decision"]
    content: str = Field(min_length=1, max_length=800)


class HandoffCreateRequest(VersionRef):
    handoff_id: str = Field(pattern=SAFE_ID)
    expected_state_version: int = Field(ge=1, strict=True)
    task_id: str = Field(pattern=SAFE_ID)
    target_task_id: str = Field(pattern=SAFE_ID)
    target_node_id: str = Field(pattern=SAFE_ID)
    from_agent_id: str = Field(pattern=SAFE_ID)
    to_agent_id: str = Field(pattern=SAFE_ID)
    next_action: TaskAction
    objective: str = Field(min_length=1, max_length=500)


class HandoffDecisionRequest(DomainCrewModel):
    expected_state_version: int = Field(ge=1, strict=True)
    receiver_agent_id: str = Field(pattern=SAFE_ID)
    decision: Literal["accept", "reject"]
    note: str = Field(default="", max_length=500)


class ConflictCreateRequest(VersionRef):
    conflict_id: str = Field(pattern=SAFE_ID)
    expected_state_version: int = Field(ge=1, strict=True)
    task_id: str = Field(pattern=SAFE_ID)
    raised_by_agent_id: str = Field(pattern=SAFE_ID)
    reason: str = Field(min_length=1, max_length=800)


class AffectedWorkRef(DomainCrewModel):
    downstream_task_id: str = Field(pattern=SAFE_ID)
    downstream_node_id: str = Field(pattern=SAFE_ID)
    responsible_agent_id: str = Field(pattern=SAFE_ID)
    responsible_agent_role: AgentRole
    entity_type: EntityType
    entity_id: str = Field(pattern=SAFE_ID)
    from_version_id: str = Field(pattern=SAFE_ID)
    approved_version_id: str = Field(pattern=SAFE_ID)


class ArbitrationRequest(DomainCrewModel):
    entity_type: EntityType
    entity_id: str = Field(pattern=SAFE_ID)
    from_version_id: str = Field(pattern=SAFE_ID)
    expected_state_version: int = Field(ge=1, strict=True)
    selected_version_id: str = Field(pattern=SAFE_ID)
    resume_agent_id: str = Field(pattern=SAFE_ID)
    next_action: TaskAction
    rationale: str = Field(min_length=1, max_length=800)
    affected_work_refs: list[AffectedWorkRef] = Field(max_length=64)

    @model_validator(mode="after")
    def selected_version_matches_ref(self) -> "ArbitrationRequest":
        task_ids = [ref.downstream_task_id for ref in self.affected_work_refs]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("affected downstream tasks must be unique")
        for ref in self.affected_work_refs:
            if (ref.entity_type, ref.entity_id, ref.from_version_id) != (
                    self.entity_type, self.entity_id, self.from_version_id):
                raise ValueError("affected work entity must match arbitration entity")
            if ref.approved_version_id != self.selected_version_id:
                raise ValueError("affected work approved version must match creator selection")
        return self


class ReconfirmationRequest(DomainCrewModel):
    expected_state_version: int = Field(ge=1, strict=True)
    responsible_agent_id: str = Field(pattern=SAFE_ID)
    action: Literal["acknowledge_reconfirm"]
    observed_version_id: str = Field(pattern=SAFE_ID)


__all__ = (
    "ArbitrationRequest", "ConflictCreateRequest", "CrewCreateRequest", "HandoffCreateRequest",
    "HandoffDecisionRequest", "MessageCreateRequest", "TaskClaimRequest", "TaskCreateRequest",
    "ReconfirmationRequest",
)
