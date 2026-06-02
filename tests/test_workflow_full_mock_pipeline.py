from __future__ import annotations

import json

from agentflow_studio.schemas import ClipPlan, Hook, ShortVideoScript
from agentflow_studio.workflow_engine import WorkflowContext, WorkflowRunner, default_node_registry, load_workflow


def test_workflow_runner_executes_full_mock_pipeline(tmp_path) -> None:
    output_dir = tmp_path / "full_mock"
    workflow = load_workflow("workflows/mock_text_to_slices.yaml")
    context = WorkflowContext(
        run_id="run_full_mock",
        workflow_name=workflow.name,
        output_dir=output_dir,
        inputs={"input_text_file": "examples/demo_text/story.txt"},
    )

    run = WorkflowRunner(default_node_registry()).run(workflow, context)

    assert run.status == "success"
    assert len(run.steps) == 4

    hooks_path = output_dir / "hooks.json"
    scripts_path = output_dir / "scripts.json"
    clip_plans_path = output_dir / "clip_plans.json"
    slice_manifest_path = output_dir / "slice_manifest.json"
    clips_dir = output_dir / "clips"
    manifest_path = output_dir / "manifest.json"

    assert hooks_path.is_file()
    assert scripts_path.is_file()
    assert clip_plans_path.is_file()
    assert slice_manifest_path.is_file()
    assert manifest_path.is_file()
    assert clips_dir.is_dir()

    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    scripts = json.loads(scripts_path.read_text(encoding="utf-8"))
    clip_plans = json.loads(clip_plans_path.read_text(encoding="utf-8"))
    slice_manifest = json.loads(slice_manifest_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert [Hook.model_validate(item) for item in hooks]
    assert [ShortVideoScript.model_validate(item) for item in scripts]
    assert [ClipPlan.model_validate(item) for item in clip_plans]
    assert slice_manifest["status"] == "success"
    assert slice_manifest["clip_count"] == 3
    assert len(list(clips_dir.glob("*.txt"))) == 3
    assert manifest["status"] == "success"
    assert manifest["artifacts"]["clip_plans"] == "clip_plans.json"
    assert manifest["artifacts"]["slice_manifest"] == "slice_manifest.json"
