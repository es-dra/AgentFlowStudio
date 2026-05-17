from __future__ import annotations

import json

from typer.testing import CliRunner

from apps.cli.main import app


def test_inspect_run_command_writes_quality_report(tmp_path) -> None:
    output_dir = tmp_path / "workflow_run"
    runner = CliRunner()
    run_result = runner.invoke(
        app,
        [
            "run-workflow",
            "--workflow",
            "workflows/mock_text_to_slices.yaml",
            "--input",
            "examples/demo_text/story.txt",
            "--output",
            str(output_dir),
        ],
    )
    assert run_result.exit_code == 0, run_result.output

    inspect_result = runner.invoke(app, ["inspect-run", "--run-dir", str(output_dir)])

    assert inspect_result.exit_code == 0, inspect_result.output
    assert "Run: workflow_run" in inspect_result.output
    assert "Workflow: workflows/mock_text_to_slices.yaml" in inspect_result.output
    assert "Status: pass" in inspect_result.output
    assert "Quality:" in inspect_result.output
    quality_report_path = output_dir / "quality_report.json"
    assert quality_report_path.is_file()
    report = json.loads(quality_report_path.read_text(encoding="utf-8"))
    assert report["status"] == "pass"
