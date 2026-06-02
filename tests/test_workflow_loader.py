from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentflow_studio.workflow_engine import WorkflowDefinition, load_workflow


def test_load_workflow_reads_mock_roi_to_script_yaml() -> None:
    workflow = load_workflow("workflows/mock_roi_to_script.yaml")

    assert workflow.name == "mock_roi_to_script"
    assert workflow.version == 1
    assert [step.id for step in workflow.steps] == ["analyze_hooks", "generate_scripts"]


def test_workflow_definition_rejects_empty_steps() -> None:
    with pytest.raises(ValidationError):
        WorkflowDefinition(name="empty", steps=[])


def test_workflow_definition_rejects_duplicate_step_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate step id"):
        WorkflowDefinition(
            name="duplicate",
            steps=[
                {"id": "same", "type": "analyze_hooks"},
                {"id": "same", "type": "generate_scripts"},
            ],
        )
