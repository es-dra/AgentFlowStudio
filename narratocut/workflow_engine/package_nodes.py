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
            "subtitled_video": context.inputs.get("subtitled_video_path"),
            "bgm_video": context.inputs.get("bgm_video_path"),
            "cover_image": context.inputs.get("cover_path"),
            "review_report": context.inputs.get("review_report_path"),
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
