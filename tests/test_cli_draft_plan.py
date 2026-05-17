from __future__ import annotations

import json

from typer.testing import CliRunner

from apps.cli.main import app


def test_draft_plan_command_writes_workflow_plan(tmp_path) -> None:
    output_path = tmp_path / "workflow_plan.json"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "draft-plan",
            "--workflow",
            "workflows/mock_text_to_slices.yaml",
            "--input",
            "examples/demo_text/story.txt",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Workflow plan:" in result.output
    assert "Status: draft" in result.output
    assert "Steps: 4" in result.output
    assert "Execution: not started" in result.output
    plan = json.loads(output_path.read_text(encoding="utf-8"))
    assert plan["status"] == "draft"
    assert len(plan["steps"]) == 4


def test_draft_plan_command_returns_failure_for_invalid_workflow(tmp_path) -> None:
    workflow_path = tmp_path / "invalid_workflow.yaml"
    workflow_path.write_text("name: broken\nsteps: []\n", encoding="utf-8")
    output_path = tmp_path / "workflow_plan.json"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "draft-plan",
            "--workflow",
            str(workflow_path),
            "--input",
            "examples/demo_text/story.txt",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 1, result.output
    assert "Status: invalid" in result.output
    plan = json.loads(output_path.read_text(encoding="utf-8"))
    assert plan["status"] == "invalid"
