from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from agentflow_studio.schemas.base import Metadata, SchemaBase, utc_now


WorkflowStatus = Literal["pending", "running", "success", "failed"]
StepStatus = Literal["pending", "running", "success", "failed", "skipped"]


class StepResult(SchemaBase):
    step_id: str
    step_type: str
    status: StepStatus
    output_ref: str | None = None
    artifacts: list[str] = Field(default_factory=list)
    error: str | None = None
    cost: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Metadata
    started_at: datetime | None = None
    ended_at: datetime | None = None


class WorkflowRun(SchemaBase):
    run_id: str
    workflow_name: str
    status: WorkflowStatus
    project_id: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    steps: list[StepResult] = Field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = Metadata
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = None
