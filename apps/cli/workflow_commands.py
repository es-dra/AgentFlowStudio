from __future__ import annotations

from pathlib import Path

from narratocut.workflow_engine import (
    WorkflowContext,
    WorkflowRunner,
    default_node_registry,
    load_workflow,
)
from narratocut.workflow_engine.input_bundle import load_workflow_inputs


def run_workflow_from_cli(
    workflow_path: Path,
    input_path: Path,
    output_dir: Path,
) -> tuple[str, Path]:
    workflow = load_workflow(workflow_path)
    context = WorkflowContext(
        run_id=output_dir.name,
        workflow_name=workflow.name,
        workflow_path=str(workflow_path),
        mode=workflow.mode,
        quality_profile=workflow.quality_profile,
        output_dir=output_dir,
        inputs=load_workflow_inputs(input_path),
    )
    run = WorkflowRunner(default_node_registry()).run(workflow, context)
    return run.status, context.output_path("manifest.json")
