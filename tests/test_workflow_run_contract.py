from __future__ import annotations

import json

from agentflow_studio.workflow_engine import WorkflowContext, WorkflowRunner, default_node_registry, load_workflow


def test_workflow_runner_writes_run_manifest_and_trace(tmp_path) -> None:
    output_dir = tmp_path / "full_mock"
    workflow_path = "workflows/mock_text_to_slices.yaml"
    workflow = load_workflow(workflow_path)
    context = WorkflowContext(
        run_id="run_full_mock",
        workflow_name=workflow.name,
        workflow_path=workflow_path,
        output_dir=output_dir,
        inputs={"input_text_file": "examples/demo_text/story.txt"},
    )

    run = WorkflowRunner(default_node_registry()).run(workflow, context)

    run_manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
    trace = json.loads((output_dir / "trace.json").read_text(encoding="utf-8"))

    assert run.status == "success"
    assert run_manifest["project"] == "AgentFlow Studio"
    assert run_manifest["run_id"] == "run_full_mock"
    assert run_manifest["workflow"] == workflow_path
    assert run_manifest["mode"] == "mock"
    assert run_manifest["status"] == "success"
    assert run_manifest["environment"] == {
        "ffmpeg_required": False,
        "network_required": False,
    }
    assert run_manifest["artifacts"]["manifest"] == "manifest.json"
    assert run_manifest["artifacts"]["clips_dir"] == "clips/"
    assert run_manifest["artifact_index"]["hooks"] == {
        "path": "hooks.json",
        "required": True,
        "exists": True,
    }

    assert trace["workflow"] == workflow_path
    assert trace["run_id"] == "run_full_mock"
    assert [step["step_id"] for step in trace["steps"]] == [
        "analyze_hooks",
        "generate_scripts",
        "generate_clip_plans",
        "mock_slice",
    ]
    assert all(step["duration_ms"] >= 0 for step in trace["steps"])
    assert trace["steps"][0]["inputs"] == ["examples/demo_text/story.txt"]
    assert trace["steps"][0]["outputs"] == ["hooks.json"]
