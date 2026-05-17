from __future__ import annotations

from narratocut.schemas import ClipPlan, ClipSegment, ROISettings, VideoMetadata
from narratocut.slicing_sop.clip_validation import validate_clip_plan


def test_validate_clip_plan_returns_warning_for_roi_duration_without_blocking() -> None:
    report = validate_clip_plan(
        _clip_plan(start=0, end=35),
        _roi(max_duration=30),
        _metadata(duration=60),
        ffmpeg_available=True,
    )

    assert report.status == "passed_with_warnings"
    assert report.hard_errors == []
    assert any(check.status == "warning" and check.name == "roi_max_duration" for check in report.checks)


def test_validate_clip_plan_fails_for_segment_outside_video_duration() -> None:
    report = validate_clip_plan(
        _clip_plan(start=50, end=70),
        _roi(max_duration=30),
        _metadata(duration=60),
        ffmpeg_available=True,
    )

    assert report.status == "failed"
    assert any(error.code == "segment_exceeds_video_duration" for error in report.hard_errors)


def test_validate_clip_plan_fails_for_path_traversal_output_name() -> None:
    plan = _clip_plan(start=0, end=10)
    plan.output_name = "../bad.mp4"

    report = validate_clip_plan(
        plan,
        _roi(max_duration=30),
        _metadata(duration=60),
        ffmpeg_available=True,
    )

    assert report.status == "failed"
    assert any(error.code == "unsafe_output_name" for error in report.hard_errors)


def test_validate_clip_plan_fails_when_ffmpeg_is_unavailable() -> None:
    report = validate_clip_plan(
        _clip_plan(start=0, end=10),
        _roi(max_duration=30),
        _metadata(duration=60),
        ffmpeg_available=False,
    )

    assert report.status == "failed"
    assert any(error.code == "ffmpeg_unavailable" for error in report.hard_errors)


def _roi(max_duration: float) -> ROISettings:
    return ROISettings(
        target_platform="douyin",
        target_audience="college students",
        content_goal="increase_completion_rate",
        min_clip_duration=8,
        max_clip_duration=max_duration,
        target_clip_count=1,
        min_clip_count=1,
        max_clip_count=3,
        risk_tolerance="low",
        priority=["hook_strength"],
    )


def _metadata(duration: float) -> VideoMetadata:
    return VideoMetadata(
        file_path="input.mp4",
        duration_sec=duration,
        width=1920,
        height=1080,
        codec="h264",
        probe_status="succeeded",
    )


def _clip_plan(start: float, end: float) -> ClipPlan:
    return ClipPlan(
        clip_plan_id="clip_plan_demo",
        project_id="project_demo",
        hook_id="hook_demo",
        title="Demo",
        cover_text="Demo",
        output_name="clip_demo.mp4",
        segments=[
            ClipSegment(
                segment_id="seg_001",
                source_video="input.mp4",
                start_sec=start,
                end_sec=end,
            )
        ],
    )
