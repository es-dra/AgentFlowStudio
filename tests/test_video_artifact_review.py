from __future__ import annotations

from pathlib import Path
from typing import Any

from apps.cli.workflow_commands import run_workflow_from_cli
from agentflow_studio.harness.inspection import inspect_run
from agentflow_studio.harness.quality_checks import build_quality_report
from agentflow_studio.harness.reviewer import review_run
from agentflow_studio.utils import write_json
from tests.video_artifact_fixtures import (
    base_clip_plan,
    base_highlight_plan,
    base_transcript,
    write_video_highlight_input,
    write_video_run,
    write_video_transcript_input,
)


VIDEO_TO_TRANSCRIPT_WORKFLOW = Path("workflows/video_to_transcript.yaml")
VIDEO_TO_HIGHLIGHT_CLIP_PLAN_WORKFLOW = Path("workflows/video_to_highlight_clip_plan.yaml")


def test_video_to_transcript_run_inspect_and_review_video_artifacts(tmp_path) -> None:
    input_path = write_video_transcript_input(tmp_path)
    run_dir = tmp_path / "video_transcript_run"

    status, _ = run_workflow_from_cli(
        workflow_path=VIDEO_TO_TRANSCRIPT_WORKFLOW,
        input_path=input_path,
        output_dir=run_dir,
    )
    assert status == "success"

    inspection = inspect_run(run_dir)
    review = review_run(run_dir)

    assert inspection["status"] == "pass"
    artifact_statuses = {item["path"]: item["status"] for item in inspection["artifacts"]}
    assert artifact_statuses["audio_manifest.json"] == "found"
    assert artifact_statuses["audio/audio.wav"] == "found"
    assert artifact_statuses["transcript.json"] == "found"
    assert "highlight_plan.json" not in artifact_statuses
    assert "clip_plan.json" not in artifact_statuses

    summary = inspection["quality_report"]["summary"]
    assert summary["quality_profile"] == "mock_asr_transcript"
    assert summary["audio_manifest"]["status"] == "mocked"
    assert summary["audio_manifest"]["extraction_mode"] == "mock"
    assert summary["audio_manifest"]["executed"] is False
    assert summary["transcript"]["provider"] == "mock"
    assert summary["transcript"]["segment_count"] == 3
    assert summary["transcript"]["segments_monotonic"] is True

    assert review["status"] == "passed"
    assert "video_artifacts" in _section_names(review)
    assert "highlight_artifacts" not in _section_names(review)
    checks = _checks_by_id(review, "video_artifacts")
    assert checks["audio_manifest_status_valid"]["status"] == "passed"
    assert checks["transcript_schema_valid"]["status"] == "passed"
    assert checks["mock_asr_provider_marked"]["status"] == "passed"


def test_video_to_highlight_clip_plan_run_reviews_video_and_highlight_artifacts(tmp_path) -> None:
    input_path = write_video_highlight_input(tmp_path)
    run_dir = tmp_path / "video_highlight_run"

    status, _ = run_workflow_from_cli(
        workflow_path=VIDEO_TO_HIGHLIGHT_CLIP_PLAN_WORKFLOW,
        input_path=input_path,
        output_dir=run_dir,
    )
    assert status == "success"

    inspection = inspect_run(run_dir)
    review = review_run(run_dir)

    assert inspection["status"] == "pass"
    artifact_statuses = {item["path"]: item["status"] for item in inspection["artifacts"]}
    assert artifact_statuses["transcript.json"] == "found"
    assert artifact_statuses["highlight_plan.json"] == "found"
    assert artifact_statuses["clip_plan.json"] == "found"

    summary = inspection["quality_report"]["summary"]
    assert summary["quality_profile"] == "video_highlight_clip_plan"
    assert summary["transcript"]["segment_count"] == 3
    assert summary["highlight_plan"]["input_mode"] == "timestamped_transcript"
    assert summary["clip_plan"]["segment_count"] == summary["highlight_plan"]["highlight_count"]

    assert review["status"] == "passed"
    assert "video_artifacts" in _section_names(review)
    assert "highlight_artifacts" in _section_names(review)
    video_checks = _checks_by_id(review, "video_artifacts")
    assert video_checks["highlight_source_segments_exist_in_transcript"]["status"] == "passed"
    assert video_checks["clip_source_segments_exist_in_transcript"]["status"] == "passed"
    highlight_checks = _checks_by_id(review, "highlight_artifacts")
    assert highlight_checks["clip_order_matches_highlights"]["status"] == "passed"


def test_real_asr_transcript_profile_reviews_provider_and_secret_safety(tmp_path) -> None:
    run_dir = write_video_run(
        tmp_path / "real_asr_run",
        quality_profile="real_asr_transcript",
        transcript=base_transcript(provider="openai_compatible"),
    )
    write_json(run_dir / "quality_report.json", build_quality_report(run_dir))

    inspection = inspect_run(run_dir)
    review = review_run(run_dir)

    assert inspection["status"] == "pass"
    checks = _checks_by_id(review, "video_artifacts")
    assert checks["real_asr_provider_marked"]["status"] == "passed"
    assert checks["api_secret_values_not_recorded"]["status"] == "passed"


def test_video_artifact_review_fails_invalid_transcript_timestamps(tmp_path) -> None:
    transcript = base_transcript(provider="mock")
    transcript["segments"][0]["end_time"] = 0.0
    run_dir = write_video_run(
        tmp_path / "bad_transcript_run",
        quality_profile="mock_asr_transcript",
        transcript=transcript,
    )
    write_json(run_dir / "quality_report.json", build_quality_report(run_dir))

    review = review_run(run_dir)

    assert review["status"] == "failed"
    checks = _checks_by_id(review, "video_artifacts")
    assert checks["transcript_schema_valid"]["status"] == "failed"
    assert checks["transcript_segment_time_ranges_valid"]["status"] == "failed"


def test_video_artifact_review_fails_highlight_source_segment_mismatch(tmp_path) -> None:
    run_dir = write_video_run(
        tmp_path / "bad_source_segment_run",
        quality_profile="video_highlight_clip_plan",
        transcript=base_transcript(provider="mock"),
        highlight_plan=base_highlight_plan(source_segment_ids=["seg_missing"]),
        clip_plan=base_clip_plan(source_segment_ids=["seg_001"]),
    )
    write_json(run_dir / "quality_report.json", build_quality_report(run_dir))

    review = review_run(run_dir)

    assert review["status"] == "failed"
    checks = _checks_by_id(review, "video_artifacts")
    assert checks["highlight_source_segments_exist_in_transcript"]["status"] == "failed"


def test_video_artifact_review_fails_when_secret_like_value_is_recorded(tmp_path) -> None:
    run_dir = write_video_run(
        tmp_path / "secret_run",
        quality_profile="real_asr_transcript",
        transcript=base_transcript(provider="openai_compatible"),
    )
    write_json(
        run_dir / "trace.json",
        {
            "steps": [
                {
                    "step_id": "transcribe_audio_openai_compatible",
                    "status": "success",
                    "inputs": ["sk-test-secret-value"],
                }
            ]
        },
    )
    write_json(run_dir / "quality_report.json", build_quality_report(run_dir))

    review = review_run(run_dir)

    assert review["status"] == "failed"
    checks = _checks_by_id(review, "video_artifacts")
    assert checks["api_secret_values_not_recorded"]["status"] == "failed"


def _section_names(report: dict[str, Any]) -> set[str]:
    return {section["name"] for section in report["sections"]}


def _checks_by_id(report: dict[str, Any], section_name: str) -> dict[str, dict[str, Any]]:
    section = next(section for section in report["sections"] if section["name"] == section_name)
    return {check["id"]: check for check in section["checks"]}
