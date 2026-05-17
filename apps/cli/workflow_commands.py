from __future__ import annotations

from pathlib import Path

from narratocut.harness import inspect_run
from narratocut.workflow_engine import (
    WorkflowContext,
    WorkflowRunner,
    default_node_registry,
    load_workflow,
)


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
        output_dir=output_dir,
        inputs={"input_text_file": str(input_path)},
    )
    run = WorkflowRunner(default_node_registry()).run(workflow, context)
    inspect_run(output_dir)
    return run.status, context.output_path("manifest.json")
