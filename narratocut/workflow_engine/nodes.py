from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from narratocut.roi_sop import analyze_hooks_from_text, generate_scripts_from_hooks
from narratocut.schemas import Hook
from narratocut.utils import write_json
from narratocut.workflow_engine.context import WorkflowContext
from narratocut.workflow_engine.definitions import WorkflowStepDefinition
from narratocut.workflow_engine.registry import NodeRegistry


def analyze_hooks_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    text_file = _require_input(step, "text_file")
    text_path = Path(str(context.resolve_input(str(text_file))))
    input_text = text_path.read_text(encoding="utf-8")
    hooks = analyze_hooks_from_text(input_text)

    output_ref = _require_output(step, "hooks")
    write_json(context.output_path(output_ref), hooks)
    context.artifacts["hooks"] = output_ref
    return [output_ref]


def generate_scripts_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    hooks_ref = _require_input(step, "hooks")
    hooks_path = Path(str(context.resolve_input(str(hooks_ref))))
    hooks = _load_hooks(hooks_path)
    scripts = generate_scripts_from_hooks(hooks)

    output_ref = _require_output(step, "scripts")
    write_json(context.output_path(output_ref), scripts)
    context.artifacts["scripts"] = output_ref
    return [output_ref]


def default_node_registry() -> NodeRegistry:
    registry = NodeRegistry()
    registry.register("analyze_hooks", analyze_hooks_node)
    registry.register("generate_scripts", generate_scripts_node)
    return registry


def _require_input(step: WorkflowStepDefinition, name: str) -> object:
    if name not in step.inputs:
        raise ValueError(f"Step {step.id} missing required input: {name}")
    return step.inputs[name]


def _require_output(step: WorkflowStepDefinition, name: str) -> str:
    if name not in step.outputs:
        raise ValueError(f"Step {step.id} missing required output: {name}")
    return step.outputs[name]


def _load_hooks(path: Path) -> list[Hook]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Hooks artifact is not valid JSON: {path}") from exc
    if not isinstance(payload, list):
        raise ValueError(f"Hooks artifact must contain a JSON array: {path}")
    try:
        return [Hook.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise ValueError(f"Hooks artifact failed Hook schema validation: {path}") from exc
