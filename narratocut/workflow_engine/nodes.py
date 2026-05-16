from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from narratocut.roi_sop import analyze_hooks_from_text, generate_scripts_from_hooks
from narratocut.schemas import ClipPlan, Hook, ShortVideoScript
from narratocut.slicing_sop import generate_clip_plans_from_scripts, mock_slice_clip_plans
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


def generate_clip_plans_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    scripts_ref = _require_input(step, "scripts")
    scripts_path = Path(str(context.resolve_input(str(scripts_ref))))
    scripts = _load_scripts(scripts_path)
    clip_plans = generate_clip_plans_from_scripts(scripts)

    output_ref = _require_output(step, "clip_plans")
    write_json(context.output_path(output_ref), clip_plans)
    context.artifacts["clip_plans"] = output_ref
    return [output_ref]


def mock_slice_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    clip_plans_ref = _require_input(step, "clip_plans")
    clip_plans_path = Path(str(context.resolve_input(str(clip_plans_ref))))
    clip_plans = _load_clip_plans(clip_plans_path)

    output_ref = _require_output(step, "slice_manifest")
    mock_slice_clip_plans(clip_plans, context.output_dir)
    context.artifacts["slice_manifest"] = output_ref
    context.artifacts["clips"] = "clips"
    return [output_ref, "clips"]


def default_node_registry() -> NodeRegistry:
    registry = NodeRegistry()
    registry.register("analyze_hooks", analyze_hooks_node)
    registry.register("generate_scripts", generate_scripts_node)
    registry.register("generate_clip_plans", generate_clip_plans_node)
    registry.register("mock_slice", mock_slice_node)
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


def _load_scripts(path: Path) -> list[ShortVideoScript]:
    payload = _load_json_array(path, "Scripts artifact")
    try:
        return [ShortVideoScript.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise ValueError(f"Scripts artifact failed ShortVideoScript schema validation: {path}") from exc


def _load_clip_plans(path: Path) -> list[ClipPlan]:
    payload = _load_json_array(path, "Clip plans artifact")
    try:
        return [ClipPlan.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise ValueError(f"Clip plans artifact failed ClipPlan schema validation: {path}") from exc


def _load_json_array(path: Path, label: str) -> list[object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(payload, list):
        raise ValueError(f"{label} must contain a JSON array: {path}")
    return payload
