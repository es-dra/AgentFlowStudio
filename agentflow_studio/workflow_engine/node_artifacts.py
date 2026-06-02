from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from agentflow_studio.schemas import (
    ClipPlan,
    ClipPlanValidationReport,
    Hook,
    ROISettings,
    ShortVideoScript,
    VideoMetadata,
)
from agentflow_studio.slicing_sop.real_slicer import REAL_SLICE_MANIFEST
from agentflow_studio.workflow_engine.context import WorkflowContext
from agentflow_studio.workflow_engine.definitions import WorkflowStepDefinition


def require_input(step: WorkflowStepDefinition, name: str) -> object:
    if name not in step.inputs:
        raise ValueError(f"Step {step.id} missing required input: {name}")
    return step.inputs[name]


def require_output(step: WorkflowStepDefinition, name: str) -> str:
    if name not in step.outputs:
        raise ValueError(f"Step {step.id} missing required output: {name}")
    return step.outputs[name]


def load_hooks(path: Path) -> list[Hook]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Hooks artifact is not valid JSON: {path}") from exc
    if not isinstance(payload, list):
        raise ValueError(f"Hooks artifact must contain a JSON array: {path}")
    try:
        return [Hook.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise ValueError(f"Hooks artifact failed Hook schema validation: {path}") from exc


def load_scripts(path: Path) -> list[ShortVideoScript]:
    payload = load_json_array(path, "Scripts artifact")
    try:
        return [ShortVideoScript.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise ValueError(f"Scripts artifact failed ShortVideoScript schema validation: {path}") from exc


def load_clip_plans(path: Path) -> list[ClipPlan]:
    payload = load_json_array(path, "Clip plans artifact")
    try:
        return [ClipPlan.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise ValueError(f"Clip plans artifact failed ClipPlan schema validation: {path}") from exc


def load_clip_plan(path: Path) -> ClipPlan:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Clip plan artifact is not valid JSON: {path}") from exc
    try:
        return ClipPlan.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Clip plan artifact failed ClipPlan schema validation: {path}") from exc


def load_roi_settings(path: Path) -> ROISettings:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"ROI config is not valid JSON: {path}") from exc
    try:
        return ROISettings.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"ROI config failed ROISettings schema validation: {path}") from exc


def load_video_metadata(path: Path) -> VideoMetadata:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Video metadata is not valid JSON: {path}") from exc
    try:
        return VideoMetadata.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Video metadata failed VideoMetadata schema validation: {path}") from exc


def load_validation_report(path: Path) -> ClipPlanValidationReport:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Validation report is not valid JSON: {path}") from exc
    try:
        return ClipPlanValidationReport.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Validation report failed schema validation: {path}") from exc


def state_or_load_clip_plan(context: WorkflowContext, key: str) -> ClipPlan:
    value = context.state.get(key)
    if isinstance(value, ClipPlan):
        return value
    return load_clip_plan(context.output_path(context.artifacts[key]))


def state_or_load_roi_settings(context: WorkflowContext, key: str) -> ROISettings:
    value = context.state.get(key)
    if isinstance(value, ROISettings):
        return value
    return load_roi_settings(context.output_path(context.artifacts[key]))


def state_or_default_roi_settings(context: WorkflowContext) -> ROISettings:
    value = context.state.get("roi_settings")
    if isinstance(value, ROISettings):
        return value
    if "roi_settings" in context.artifacts:
        return load_roi_settings(context.output_path(context.artifacts["roi_settings"]))
    return ROISettings(
        target_platform=str(context.inputs.get("target_platform") or "generic"),
        target_audience=str(context.inputs.get("target_audience") or "unspecified"),
        content_goal=str(context.inputs.get("content_goal") or "execute_clip_plan"),
        validation_policy="advisory",
    )


def state_or_load_video_metadata(context: WorkflowContext, key: str) -> VideoMetadata:
    value = context.state.get(key)
    if isinstance(value, VideoMetadata):
        return value
    return load_video_metadata(context.output_path(context.artifacts[key]))


def skipped_real_slice_manifest(
    reason: str,
    report: ClipPlanValidationReport,
) -> dict[str, object]:
    return {
        "status": "skipped",
        "reason": reason,
        "clips": [],
        "errors": [issue.code for issue in report.hard_errors],
        "manifest_path": REAL_SLICE_MANIFEST,
    }


def load_json_array(path: Path, label: str) -> list[object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(payload, list):
        raise ValueError(f"{label} must contain a JSON array: {path}")
    return payload


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object: {path}")
    return payload
