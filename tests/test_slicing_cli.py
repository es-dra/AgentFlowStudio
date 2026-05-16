from __future__ import annotations

import json

from typer.testing import CliRunner

from apps.cli.main import app
from narratocut.roi_sop import analyze_hooks_from_text, generate_scripts_from_hooks
from narratocut.utils import write_json


def test_generate_clip_plans_and_mock_slice_commands(tmp_path) -> None:
    hooks = analyze_hooks_from_text("女主被误会后当众反转，揭露真正身份。")
    scripts = generate_scripts_from_hooks(hooks)
    scripts_path = tmp_path / "scripts.json"
    clip_plans_path = tmp_path / "clip_plans.json"
    output_dir = tmp_path / "slices"
    write_json(scripts_path, scripts)

    runner = CliRunner()

    generate_result = runner.invoke(
        app,
        [
            "generate-clip-plans",
            "--scripts",
            str(scripts_path),
            "--output",
            str(clip_plans_path),
        ],
    )

    assert generate_result.exit_code == 0, generate_result.output
    assert clip_plans_path.is_file()
    clip_plans = json.loads(clip_plans_path.read_text(encoding="utf-8"))
    assert len(clip_plans) == len(scripts)

    slice_result = runner.invoke(
        app,
        [
            "mock-slice",
            "--clip-plans",
            str(clip_plans_path),
            "--output",
            str(output_dir),
        ],
    )

    assert slice_result.exit_code == 0, slice_result.output
    assert (output_dir / "slice_manifest.json").is_file()
    manifest = json.loads((output_dir / "slice_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "success"
    assert manifest["clip_count"] == len(scripts)
