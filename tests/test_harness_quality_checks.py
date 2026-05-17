from __future__ import annotations

import json

from narratocut.harness.quality_checks import build_quality_report
from narratocut.utils import write_json


def test_build_quality_report_passes_for_complete_mock_run(tmp_path) -> None:
    run_dir = tmp_path / "run"
    clips_dir = run_dir / "clips"
    clips_dir.mkdir(parents=True)
    write_json(run_dir / "hooks.json", [{"id": "hook_1"}])
    write_json(run_dir / "scripts.json", [{"id": "script_1"}])
    write_json(run_dir / "clip_plans.json", [{"id": "clip_plan_1"}])
    write_json(run_dir / "manifest.json", {"status": "success"})
    write_json(run_dir / "run_manifest.json", {"run_id": "run"})
    write_json(run_dir / "trace.json", {"steps": []})
    write_json(
        run_dir / "slice_manifest.json",
        {
            "status": "success",
            "clip_count": 1,
            "items": [{"clip_path": "clips/clip_plan_1.txt"}],
        },
    )
    (clips_dir / "clip_plan_1.txt").write_text("mock clip", encoding="utf-8")

    report = build_quality_report(run_dir)

    assert report["status"] == "pass"
    checks = {check["name"]: check for check in report["checks"]}
    assert checks["hooks_non_empty"]["details"]["count"] == 1
    assert checks["scripts_non_empty"]["details"]["count"] == 1
    assert checks["clip_plans_non_empty"]["details"]["count"] == 1
    assert checks["mock_clips_count_matches_manifest"]["status"] == "pass"


def test_build_quality_report_fails_when_required_artifact_is_missing(tmp_path) -> None:
    report = build_quality_report(tmp_path)

    assert report["status"] == "fail"
    failed = [check for check in report["checks"] if check["status"] == "fail"]
    assert any(check["name"] == "hooks_file_exists" for check in failed)
    assert report["errors"]
