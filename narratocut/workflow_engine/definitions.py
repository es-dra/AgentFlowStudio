from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from narratocut.schemas.base import SchemaBase


class WorkflowStepDefinition(SchemaBase):
    id: str
    type: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, str] = Field(default_factory=dict)


class WorkflowDefinition(SchemaBase):
    name: str
    version: int = Field(default=1, ge=1)
    mode: str = "mock"
    quality_profile: str = "mock"
    metadata: dict[str, Any] = Field(default_factory=dict)
    steps: list[WorkflowStepDefinition] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_step_ids(self) -> "WorkflowDefinition":
        seen: set[str] = set()
        for step in self.steps:
            if step.id in seen:
                raise ValueError(f"duplicate step id: {step.id}")
            seen.add(step.id)
        return self
