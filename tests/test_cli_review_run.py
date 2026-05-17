from __future__ import annotations

import json

from typer.testing import CliRunner

from apps.cli.main import app


def test_review_run_command_writes_review_report(tmp_path) -> None:
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

    review_result = runner.invoke(app, ["review-run", "--run-dir", str(output_dir)])

    assert review_result.exit_code == 0, review_result.output
    assert "Review report:" in review_result.output
    assert "Status: passed" in review_result.output
    assert "Checks:" in review_result.output
    report_path = output_dir / "review_report.json"
    assert report_path.is_file()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "passed"


def test_review_run_command_returns_failure_for_broken_run(tmp_path) -> None:
    run_dir = tmp_path / "broken_run"
    run_dir.mkdir()
    runner = CliRunner()

    result = runner.invoke(app, ["review-run", "--run-dir", str(run_dir)])

    assert result.exit_code == 1, result.output
    assert "Status: failed" in result.output
    assert (run_dir / "review_report.json").is_file()
