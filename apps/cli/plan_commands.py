from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow_studio.workflow_engine import draft_workflow_plan, write_workflow_plan


def write_draft_plan_from_cli(
    workflow_path: Path,
    input_path: Path,
    output_path: Path,
    tool_catalog_path: Path,
) -> tuple[dict[str, Any], Path]:
    plan = draft_workflow_plan(
        workflow_path=workflow_path,
        input_path=input_path,
        tool_catalog_path=tool_catalog_path,
    )
    plan_path = write_workflow_plan(
        output_path=output_path,
        workflow_path=workflow_path,
        input_path=input_path,
        tool_catalog_path=tool_catalog_path,
        plan=plan,
    )
    return plan, plan_path
