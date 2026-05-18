from __future__ import annotations

from pathlib import Path

from narratocut.package_sop import FINISHED_PACKAGE_MANIFEST, build_finished_package_manifest
from narratocut.utils import write_json
from narratocut.workflow_engine.context import WorkflowContext
from narratocut.workflow_engine.definitions import WorkflowStepDefinition


def write_finished_package_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    final_video_path = Path(str(context.resolve_input(str(_require_input(step, "final_video")))))
    manifest_ref = step.outputs.get("finished_package_manifest") or FINISHED_PACKAGE_MANIFEST
    package_id = str(context.inputs.get("package_id") or context.run_id)

    manifest = build_finished_package_manifest(
        package_id=package_id,
        final_video_path=final_video_path,
        optional_assets={
            "subtitled_video": _optional_resolved_asset(step, context, "subtitled_video", "subtitled_video_path"),
            "bgm_video": _optional_resolved_asset(step, context, "bgm_video", "bgm_video_path"),
            "cover_image": _optional_resolved_asset(step, context, "cover_image", "cover_path"),
            "review_report": _optional_resolved_asset(step, context, "review_report", "review_report_path"),
        },
        evidence={
            "final_video_manifest": _optional_resolved_asset(step, context, "final_video_manifest", "final_video_manifest_path"),
            "real_slice_manifest": _optional_resolved_asset(step, context, "real_slice_manifest", "real_slice_manifest_path"),
            "clip_plan": _optional_resolved_asset(step, context, "clip_plan", "clip_plan_path"),
            "subtitle_manifest": _optional_resolved_asset(step, context, "subtitle_manifest", "subtitle_manifest_path"),
            "audio_mix_manifest": _optional_resolved_asset(step, context, "audio_mix_manifest", "audio_mix_manifest_path"),
        },
    )
    write_json(context.output_path(manifest_ref), manifest)
    context.state["finished_package_manifest"] = manifest
    context.artifacts["finished_package_manifest"] = manifest_ref
    if manifest.status != "succeeded":
        raise ValueError(str(manifest.errors or "finished_package_failed"))
    return [manifest_ref]


def _require_input(step: WorkflowStepDefinition, name: str) -> object:
    if name not in step.inputs:
        raise ValueError(f"Step {step.id} missing required input: {name}")
    return step.inputs[name]


def _optional_resolved_asset(
    step: WorkflowStepDefinition,
    context: WorkflowContext,
    input_name: str,
    legacy_input_name: str,
) -> object | None:
    if input_name in step.inputs:
        value = step.inputs[input_name]
        if isinstance(value, str):
            return context.resolve_input(value)
        return value
    return context.inputs.get(legacy_input_name)
