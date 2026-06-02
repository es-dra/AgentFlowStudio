from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentflow_studio.highlight_sop import (
    DeterministicHighlightDetector,
    detect_highlights_from_script,
    detect_highlights_from_transcript,
)
from agentflow_studio.schemas import HighlightPlan, Transcript


DEMO_SCRIPT = Path("examples/demo_highlight/script.txt")
DEMO_TRANSCRIPT = Path("examples/demo_highlight/transcript.json")


def test_detect_highlights_from_script_returns_untimed_highlight_plan() -> None:
    plan = detect_highlights_from_script(
        DEMO_SCRIPT.read_text(encoding="utf-8"),
        source_id="demo_script",
    )

    assert isinstance(plan, HighlightPlan)
    assert plan.plan_id == "highlight_plan_demo_script"
    assert plan.input_mode == "script_only"
    assert plan.source_id == "demo_script"
    assert len(plan.highlights) >= 3
    assert {highlight.highlight_type for highlight in plan.highlights} >= {
        "hook",
        "conflict",
        "insight",
    }
    assert all(highlight.start_time is None and highlight.end_time is None for highlight in plan.highlights)
    assert all(highlight.source_type == "script" for highlight in plan.highlights)


def test_detect_highlights_from_transcript_preserves_source_timestamps() -> None:
    transcript = Transcript.model_validate(json.loads(DEMO_TRANSCRIPT.read_text(encoding="utf-8")))

    plan = detect_highlights_from_transcript(transcript)

    assert plan.plan_id == "highlight_plan_demo_transcript_001"
    assert plan.input_mode == "timestamped_transcript"
    assert plan.source_id == "demo_transcript_001"
    assert len(plan.highlights) >= 3
    first = plan.highlights[0]
    assert first.source_type == "transcript"
    assert first.start_time is not None
    assert first.end_time is not None
    assert first.end_time > first.start_time
    assert first.source_segment_ids

    source_by_id = {segment.segment_id: segment for segment in transcript.segments}
    for highlight in plan.highlights:
        segment = source_by_id[highlight.source_segment_ids[0]]
        assert highlight.start_time == segment.start_time
        assert highlight.end_time == segment.end_time
        assert highlight.suggested_duration == pytest.approx(segment.duration_sec)


def test_detector_is_deterministic_for_same_script_input() -> None:
    detector = DeterministicHighlightDetector()
    script_text = DEMO_SCRIPT.read_text(encoding="utf-8")

    first = detector.detect_script(script_text, source_id="demo_script")
    second = detector.detect_script(script_text, source_id="demo_script")

    assert first.model_dump(mode="json", exclude={"created_at"}) == second.model_dump(
        mode="json",
        exclude={"created_at"},
    )


def test_detector_limits_highlight_count() -> None:
    plan = detect_highlights_from_script(
        DEMO_SCRIPT.read_text(encoding="utf-8"),
        source_id="demo_script",
        max_highlights=2,
    )

    assert len(plan.highlights) == 2


def test_detector_matches_readable_chinese_keywords() -> None:
    plan = detect_highlights_from_script(
        "韩渊本以为自己会一直落魄，没想到觉醒系统后真相反转。\n"
        "他被废修为逐出宗门，但凭杀猪刀重新杀回去。\n"
        "所以这一集最强爆点就是扮猪吃虎后的打脸复仇。",
        source_id="zh_script",
        max_highlights=3,
    )

    types = {highlight.highlight_type for highlight in plan.highlights}
    assert {"hook", "conflict", "cta"}.issubset(types)
    assert any("以为" in highlight.metadata["matched_keywords"] for highlight in plan.highlights)


def test_detector_rejects_empty_script_input() -> None:
    with pytest.raises(ValueError, match="script_text"):
        detect_highlights_from_script("   ")


def test_transcript_detector_uses_fallback_for_plain_transcript() -> None:
    transcript = Transcript(
        transcript_id="plain_transcript",
        segments=[
            {
                "segment_id": "seg_001",
                "start_time": 0.0,
                "end_time": 4.0,
                "text": "This is a neutral segment without obvious rule keywords.",
            }
        ],
    )

    plan = detect_highlights_from_transcript(transcript)

    assert len(plan.highlights) == 1
    assert plan.highlights[0].highlight_type == "other"
    assert plan.highlights[0].source_segment_ids == ["seg_001"]
