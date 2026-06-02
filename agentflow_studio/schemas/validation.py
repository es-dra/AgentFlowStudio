from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from agentflow_studio.schemas.base import Metadata, SchemaBase, utc_now


ValidationReportStatus = Literal["passed", "passed_with_warnings", "failed"]
ValidationCheckStatus = Literal["passed", "warning", "failed"]


class ValidationIssue(SchemaBase):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ValidationCheck(SchemaBase):
    name: str
    status: ValidationCheckStatus
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ClipPlanValidationReport(SchemaBase):
    status: ValidationReportStatus
    hard_errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
    checks: list[ValidationCheck] = Field(default_factory=list)
    metadata: dict[str, Any] = Metadata
    created_at: datetime = Field(default_factory=utc_now)
