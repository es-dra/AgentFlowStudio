from __future__ import annotations

from pathlib import Path

from narratocut.roi_sop import analyze_hooks_from_text, generate_scripts_from_hooks
from narratocut.slicing_sop import (
    RealSlicingConfig,
    check_ffmpeg_available,
    generate_clip_plans_from_scripts,
    mock_slice_clip_plans,
    probe_video_metadata,
    resolve_media_tool_paths,
    slice_clip_plans_real,
    validate_clip_plan,
)
from narratocut.slicing_sop.real_slicer import REAL_SLICE_MANIFEST
from narratocut.utils import write_json
from narratocut.workflow_engine.context import WorkflowContext
from narratocut.workflow_engine.definitions import WorkflowStepDefinition
from narratocut.workflow_engine.node_artifacts import (
    load_clip_plan,
    load_clip_plans,
    load_hooks,
    load_roi_settings,
    load_scripts,
    require_input,
    require_output,
    skipped_real_slice_manifest,
    state_or_default_roi_settings,
    state_or_load_clip_plan,
    state_or_load_video_metadata,
)
from narratocut.workflow_engine.assembly_nodes import (
    concat_clips_node,
    generate_assembly_plan_node,
    load_real_slice_manifest_node,
    probe_final_video_node,
)
from narratocut.workflow_engine.highlight_nodes import (
    align_script_highlights_to_transcript_node,
    detect_highlights_node,
    generate_candidate_windows_node,
    generate_highlight_clip_plan_node,
    load_script_node,
    load_transcript_node,
    rank_highlights_by_roi_node,
    write_clip_plan_node,
    write_highlight_plan_node,
)
from narratocut.workflow_engine.transcription_nodes import (
    analyze_audio_boundary_signals_node,
    extract_audio_node,
    load_video_node,
    transcribe_audio_openai_compatible_node,
    transcribe_audio_faster_whisper_node,
    transcribe_audio_mock_node,
    write_transcript_node,
)
from narratocut.workflow_engine.subtitle_nodes import write_clip_timeline_subtitles_node, write_subtitles_node
from narratocut.workflow_engine.subtitle_burn_nodes import burn_subtitles_node, probe_subtitle_burn_node
from narratocut.workflow_engine.cover_nodes import export_cover_node
from narratocut.workflow_engine.bgm_nodes import mix_bgm_node, probe_bgm_mix_node
from narratocut.workflow_engine.ocr_nodes import (
    build_ocr_transcript_node,
    score_candidate_windows_node,
    write_highlight_score_report_node,
    write_selection_diagnostics_node,
    write_ocr_transcript_node,
)
from narratocut.workflow_engine.package_nodes import write_finished_package_node, write_package_report_node
from narratocut.workflow_engine.narratostudio_nodes import register_narratostudio_nodes
from narratocut.workflow_engine.posterflow_nodes import register_posterflow_nodes
from narratocut.workflow_engine.registry import NodeRegistry


def analyze_hooks_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    text_file = require_input(step, "text_file")
    text_path = Path(str(context.resolve_input(str(text_file))))
    input_text = text_path.read_text(encoding="utf-8")
    hooks = analyze_hooks_from_text(input_text)

    output_ref = require_output(step, "hooks")
    write_json(context.output_path(output_ref), hooks)
    context.artifacts["hooks"] = output_ref
    return [output_ref]


def generate_scripts_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    hooks_ref = require_input(step, "hooks")
    hooks_path = Path(str(context.resolve_input(str(hooks_ref))))
    hooks = load_hooks(hooks_path)
    scripts = generate_scripts_from_hooks(hooks)

    output_ref = require_output(step, "scripts")
    write_json(context.output_path(output_ref), scripts)
    context.artifacts["scripts"] = output_ref
    return [output_ref]


def generate_clip_plans_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    scripts_ref = require_input(step, "scripts")
    scripts_path = Path(str(context.resolve_input(str(scripts_ref))))
    scripts = load_scripts(scripts_path)
    clip_plans = generate_clip_plans_from_scripts(scripts)

    output_ref = require_output(step, "clip_plans")
    write_json(context.output_path(output_ref), clip_plans)
    context.artifacts["clip_plans"] = output_ref
    return [output_ref]


def mock_slice_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    clip_plans_ref = require_input(step, "clip_plans")
    clip_plans_path = Path(str(context.resolve_input(str(clip_plans_ref))))
    clip_plans = load_clip_plans(clip_plans_path)

    output_ref = require_output(step, "slice_manifest")
    mock_slice_clip_plans(clip_plans, context.output_dir)
    context.artifacts["slice_manifest"] = output_ref
    context.artifacts["clips"] = "clips"
    return [output_ref, "clips"]


def load_roi_config_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    roi_ref = require_input(step, "roi_config")
    roi_path = Path(str(context.resolve_input(str(roi_ref))))
    roi_settings = load_roi_settings(roi_path)

    output_ref = require_output(step, "roi_settings")
    write_json(context.output_path(output_ref), roi_settings)
    context.artifacts["roi_settings"] = output_ref
    context.state["roi_settings"] = roi_settings
    return [output_ref]


def load_clip_plan_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    clip_plan_ref = require_input(step, "clip_plan")
    clip_plan_path = Path(str(context.resolve_input(str(clip_plan_ref))))
    clip_plan = load_clip_plan(clip_plan_path)

    output_ref = require_output(step, "clip_plan")
    write_json(context.output_path(output_ref), clip_plan)
    context.artifacts["clip_plan"] = output_ref
    context.state["clip_plan"] = clip_plan
    context.state["clip_plan_path"] = str(clip_plan_path)
    return [output_ref]


def probe_video_metadata_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    video_ref = require_input(step, "video")
    video_path = Path(str(context.resolve_input(str(video_ref))))
    paths = resolve_media_tool_paths()
    metadata = probe_video_metadata(video_path, ffprobe_executable=paths.ffprobe)

    output_ref = require_output(step, "video_metadata")
    write_json(context.output_path(output_ref), metadata)
    context.artifacts["video_metadata"] = output_ref
    context.state["video_metadata"] = metadata
    return [output_ref]


def validate_clip_plan_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    clip_plan = state_or_load_clip_plan(context, "clip_plan")
    roi_settings = state_or_default_roi_settings(context)
    metadata = state_or_load_video_metadata(context, "video_metadata")
    paths = resolve_media_tool_paths()
    ffmpeg_info = check_ffmpeg_available(paths.ffmpeg)
    report = validate_clip_plan(
        clip_plan,
        roi_settings,
        metadata,
        ffmpeg_available=ffmpeg_info.available,
    )

    output_ref = require_output(step, "validation")
    write_json(context.output_path(output_ref), report)
    context.artifacts["clip_plan_validation"] = output_ref
    context.state["clip_plan_validation"] = report
    if report.status == "failed":
        skipped = skipped_real_slice_manifest("clip_plan_validation_failed", report)
        write_json(context.output_path(REAL_SLICE_MANIFEST), skipped)
        context.artifacts["real_slice_manifest"] = REAL_SLICE_MANIFEST
        context.artifacts["clips"] = _clips_dir(context)
        raise ValueError("clip_plan_validation_failed")
    return [output_ref]


def real_slice_video_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    clip_plan = state_or_load_clip_plan(context, "clip_plan")
    paths = resolve_media_tool_paths()
    ffmpeg_info = check_ffmpeg_available(paths.ffmpeg)
    if not ffmpeg_info.available:
        failed = {
            "status": "failed",
            "reason": "ffmpeg_unavailable",
            "clips": [],
            "errors": [ffmpeg_info.error or "ffmpeg_unavailable"],
            "manifest_path": REAL_SLICE_MANIFEST,
        }
        write_json(context.output_path(REAL_SLICE_MANIFEST), failed)
        context.artifacts["real_slice_manifest"] = REAL_SLICE_MANIFEST
        context.artifacts["clips"] = _clips_dir(context)
        raise ValueError("ffmpeg_unavailable")

    video_ref = require_input(step, "video")
    video_path = Path(str(context.resolve_input(str(video_ref))))
    manifest = slice_clip_plans_real(
        input_video=video_path,
        clip_plans=[clip_plan],
        output_dir=context.output_dir,
        config=RealSlicingConfig(ffmpeg_executable=paths.ffmpeg, clips_dir=_clips_dir(context)),
    )
    manifest = _add_real_slice_provenance(
        manifest,
        source_video=video_path,
        clip_plan_path=context.state.get("clip_plan_path"),
        clips_dir=_clips_dir(context),
    )
    write_json(context.output_path(REAL_SLICE_MANIFEST), manifest)
    context.artifacts["real_slice_manifest"] = REAL_SLICE_MANIFEST
    context.artifacts["clips"] = _clips_dir(context)
    if manifest.get("status") not in {"succeeded", "passed"}:
        raise ValueError(str(manifest.get("reason") or manifest.get("errors") or "real_slice_failed"))
    return [REAL_SLICE_MANIFEST, _clips_dir(context)]


def default_node_registry() -> NodeRegistry:
    registry = NodeRegistry()
    registry.register("analyze_hooks", analyze_hooks_node)
    registry.register("generate_scripts", generate_scripts_node)
    registry.register("generate_clip_plans", generate_clip_plans_node)
    registry.register("mock_slice", mock_slice_node)
    registry.register("load_roi_config", load_roi_config_node)
    registry.register("load_clip_plan", load_clip_plan_node)
    registry.register("probe_video_metadata", probe_video_metadata_node)
    registry.register("validate_clip_plan", validate_clip_plan_node)
    registry.register("real_slice_video", real_slice_video_node)
    registry.register("load_script", load_script_node)
    registry.register("load_transcript", load_transcript_node)
    registry.register("detect_highlights", detect_highlights_node)
    registry.register("generate_candidate_windows", generate_candidate_windows_node)
    registry.register("build_ocr_transcript", build_ocr_transcript_node)
    registry.register("write_ocr_transcript", write_ocr_transcript_node)
    registry.register("score_candidate_windows", score_candidate_windows_node)
    registry.register("write_highlight_score_report", write_highlight_score_report_node)
    registry.register("write_selection_diagnostics", write_selection_diagnostics_node)
    registry.register("rank_highlights_by_roi", rank_highlights_by_roi_node)
    registry.register("generate_highlight_clip_plan", generate_highlight_clip_plan_node)
    registry.register("generate_clip_plan_from_highlights", generate_highlight_clip_plan_node)
    registry.register("align_script_highlights_to_transcript", align_script_highlights_to_transcript_node)
    registry.register("write_highlight_plan", write_highlight_plan_node)
    registry.register("write_clip_plan", write_clip_plan_node)
    registry.register("load_video", load_video_node)
    registry.register("extract_audio", extract_audio_node)
    registry.register("analyze_audio_boundary_signals", analyze_audio_boundary_signals_node)
    registry.register("transcribe_audio_mock", transcribe_audio_mock_node)
    registry.register("transcribe_audio_openai_compatible", transcribe_audio_openai_compatible_node)
    registry.register("transcribe_audio_faster_whisper", transcribe_audio_faster_whisper_node)
    registry.register("write_transcript", write_transcript_node)
    registry.register("load_real_slice_manifest", load_real_slice_manifest_node)
    registry.register("generate_assembly_plan", generate_assembly_plan_node)
    registry.register("concat_clips", concat_clips_node)
    registry.register("probe_final_video", probe_final_video_node)
    registry.register("write_subtitles", write_subtitles_node)
    registry.register("write_clip_timeline_subtitles", write_clip_timeline_subtitles_node)
    registry.register("burn_subtitles", burn_subtitles_node)
    registry.register("probe_subtitle_burn", probe_subtitle_burn_node)
    registry.register("export_cover", export_cover_node)
    registry.register("mix_bgm", mix_bgm_node)
    registry.register("probe_bgm_mix", probe_bgm_mix_node)
    registry.register("write_finished_package", write_finished_package_node)
    registry.register("write_package_report", write_package_report_node)
    register_narratostudio_nodes(registry)
    register_posterflow_nodes(registry)
    return registry


def _add_real_slice_provenance(
    manifest: dict[str, object],
    *,
    source_video: Path,
    clip_plan_path: object,
    clips_dir: str,
) -> dict[str, object]:
    enriched = dict(manifest)
    enriched["source_video"] = str(source_video)
    if clip_plan_path:
        enriched["clip_plan_path"] = str(clip_plan_path)
    enriched["clips_dir"] = clips_dir
    return enriched


def _clips_dir(context: WorkflowContext) -> str:
    value = context.inputs.get("output_clips_dir") or "clips"
    return str(value).strip().replace("\\", "/") or "clips"
