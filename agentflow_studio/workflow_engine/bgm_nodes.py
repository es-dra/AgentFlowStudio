from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow_studio.bgm_sop import (
    AUDIO_MIX_MANIFEST,
    BGM_VIDEO,
    BGMMixConfig,
    mix_bgm_into_video,
)
from agentflow_studio.slicing_sop import check_ffmpeg_available, probe_video_metadata, resolve_media_tool_paths
from agentflow_studio.utils import write_json
from agentflow_studio.workflow_engine.context import WorkflowContext
from agentflow_studio.workflow_engine.definitions import WorkflowStepDefinition
from agentflow_studio.workflow_engine.node_artifacts import (
    load_json_object as _load_json_object,
    require_input as _require_input,
)


def mix_bgm_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    video_path = Path(str(context.resolve_input(str(_require_input(step, "video")))))
    bgm_path = Path(str(context.resolve_input(str(_require_input(step, "bgm")))))
    bgm_metadata = _optional_bgm_metadata(step, context)
    output_ref = str(context.inputs.get("output_name") or step.outputs.get("final_video") or BGM_VIDEO)
    manifest_ref = step.outputs.get("audio_mix_manifest") or AUDIO_MIX_MANIFEST
    paths = resolve_media_tool_paths()
    ffmpeg_info = check_ffmpeg_available(paths.ffmpeg)
    if not ffmpeg_info.available:
        failed = _failed_manifest(video_path, bgm_path, output_ref, [ffmpeg_info.error or "ffmpeg_unavailable"])
        write_json(context.output_path(manifest_ref), failed)
        _record_bgm_artifacts(context, output_ref, manifest_ref)
        raise ValueError("ffmpeg_unavailable")

    try:
        manifest = mix_bgm_into_video(
            source_video=video_path,
            bgm_audio=bgm_path,
            output_dir=context.output_dir,
            config=BGMMixConfig(
                ffmpeg_executable=paths.ffmpeg,
                output_name=output_ref,
                bgm_volume=_float_input(context, "bgm_volume", 0.2),
                original_audio_volume=_float_input(context, "original_audio_volume", 1.0),
                mix_strategy=str(context.inputs.get("mix_strategy") or "mix_with_original"),
            ),
        )
    except ValueError as exc:
        failed = _failed_manifest(video_path, bgm_path, output_ref, [str(exc)])
        write_json(context.output_path(manifest_ref), failed)
        _record_bgm_artifacts(context, output_ref, manifest_ref)
        raise

    manifest = _with_bgm_metadata(manifest, bgm_metadata)
    write_json(context.output_path(manifest_ref), manifest)
    context.state["audio_mix_manifest"] = manifest
    _record_bgm_artifacts(context, str(manifest.get("output_video") or output_ref), manifest_ref)
    if manifest.get("status") != "succeeded":
        raise ValueError(str(manifest.get("errors") or "bgm_mix_failed"))
    return [manifest_ref, str(manifest.get("output_video") or output_ref)]


def probe_bgm_mix_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    manifest_ref = context.artifacts.get("audio_mix_manifest") or AUDIO_MIX_MANIFEST
    manifest_path = context.output_path(manifest_ref)
    manifest = _load_json_object(manifest_path, "Audio mix manifest")
    output_ref = str(manifest.get("output_video") or context.artifacts.get("bgm_video") or BGM_VIDEO)

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
    context.state["audio_mix_manifest"] = updated
    _record_bgm_artifacts(context, output_ref, manifest_ref)
    return [manifest_ref]


def _record_bgm_artifacts(context: WorkflowContext, output_ref: str, manifest_ref: str) -> None:
    context.artifacts["audio_mix_manifest"] = manifest_ref
    context.artifacts["bgm_video"] = output_ref


def _failed_manifest(source_video: Path, bgm_path: Path, output_video: str, errors: list[str]) -> dict[str, Any]:
    return {
        "status": "failed",
        "source_video": _display_ref(source_video),
        "bgm_path": _display_ref(bgm_path),
        "output_video": _display_ref(output_video),
        "bgm_volume": None,
        "original_audio_volume": None,
        "mix_strategy": None,
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
        "manifest_path": AUDIO_MIX_MANIFEST,
    }


def _float_input(context: WorkflowContext, name: str, default: float) -> float:
    value = context.inputs.get(name, default)
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number.") from exc


def _optional_bgm_metadata(step: WorkflowStepDefinition, context: WorkflowContext) -> dict[str, Any] | None:
    if "bgm_metadata" not in step.inputs:
        return None
    value = step.inputs["bgm_metadata"]
    if isinstance(value, str) and value not in context.inputs and value not in context.state and value not in context.artifacts:
        return None
    metadata_path = Path(str(context.resolve_input(str(value))))
    metadata = _load_json_object(metadata_path, "BGM metadata")
    if not isinstance(metadata.get("quality_verified"), bool):
        raise ValueError("BGM metadata must include boolean quality_verified.")
    return metadata


def _with_bgm_metadata(manifest: dict[str, Any], metadata: dict[str, Any] | None) -> dict[str, Any]:
    if metadata is None:
        return manifest
    enriched = dict(manifest)
    enriched["quality_verified"] = bool(metadata.get("quality_verified"))
    enriched["bgm_metadata"] = metadata
    return enriched


def _display_ref(value: str | Path) -> str:
    return str(value).replace("\\", "/")
