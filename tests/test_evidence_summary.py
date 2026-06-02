from __future__ import annotations

from pathlib import Path

from agentflow.harness.evidence_summary import build_evidence_summary
from agentflow_studio.harness.quality_checks import build_quality_report
from agentflow_studio.harness.reviewer import review_run
from agentflow_studio.utils import write_json


def test_evidence_summary_normalizes_statuses_and_boundary() -> None:
    summary = build_evidence_summary(
        surface="unit_test_surface",
        source_status="pass",
        checks=[
            {"name": "ok", "status": "pass"},
            {"name": "soft_risk", "status": "warn"},
            {"name": "broken", "status": "fail"},
        ],
        artifact_refs=["quality_report.json", Path("reports\\review_report.json"), "quality_report.json"],
    )

    assert summary["artifact_type"] == "agentflow_evidence_summary"
    assert summary["status"] == "failed"
    assert summary["counts"] == {"total": 3, "passed": 1, "failed": 1, "warnings": 1}
    assert summary["artifact_refs"] == ["quality_report.json", "reports/review_report.json"]
    assert summary["decision_boundary"]["machine_verification"] == "reported"
    assert summary["decision_boundary"]["human_acceptance"] == "not_reviewed"
    assert summary["decision_boundary"]["business_validation"] == "not_validated"
    assert summary["decision_boundary"]["memory_promotion"] == "not_decided"


def test_quality_report_maps_to_evidence_summary(tmp_path) -> None:
    run_dir = _write_complete_run(tmp_path / "quality_run")

    report = build_quality_report(run_dir)

    assert report["status"] == "pass"
    assert report["evidence_summary"]["surface"] == "quality_report"
    assert report["evidence_summary"]["status"] == "passed"
    assert report["evidence_summary"]["artifact_refs"] == ["quality_report.json"]
    assert report["evidence_summary"]["counts"]["failed"] == 0
    assert report["evidence_summary"]["decision_boundary"]["human_acceptance"] == "not_reviewed"


def test_review_report_maps_warning_to_evidence_summary(tmp_path) -> None:
    run_dir = _write_complete_run(tmp_path / "review_run")
    quality_report = build_quality_report(run_dir)
    quality_report["warnings"] = ["manual_review_recommended"]
    quality_report["checks"].append({"name": "manual_review_recommended", "status": "warning"})
    write_json(run_dir / "quality_report.json", quality_report)

    report = review_run(run_dir)

    assert report["status"] == "warning"
    assert report["evidence_summary"]["surface"] == "review_report"
    assert report["evidence_summary"]["status"] == "warning"
    assert report["evidence_summary"]["artifact_refs"] == [
        "review_report.json",
        "run_manifest.json",
        "trace.json",
        "quality_report.json",
    ]
    assert report["evidence_summary"]["counts"]["warnings"] >= 1
    assert report["evidence_summary"]["decision_boundary"]["business_validation"] == "not_validated"


def _write_complete_run(run_dir: Path) -> Path:
    clips_dir = run_dir / "clips"
    clips_dir.mkdir(parents=True)
    write_json(run_dir / "hooks.json", [{"id": "hook_1"}])
    write_json(run_dir / "scripts.json", [{"id": "script_1"}])
    write_json(run_dir / "clip_plans.json", [{"id": "clip_plan_1"}])
    write_json(run_dir / "manifest.json", {"run_id": run_dir.name, "status": "success"})
    write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": run_dir.name,
            "workflow": "workflows/mock_text_to_slices.yaml",
            "artifacts": {
                "hooks": "hooks.json",
                "scripts": "scripts.json",
                "clip_plans": "clip_plans.json",
                "slice_manifest": "slice_manifest.json",
                "manifest": "manifest.json",
                "clips_dir": "clips/",
            },
        },
    )
    write_json(run_dir / "trace.json", {"steps": [{"step_id": "mock", "status": "success"}]})
    write_json(run_dir / "slice_manifest.json", {"clip_count": 1, "items": []})
    (clips_dir / "clip_plan_1.txt").write_text("mock clip", encoding="utf-8")
    return run_dir
