from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from narratocut.utils import write_json
from narratocut.workflow_engine.loader import load_workflow


SCHEMA_VERSION = "0.1"
DEFAULT_TOOL_CATALOG = Path("configs/tool_catalog.yaml")
PLAN_CONSTRAINTS = [
    "draft_only",
    "no_execution",
    "no_ffmpeg",
    "no_file_mutation_except_plan_output",
]
EXPECTED_RUN_CONTRACT_ARTIFACTS = [
    "run_manifest.json",
    "trace.json",
    "quality_report.json",
]


def draft_workflow_plan(
    workflow_path: str | Path,
    input_path: str | Path,
    tool_catalog_path: str | Path | None = DEFAULT_TOOL_CATALOG,
) -> dict[str, Any]:
    workflow_ref = _display_ref(workflow_path)
    input_ref = _display_ref(input_path)
    tool_catalog = _load_tool_catalog(tool_catalog_path)

    try:
        workflow = load_workflow(workflow_path)
    except (FileNotFoundError, ValueError) as exc:
        return _invalid_plan(workflow_ref, input_ref, str(exc))

    steps = [_plan_step(step, tool_catalog) for step in workflow.steps]
    return {
        "schema_version": SCHEMA_VERSION,
        "plan_id": _plan_id(workflow.name),
        "status": "draft",
        "workflow": {
            "path": workflow_ref,
            "name": workflow.name,
        },
        "input": {
            "path": input_ref,
            "type": "file",
        },
        "steps": steps,
        "artifacts": {
            "expected": _expected_artifacts(steps),
        },
        "constraints": list(PLAN_CONSTRAINTS),
        "risks": [],
        "notes": [
            "This is a draft plan only. It does not execute the workflow.",
        ],
        "created_by": "ncut draft-plan",
    }


def write_workflow_plan(
    output_path: str | Path,
    workflow_path: str | Path,
    input_path: str | Path,
    tool_catalog_path: str | Path | None = DEFAULT_TOOL_CATALOG,
    plan: dict[str, Any] | None = None,
) -> Path:
    workflow_plan = plan or draft_workflow_plan(
        workflow_path=workflow_path,
        input_path=input_path,
        tool_catalog_path=tool_catalog_path,
    )
    return write_json(output_path, workflow_plan)


def _invalid_plan(workflow_ref: str, input_ref: str, error: str) -> dict[str, Any]:
    workflow_name = Path(workflow_ref).stem or "unknown"
    return {
        "schema_version": SCHEMA_VERSION,
        "plan_id": _plan_id(workflow_name),
        "status": "invalid",
        "workflow": {
            "path": workflow_ref,
            "name": workflow_name,
        },
        "input": {
            "path": input_ref,
            "type": "file",
        },
        "steps": [],
        "artifacts": {
            "expected": list(EXPECTED_RUN_CONTRACT_ARTIFACTS),
        },
        "constraints": list(PLAN_CONSTRAINTS),
        "risks": [],
        "notes": [
            "This is a draft plan only. It does not execute the workflow.",
        ],
        "errors": [error],
        "created_by": "ncut draft-plan",
    }


def _plan_step(step: Any, tool_catalog: dict[str, dict[str, Any]]) -> dict[str, Any]:
    tool = tool_catalog.get(step.type, {})
    outputs = list(step.outputs.values()) or list(tool.get("output_artifacts", []))
    inputs = list(step.inputs.values()) or list(tool.get("input_artifacts", []))
    return {
        "step_id": step.id,
        "tool": step.type,
        "purpose": str(tool.get("description") or f"Run workflow node {step.type}."),
        "inputs": [_display_ref(value) for value in inputs],
        "expected_outputs": [_display_ref(value) for value in outputs],
        "execution_status": "not_started",
    }


def _expected_artifacts(steps: list[dict[str, Any]]) -> list[str]:
    artifacts = list(EXPECTED_RUN_CONTRACT_ARTIFACTS)
    for step in steps:
        for output in step["expected_outputs"]:
            if output not in artifacts:
                artifacts.append(output)
    return artifacts


def _load_tool_catalog(tool_catalog_path: str | Path | None) -> dict[str, dict[str, Any]]:
    if tool_catalog_path is None:
        return {}

    path = Path(tool_catalog_path)
    if not path.is_file():
        return {}

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return {}
    if not isinstance(payload, dict):
        return {}

    tools = payload.get("tools")
    if not isinstance(tools, list):
        return {}

    catalog: dict[str, dict[str, Any]] = {}
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        node_name = _workflow_node_name(tool)
        if node_name:
            catalog[node_name] = tool
    return catalog


def _workflow_node_name(tool: dict[str, Any]) -> str | None:
    entrypoints = tool.get("entrypoints")
    if isinstance(entrypoints, dict) and entrypoints.get("workflow_node"):
        return str(entrypoints["workflow_node"])
    if tool.get("name"):
        return str(tool["name"])
    return None


def _plan_id(workflow_name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", workflow_name).strip("_").lower()
    return f"plan_{normalized or 'workflow'}"


def _display_ref(value: str | Path) -> str:
    return str(value).replace("\\", "/")
