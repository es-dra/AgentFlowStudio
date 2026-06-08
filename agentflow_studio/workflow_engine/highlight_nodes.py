from __future__ import annotations

from pathlib import Path

from agentflow_studio.highlight_sop import (
    ALIGNMENT_MANIFEST,
    align_script_highlights_to_transcript,
    detect_highlights_from_script,
    detect_highlights_from_transcript,
    generate_clip_plan_from_highlights,
    rank_highlights_by_roi,
)
from agentflow_studio.candidate_sop import CANDIDATE_WINDOWS_MANIFEST, generate_candidate_windows
from agentflow_studio.schemas import ClipPlan, Transcript
from agentflow_studio.utils import write_json
from agentflow_studio.workflow_engine.context import WorkflowContext
from agentflow_studio.workflow_engine.definitions import WorkflowStepDefinition
from agentflow_studio.workflow_engine.node_artifacts import (
    require_input as _require_input,
    require_output as _require_output,
)
from agentflow_studio.workflow_engine.highlight_node_inputs import (
    load_transcript,
    max_highlights,
    optional_bool,
    optional_dict_state,
    optional_float,
    optional_float_unbounded,
    optional_int,
    optional_raw_input,
    optional_resolved_input,
    resolve_ref,
    source_video,
    state_highlight_plan,
    state_roi_settings,
    state_transcript,
    state_value,
)


def load_script_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    script_ref = _require_input(step, "script")
    script_path = Path(str(resolve_ref(context, script_ref)))
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
    transcript_path = Path(str(resolve_ref(context, transcript_ref)))
    transcript = load_transcript(transcript_path)
    context.state["transcript"] = transcript
    context.state["input_mode"] = "timestamped_transcript"
    if transcript.source_video:
        context.state["source_video"] = transcript.source_video
    return []


def detect_highlights_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    input_mode = str(optional_resolved_input(step, context, "input_mode") or context.state.get("input_mode") or "")
    limit = max_highlights(step, context)
    if input_mode == "script_only":
        script_text = state_value(context, "script_text", str(optional_raw_input(step, "script_text") or "script_text"))
        plan = detect_highlights_from_script(
            str(script_text),
            source_id=str(context.inputs.get("source_id") or "script_input"),
            max_highlights=limit,
        )
    elif input_mode == "timestamped_transcript":
        transcript = state_value(context, "transcript", str(optional_raw_input(step, "transcript") or "transcript"))
        if not isinstance(transcript, Transcript):
            raise ValueError("transcript input must be loaded before detect_highlights")
        plan = detect_highlights_from_transcript(transcript, max_highlights=limit)
    else:
        raise ValueError("input_mode must be script_only or timestamped_transcript")

    context.state["detected_highlight_plan"] = plan
    context.state["highlight_plan"] = plan
    return []


def rank_highlights_by_roi_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    plan = state_highlight_plan(context, str(optional_raw_input(step, "highlight_plan") or "highlight_plan"))
    roi_settings = state_roi_settings(context)
    ranked = rank_highlights_by_roi(plan, roi_settings)
    context.state["ranked_highlight_plan"] = ranked
    context.state["highlight_plan"] = ranked
    return []


def generate_highlight_clip_plan_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    plan = state_highlight_plan(context, str(optional_raw_input(step, "highlight_plan") or "highlight_plan"))
    video_ref = source_video(step, context)
    max_clips = optional_int(step, context, "max_clips")
    clip_plan = generate_clip_plan_from_highlights(
        plan,
        source_video=video_ref,
        project_id=str(context.inputs.get("project_id") or plan.source_id or plan.plan_id),
        max_clips=max_clips,
    )
    context.state["clip_plan"] = clip_plan
    return []


def generate_candidate_windows_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    transcript = state_transcript(context, str(optional_raw_input(step, "transcript") or "transcript"))
    product_short_defaults = optional_bool(step, context, "product_short_defaults")
    max_window_size = optional_int(step, context, "max_window_size")
    min_duration_sec = optional_float_unbounded(step, context, "min_duration_sec")
    max_duration_sec = optional_float_unbounded(step, context, "max_duration_sec")
    target_window_sec = optional_float_unbounded(step, context, "target_window_sec")
    script_highlight_alignment = optional_dict_state(step, context, "script_highlight_alignment")
    boundary_signal_manifest = optional_dict_state(step, context, "boundary_signal_manifest")
    manifest = generate_candidate_windows(
        transcript,
        max_window_size=max_window_size or (2 if product_short_defaults else 4),
        min_duration_sec=4.0 if product_short_defaults and min_duration_sec is None else min_duration_sec,
        max_duration_sec=6.0 if product_short_defaults and max_duration_sec is None else max_duration_sec,
        target_window_sec=5.0 if product_short_defaults and target_window_sec is None else target_window_sec,
        script_highlight_alignment=script_highlight_alignment,
        boundary_signal_manifest=boundary_signal_manifest,
    )

    output_ref = str(step.outputs.get("candidate_windows") or CANDIDATE_WINDOWS_MANIFEST)
    write_json(context.output_path(output_ref), manifest)
    context.artifacts["candidate_windows"] = output_ref
    context.state["candidate_windows"] = manifest
    return [output_ref]


def align_script_highlights_to_transcript_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    script_plan = state_highlight_plan(context, str(optional_raw_input(step, "script_highlight_plan") or "highlight_plan"))
    transcript = state_transcript(context, str(optional_raw_input(step, "transcript") or "transcript"))
    min_confidence = optional_float(step, context, "min_confidence")
    result = align_script_highlights_to_transcript(
        script_plan,
        transcript,
        min_confidence=min_confidence if min_confidence is not None else 0.25,
    )
    output_ref = str(step.outputs.get("script_highlight_alignment") or ALIGNMENT_MANIFEST)
    write_json(context.output_path(output_ref), result.manifest)
    context.artifacts["script_highlight_alignment"] = output_ref
    context.state["script_highlight_alignment"] = result.manifest
    if result.highlight_plan is None:
        raise ValueError("script_highlight_alignment_empty")
    context.state["aligned_highlight_plan"] = result.highlight_plan
    context.state["highlight_plan"] = result.highlight_plan
    return [output_ref]


def write_highlight_plan_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    plan = state_highlight_plan(context, str(optional_raw_input(step, "highlight_plan") or "highlight_plan"))
    output_ref = _require_output(step, "highlight_plan")
    write_json(context.output_path(output_ref), plan)
    context.artifacts["highlight_plan"] = output_ref
    return [output_ref]


def write_clip_plan_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    value = context.state.get(str(optional_raw_input(step, "clip_plan") or "clip_plan"))
    if not isinstance(value, ClipPlan):
        raise ValueError("clip_plan must be generated before write_clip_plan")
    output_ref = _require_output(step, "clip_plan")
    write_json(context.output_path(output_ref), value)
    context.artifacts["clip_plan"] = output_ref
    return [output_ref]
