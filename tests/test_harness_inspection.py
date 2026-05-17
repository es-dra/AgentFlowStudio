from __future__ import annotations

import json

from narratocut.harness.inspection import inspect_run
from narratocut.utils import write_json


def test_inspect_run_writes_quality_report_and_artifact_statuses(tmp_path) -> None:
    run_dir = tmp_path / "run"
    clips_dir = run_dir / "clips"
    clips_dir.mkdir(parents=True)
    write_json(
        run_dir / "run_manifest.json",
        {"run_id": "run", "workflow": "workflows/mock_text_to_slices.yaml"},
    )
    write_json(run_dir / "trace.json", {"steps": []})
    write_json(run_dir / "manifest.json", {"status": "success"})
    write_json(run_dir / "hooks.json", [{"id": "hook_1"}])
    write_json(run_dir / "scripts.json", [{"id": "script_1"}])
    write_json(run_dir / "clip_plans.json", [{"id": "clip_plan_1"}])
    write_json(run_dir / "slice_manifest.json", {"clip_count": 1, "items": []})
    (clips_dir / "clip_plan_1.txt").write_text("mock clip", encoding="utf-8")

    inspection = inspect_run(run_dir)

    assert inspection["run_id"] == "run"
    assert inspection["workflow"] == "workflows/mock_text_to_slices.yaml"
    assert inspection["status"] == "pass"
    assert (run_dir / "quality_report.json").is_file()
    report = json.loads((run_dir / "quality_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "pass"
    artifact_statuses = {item["path"]: item["status"] for item in inspection["artifacts"]}
    assert artifact_statuses["run_manifest.json"] == "found"
    assert artifact_statuses["trace.json"] == "found"
