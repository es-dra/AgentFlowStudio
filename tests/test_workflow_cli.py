from __future__ import annotations

import json

from typer.testing import CliRunner

from apps.cli.main import app


def test_run_workflow_command_writes_manifest_and_artifacts(tmp_path) -> None:
    output_dir = tmp_path / "workflow_run"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "run-workflow",
            "--workflow",
            "workflows/mock_roi_to_script.yaml",
            "--input",
            "examples/demo_text/story.txt",
            "--output",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Workflow success" in result.output
    assert (output_dir / "manifest.json").is_file()
    assert (output_dir / "hooks.json").is_file()
    assert (output_dir / "scripts.json").is_file()

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "success"
