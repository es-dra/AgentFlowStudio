from __future__ import annotations

from narratocut.highlight_sop import ROIHighlightRanker, rank_highlights_by_roi
from narratocut.schemas import HighlightPlan, HighlightSegment, ROISettings


def test_ranker_without_roi_returns_new_plan_sorted_by_base_signal() -> None:
    plan = _plan(
        [
            _highlight("hl_low", "hook", score=0.6, confidence=0.9),
            _highlight("hl_high", "insight", score=0.8, confidence=0.4),
        ]
    )

    ranked = rank_highlights_by_roi(plan)

    assert ranked is not plan
    assert [item.highlight_id for item in plan.highlights] == ["hl_low", "hl_high"]
    assert [item.highlight_id for item in ranked.highlights] == ["hl_high", "hl_low"]
    assert _factors(ranked.highlights[0])["final_score"] > _factors(ranked.highlights[1])["final_score"]


def test_content_goal_retention_boosts_hooks_over_slightly_higher_insight() -> None:
    plan = _plan(
        [
            _highlight("hl_insight", "insight", score=0.72, confidence=0.8),
            _highlight("hl_hook", "hook", score=0.7, confidence=0.8),
        ]
    )
    roi = _roi(content_goal="increase_completion_rate", target_platform="neutral")

    ranked = ROIHighlightRanker().rank(plan, roi)

    assert ranked.highlights[0].highlight_id == "hl_hook"
    factors = _factors(ranked.highlights[0])
    assert factors["content_goal_boost"] > 0
    assert any("content_goal" in rule for rule in factors["matched_rules"])


def test_content_goal_education_boosts_insights() -> None:
    plan = _plan(
        [
            _highlight("hl_hook", "hook", score=0.75, confidence=0.8),
            _highlight("hl_insight", "insight", score=0.7, confidence=0.8),
        ]
    )
    roi = _roi(content_goal="education", target_platform="neutral")

    ranked = rank_highlights_by_roi(plan, roi)

    assert ranked.highlights[0].highlight_id == "hl_insight"
    assert _factors(ranked.highlights[0])["content_goal_boost"] > 0


def test_target_platform_changes_ranking_preference() -> None:
    plan = _plan(
        [
            _highlight("hl_insight", "insight", score=0.72, confidence=0.8),
            _highlight("hl_hook", "hook", score=0.7, confidence=0.8),
        ]
    )

    douyin_ranked = rank_highlights_by_roi(plan, _roi(content_goal="neutral", target_platform="douyin"))
    bilibili_ranked = rank_highlights_by_roi(plan, _roi(content_goal="neutral", target_platform="bilibili"))

    assert douyin_ranked.highlights[0].highlight_id == "hl_hook"
    assert bilibili_ranked.highlights[0].highlight_id == "hl_insight"
    assert _factors(douyin_ranked.highlights[0])["target_platform_boost"] > 0


def test_priority_boost_is_explained_in_ranking_factors() -> None:
    plan = _plan(
        [
            _highlight("hl_summary", "summary", score=0.7, confidence=0.8),
            _highlight("hl_cta", "cta", score=0.69, confidence=0.8),
        ]
    )
    roi = _roi(
        content_goal="neutral",
        target_platform="neutral",
        priority=["conversion", "clarity"],
    )

    ranked = rank_highlights_by_roi(plan, roi)

    assert ranked.highlights[0].highlight_id == "hl_cta"
    factors = _factors(ranked.highlights[0])
    assert factors["priority_boost"] > 0
    assert factors["matched_rules"]
    assert "priority:conversion" in " ".join(factors["matched_rules"])


def test_call_to_action_type_uses_cta_ranking_rules() -> None:
    plan = _plan(
        [
            _highlight("hl_summary", "summary", score=0.7, confidence=0.8),
            _highlight("hl_cta_alias", "call_to_action", score=0.69, confidence=0.8),
        ]
    )

    ranked = rank_highlights_by_roi(
        plan,
        _roi(content_goal="neutral", target_platform="neutral", priority=["conversion"]),
    )

    assert ranked.highlights[0].highlight_id == "hl_cta_alias"
    assert "boosts cta" in " ".join(_factors(ranked.highlights[0])["matched_rules"])


def test_final_score_is_clamped_to_one() -> None:
    plan = _plan([_highlight("hl_hook", "hook", score=0.99, confidence=1.0)])
    roi = _roi(
        content_goal="increase_completion_rate",
        target_platform="douyin",
        priority=["retention", "hook_strength"],
    )

    ranked = rank_highlights_by_roi(plan, roi)

    assert _factors(ranked.highlights[0])["final_score"] == 1.0


def test_ranking_preserves_input_mode_timestamps_and_source_segments() -> None:
    plan = _plan(
        [
            _highlight(
                "hl_insight",
                "insight",
                score=0.72,
                confidence=0.8,
                source_type="transcript",
                start_time=4.2,
                end_time=8.6,
                source_segment_ids=["seg_002"],
            ),
            _highlight(
                "hl_hook",
                "hook",
                score=0.7,
                confidence=0.8,
                source_type="transcript",
                start_time=0.0,
                end_time=4.2,
                source_segment_ids=["seg_001"],
            ),
        ],
        input_mode="timestamped_transcript",
    )

    ranked = rank_highlights_by_roi(plan, _roi(content_goal="increase_completion_rate"))

    assert ranked.input_mode == "timestamped_transcript"
    first = ranked.highlights[0]
    assert first.highlight_id == "hl_hook"
    assert first.start_time == 0.0
    assert first.end_time == 4.2
    assert first.source_segment_ids == ["seg_001"]


def test_ranking_adds_user_facing_roi_tags_without_overwriting_existing_tags() -> None:
    plan = _plan([_highlight("hl_hook", "hook", roi_tags=["hook_strength"])])

    ranked = rank_highlights_by_roi(plan, _roi(content_goal="increase_completion_rate", target_platform="douyin"))

    assert "hook_strength" in ranked.highlights[0].roi_tags
    assert "goal:increase_completion_rate" in ranked.highlights[0].roi_tags
    assert "platform:douyin" in ranked.highlights[0].roi_tags


def _highlight(
    highlight_id: str,
    highlight_type: str,
    *,
    score: float = 0.7,
    confidence: float = 0.8,
    source_type: str = "script",
    start_time: float | None = None,
    end_time: float | None = None,
    source_segment_ids: list[str] | None = None,
    roi_tags: list[str] | None = None,
) -> HighlightSegment:
    return HighlightSegment(
        highlight_id=highlight_id,
        source_type=source_type,
        highlight_type=highlight_type,
        title=f"{highlight_type} title",
        text=f"{highlight_type} text",
        reason=f"{highlight_type} reason",
        score=score,
        confidence=confidence,
        roi_tags=roi_tags or [highlight_type],
        source_segment_ids=source_segment_ids or ["script_para_001"],
        start_time=start_time,
        end_time=end_time,
    )


def _plan(
    highlights: list[HighlightSegment],
    *,
    input_mode: str = "script_only",
) -> HighlightPlan:
    return HighlightPlan(
        plan_id="highlight_plan_test",
        input_mode=input_mode,
        source_id="test_source",
        highlights=highlights,
    )


def _roi(
    *,
    content_goal: str = "increase_completion_rate",
    target_platform: str = "douyin",
    priority: list[str] | None = None,
) -> ROISettings:
    return ROISettings(
        target_platform=target_platform,
        target_audience="product builders",
        content_goal=content_goal,
        priority=priority or [],
    )


def _factors(highlight: HighlightSegment) -> dict[str, object]:
    factors = highlight.metadata.get("ranking_factors")
    assert isinstance(factors, dict)
    return factors
