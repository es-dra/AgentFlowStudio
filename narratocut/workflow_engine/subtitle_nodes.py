from __future__ import annotations

from narratocut.schemas import Transcript
from narratocut.subtitle_sop import (
    SUBTITLE_MANIFEST,
    SUBTITLES_SRT,
    build_failed_subtitle_manifest,
    build_subtitle_export,
)
from narratocut.utils import write_json
from narratocut.workflow_engine.context import WorkflowContext
from narratocut.workflow_engine.definitions import WorkflowStepDefinition


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


def _state_transcript(context: WorkflowContext, key: str) -> Transcript:
    value = context.state.get(key)
    if isinstance(value, Transcript):
        return value
    raise ValueError("transcript must be loaded before write_subtitles")
