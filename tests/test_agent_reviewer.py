from __future__ import annotations

import json
from typing import Any

from agentflow_studio.harness.quality_checks import build_quality_report
from agentflow_studio.harness.reviewer import review_run, write_review_report
from agentflow_studio.utils import write_json


def test_review_run_builds_passed_report_for_complete_mock_run(tmp_path) -> None:
    run_dir = _write_complete_run(tmp_path / "demo_run")

    report = review_run(run_dir)

    assert report["schema_version"] == "0.1"
    assert report["run_id"] == "demo_run"
    assert report["status"] == "passed"
    assert report["quality_level"] == "engineering_pass"
    assert report["delivery_status"] == "pass"
    assert report["summary"]["failed"] == 0
    assert report["summary"]["warnings"] == 0
    assert report["summary"]["passed"] == report["summary"]["total_checks"]
    assert [section["name"] for section in report["sections"]] == [
        "run_contract",
        "workflow_outputs",
    ]
    assert report["recommendations"] == []
    assert "\\" not in _json_text(report)


def test_write_review_report_writes_review_report_json(tmp_path) -> None:
    run_dir = _write_complete_run(tmp_path / "demo_run")

    report_path = write_review_report(run_dir)

    assert report_path == run_dir / "review_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["inputs"]["manifest"] == "run_manifest.json"
    assert report["inputs"]["trace"] == "trace.json"
    assert report["inputs"]["quality_report"] == "quality_report.json"


def test_review_run_fails_when_required_contract_files_are_missing(tmp_path) -> None:
    run_dir = tmp_path / "broken_run"
    run_dir.mkdir()

    report = review_run(run_dir)

    assert report["status"] == "failed"
    assert report["quality_level"] == "needs_review"
    assert report["delivery_status"] == "failed"
    failed_ids = _check_ids(report, "failed")
    assert "manifest_exists" in failed_ids
    assert "trace_exists" in failed_ids
    assert "quality_report_exists" in failed_ids


def test_review_run_explains_missing_quality_report_requires_inspect_run(tmp_path) -> None:
    run_dir = _write_complete_run(tmp_path / "demo_run")
    (run_dir / "quality_report.json").unlink()

    report = review_run(run_dir)

    quality_check = next(
        check
        for section in report["sections"]
        for check in section["checks"]
        if check["id"] == "quality_report_passed"
    )
    assert report["status"] == "failed"
    assert quality_check["status"] == "failed"
    assert "inspect-run" in quality_check["message"]
    assert quality_check["details"]["missing_quality_report"] is True


def test_review_run_fails_when_quality_report_has_failed_checks(tmp_path) -> None:
    run_dir = _write_complete_run(tmp_path / "demo_run")
    quality_report = json.loads((run_dir / "quality_report.json").read_text(encoding="utf-8"))
    quality_report["status"] = "fail"
    quality_report["checks"].append({"name": "forced_failure", "status": "fail"})
    write_json(run_dir / "quality_report.json", quality_report)

    report = review_run(run_dir)

    assert report["status"] == "failed"
    failed_ids = _check_ids(report, "failed")
    assert "quality_report_passed" in failed_ids


def _write_complete_run(run_dir) -> Any:
    clips_dir = run_dir / "clips"
    clips_dir.mkdir(parents=True)
    write_json(
        run_dir / "run_manifest.json",
        {
            "project": "AgentFlow Studio",
            "run_id": run_dir.name,
            "workflow": "workflows/mock_text_to_slices.yaml",
            "mode": "mock",
            "status": "success",
            "inputs": {"text": "examples/demo_text/story.txt"},
            "artifacts": {
                "hooks": "hooks.json",
                "scripts": "scripts.json",
                "clip_plans": "clip_plans.json",
                "slice_manifest": "slice_manifest.json",
                "manifest": "manifest.json",
                "clips_dir": "clips/",
            },
            "environment": {
                "ffmpeg_required": False,
                "network_required": False,
            },
        },
    )
    write_json(
        run_dir / "trace.json",
        {
            "workflow": "workflows/mock_text_to_slices.yaml",
            "run_id": run_dir.name,
            "steps": [{"step_id": "analyze_hooks", "status": "success"}],
        },
    )
    write_json(run_dir / "manifest.json", {"run_id": run_dir.name, "status": "success"})
    write_json(run_dir / "hooks.json", [{"id": "hook_1"}])
    write_json(run_dir / "scripts.json", [{"id": "script_1"}])
    write_json(run_dir / "clip_plans.json", [{"id": "clip_plan_1"}])
    write_json(run_dir / "slice_manifest.json", {"clip_count": 1, "items": []})
    (clips_dir / "clip_plan_1.txt").write_text("mock clip", encoding="utf-8")
    write_json(run_dir / "quality_report.json", build_quality_report(run_dir))
    return run_dir


def _check_ids(report: dict[str, Any], status: str) -> set[str]:
    return {
        check["id"]
        for section in report["sections"]
        for check in section["checks"]
        if check["status"] == status
    }


def _json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)
