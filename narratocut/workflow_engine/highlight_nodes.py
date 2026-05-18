from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from narratocut.highlight_sop import (
    detect_highlights_from_script,
    detect_highlights_from_transcript,
    generate_clip_plan_from_highlights,
    rank_highlights_by_roi,
)
from narratocut.schemas import ClipPlan, HighlightPlan, ROISettings, Transcript
from narratocut.utils import write_json
from narratocut.workflow_engine.context import WorkflowContext
from narratocut.workflow_engine.definitions import WorkflowStepDefinition


DEFAULT_MAX_HIGHLIGHTS = 5


def load_script_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    script_ref = _require_input(step, "script")
    script_path = Path(str(_resolve_ref(context, script_ref)))
    if not script_path.is_file():
        raise ValueError(f"script_path does not exist: {script_path}")
    script_text = script_path.read_text(encoding="utf-8").strip()
    if not script_text:
        raise ValueError(f"script is empty: {script_path}")
    context.state["script_text"] = script_text
    context.state["input_mode"] = "script_only"
    return []


def load_transcript_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    transcript_ref = _require_input(step, "transcript")
    transcript_path = Path(str(_resolve_ref(context, transcript_ref)))
    transcript = _load_transcript(transcript_path)
    context.state["transcript"] = transcript
    context.state["input_mode"] = "timestamped_transcript"
    if transcript.source_video:
        context.state["source_video"] = transcript.source_video
    return []


def detect_highlights_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    input_mode = str(_optional_resolved_input(step, context, "input_mode") or context.state.get("input_mode") or "")
    max_highlights = _max_highlights(step, context)
    if input_mode == "script_only":
        script_text = _state_value(context, "script_text", str(_optional_raw_input(step, "script_text") or "script_text"))
        plan = detect_highlights_from_script(
            str(script_text),
            source_id=str(context.inputs.get("source_id") or "script_input"),
            max_highlights=max_highlights,
        )
    elif input_mode == "timestamped_transcript":
        transcript = _state_value(context, "transcript", str(_optional_raw_input(step, "transcript") or "transcript"))
        if not isinstance(transcript, Transcript):
            raise ValueError("transcript input must be loaded before detect_highlights")
        plan = detect_highlights_from_transcript(transcript, max_highlights=max_highlights)
    else:
        raise ValueError("input_mode must be script_only or timestamped_transcript")

    context.state["detected_highlight_plan"] = plan
    context.state["highlight_plan"] = plan
    return []


def rank_highlights_by_roi_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    plan = _state_highlight_plan(context, str(_optional_raw_input(step, "highlight_plan") or "highlight_plan"))
    roi_settings = _state_roi_settings(context)
    ranked = rank_highlights_by_roi(plan, roi_settings)
    context.state["ranked_highlight_plan"] = ranked
    context.state["highlight_plan"] = ranked
    return []


def generate_highlight_clip_plan_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    plan = _state_highlight_plan(context, str(_optional_raw_input(step, "highlight_plan") or "highlight_plan"))
    source_video = _source_video(step, context)
    max_clips = _optional_int(step, context, "max_clips")
    clip_plan = generate_clip_plan_from_highlights(
        plan,
        source_video=source_video,
        project_id=str(context.inputs.get("project_id") or plan.source_id or plan.plan_id),
        max_clips=max_clips,
    )
    context.state["clip_plan"] = clip_plan
    return []


def write_highlight_plan_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    plan = _state_highlight_plan(context, str(_optional_raw_input(step, "highlight_plan") or "highlight_plan"))
    output_ref = _require_output(step, "highlight_plan")
    write_json(context.output_path(output_ref), plan)
    context.artifacts["highlight_plan"] = output_ref
    return [output_ref]


def write_clip_plan_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    value = context.state.get(str(_optional_raw_input(step, "clip_plan") or "clip_plan"))
    if not isinstance(value, ClipPlan):
        raise ValueError("clip_plan must be generated before write_clip_plan")
    output_ref = _require_output(step, "clip_plan")
    write_json(context.output_path(output_ref), value)
    context.artifacts["clip_plan"] = output_ref
    return [output_ref]


def _require_input(step: WorkflowStepDefinition, name: str) -> object:
    if name not in step.inputs:
        raise ValueError(f"Step {step.id} missing required input: {name}")
    return step.inputs[name]


def _require_output(step: WorkflowStepDefinition, name: str) -> str:
    if name not in step.outputs:
        raise ValueError(f"Step {step.id} missing required output: {name}")
    return step.outputs[name]


def _optional_raw_input(step: WorkflowStepDefinition, name: str) -> object | None:
    return step.inputs.get(name)


def _optional_resolved_input(
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
    return _resolve_ref(context, value)


def _resolve_ref(context: WorkflowContext, value: object) -> object:
    if isinstance(value, str) and value in context.state:
        return context.state[value]
    return context.resolve_input(str(value))


def _state_value(context: WorkflowContext, key: str, fallback_key: str) -> object:
    if key in context.state:
        return context.state[key]
    if fallback_key in context.state:
        return context.state[fallback_key]
    raise ValueError(f"{key} must be loaded before this node")


def _state_highlight_plan(context: WorkflowContext, key: str) -> HighlightPlan:
    value = context.state.get(key)
    if isinstance(value, HighlightPlan):
        return value
    raise ValueError("highlight_plan must be detected before this node")


def _state_roi_settings(context: WorkflowContext) -> ROISettings | None:
    value = context.state.get("roi_settings")
    if value is None:
        return None
    if isinstance(value, ROISettings):
        return value
    raise ValueError("roi_settings state is not a ROISettings object")


def _max_highlights(step: WorkflowStepDefinition, context: WorkflowContext) -> int:
    return _optional_int(step, context, "max_highlights") or DEFAULT_MAX_HIGHLIGHTS


def _optional_int(
    step: WorkflowStepDefinition,
    context: WorkflowContext,
    name: str,
) -> int | None:
    raw = _optional_resolved_input(step, context, name)
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0")
    return value


def _source_video(step: WorkflowStepDefinition, context: WorkflowContext) -> str:
    value = _optional_resolved_input(step, context, "source_video")
    if value is None:
        value = _optional_resolved_input(step, context, "video")
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


def _load_transcript(path: Path) -> Transcript:
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
