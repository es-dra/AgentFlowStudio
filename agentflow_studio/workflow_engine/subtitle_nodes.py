from __future__ import annotations

import json

from agentflow_studio.schemas import Transcript
from agentflow_studio.subtitle_sop import (
    SUBTITLE_MANIFEST,
    SUBTITLES_SRT,
    build_clip_timeline_subtitle_export,
    build_failed_subtitle_manifest,
    build_subtitle_export,
)
from agentflow_studio.utils import write_json
from agentflow_studio.workflow_engine.context import WorkflowContext
from agentflow_studio.workflow_engine.definitions import WorkflowStepDefinition


def write_subtitles_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    transcript = _state_transcript(context, str(step.inputs.get("transcript") or "transcript"))
    subtitle_ref = step.outputs.get("subtitles") or SUBTITLES_SRT
    manifest_ref = step.outputs.get("subtitle_manifest") or SUBTITLE_MANIFEST

    try:
        export = build_subtitle_export(transcript, subtitle_path=subtitle_ref)
    except ValueError as exc:
        failed = build_failed_subtitle_manifest(transcript, subtitle_path=subtitle_ref, errors=[str(exc)])
        write_json(context.output_path(manifest_ref), failed)
        context.artifacts["subtitle_manifest"] = manifest_ref
        context.artifacts["subtitles"] = subtitle_ref
        raise

    context.output_path(subtitle_ref).write_text(export.srt_text, encoding="utf-8")
    write_json(context.output_path(manifest_ref), export.manifest)
    context.artifacts["subtitles"] = subtitle_ref
    context.artifacts["subtitle_manifest"] = manifest_ref
    context.state["subtitle_manifest"] = export.manifest
    return [subtitle_ref, manifest_ref]


def write_clip_timeline_subtitles_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    transcript = _state_transcript(context, str(step.inputs.get("transcript") or "transcript"))
    real_slice_manifest = _state_json(context, "real_slice_manifest")
    final_video_manifest = _state_json(context, "final_video_manifest")
    subtitle_ref = step.outputs.get("subtitles") or SUBTITLES_SRT
    manifest_ref = step.outputs.get("subtitle_manifest") or SUBTITLE_MANIFEST

    try:
        export = build_clip_timeline_subtitle_export(
            transcript,
            real_slice_manifest,
            final_video_manifest=final_video_manifest,
            subtitle_path=subtitle_ref,
        )
    except ValueError as exc:
        failed = build_failed_subtitle_manifest(transcript, subtitle_path=subtitle_ref, errors=[str(exc)])
        write_json(context.output_path(manifest_ref), failed)
        context.artifacts["subtitle_manifest"] = manifest_ref
        context.artifacts["subtitles"] = subtitle_ref
        raise

    context.output_path(subtitle_ref).write_text(export.srt_text, encoding="utf-8")
    write_json(context.output_path(manifest_ref), export.manifest)
    context.artifacts["subtitles"] = subtitle_ref
    context.artifacts["subtitle_manifest"] = manifest_ref
    context.state["subtitle_manifest"] = export.manifest
    return [subtitle_ref, manifest_ref]


def _state_transcript(context: WorkflowContext, key: str) -> Transcript:
    value = context.state.get(key)
    if isinstance(value, Transcript):
        return value
    raise ValueError("transcript must be loaded before write_subtitles")


def _state_json(context: WorkflowContext, key: str) -> dict:
    value = context.state.get(key)
    if isinstance(value, dict):
        return value
    ref = context.artifacts.get(key)
    if ref:
        try:
            payload = json.loads(context.output_path(ref).read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValueError(f"{key} artifact not found before write_clip_timeline_subtitles") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"{key} artifact is not valid JSON") from exc
        if isinstance(payload, dict):
            context.state[key] = payload
            return payload
    raise ValueError(f"{key} must be generated before write_clip_timeline_subtitles")
