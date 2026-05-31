from __future__ import annotations

from pathlib import Path
from typing import Any

from narratocut.assembly_sop import (
    ASSEMBLY_PLAN,
    FINAL_VIDEO,
    FINAL_VIDEO_MANIFEST,
    AssemblyConfig,
    build_assembly_plan,
    concat_clips,
)
from narratocut.slicing_sop import check_ffmpeg_available, probe_video_metadata, resolve_media_tool_paths
from narratocut.utils import write_json
from narratocut.workflow_engine.context import WorkflowContext
from narratocut.workflow_engine.definitions import WorkflowStepDefinition
from narratocut.workflow_engine.node_artifacts import (
    load_json_object as _load_json_object,
    require_input as _require_input,
    require_output as _require_output,
)


def load_real_slice_manifest_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    manifest_ref = _require_input(step, "real_slice_manifest")
    manifest_path = Path(str(context.resolve_input(str(manifest_ref))))
    manifest = _load_json_object(manifest_path, "Real slice manifest")

    output_ref = _require_output(step, "real_slice_manifest")
    write_json(context.output_path(output_ref), manifest)
    context.artifacts["real_slice_manifest"] = output_ref
    context.state["real_slice_manifest"] = manifest
    context.state["real_slice_manifest_path"] = str(manifest_path)
    context.state["source_run_dir"] = str(manifest_path.parent)
    return [output_ref]


def generate_assembly_plan_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    manifest = _state_or_load_json(context, "real_slice_manifest", "real_slice_manifest")
    output_name = str(context.inputs.get("output_name") or FINAL_VIDEO)
    plan = build_assembly_plan(
        manifest,
        source_manifest_path=context.state.get("real_slice_manifest_path") or "real_slice_manifest.json",
        output_name=output_name,
    )

    output_ref = _require_output(step, "assembly_plan")
    write_json(context.output_path(output_ref), plan)
    context.artifacts["assembly_plan"] = output_ref
    context.state["assembly_plan"] = plan
    return [output_ref]


def concat_clips_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    plan = _state_or_load_json(context, "assembly_plan", "assembly_plan")
    paths = resolve_media_tool_paths()
    ffmpeg_info = check_ffmpeg_available(paths.ffmpeg)
    if not ffmpeg_info.available:
        failed = _failed_final_manifest("ffmpeg_unavailable", [ffmpeg_info.error or "ffmpeg_unavailable"], plan)
        write_json(context.output_path(FINAL_VIDEO_MANIFEST), failed)
        _record_final_artifacts(context)
        raise ValueError("ffmpeg_unavailable")

    manifest = concat_clips(
        plan,
        source_run_dir=str(context.state.get("source_run_dir") or context.output_dir),
        output_dir=context.output_dir,
        config=AssemblyConfig(ffmpeg_executable=paths.ffmpeg, output_name=str(plan.get("output_name") or FINAL_VIDEO)),
    )
    _record_final_artifacts(context)
    if manifest.get("status") != "succeeded":
        raise ValueError(str(manifest.get("errors") or "final_video_assembly_failed"))
    return [FINAL_VIDEO_MANIFEST, str(plan.get("output_name") or FINAL_VIDEO), "concat_list.txt"]


def probe_final_video_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    manifest = _state_or_load_final_manifest(context)
    final_video = str(manifest.get("final_video") or FINAL_VIDEO)
    paths = resolve_media_tool_paths()
    metadata = probe_video_metadata(context.output_path(final_video), ffprobe_executable=paths.ffprobe)
    updated = dict(manifest)
    if metadata.probe_status == "succeeded":
        updated.update(
            {
                "duration_sec": metadata.duration_sec,
                "width": metadata.width,
                "height": metadata.height,
                "codec": metadata.codec,
            }
        )
    else:
        updated["warnings"] = list(updated.get("warnings", [])) + metadata.errors
    write_json(context.output_path(FINAL_VIDEO_MANIFEST), updated)
    context.state["final_video_manifest"] = updated
    _record_final_artifacts(context)
    return [FINAL_VIDEO_MANIFEST]


def _record_final_artifacts(context: WorkflowContext) -> None:
    final_video = FINAL_VIDEO
    manifest = context.output_path(FINAL_VIDEO_MANIFEST)
    if manifest.is_file():
        payload = _load_json_object(manifest, "Final video manifest")
        if payload.get("final_video"):
            final_video = str(payload["final_video"])
            context.state["final_video_manifest"] = payload
    context.artifacts["final_video_manifest"] = FINAL_VIDEO_MANIFEST
    context.artifacts["final_video"] = final_video
    context.artifacts["concat_list"] = "concat_list.txt"


def _state_or_load_json(context: WorkflowContext, state_key: str, artifact_key: str) -> dict[str, Any]:
    value = context.state.get(state_key)
    if isinstance(value, dict):
        return value
    return _load_json_object(context.output_path(context.artifacts[artifact_key]), state_key)


def _state_or_load_final_manifest(context: WorkflowContext) -> dict[str, Any]:
    value = context.state.get("final_video_manifest")
    if isinstance(value, dict):
        return value
    return _load_json_object(context.output_path(FINAL_VIDEO_MANIFEST), "Final video manifest")


def _failed_final_manifest(reason: str, errors: list[str], plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "failed",
        "final_video": str(plan.get("output_name") or FINAL_VIDEO),
        "input_clip_count": int(plan.get("clip_count") or 0),
        "input_clips": [clip.get("path") for clip in plan.get("clips", []) if isinstance(clip, dict)],
        "duration_sec": plan.get("target_duration_sec"),
        "ffmpeg_command": [],
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "errors": [reason, *errors],
        "warnings": [],
        "manifest_path": FINAL_VIDEO_MANIFEST,
    }
