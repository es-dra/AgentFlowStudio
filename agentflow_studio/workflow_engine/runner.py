from __future__ import annotations

from datetime import datetime
from typing import Any

from agentflow_studio.package_sop import write_package_report
from agentflow_studio.schemas import StepResult, WorkflowRun
from agentflow_studio.utils import write_json
from agentflow_studio.workflow_run_artifacts import write_run_manifest, write_trace
from agentflow_studio.workflow_engine.context import WorkflowContext
from agentflow_studio.workflow_engine.definitions import WorkflowDefinition, WorkflowStepDefinition
from agentflow_studio.workflow_engine.registry import NodeRegistry


class WorkflowRunner:
    def __init__(self, registry: NodeRegistry) -> None:
        self.registry = registry

    def run(self, definition: WorkflowDefinition, context: WorkflowContext) -> WorkflowRun:
        run = WorkflowRun(
            run_id=context.run_id,
            workflow_name=definition.name,
            status="running",
            input=context.inputs,
        )

        for step in definition.steps:
            result = self._run_step(step, context)
            context.step_results.append(result)
            run.steps.append(result)
            if result.status == "failed":
                run.status = "failed"
                run.error = result.error
                run.ended_at = datetime.now().astimezone()
                self._write_run_artifacts(definition, run, context)
                return run

        run.status = "success"
        run.outputs = dict(context.artifacts)
        run.ended_at = datetime.now().astimezone()
        self._write_run_artifacts(definition, run, context)
        return run

    def _run_step(self, step: WorkflowStepDefinition, context: WorkflowContext) -> StepResult:
        started_at = datetime.now().astimezone()
        try:
            handler = self.registry.get(step.type)
            artifacts = handler(step, context)
        except Exception as exc:  # noqa: BLE001 - workflow manifest needs failure capture.
            return StepResult(
                step_id=step.id,
                step_type=step.type,
                status="failed",
                error=str(exc),
                started_at=started_at,
                ended_at=datetime.now().astimezone(),
            )
        return StepResult(
            step_id=step.id,
            step_type=step.type,
            status="success",
            output_ref=artifacts[0] if artifacts else None,
            artifacts=artifacts,
            started_at=started_at,
            ended_at=datetime.now().astimezone(),
        )

    def _write_manifest(self, run: WorkflowRun, context: WorkflowContext) -> None:
        manifest: dict[str, Any] = {
            "run_id": run.run_id,
            "workflow_name": run.workflow_name,
            "status": run.status,
            "inputs": context.inputs,
            "artifacts": context.artifacts,
            "steps": [step.model_dump(mode="json") for step in run.steps],
            "error": run.error,
        }
        write_json(context.output_path("manifest.json"), manifest)

    def _write_run_artifacts(
        self,
        definition: WorkflowDefinition,
        run: WorkflowRun,
        context: WorkflowContext,
    ) -> None:
        self._write_manifest(run, context)
        write_trace(definition, run, context)
        write_run_manifest(run, context)
        report_ref = context.artifacts.get("package_report")
        if report_ref:
            write_package_report(context.output_dir, report_ref)
