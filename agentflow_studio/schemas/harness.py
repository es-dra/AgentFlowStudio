from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from agentflow_studio.schemas.base import Metadata, SchemaBase, utc_now


class TaskPacket(SchemaBase):
    task_id: str
    task_type: str
    run_id: str
    input_refs: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Metadata
    created_at: datetime = Field(default_factory=utc_now)


class EvidenceCard(SchemaBase):
    evidence_id: str
    task_id: str
    run_id: str
    step_id: str
    input_refs: list[str] = Field(default_factory=list)
    output_refs: list[str] = Field(default_factory=list)
    tool_names: list[str] = Field(default_factory=list)
    model_name: str | None = None
    prompt_ref: str | None = None
    prompt_hash: str | None = None
    cost: dict[str, Any] = Field(default_factory=dict)
    quality_notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Metadata
    created_at: datetime = Field(default_factory=utc_now)


class GateResult(SchemaBase):
    gate_id: str
    task_id: str
    passed: bool
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Metadata
    created_at: datetime = Field(default_factory=utc_now)
