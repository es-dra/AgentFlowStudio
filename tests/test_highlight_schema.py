from __future__ import annotations

import pytest
from pydantic import ValidationError

from narratocut.schemas import HighlightPlan, HighlightSegment


def test_script_only_highlight_plan_allows_untimed_highlights() -> None:
    highlight = HighlightSegment(
        highlight_id="hl_001",
        source_type="script",
        highlight_type="hook",
        title="努力不一定成功",
        text="很多人以为努力就一定会成功，但真相可能完全相反。",
        reason="This creates a clear expectation gap for the opening.",
        score=0.91,
        confidence=0.86,
        roi_tags=["hook_strength", "watch_completion"],
        source_segment_ids=["script_para_001"],
        suggested_duration=8,
    )

    plan = HighlightPlan(
        plan_id="highlight_plan_script_001",
        input_mode="script_only",
        source_id="demo_script",
        roi_profile={"target_platform": "douyin"},
        highlights=[highlight],
        summary="One script-only highlight candidate.",
    )

    assert plan.input_mode == "script_only"
    assert plan.highlights[0].start_time is None
    assert plan.highlights[0].end_time is None


def test_timestamped_transcript_highlight_plan_allows_timed_highlights() -> None:
    highlight = HighlightSegment(
        highlight_id="hl_001",
        source_type="transcript",
        highlight_type="conflict",
        title="努力但失败",
        text="我曾经连续三个月每天工作到凌晨，但项目还是失败了。",
        reason="This segment contains strong contrast and conflict.",
        score=0.88,
        confidence=0.9,
        roi_tags=["conflict", "watch_completion"],
        source_segment_ids=["seg_003"],
        start_time=12.0,
        end_time=18.5,
        suggested_duration=6.5,
    )

    plan = HighlightPlan(
        plan_id="highlight_plan_transcript_001",
        input_mode="timestamped_transcript",
        source_id="demo_transcript",
        highlights=[highlight],
    )

    assert plan.highlights[0].start_time == 12.0
    assert plan.highlights[0].end_time == 18.5


def test_highlight_score_and_confidence_must_be_between_zero_and_one() -> None:
    with pytest.raises(ValidationError):
        _highlight(score=1.2)

    with pytest.raises(ValidationError):
        _highlight(confidence=-0.1)


def test_invalid_highlight_type_fails() -> None:
    with pytest.raises(ValidationError):
        _highlight(highlight_type="dramatic_pause")


def test_script_only_plan_rejects_timestamped_highlight() -> None:
    with pytest.raises(ValueError, match="script_only"):
        HighlightPlan(
            plan_id="highlight_plan_script_bad",
            input_mode="script_only",
            highlights=[
                _highlight(
                    source_type="script",
                    start_time=1.0,
                    end_time=3.0,
                )
            ],
        )


def test_highlight_time_range_requires_end_after_start() -> None:
    with pytest.raises(ValidationError):
        _highlight(start_time=5.0, end_time=5.0)


def _highlight(**overrides) -> HighlightSegment:  # noqa: ANN003
    payload = {
        "highlight_id": "hl_001",
        "source_type": "script",
        "highlight_type": "hook",
        "title": "Demo highlight",
        "text": "A useful short-video opening.",
        "reason": "It sets up a clear contrast.",
        "score": 0.8,
        "confidence": 0.75,
        "roi_tags": ["hook_strength"],
        "source_segment_ids": ["script_para_001"],
    }
    payload.update(overrides)
    return HighlightSegment(**payload)
