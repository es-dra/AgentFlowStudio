from __future__ import annotations

from narratocut.harness.reviewer import review_run
from narratocut.utils import write_json


def test_reviewer_adds_recommendation_for_unavailable_ffmpeg(tmp_path) -> None:
    run_dir = tmp_path / "real_run"
    run_dir.mkdir()
    write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": "real_run",
            "workflow": "workflows/real_video_roi_to_clips.yaml",
            "workflow_mode": "real_video",
            "quality_profile": "real_video",
            "artifacts": {
                "video_metadata": "video_metadata.json",
                "clip_plan_validation": "clip_plan_validation.json",
                "real_slice_manifest": "real_slice_manifest.json",
            },
        },
    )
    write_json(run_dir / "trace.json", {"steps": [{"step_id": "real_slice_video"}]})
    write_json(
        run_dir / "quality_report.json",
        {
            "status": "fail",
            "checks": [{"name": "real_slice_manifest_status", "status": "fail"}],
            "errors": ["ffmpeg_unavailable"],
            "warnings": [],
        },
    )
    write_json(run_dir / "video_metadata.json", {"probe_status": "failed"})
    write_json(run_dir / "clip_plan_validation.json", {"status": "failed"})
    write_json(run_dir / "real_slice_manifest.json", {"status": "failed", "reason": "ffmpeg_unavailable"})

    report = review_run(run_dir)

    assert report["status"] == "failed"
    assert any("NCUT_FFMPEG_PATH" in item for item in report["recommendations"])


def test_reviewer_preserves_real_video_quality_warnings(tmp_path) -> None:
    run_dir = tmp_path / "real_run"
    run_dir.mkdir()
    write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": "real_run",
            "workflow": "workflows/real_video_roi_to_clips.yaml",
            "workflow_mode": "real_video",
            "quality_profile": "real_video",
            "artifacts": {
                "video_metadata": "video_metadata.json",
                "clip_plan_validation": "clip_plan_validation.json",
                "real_slice_manifest": "real_slice_manifest.json",
            },
        },
    )
    write_json(run_dir / "trace.json", {"steps": [{"step_id": "real_slice_video"}]})
    write_json(
        run_dir / "quality_report.json",
        {
            "status": "pass",
            "checks": [{"name": "clip_plan_validation_status", "status": "warning"}],
            "errors": [],
            "warnings": ["clip_duration_exceeds_roi_max"],
        },
    )
    write_json(run_dir / "video_metadata.json", {"probe_status": "succeeded"})
    write_json(run_dir / "clip_plan_validation.json", {"status": "passed_with_warnings"})
    write_json(run_dir / "real_slice_manifest.json", {"status": "succeeded", "clips": []})

    report = review_run(run_dir)

    assert report["status"] == "warning"
    assert report["summary"]["warnings"] == 1
    quality_check = next(
        check
        for section in report["sections"]
        for check in section["checks"]
        if check["id"] == "quality_report_passed"
    )
    assert quality_check["details"]["warnings"] == 2
