from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from apps.cli.report_commands import (
    inspect_run_output,
    package_report_output,
    review_run_output,
)
from apps.web_bridge.diagnostics import bridge_health, inspect_workflow_input
from apps.web_bridge.run_state import bridge_progress, initial_steps, run_status, steps_from_context, write_bridge_status
from apps.web_bridge.utils import display_ref, safe_stem
from apps.web_bridge.workflow_profiles import workflow_web_profile
from narratocut.workflow_engine import WorkflowContext, WorkflowRunner, default_node_registry, load_workflow
from narratocut.workflow_engine.input_bundle import load_workflow_inputs
from narratocut.workflow_engine.planner import draft_workflow_plan, write_workflow_plan


WORKFLOW_ROOT = Path("workflows")
DEFAULT_RUN_ROOT = Path("data/processed/runs/web_bridge")
DEFAULT_PLAN_ROOT = Path("data/reports/web_bridge")
_RUN_THREADS: dict[str, threading.Thread] = {}


def list_workflows(workflow_root: Path = WORKFLOW_ROOT) -> list[dict[str, Any]]:
    workflows: list[dict[str, Any]] = []
    for path in sorted(workflow_root.glob("*.yaml")):
        try:
            definition = load_workflow(path)
        except (FileNotFoundError, ValueError) as exc:
            workflows.append(
                {
                    "name": path.stem,
                    "path": display_ref(path),
                    "status": "invalid",
                    "error": str(exc),
                    "metadata": {},
                    "step_count": 0,
                    "inputs": [],
                    "outputs": [],
                }
            )
            continue
        workflows.append(
            {
                "name": definition.name,
                "path": display_ref(path),
                "version": definition.version,
                "mode": definition.mode,
                "quality_profile": definition.quality_profile,
                "status": "valid",
                "metadata": definition.metadata,
                "step_count": len(definition.steps),
                "inputs": _workflow_inputs(definition),
                "outputs": _workflow_outputs(definition),
                "steps": [
                    {
                        "id": step.id,
                        "type": step.type,
                        "inputs": step.inputs,
                        "outputs": step.outputs,
                    }
                    for step in definition.steps
                ],
                "web_profile": workflow_web_profile(definition, path),
            }
        )
    return workflows


def create_workflow_plan(
    workflow_path: Path,
    input_path: Path,
    output_dir: Path | None = None,
    *,
    tool_catalog_path: Path = Path("configs/tool_catalog.yaml"),
) -> dict[str, Any]:
    plan_dir = output_dir or DEFAULT_PLAN_ROOT / safe_stem(workflow_path.stem)
    plan_path = plan_dir / "workflow_plan.json"
    plan = draft_workflow_plan(workflow_path=workflow_path, input_path=input_path, tool_catalog_path=tool_catalog_path)
    written_path = write_workflow_plan(
        output_path=plan_path,
        workflow_path=workflow_path,
        input_path=input_path,
        tool_catalog_path=tool_catalog_path,
        plan=plan,
    )
    return {
        **plan,
        "plan_path": display_ref(written_path),
        "input_check": inspect_workflow_input(input_path),
        "next_actions": _plan_next_actions(plan),
    }


def run_workflow(workflow_path: Path, input_path: Path, output_dir: Path | None = None) -> dict[str, Any]:
    run_dir = output_dir or DEFAULT_RUN_ROOT / safe_stem(workflow_path.stem)
    workflow = load_workflow(workflow_path)
    context = _workflow_context(workflow, workflow_path, input_path, run_dir)
    run = _run_workflow_with_bridge_status(workflow, context)
    return run_status(run_dir) | {
        "status": run.status,
        "manifest_path": display_ref(context.output_path("manifest.json")),
        "input_check": inspect_workflow_input(input_path),
    }


def start_workflow_run(workflow_path: Path, input_path: Path, output_dir: Path | None = None) -> dict[str, Any]:
    run_dir = output_dir or DEFAULT_RUN_ROOT / safe_stem(workflow_path.stem)
    run_key = display_ref(run_dir)
    running_thread = _RUN_THREADS.get(run_key)
    if running_thread and running_thread.is_alive():
        return run_status(run_dir) | {"accepted": False, "message": "run already in progress"}

    workflow = load_workflow(workflow_path)
    context = _workflow_context(workflow, workflow_path, input_path, run_dir)
    write_bridge_status(
        run_dir,
        {
            "run_id": context.run_id,
            "run_dir": display_ref(run_dir),
            "workflow": display_ref(workflow_path),
            "status": "pending",
            "steps": initial_steps(workflow),
            "current_step": None,
            "event": "queued",
            "errors": [],
        },
    )
    thread = threading.Thread(
        target=_run_workflow_thread,
        args=(workflow, context, run_key),
        name=f"narratocut-web-run-{context.run_id}",
        daemon=True,
    )
    _RUN_THREADS[run_key] = thread
    thread.start()
    return run_status(run_dir) | {
        "accepted": True,
        "message": "run started",
        "input_check": inspect_workflow_input(input_path),
        "status_url": f"/runs/{display_ref(run_dir)}",
    }


def refresh_run_review(run_dir: Path) -> dict[str, Any]:
    inspection, inspect_lines = inspect_run_output(run_dir)
    report, review_lines = review_run_output(run_dir)
    package_path, package_lines = package_report_output(run_dir)
    return {
        "run_id": run_dir.name,
        "run_dir": display_ref(run_dir),
        "quality": inspection["quality_report"],
        "review": report,
        "package_report": display_ref(package_path),
        "artifacts": {
            "quality_report": display_ref(run_dir / "quality_report.json"),
            "review_report": display_ref(run_dir / "review_report.json"),
            "package_report": display_ref(package_path),
        },
        "logs": inspect_lines + review_lines + package_lines,
        "status": report.get("status", inspection.get("status", "unknown")),
    }


def _workflow_inputs(definition: Any) -> list[str]:
    values: list[str] = []
    for step in definition.steps:
        for ref in step.inputs.values():
            text = str(ref)
            if text not in values:
                values.append(text)
    return values


def _workflow_outputs(definition: Any) -> list[str]:
    values: list[str] = []
    for step in definition.steps:
        for ref in step.outputs.values():
            text = str(ref)
            if text not in values:
                values.append(text)
    return values


def _run_workflow_thread(workflow: Any, context: WorkflowContext, run_key: str) -> None:
    try:
        _run_workflow_with_bridge_status(workflow, context)
    except Exception as exc:  # noqa: BLE001 - bridge status must show local workflow failures.
        write_bridge_status(
            context.output_dir,
            {
                "run_id": context.run_id,
                "run_dir": display_ref(context.output_dir),
                "workflow": display_ref(context.workflow_path or context.workflow_name),
                "status": "failed",
                "steps": steps_from_context(workflow, context),
                "current_step": None,
                "event": "bridge_error",
                "errors": [str(exc)],
            },
        )
    finally:
        _RUN_THREADS.pop(run_key, None)


def _run_workflow_with_bridge_status(workflow: Any, context: WorkflowContext) -> Any:
    run = WorkflowRunner(default_node_registry()).run(workflow, context)
    bridge_progress(workflow, run, context, None, "run_finished")
    return run


def _workflow_context(workflow: Any, workflow_path: Path, input_path: Path, output_dir: Path) -> WorkflowContext:
    return WorkflowContext(
        run_id=output_dir.name,
        workflow_name=workflow.name,
        workflow_path=display_ref(workflow_path),
        mode=workflow.mode,
        quality_profile=workflow.quality_profile,
        output_dir=output_dir,
        inputs=load_workflow_inputs(input_path),
    )


def _plan_next_actions(plan: dict[str, Any]) -> list[str]:
    if plan.get("status") == "draft":
        return ["review_plan", "adjust_inputs", "run_workflow"]
    return ["fix_workflow_or_input"]
