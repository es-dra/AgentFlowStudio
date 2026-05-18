from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from narratocut.schemas import HighlightPlan, HighlightSegment, ROISettings


RANKER_NAME = "roi_ranker_v0"


TYPE_BOOSTS = {
    "retention": {"hook": 0.12, "conflict": 0.10, "reversal": 0.10},
    "engagement": {"hook": 0.10, "conflict": 0.10, "reversal": 0.08, "cta": 0.04},
    "conversion": {"insight": 0.08, "summary": 0.06, "cta": 0.12},
    "education": {"insight": 0.12, "summary": 0.08, "quote": 0.04},
    "awareness": {"hook": 0.12, "reversal": 0.08, "quote": 0.05},
}

PLATFORM_BOOSTS = {
    "douyin": {"hook": 0.10, "conflict": 0.08, "reversal": 0.08, "cta": 0.04},
    "tiktok": {"hook": 0.10, "conflict": 0.08, "reversal": 0.08, "cta": 0.04},
    "youtube_shorts": {"hook": 0.08, "insight": 0.06, "summary": 0.04},
    "bilibili": {"insight": 0.10, "summary": 0.08, "quote": 0.04},
}

PRIORITY_BOOSTS = {
    "retention": {"hook": 0.10, "conflict": 0.08, "reversal": 0.08},
    "watch_completion": {"hook": 0.10, "conflict": 0.08, "reversal": 0.08},
    "clarity": {"insight": 0.08, "summary": 0.08, "cta": 0.03},
    "conversion": {"cta": 0.12, "summary": 0.05},
    "credibility": {"quote": 0.08, "insight": 0.05},
    "hook_strength": {"hook": 0.08},
    "conflict": {"conflict": 0.08},
}


@dataclass(frozen=True)
class RankingResult:
    highlight: HighlightSegment
    original_index: int
    final_score: float


class ROIHighlightRanker:
    def rank(
        self,
        plan: HighlightPlan,
        roi_settings: ROISettings | None = None,
    ) -> HighlightPlan:
        ranked_plan = plan.model_copy(deep=True)
        results = [
            self._rank_highlight(highlight, index, roi_settings)
            for index, highlight in enumerate(ranked_plan.highlights)
        ]
        results.sort(key=_sort_key)
        ranked_plan.highlights = [result.highlight for result in results]
        ranked_plan.metadata = {
            **ranked_plan.metadata,
            "ranker": RANKER_NAME,
            "ranking_basis": "base_score * 0.70 + confidence * 0.15 + roi_boosts",
        }
        return ranked_plan

    def _rank_highlight(
        self,
        highlight: HighlightSegment,
        original_index: int,
        roi_settings: ROISettings | None,
    ) -> RankingResult:
        content_goal = _content_goal(roi_settings)
        content_goal_tag = _content_goal_tag(roi_settings)
        target_platform = _target_platform(roi_settings)
        priorities = _priorities(roi_settings)
        highlight_type = highlight.highlight_type

        content_goal_boost, content_rules = _boost_for_type(
            TYPE_BOOSTS.get(content_goal, {}),
            highlight_type,
            f"content_goal:{content_goal}",
        )
        target_platform_boost, platform_rules = _boost_for_type(
            PLATFORM_BOOSTS.get(target_platform, {}),
            highlight_type,
            f"target_platform:{target_platform}",
        )
        priority_boost, priority_rules = _priority_boost(highlight_type, priorities)
        tag_boost, tag_rules = _tag_boost(highlight.roi_tags, priorities)

        final_score = _clamp(
            highlight.score * 0.70
            + highlight.confidence * 0.15
            + content_goal_boost
            + target_platform_boost
            + priority_boost
            + tag_boost
        )
        ranking_factors = {
            "ranker": RANKER_NAME,
            "base_score": highlight.score,
            "confidence": highlight.confidence,
            "content_goal": content_goal,
            "target_platform": target_platform,
            "priority": priorities,
            "content_goal_boost": content_goal_boost,
            "target_platform_boost": target_platform_boost,
            "priority_boost": priority_boost + tag_boost,
            "final_score": final_score,
            "matched_rules": content_rules + platform_rules + priority_rules + tag_rules,
        }
        highlight.metadata = {
            **highlight.metadata,
            "ranking_factors": ranking_factors,
            "original_rank": original_index + 1,
        }
        highlight.roi_tags = _ranked_tags(
            highlight.roi_tags,
            content_goal=content_goal_tag,
            target_platform=target_platform,
            priorities=priorities,
        )
        return RankingResult(highlight=highlight, original_index=original_index, final_score=final_score)


def rank_highlights_by_roi(
    plan: HighlightPlan,
    roi_settings: ROISettings | None = None,
) -> HighlightPlan:
    return ROIHighlightRanker().rank(plan, roi_settings)


def _sort_key(result: RankingResult) -> tuple[float, float, float, int]:
    start_time = result.highlight.start_time
    return (
        -result.final_score,
        -result.highlight.score,
        start_time if start_time is not None else float("inf"),
        result.original_index,
    )


def _content_goal(roi_settings: ROISettings | None) -> str:
    if roi_settings is None:
        return "default"
    text = _normalize(roi_settings.content_goal)
    if any(token in text for token in ["completion", "retention", "retain"]):
        return "retention"
    if any(token in text for token in ["engagement", "engage"]):
        return "engagement"
    if any(token in text for token in ["conversion", "convert", "sales"]):
        return "conversion"
    if any(token in text for token in ["education", "educate", "learning", "knowledge"]):
        return "education"
    if any(token in text for token in ["awareness", "brand"]):
        return "awareness"
    return text


def _content_goal_tag(roi_settings: ROISettings | None) -> str:
    if roi_settings is None:
        return "default"
    return _normalize(roi_settings.content_goal)


def _target_platform(roi_settings: ROISettings | None) -> str:
    if roi_settings is None:
        return "default"
    return _normalize(roi_settings.target_platform)


def _priorities(roi_settings: ROISettings | None) -> list[str]:
    if roi_settings is None:
        return []
    return [_normalize(item) for item in roi_settings.priority if _normalize(item)]


def _boost_for_type(
    boosts: dict[str, float],
    highlight_type: str,
    rule_prefix: str,
) -> tuple[float, list[str]]:
    canonical_type = _canonical_highlight_type(highlight_type)
    boost = boosts.get(canonical_type, 0.0)
    if boost <= 0:
        return 0.0, []
    return boost, [f"{rule_prefix} boosts {canonical_type}"]


def _priority_boost(highlight_type: str, priorities: list[str]) -> tuple[float, list[str]]:
    canonical_type = _canonical_highlight_type(highlight_type)
    boost = 0.0
    rules: list[str] = []
    for priority in priorities:
        value = PRIORITY_BOOSTS.get(priority, {}).get(canonical_type, 0.0)
        if value <= 0:
            continue
        boost += value
        rules.append(f"priority:{priority} boosts {canonical_type}")
    return boost, rules


def _tag_boost(roi_tags: list[str], priorities: list[str]) -> tuple[float, list[str]]:
    boost = 0.0
    rules: list[str] = []
    tag_set = {_normalize(tag) for tag in roi_tags}
    for priority in priorities:
        if priority not in tag_set:
            continue
        boost += 0.04
        rules.append(f"priority:{priority} matches roi_tags")
    return boost, rules


def _ranked_tags(
    existing: list[str],
    *,
    content_goal: str,
    target_platform: str,
    priorities: list[str],
) -> list[str]:
    tags = list(existing)
    if content_goal != "default":
        tags.append(f"goal:{content_goal}")
    if target_platform != "default":
        tags.append(f"platform:{target_platform}")
    tags.extend(f"priority:{priority}" for priority in priorities)
    return sorted(dict.fromkeys(tags))


def _normalize(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _canonical_highlight_type(value: str) -> str:
    normalized = _normalize(value)
    if normalized == "call_to_action":
        return "cta"
    return normalized


def _clamp(value: float) -> float:
    return round(min(max(value, 0.0), 1.0), 6)
