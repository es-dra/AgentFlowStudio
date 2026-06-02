from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow_studio.cover_sop import COVER_IMAGE, COVER_MANIFEST, CoverExportConfig, export_cover_from_video
from agentflow_studio.slicing_sop import check_ffmpeg_available, resolve_media_tool_paths
from agentflow_studio.utils import write_json
from agentflow_studio.workflow_engine.context import WorkflowContext
from agentflow_studio.workflow_engine.definitions import WorkflowStepDefinition
from agentflow_studio.workflow_engine.node_artifacts import require_input as _require_input


def export_cover_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    video_path = Path(str(context.resolve_input(str(_require_input(step, "video")))))
    output_ref = str(context.inputs.get("output_name") or step.outputs.get("cover_image") or COVER_IMAGE)
    manifest_ref = step.outputs.get("cover_manifest") or COVER_MANIFEST
    cover_time_sec = _cover_time_sec(context)

    paths = resolve_media_tool_paths()
    ffmpeg_info = check_ffmpeg_available(paths.ffmpeg)
    if not ffmpeg_info.available:
        failed = _failed_manifest(video_path, output_ref, cover_time_sec, [ffmpeg_info.error or "ffmpeg_unavailable"])
        write_json(context.output_path(manifest_ref), failed)
        _record_cover_artifacts(context, output_ref, manifest_ref)
        raise ValueError("ffmpeg_unavailable")

    try:
        config = CoverExportConfig(
            ffmpeg_executable=paths.ffmpeg,
            output_name=output_ref,
            cover_time_sec=cover_time_sec,
        )
        manifest = export_cover_from_video(
            source_video=video_path,
            output_dir=context.output_dir,
            config=config,
        )
    except ValueError as exc:
        failed = _failed_manifest(video_path, output_ref, cover_time_sec, [str(exc)])
        write_json(context.output_path(manifest_ref), failed)
        _record_cover_artifacts(context, output_ref, manifest_ref)
        raise

    if manifest_ref != COVER_MANIFEST:
        write_json(context.output_path(manifest_ref), manifest)
    context.state["cover_manifest"] = manifest
    _record_cover_artifacts(context, str(manifest.get("cover_path") or output_ref), manifest_ref)
    if manifest.get("status") != "succeeded":
        raise ValueError(str(manifest.get("errors") or "cover_export_failed"))
    return [manifest_ref, str(manifest.get("cover_path") or output_ref)]


def _record_cover_artifacts(context: WorkflowContext, cover_ref: str, manifest_ref: str) -> None:
    context.artifacts["cover_manifest"] = manifest_ref
    context.artifacts["cover_image"] = cover_ref


def _failed_manifest(
    source_video: Path,
    cover_path: str,
    cover_time_sec: float,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "status": "failed",
        "source_video": _display_ref(source_video),
        "cover_path": _display_ref(cover_path),
        "cover_time_sec": cover_time_sec,
        "ffmpeg_command": [],
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "errors": errors,
        "warnings": [],
        "manifest_path": COVER_MANIFEST,
    }


def _cover_time_sec(context: WorkflowContext) -> float:
    value = context.inputs.get("cover_time_sec", 1.0)
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("cover_time_sec must be a number.") from exc


def _display_ref(value: str | Path) -> str:
    return str(value).replace("\\", "/")
