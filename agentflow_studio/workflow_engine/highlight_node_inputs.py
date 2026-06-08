from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from agentflow_studio.schemas import HighlightPlan, ROISettings, Transcript
from agentflow_studio.workflow_engine.context import WorkflowContext
from agentflow_studio.workflow_engine.definitions import WorkflowStepDefinition


DEFAULT_MAX_HIGHLIGHTS = 5


def optional_raw_input(step: WorkflowStepDefinition, name: str) -> object | None:
    return step.inputs.get(name)


def optional_resolved_input(
    step: WorkflowStepDefinition,
    context: WorkflowContext,
    name: str,
) -> object | None:
    if name not in step.inputs:
        return None
    value = step.inputs[name]
    if value == name and name not in context.inputs and name not in context.state:
        return None
    if isinstance(value, str) and value not in context.inputs and value not in context.state:
        return value
    return resolve_ref(context, value)


def resolve_ref(context: WorkflowContext, value: object) -> object:
    if isinstance(value, str) and value in context.state:
        return context.state[value]
    return context.resolve_input(str(value))


def state_value(context: WorkflowContext, key: str, fallback_key: str) -> object:
    if key in context.state:
        return context.state[key]
    if fallback_key in context.state:
        return context.state[fallback_key]
    raise ValueError(f"{key} must be loaded before this node")


def state_highlight_plan(context: WorkflowContext, key: str) -> HighlightPlan:
    value = context.state.get(key)
    if isinstance(value, HighlightPlan):
        return value
    raise ValueError("highlight_plan must be detected before this node")


def state_transcript(context: WorkflowContext, key: str) -> Transcript:
    value = context.state.get(key)
    if isinstance(value, Transcript):
        return value
    raise ValueError("transcript must be loaded before this node")


def state_roi_settings(context: WorkflowContext) -> ROISettings | None:
    value = context.state.get("roi_settings")
    if value is None:
        return None
    if isinstance(value, ROISettings):
        return value
    raise ValueError("roi_settings state is not a ROISettings object")


def optional_dict_state(
    step: WorkflowStepDefinition,
    context: WorkflowContext,
    name: str,
) -> dict[str, Any] | None:
    raw = optional_raw_input(step, name)
    key = str(raw or name)
    value = context.state.get(key)
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    raise ValueError(f"{name} state must be a JSON object")


def max_highlights(step: WorkflowStepDefinition, context: WorkflowContext) -> int:
    return optional_int(step, context, "max_highlights") or DEFAULT_MAX_HIGHLIGHTS


def optional_int(
    step: WorkflowStepDefinition,
    context: WorkflowContext,
    name: str,
) -> int | None:
    raw = optional_resolved_input(step, context, name)
    if raw is None:
        return None
    if isinstance(raw, str) and raw == name and raw not in context.inputs and raw not in context.state:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        if isinstance(raw, str) and raw not in context.inputs and raw not in context.state:
            return None
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0")
    return value


def optional_float(
    step: WorkflowStepDefinition,
    context: WorkflowContext,
    name: str,
) -> float | None:
    raw = optional_resolved_input(step, context, name)
    if raw is None:
        return None
    if isinstance(raw, str) and raw == name and raw not in context.inputs and raw not in context.state:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        if isinstance(raw, str) and raw not in context.inputs and raw not in context.state:
            return None
        raise ValueError(f"{name} must be a number") from exc
    if value < 0 or value > 1:
        raise ValueError(f"{name} must be between 0 and 1")
    return value


def optional_float_unbounded(
    step: WorkflowStepDefinition,
    context: WorkflowContext,
    name: str,
) -> float | None:
    raw = optional_resolved_input(step, context, name)
    if raw is None:
        return None
    if isinstance(raw, str) and raw == name and raw not in context.inputs and raw not in context.state:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError) as exc:
        if isinstance(raw, str) and raw not in context.inputs and raw not in context.state:
            return None
        raise ValueError(f"{name} must be a number") from exc


def optional_bool(
    step: WorkflowStepDefinition,
    context: WorkflowContext,
    name: str,
) -> bool:
    raw = optional_resolved_input(step, context, name)
    if raw is None:
        return False
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"} or (isinstance(raw, str) and raw not in context.inputs and raw not in context.state):
        return False
    raise ValueError(f"{name} must be a boolean")


def source_video(step: WorkflowStepDefinition, context: WorkflowContext) -> str:
    value = optional_resolved_input(step, context, "source_video")
    if value is None:
        value = optional_resolved_input(step, context, "video")
    if value is None:
        value = context.state.get("source_video")
    if value is None:
        transcript = context.state.get("transcript")
        if isinstance(transcript, Transcript):
            value = transcript.source_video or f"transcript://{transcript.transcript_id}"
    text = str(value or "").strip()
    if not text:
        raise ValueError("source_video must be provided or derivable from transcript")
    return text


def load_transcript(path: Path) -> Transcript:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"transcript_path does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Transcript JSON is invalid: {path}") from exc
    try:
        return Transcript.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Transcript schema validation failed: {path}") from exc
