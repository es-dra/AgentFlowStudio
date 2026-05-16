from __future__ import annotations

import json

from narratocut.schemas import Hook, ShortVideoScript
from narratocut.workflow_engine import (
    WorkflowContext,
    WorkflowDefinition,
    WorkflowRunner,
    default_node_registry,
    load_workflow,
)


def test_workflow_runner_executes_mock_roi_to_script(tmp_path) -> None:
    output_dir = tmp_path / "run"
    workflow = load_workflow("workflows/mock_roi_to_script.yaml")
    context = WorkflowContext(
        run_id="run_test",
        workflow_name=workflow.name,
        output_dir=output_dir,
        inputs={"input_text_file": "examples/demo_text/story.txt"},
    )

    run = WorkflowRunner(default_node_registry()).run(workflow, context)

    hooks_path = output_dir / "hooks.json"
    scripts_path = output_dir / "scripts.json"
    manifest_path = output_dir / "manifest.json"

    assert run.status == "success"
    assert len(run.steps) == 2
    assert hooks_path.is_file()
    assert scripts_path.is_file()
    assert manifest_path.is_file()

    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    scripts = json.loads(scripts_path.read_text(encoding="utf-8"))
    assert [Hook.model_validate(item) for item in hooks]
    assert [ShortVideoScript.model_validate(item) for item in scripts]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "success"
    assert manifest["inputs"]["input_text_file"] == "examples/demo_text/story.txt"
    assert manifest["artifacts"]["hooks"] == "hooks.json"
    assert manifest["artifacts"]["scripts"] == "scripts.json"
    assert len(manifest["steps"]) == 2


def test_workflow_runner_records_failure_for_unknown_step_type(tmp_path) -> None:
    workflow = WorkflowDefinition(
        name="bad",
        steps=[{"id": "bad_step", "type": "missing_node"}],
    )
    context = WorkflowContext(
        run_id="run_failed",
        workflow_name=workflow.name,
        output_dir=tmp_path / "failed",
        inputs={},
    )

    run = WorkflowRunner(default_node_registry()).run(workflow, context)
    manifest = json.loads((context.output_dir / "manifest.json").read_text(encoding="utf-8"))

    assert run.status == "failed"
    assert run.error
    assert run.steps[0].status == "failed"
    assert "Unknown workflow node type" in manifest["error"]
