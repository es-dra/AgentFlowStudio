from __future__ import annotations

from pathlib import Path
from typing import Any

from apps.cli.workflow_commands import run_workflow_from_cli
from narratocut.harness.inspection import inspect_run
from narratocut.harness.quality_checks import build_quality_report
from narratocut.harness.reviewer import review_run
from narratocut.utils import write_json


SCRIPT_WORKFLOW = Path("workflows/script_to_highlight_plan.yaml")
TRANSCRIPT_WORKFLOW = Path("workflows/transcript_to_highlight_clip_plan.yaml")
CANDIDATE_WORKFLOW = Path("workflows/transcript_to_candidate_windows.yaml")


def test_script_highlight_run_inspect_and_review_highlight_plan(tmp_path) -> None:
    run_dir = tmp_path / "script_highlight_run"
    status, _ = run_workflow_from_cli(
        workflow_path=SCRIPT_WORKFLOW,
        input_path=Path("examples/demo_highlight/script_input.example.json"),
        output_dir=run_dir,
    )
    assert status == "success"

    inspection = inspect_run(run_dir)
    review = review_run(run_dir)

    assert inspection["status"] == "pass"
    artifact_statuses = {item["path"]: item["status"] for item in inspection["artifacts"]}
    assert artifact_statuses["highlight_plan.json"] == "found"
    assert "clip_plan.json" not in artifact_statuses

    summary = inspection["quality_report"]["summary"]["highlight_plan"]
    assert summary["input_mode"] == "script_only"
    assert summary["highlight_count"] > 0
    assert summary["has_timestamps"] is False
    assert summary["has_ranking_factors"] is True
    assert summary["clip_plan_expected"] is False

    assert review["status"] == "passed"
    checks = _checks_by_id(review, "highlight_artifacts")
    assert checks["script_only_without_timestamps"]["status"] == "passed"
    assert checks["clip_plan_not_generated_for_script"]["status"] == "passed"


def test_transcript_highlight_run_inspect_and_review_clip_plan(tmp_path) -> None:
    run_dir = tmp_path / "transcript_highlight_run"
    status, _ = run_workflow_from_cli(
        workflow_path=TRANSCRIPT_WORKFLOW,
        input_path=Path("examples/demo_highlight/transcript_input.example.json"),
        output_dir=run_dir,
    )
    assert status == "success"

    inspection = inspect_run(run_dir)
    review = review_run(run_dir)

    assert inspection["status"] == "pass"
    artifact_statuses = {item["path"]: item["status"] for item in inspection["artifacts"]}
    assert artifact_statuses["highlight_plan.json"] == "found"
    assert artifact_statuses["clip_plan.json"] == "found"

    highlight_summary = inspection["quality_report"]["summary"]["highlight_plan"]
    clip_summary = inspection["quality_report"]["summary"]["clip_plan"]
    assert highlight_summary["input_mode"] == "timestamped_transcript"
    assert highlight_summary["has_timestamps"] is True
    assert highlight_summary["has_ranking_factors"] is True
    assert clip_summary["segment_count"] == highlight_summary["highlight_count"]
    assert clip_summary["has_highlight_metadata"] is True

    assert review["status"] == "passed"
    checks = _checks_by_id(review, "highlight_artifacts")
    assert checks["timestamped_highlights_have_timestamps"]["status"] == "passed"
    assert checks["clip_segments_have_highlight_metadata"]["status"] == "passed"
    assert checks["clip_order_matches_highlights"]["status"] == "passed"


def test_candidate_windows_run_inspect_and_review_candidate_manifest(tmp_path) -> None:
    run_dir = tmp_path / "candidate_windows_run"
    status, _ = run_workflow_from_cli(
        workflow_path=CANDIDATE_WORKFLOW,
        input_path=Path("examples/demo_highlight/transcript_candidate_windows_input.example.json"),
        output_dir=run_dir,
    )
    assert status == "success"

    inspection = inspect_run(run_dir)
    review = review_run(run_dir)

    assert inspection["status"] == "pass"
    artifact_statuses = {item["path"]: item["status"] for item in inspection["artifacts"]}
    assert artifact_statuses["candidate_windows.json"] == "found"
    assert "hooks.json" not in artifact_statuses
    assert "clips/" not in artifact_statuses

    summary = inspection["quality_report"]["summary"]["candidate_windows"]
    assert summary["candidate_count"] > 0
    assert summary["content_channel"] == "transcript"

    assert review["status"] == "passed"
    checks = _checks_by_id(review, "candidate_windows")
    assert checks["candidate_count_positive"]["status"] == "passed"
    assert checks["candidate_timestamps_valid"]["status"] == "passed"
    assert checks["candidate_duration_bounds"]["status"] == "passed"


def test_highlight_review_fails_script_only_plan_with_timestamps(tmp_path) -> None:
    run_dir = _write_highlight_run(tmp_path / "bad_script", quality_profile="highlight_plan")
    highlight_plan = _base_highlight_plan(input_mode="script_only")
    highlight_plan["highlights"][0]["start_time"] = 0.0
    highlight_plan["highlights"][0]["end_time"] = 4.0
    write_json(run_dir / "highlight_plan.json", highlight_plan)
    write_json(run_dir / "quality_report.json", build_quality_report(run_dir))

    review = review_run(run_dir)

    assert review["status"] == "failed"
    checks = _checks_by_id(review, "highlight_artifacts")
    assert checks["script_only_without_timestamps"]["status"] == "failed"


def test_highlight_review_fails_timestamped_plan_without_timestamps(tmp_path) -> None:
    run_dir = _write_highlight_run(tmp_path / "bad_transcript", quality_profile="highlight_clip_plan")
    highlight_plan = _base_highlight_plan(input_mode="timestamped_transcript")
    highlight_plan["highlights"][0]["start_time"] = None
    highlight_plan["highlights"][0]["end_time"] = None
    write_json(run_dir / "highlight_plan.json", highlight_plan)
    write_json(run_dir / "clip_plan.json", _base_clip_plan())
    write_json(run_dir / "quality_report.json", build_quality_report(run_dir))

    review = review_run(run_dir)

    assert review["status"] == "failed"
    checks = _checks_by_id(review, "highlight_artifacts")
    assert checks["timestamped_highlights_have_timestamps"]["status"] == "failed"


def test_highlight_review_fails_invalid_ranking_factors(tmp_path) -> None:
    run_dir = _write_highlight_run(tmp_path / "bad_ranking", quality_profile="highlight_plan")
    highlight_plan = _base_highlight_plan(input_mode="script_only")
    highlight_plan["highlights"][0]["metadata"]["ranking_factors"]["final_score"] = 1.4
    write_json(run_dir / "highlight_plan.json", highlight_plan)
    write_json(run_dir / "quality_report.json", build_quality_report(run_dir))

    review = review_run(run_dir)

    assert review["status"] == "failed"
    checks = _checks_by_id(review, "highlight_artifacts")
    assert checks["ranking_final_scores_valid"]["status"] == "failed"


def test_candidate_windows_review_fails_invalid_manifest(tmp_path) -> None:
    run_dir = _write_candidate_run(tmp_path / "bad_candidates")
    write_json(
        run_dir / "candidate_windows.json",
        {
            "status": "succeeded",
            "content_channel": "transcript",
            "candidate_count": 1,
            "candidates": [
                {
                    "candidate_id": "cand_001",
                    "start_sec": 5.0,
                    "end_sec": 3.0,
                    "duration_sec": -2.0,
                    "segment_ids": [],
                    "text": "bad",
                }
            ],
        },
    )
    write_json(run_dir / "quality_report.json", build_quality_report(run_dir))

    review = review_run(run_dir)

    assert review["status"] == "failed"
    checks = _checks_by_id(review, "candidate_windows")
    assert checks["candidate_timestamps_valid"]["status"] == "failed"
    assert checks["candidate_segment_ids_present"]["status"] == "failed"


def _write_highlight_run(run_dir: Path, *, quality_profile: str) -> Path:
    run_dir.mkdir(parents=True)
    artifacts = {"highlight_plan": "highlight_plan.json", "manifest": "manifest.json"}
    if quality_profile == "highlight_clip_plan":
        artifacts["clip_plan"] = "clip_plan.json"
    write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": run_dir.name,
            "workflow": "workflows/script_to_highlight_plan.yaml",
            "workflow_mode": "highlight_detection",
            "quality_profile": quality_profile,
            "artifacts": artifacts,
        },
    )
    write_json(run_dir / "trace.json", {"steps": [{"step_id": "detect_highlights", "status": "success"}]})
    write_json(run_dir / "manifest.json", {"status": "success"})
    return run_dir


def _write_candidate_run(run_dir: Path) -> Path:
    run_dir.mkdir(parents=True)
    write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": run_dir.name,
            "workflow": "workflows/transcript_to_candidate_windows.yaml",
            "workflow_mode": "candidate_windows",
            "quality_profile": "candidate_windows",
            "artifacts": {"candidate_windows": "candidate_windows.json"},
        },
    )
    write_json(run_dir / "trace.json", {"steps": [{"step_id": "generate_candidate_windows", "status": "success"}]})
    write_json(run_dir / "manifest.json", {"status": "success"})
    return run_dir


def _base_highlight_plan(*, input_mode: str) -> dict[str, Any]:
    highlight: dict[str, Any] = {
        "highlight_id": "hl_001",
        "source_type": "script" if input_mode == "script_only" else "transcript",
        "highlight_type": "hook",
        "title": "Hook",
        "text": "A useful highlight.",
        "reason": "The segment opens a clear gap.",
        "score": 0.8,
        "confidence": 0.9,
        "roi_tags": ["hook_strength"],
        "source_segment_ids": ["script_para_001" if input_mode == "script_only" else "seg_001"],
        "start_time": None,
        "end_time": None,
        "suggested_duration": 4.0,
        "metadata": {"ranking_factors": {"final_score": 0.88}},
    }
    if input_mode == "timestamped_transcript":
        highlight["start_time"] = 0.0
        highlight["end_time"] = 4.0
    return {
        "plan_id": f"highlight_plan_{input_mode}",
        "input_mode": input_mode,
        "source_id": "source",
        "highlights": [highlight],
        "summary": "test plan",
        "warnings": [],
        "metadata": {},
        "created_at": "2026-05-18T00:00:00Z",
    }


def _base_clip_plan() -> dict[str, Any]:
    return {
        "clip_plan_id": "clip_plan_highlight_plan_timestamped_transcript",
        "project_id": "source",
        "hook_id": "hl_001",
        "script_id": None,
        "duration_sec": 4.0,
        "title": "Hook",
        "cover_text": "A useful highlight.",
        "segments": [
            {
                "segment_id": "clip_plan_seg_001",
                "source_video": "transcript://source",
                "start_sec": 0.0,
                "end_sec": 4.0,
                "text": "A useful highlight.",
                "metadata": {
                    "highlight_id": "hl_001",
                    "ranking_factors": {"final_score": 0.88},
                },
            }
        ],
        "voiceover_text": None,
        "cta_text": None,
        "output_name": "clip_plan.mp4",
        "metadata": {"source": "phase10_highlight_clip_plan_generator"},
        "created_at": "2026-05-18T00:00:00Z",
    }


def _checks_by_id(report: dict[str, Any], section_name: str) -> dict[str, dict[str, Any]]:
    section = next(section for section in report["sections"] if section["name"] == section_name)
    return {check["id"]: check for check in section["checks"]}
