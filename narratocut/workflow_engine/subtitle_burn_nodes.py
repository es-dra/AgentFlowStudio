from __future__ import annotations

from pathlib import Path
from typing import Any

from narratocut.slicing_sop import check_ffmpeg_available, probe_video_metadata, resolve_media_tool_paths
from narratocut.subtitle_burn_sop import (
    SUBTITLE_BURN_MANIFEST,
    SUBTITLED_VIDEO,
    SubtitleBurnConfig,
    burn_subtitles_into_video,
)
from narratocut.utils import write_json
from narratocut.workflow_engine.context import WorkflowContext
from narratocut.workflow_engine.definitions import WorkflowStepDefinition
from narratocut.workflow_engine.node_artifacts import (
    load_json_object as _load_json_object,
    require_input as _require_input,
)


def burn_subtitles_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    video_path = Path(str(context.resolve_input(str(_require_input(step, "video")))))
    subtitles_path = Path(str(context.resolve_input(str(_require_input(step, "subtitles")))))
    output_ref = str(context.inputs.get("output_name") or step.outputs.get("final_video") or SUBTITLED_VIDEO)
    manifest_ref = step.outputs.get("subtitle_burn_manifest") or SUBTITLE_BURN_MANIFEST
    paths = resolve_media_tool_paths()
    ffmpeg_info = check_ffmpeg_available(paths.ffmpeg)
    if not ffmpeg_info.available:
        failed = _failed_manifest(
            video_path,
            subtitles_path,
            output_ref,
            [ffmpeg_info.error or "ffmpeg_unavailable"],
        )
        write_json(context.output_path(manifest_ref), failed)
        _record_burn_artifacts(context, output_ref, manifest_ref)
        raise ValueError("ffmpeg_unavailable")

    try:
        manifest = burn_subtitles_into_video(
            source_video=video_path,
            subtitles_path=subtitles_path,
            output_dir=context.output_dir,
            config=SubtitleBurnConfig(ffmpeg_executable=paths.ffmpeg, output_name=output_ref),
        )
    except ValueError as exc:
        failed = _failed_manifest(video_path, subtitles_path, output_ref, [str(exc)])
        write_json(context.output_path(manifest_ref), failed)
        _record_burn_artifacts(context, output_ref, manifest_ref)
        raise

    if manifest_ref != SUBTITLE_BURN_MANIFEST:
        write_json(context.output_path(manifest_ref), manifest)
    context.state["subtitle_burn_manifest"] = manifest
    _record_burn_artifacts(context, str(manifest.get("output_video") or output_ref), manifest_ref)
    if manifest.get("status") != "succeeded":
        raise ValueError(str(manifest.get("errors") or "subtitle_burn_failed"))
    return [manifest_ref, str(manifest.get("output_video") or output_ref)]


def probe_subtitle_burn_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    manifest_ref = context.artifacts.get("subtitle_burn_manifest") or SUBTITLE_BURN_MANIFEST
    manifest_path = context.output_path(manifest_ref)
    manifest = _load_json_object(manifest_path, "Subtitle burn manifest")
    output_ref = str(manifest.get("output_video") or context.artifacts.get("subtitled_video") or SUBTITLED_VIDEO)

    paths = resolve_media_tool_paths()
    metadata = probe_video_metadata(context.output_path(output_ref), ffprobe_executable=paths.ffprobe)
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
    write_json(manifest_path, updated)
    context.state["subtitle_burn_manifest"] = updated
    artifact_ref = context.artifacts.get("subtitle_burn_manifest") or SUBTITLE_BURN_MANIFEST
    _record_burn_artifacts(context, output_ref, artifact_ref)
    return [artifact_ref]


def _record_burn_artifacts(context: WorkflowContext, output_ref: str, manifest_ref: str) -> None:
    context.artifacts["subtitle_burn_manifest"] = manifest_ref
    context.artifacts["subtitled_video"] = output_ref


def _failed_manifest(source_video: Path, subtitles_path: Path, output_video: str, errors: list[str]) -> dict[str, Any]:
    return {
        "status": "failed",
        "source_video": _display_ref(source_video),
        "subtitles_path": _display_ref(subtitles_path),
        "output_video": _display_ref(output_video),
        "duration_sec": None,
        "width": None,
        "height": None,
        "codec": None,
        "ffmpeg_command": [],
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "errors": errors,
        "warnings": [],
        "manifest_path": SUBTITLE_BURN_MANIFEST,
    }


def _display_ref(value: str | Path) -> str:
    return str(value).replace("\\", "/")
