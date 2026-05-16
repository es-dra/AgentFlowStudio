from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from narratocut.workflow_engine.definitions import WorkflowDefinition


def load_workflow(path: str | Path) -> WorkflowDefinition:
    workflow_path = Path(path)
    if not workflow_path.is_file():
        raise FileNotFoundError(f"Workflow file not found: {workflow_path}")
    try:
        payload: Any = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Workflow YAML is invalid: {workflow_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Workflow YAML must contain a mapping: {workflow_path}")
    try:
        return WorkflowDefinition.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Workflow definition is invalid: {workflow_path}: {exc}") from exc
