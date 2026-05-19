from __future__ import annotations

from narratocut.highlight_sop.alignment import align_script_highlights_to_transcript
from narratocut.schemas import HighlightPlan, Transcript


def test_script_highlight_alignment_creates_timestamped_highlights_from_transcript_segments() -> None:
    script_plan = HighlightPlan.model_validate(_script_highlight_plan())
    transcript = Transcript.model_validate(_transcript())

    result = align_script_highlights_to_transcript(script_plan, transcript, min_confidence=0.25)

    assert result.highlight_plan.input_mode == "timestamped_transcript"
    assert len(result.highlight_plan.highlights) == 2
    first = result.highlight_plan.highlights[0]
    assert first.highlight_id == "hl_script_001"
    assert first.start_time == 6.0
    assert first.end_time == 10.0
    assert first.source_segment_ids == ["seg_002"]
    assert first.metadata["alignment"]["matched_segment_ids"] == ["seg_002"]
    assert first.metadata["alignment"]["confidence"] >= 0.25
    assert result.manifest["status"] == "succeeded"
    assert result.manifest["aligned_count"] == 2
    assert result.manifest["skipped_count"] == 0


def test_script_highlight_alignment_skips_low_confidence_highlights() -> None:
    script_plan = HighlightPlan.model_validate(_script_highlight_plan(text="completely unrelated promise"))
    transcript = Transcript.model_validate(_transcript())

    result = align_script_highlights_to_transcript(script_plan, transcript, min_confidence=0.8)

    assert result.manifest["status"] == "partial"
    assert result.manifest["aligned_count"] == 0
    assert result.manifest["skipped_count"] == 2
    assert result.manifest["warnings"]
    assert result.highlight_plan is None


def test_script_highlight_alignment_matches_chinese_highlights_with_character_ngrams() -> None:
    script_plan = HighlightPlan.model_validate(
        _script_highlight_plan(text="韩渊被废修为逐出宗门，沦为市井屠夫")
    )
    transcript = Transcript.model_validate(
        {
            "transcript_id": "zh_asr_transcript",
            "source_video": "data/raw/demo.mp4",
            "language": "zh",
            "duration": 12.0,
            "segments": [
                {
                    "segment_id": "seg_001",
                    "start_time": 0.0,
                    "end_time": 4.0,
                    "text": "热闹集市里韩渊正在卖肉",
                },
                {
                    "segment_id": "seg_002",
                    "start_time": 5.0,
                    "end_time": 9.0,
                    "text": "韩渊被废修为逐出宗门之后沦为市井屠夫",
                },
            ],
            "metadata": {},
        }
    )

    result = align_script_highlights_to_transcript(script_plan, transcript, min_confidence=0.25)

    assert result.highlight_plan is not None
    assert result.highlight_plan.highlights[0].source_segment_ids == ["seg_002"]
    assert result.highlight_plan.highlights[0].start_time == 5.0
    assert result.manifest["aligned_count"] == 1
    assert result.manifest["skipped_count"] == 1
    assert result.manifest["alignments"][0]["confidence"] >= 0.25


def test_script_highlight_alignment_matches_multiple_source_segments_with_chinese_windows() -> None:
    script_plan = HighlightPlan.model_validate(
        {
            "plan_id": "script_highlight_plan",
            "input_mode": "script_only",
            "source_id": "script_demo",
            "highlights": [
                {
                    "highlight_id": "hl_script_001",
                    "source_type": "script",
                    "highlight_type": "hook",
                    "title": "Opening",
                    "text": "2088年，末日后第三个月。广播里说疫苗已经开始扩散。",
                    "reason": "Opening world setup.",
                    "score": 0.88,
                    "confidence": 0.9,
                    "roi_tags": ["hook_strength"],
                    "source_segment_ids": ["script_para_001", "script_para_002"],
                    "metadata": {"ranking_factors": {"final_score": 0.88}},
                }
            ],
            "warnings": [],
            "metadata": {},
        }
    )
    transcript = Transcript.model_validate(
        {
            "transcript_id": "zh_asr_transcript",
            "source_video": "data/raw/demo.mp4",
            "language": "zh",
            "duration": 30.0,
            "segments": [
                {"segment_id": "seg_001", "start_time": 1.0, "end_time": 3.0, "text": "2088年"},
                {"segment_id": "seg_002", "start_time": 3.0, "end_time": 5.0, "text": "末日后第三个月"},
                {"segment_id": "seg_003", "start_time": 20.0, "end_time": 22.0, "text": "广播里说了"},
                {"segment_id": "seg_004", "start_time": 22.0, "end_time": 26.0, "text": "疫苗已经开始扩散"},
            ],
            "metadata": {},
        }
    )

    result = align_script_highlights_to_transcript(script_plan, transcript, min_confidence=0.25)

    assert result.highlight_plan is not None
    highlight = result.highlight_plan.highlights[0]
    assert highlight.source_segment_ids == ["seg_001", "seg_002", "seg_003", "seg_004"]
    assert highlight.start_time == 1.0
    assert highlight.end_time == 26.0


def _script_highlight_plan(text: str | None = None) -> dict[str, object]:
    return {
        "plan_id": "script_highlight_plan",
        "input_mode": "script_only",
        "source_id": "script_demo",
        "highlights": [
            {
                "highlight_id": "hl_script_001",
                "source_type": "script",
                "highlight_type": "hook",
                "title": "Real bottleneck",
                "text": text or "the real bottleneck is choosing what to cut",
                "reason": "Strong contrast in the script.",
                "score": 0.88,
                "confidence": 0.9,
                "roi_tags": ["hook_strength"],
                "metadata": {"ranking_factors": {"final_score": 0.88}},
            },
            {
                "highlight_id": "hl_script_002",
                "source_type": "script",
                "highlight_type": "climax",
                "title": "Validate story",
                "text": "Validate the story before final assembly",
                "reason": "Clear execution checkpoint.",
                "score": 0.82,
                "confidence": 0.87,
                "roi_tags": ["clarity"],
                "metadata": {"ranking_factors": {"final_score": 0.82}},
            },
        ],
        "warnings": [],
        "metadata": {},
    }


def _transcript() -> dict[str, object]:
    return {
        "transcript_id": "asr_transcript",
        "source_video": "data/raw/demo.mp4",
        "language": "en",
        "duration": 15.0,
        "segments": [
            {
                "segment_id": "seg_001",
                "start_time": 0.0,
                "end_time": 5.0,
                "text": "Most teams chase automation first.",
            },
            {
                "segment_id": "seg_002",
                "start_time": 6.0,
                "end_time": 10.0,
                "text": "But the real bottleneck is choosing what to cut.",
            },
            {
                "segment_id": "seg_003",
                "start_time": 11.0,
                "end_time": 15.0,
                "text": "Validate the story before spending time on final assembly.",
            },
        ],
        "metadata": {},
    }
