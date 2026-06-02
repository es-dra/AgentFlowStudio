from __future__ import annotations

import pytest

from agentflow_studio.highlight_sop import generate_clip_plan_from_highlights
from agentflow_studio.schemas import HighlightPlan, HighlightSegment, ROISettings, VideoMetadata
from agentflow_studio.slicing_sop import validate_clip_plan


def test_generate_clip_plan_from_ranked_timestamped_highlights_preserves_order() -> None:
    plan = _timestamped_plan(
        [
            _highlight("hl_hook", "hook", start_time=8.6, end_time=13.8, final_score=0.94),
            _highlight("hl_insight", "insight", start_time=0.0, end_time=4.2, final_score=0.88),
        ]
    )

    clip_plan = generate_clip_plan_from_highlights(
        plan,
        source_video="data/raw/demo_real_video/input.mp4",
        project_id="demo_project",
    )

    assert clip_plan.clip_plan_id == "clip_plan_highlight_plan_test"
    assert clip_plan.project_id == "demo_project"
    assert clip_plan.hook_id == "hl_hook"
    assert clip_plan.script_id is None
    assert clip_plan.title == "hook title"
    assert clip_plan.cover_text == "hook text"
    assert clip_plan.duration_sec == pytest.approx(9.4)
    assert clip_plan.output_name == "clip_plan_highlight_plan_test.mp4"
    assert [segment.start_sec for segment in clip_plan.segments] == [8.6, 0.0]
    assert [segment.end_sec for segment in clip_plan.segments] == [13.8, 4.2]
    assert [segment.segment_id for segment in clip_plan.segments] == [
        "clip_plan_highlight_plan_test_seg_001",
        "clip_plan_highlight_plan_test_seg_002",
    ]
    assert clip_plan.segments[0].source_video == "data/raw/demo_real_video/input.mp4"
    assert clip_plan.segments[0].metadata["highlight_id"] == "hl_hook"
    assert clip_plan.segments[0].metadata["ranking_factors"]["final_score"] == 0.94
    assert clip_plan.segments[0].metadata["candidate_id"] == "cand_hl_hook"
    assert clip_plan.segments[0].metadata["scorer"] == "deterministic_viral_scorer_v0"
    assert clip_plan.metadata["source"] == "phase10_highlight_clip_plan_generator"
    assert clip_plan.metadata["highlight_plan_id"] == "highlight_plan_test"
    assert clip_plan.metadata["clip_plan_status"] == "generated"


def test_generate_clip_plan_rejects_script_only_highlight_plan() -> None:
    plan = HighlightPlan(
        plan_id="highlight_plan_script",
        input_mode="script_only",
        source_id="demo_script",
        highlights=[
            _highlight(
                "hl_hook",
                "hook",
                source_type="script",
                start_time=None,
                end_time=None,
            )
        ],
    )

    with pytest.raises(ValueError, match="script_only"):
        generate_clip_plan_from_highlights(plan, source_video="input.mp4")


def test_generate_clip_plan_requires_source_video() -> None:
    plan = _timestamped_plan([_highlight("hl_hook", "hook", start_time=0.0, end_time=4.2)])

    with pytest.raises(ValueError, match="source_video"):
        generate_clip_plan_from_highlights(plan, source_video="  ")


def test_generate_clip_plan_can_limit_ranked_highlights() -> None:
    plan = _timestamped_plan(
        [
            _highlight("hl_hook", "hook", start_time=0.0, end_time=4.2),
            _highlight("hl_conflict", "conflict", start_time=4.2, end_time=8.6),
        ]
    )

    clip_plan = generate_clip_plan_from_highlights(plan, source_video="input.mp4", max_clips=1)

    assert len(clip_plan.segments) == 1
    assert clip_plan.segments[0].metadata["highlight_id"] == "hl_hook"
    assert clip_plan.duration_sec == pytest.approx(4.2)


def test_generate_clip_plan_rejects_invalid_max_clips() -> None:
    plan = _timestamped_plan([_highlight("hl_hook", "hook", start_time=0.0, end_time=4.2)])

    with pytest.raises(ValueError, match="max_clips"):
        generate_clip_plan_from_highlights(plan, source_video="input.mp4", max_clips=0)


def test_generated_clip_plan_can_pass_phase9_validation() -> None:
    plan = _timestamped_plan(
        [
            _highlight("hl_hook", "hook", start_time=0.0, end_time=4.2),
            _highlight("hl_insight", "insight", start_time=4.2, end_time=8.6),
        ]
    )
    clip_plan = generate_clip_plan_from_highlights(plan, source_video="input.mp4")

    report = validate_clip_plan(
        clip_plan,
        ROISettings(
            target_platform="douyin",
            target_audience="product builders",
            content_goal="increase_completion_rate",
            min_clip_duration=1,
            max_clip_duration=10,
        ),
        VideoMetadata(
            file_path="input.mp4",
            duration_sec=30,
            width=1080,
            height=1920,
            codec="h264",
            fps=30,
            bitrate=1000,
            probe_status="succeeded",
        ),
        ffmpeg_available=True,
    )

    assert report.status == "passed"


def _timestamped_plan(highlights: list[HighlightSegment]) -> HighlightPlan:
    return HighlightPlan(
        plan_id="highlight_plan_test",
        input_mode="timestamped_transcript",
        source_id="demo_transcript",
        highlights=highlights,
        metadata={"ranker": "roi_ranker_v0"},
    )


def _highlight(
    highlight_id: str,
    highlight_type: str,
    *,
    start_time: float | None,
    end_time: float | None,
    final_score: float = 0.8,
    source_type: str = "transcript",
) -> HighlightSegment:
    metadata = {
        "candidate_id": f"cand_{highlight_id}",
        "scorer": "deterministic_viral_scorer_v0",
        "ranking_factors": {"final_score": final_score},
    }
    return HighlightSegment(
        highlight_id=highlight_id,
        source_type=source_type,
        highlight_type=highlight_type,
        title=f"{highlight_type} title",
        text=f"{highlight_type} text",
        reason=f"{highlight_type} reason",
        score=0.8,
        confidence=0.75,
        roi_tags=[highlight_type],
        source_segment_ids=[f"seg_{highlight_id}"],
        start_time=start_time,
        end_time=end_time,
        suggested_duration=(end_time - start_time) if start_time is not None and end_time is not None else None,
        metadata=metadata,
    )
