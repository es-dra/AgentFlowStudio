from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from narratocut.schemas import StepResult, WorkflowRun
from narratocut.utils import write_json

if TYPE_CHECKING:
    from narratocut.workflow_engine.context import WorkflowContext
    from narratocut.workflow_engine.definitions import WorkflowDefinition, WorkflowStepDefinition


def write_trace(
    definition: WorkflowDefinition,
    run: WorkflowRun,
    context: WorkflowContext,
) -> dict[str, Any]:
    trace = build_trace(definition, run, context)
    write_json(context.output_path("trace.json"), trace)
    return trace


def build_trace(
    definition: WorkflowDefinition,
    run: WorkflowRun,
    context: WorkflowContext,
) -> dict[str, Any]:
    step_definitions = {step.id: step for step in definition.steps}
    return {
        "workflow": _display_ref(context.workflow_path or run.workflow_name),
        "run_id": run.run_id,
        "steps": [
            _trace_step(result, step_definitions.get(result.step_id), context)
            for result in run.steps
        ],
    }


def _trace_step(
    result: StepResult,
    definition: WorkflowStepDefinition | None,
    context: WorkflowContext,
) -> dict[str, Any]:
    return {
        "step_id": result.step_id,
        "status": result.status,
        "started_at": _format_datetime(result.started_at),
        "ended_at": _format_datetime(result.ended_at),
        "duration_ms": _duration_ms(result.started_at, result.ended_at),
        "inputs": _trace_inputs(definition, context),
        "outputs": result.artifacts,
        "warnings": [],
        "errors": [result.error] if result.error else [],
    }


def _trace_inputs(
    definition: WorkflowStepDefinition | None,
    context: WorkflowContext,
) -> list[str]:
    if definition is None:
        return []
    return [_resolve_trace_ref(value, context) for value in definition.inputs.values()]


def _resolve_trace_ref(value: object, context: WorkflowContext) -> str:
    ref = str(value)
    if ref in context.inputs:
        return _display_ref(str(context.inputs[ref]))
    if ref in context.artifacts:
        return _display_ref(context.artifacts[ref])
    return _display_ref(ref)


def _duration_ms(started_at: datetime | None, ended_at: datetime | None) -> int:
    if started_at is None or ended_at is None:
        return 0
    return max(0, round((ended_at - started_at).total_seconds() * 1000))


def _format_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _display_ref(path: str) -> str:
    return path.replace("\\", "/")
