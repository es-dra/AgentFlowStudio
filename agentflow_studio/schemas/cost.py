from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from agentflow_studio.schemas.base import Metadata, SchemaBase, utc_now


CostStatus = Literal["estimated", "recorded", "failed"]


class CostRecord(SchemaBase):
    cost_id: str
    run_id: str
    provider: str
    status: CostStatus
    task_id: str | None = None
    model: str | None = None
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    api_cost: float = Field(default=0.0, ge=0)
    gpu_seconds: float = Field(default=0.0, ge=0)
    local_compute_cost: float = Field(default=0.0, ge=0)
    metadata: dict[str, Any] = Metadata
    created_at: datetime = Field(default_factory=utc_now)
