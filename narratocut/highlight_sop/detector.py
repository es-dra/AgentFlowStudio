from __future__ import annotations

import re
from dataclasses import dataclass

from narratocut.schemas import HighlightPlan, HighlightSegment, Transcript


DEFAULT_MAX_HIGHLIGHTS = 5
DETECTOR_NAME = "deterministic_v0"


@dataclass(frozen=True)
class HighlightRule:
    highlight_type: str
    title: str
    reason: str
    score: float
    confidence: float
    roi_tags: tuple[str, ...]
    keywords: tuple[str, ...]


RULES = [
    HighlightRule(
        highlight_type="hook",
        title="Expectation gap opening",
        reason="The text sets up a clear expectation gap suitable for an opening hook.",
        score=0.92,
        confidence=0.82,
        roi_tags=("hook_strength", "watch_completion"),
        keywords=("以为", "真相", "相反", "truth", "myth", "actually"),
    ),
    HighlightRule(
        highlight_type="conflict",
        title="Visible conflict",
        reason="The text contains effort, failure, pressure, or contrast that can sustain attention.",
        score=0.86,
        confidence=0.8,
        roi_tags=("conflict", "watch_completion"),
        keywords=("失败", "但", "却", "困境", "凌晨", "failed", "but", "however"),
    ),
    HighlightRule(
        highlight_type="insight",
        title="Actionable insight",
        reason="The text reveals a practical lesson or cause behind the outcome.",
        score=0.82,
        confidence=0.78,
        roi_tags=("clarity", "insight"),
        keywords=("发现", "用户", "需求", "真正", "决定", "learned", "realized", "need"),
    ),
    HighlightRule(
        highlight_type="cta",
        title="Action prompt",
        reason="The text gives the viewer a clear next action or summary recommendation.",
        score=0.76,
        confidence=0.74,
        roi_tags=("clarity", "actionability"),
        keywords=("所以", "请", "先", "如果", "please", "if you", "remember"),
    ),
]


class DeterministicHighlightDetector:
    def detect_script(
        self,
        script_text: str,
        *,
        source_id: str | None = None,
        max_highlights: int = DEFAULT_MAX_HIGHLIGHTS,
    ) -> HighlightPlan:
        lines = _split_script(script_text)
        if not lines:
            raise ValueError("script_text must not be empty")
        candidates = [
            self._candidate_from_text(
                text=line,
                source_type="script",
                source_segment_id=f"script_para_{index:03d}",
                source_index=index,
            )
            for index, line in enumerate(lines, start=1)
        ]
        return _build_plan(
            input_mode="script_only",
            source_id=source_id or "script_input",
            candidates=candidates,
            max_highlights=max_highlights,
        )

    def detect_transcript(
        self,
        transcript: Transcript,
        *,
        source_id: str | None = None,
        max_highlights: int = DEFAULT_MAX_HIGHLIGHTS,
    ) -> HighlightPlan:
        candidates = [
            self._candidate_from_text(
                text=segment.text,
                source_type="transcript",
                source_segment_id=segment.segment_id,
                source_index=index,
                start_time=segment.start_time,
                end_time=segment.end_time,
                suggested_duration=segment.duration_sec,
            )
            for index, segment in enumerate(transcript.segments, start=1)
        ]
        return _build_plan(
            input_mode="timestamped_transcript",
            source_id=source_id or transcript.transcript_id,
            candidates=candidates,
            max_highlights=max_highlights,
        )

    def _candidate_from_text(
        self,
        *,
        text: str,
        source_type: str,
        source_segment_id: str,
        source_index: int,
        start_time: float | None = None,
        end_time: float | None = None,
        suggested_duration: float | None = None,
    ) -> HighlightSegment:
        rule = _first_matching_rule(text) or _fallback_rule()
        return HighlightSegment(
            highlight_id=f"hl_{source_index:03d}",
            source_type=source_type,
            highlight_type=rule.highlight_type,
            title=rule.title,
            text=text,
            reason=rule.reason,
            score=rule.score,
            confidence=rule.confidence,
            roi_tags=list(rule.roi_tags),
            source_segment_ids=[source_segment_id],
            start_time=start_time,
            end_time=end_time,
            suggested_duration=suggested_duration or _suggested_duration(text),
            metadata={
                "detector": DETECTOR_NAME,
                "source_index": source_index,
                "matched_keywords": _matched_keywords(text, rule),
            },
        )


def detect_highlights_from_script(
    script_text: str,
    *,
    source_id: str | None = None,
    max_highlights: int = DEFAULT_MAX_HIGHLIGHTS,
) -> HighlightPlan:
    return DeterministicHighlightDetector().detect_script(
        script_text,
        source_id=source_id,
        max_highlights=max_highlights,
    )


def detect_highlights_from_transcript(
    transcript: Transcript,
    *,
    source_id: str | None = None,
    max_highlights: int = DEFAULT_MAX_HIGHLIGHTS,
) -> HighlightPlan:
    return DeterministicHighlightDetector().detect_transcript(
        transcript,
        source_id=source_id,
        max_highlights=max_highlights,
    )


def _build_plan(
    *,
    input_mode: str,
    source_id: str,
    candidates: list[HighlightSegment],
    max_highlights: int,
) -> HighlightPlan:
    if max_highlights <= 0:
        raise ValueError("max_highlights must be greater than 0")
    selected = sorted(
        candidates,
        key=lambda item: (-item.score, int(item.metadata.get("source_index", 0))),
    )[:max_highlights]
    return HighlightPlan(
        plan_id=f"highlight_plan_{source_id}",
        input_mode=input_mode,
        source_id=source_id,
        highlights=selected,
        summary=f"Detected {len(selected)} highlight candidate(s) with {DETECTOR_NAME}.",
        metadata={"detector": DETECTOR_NAME, "max_highlights": max_highlights},
    )


def _split_script(script_text: str) -> list[str]:
    return [line.strip() for line in re.split(r"[\r\n]+", script_text) if line.strip()]


def _first_matching_rule(text: str) -> HighlightRule | None:
    normalized = text.lower()
    for rule in RULES:
        if any(keyword.lower() in normalized for keyword in rule.keywords):
            return rule
    return None


def _matched_keywords(text: str, rule: HighlightRule) -> list[str]:
    normalized = text.lower()
    return [keyword for keyword in rule.keywords if keyword.lower() in normalized]


def _fallback_rule() -> HighlightRule:
    return HighlightRule(
        highlight_type="other",
        title="General candidate",
        reason="The text is kept as a fallback candidate because no stronger deterministic rule matched.",
        score=0.5,
        confidence=0.55,
        roi_tags=("baseline_candidate",),
        keywords=(),
    )


def _suggested_duration(text: str) -> float:
    return min(max(len(text) / 8.0, 4.0), 12.0)
