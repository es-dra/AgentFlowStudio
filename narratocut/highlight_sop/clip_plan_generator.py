from __future__ import annotations

import re
from typing import Any

from narratocut.schemas import ClipPlan, ClipSegment, HighlightPlan, HighlightSegment


GENERATOR_NAME = "phase10_highlight_clip_plan_generator"


class HighlightClipPlanGenerator:
    def generate(
        self,
        plan: HighlightPlan,
        *,
        source_video: str,
        project_id: str | None = None,
        max_clips: int | None = None,
    ) -> ClipPlan:
        if plan.input_mode == "script_only":
            raise ValueError("script_only HighlightPlan cannot generate ClipPlan because it has no timestamps")
        if not source_video.strip():
            raise ValueError("source_video must not be empty")
        if max_clips is not None and max_clips <= 0:
            raise ValueError("max_clips must be greater than 0")

        selected = plan.highlights[:max_clips] if max_clips is not None else plan.highlights
        clip_plan_id = f"clip_plan_{_safe_id(plan.plan_id)}"
        segments = [
            _segment_from_highlight(
                clip_plan_id=clip_plan_id,
                index=index,
                highlight=highlight,
                source_video=source_video.strip(),
            )
            for index, highlight in enumerate(selected, start=1)
        ]
        first = selected[0]
        return ClipPlan(
            clip_plan_id=clip_plan_id,
            project_id=project_id or plan.source_id or plan.plan_id,
            hook_id=first.highlight_id,
            script_id=None,
            duration_sec=_total_duration(segments),
            title=first.title,
            cover_text=first.text,
            segments=segments,
            voiceover_text=None,
            cta_text=_first_cta_text(selected),
            output_name=f"{clip_plan_id}.mp4",
            metadata={
                "source": GENERATOR_NAME,
                "highlight_plan_id": plan.plan_id,
                "input_mode": plan.input_mode,
                "source_id": plan.source_id,
                "source_video": source_video.strip(),
                "clip_plan_status": "generated",
                "clip_count": len(segments),
                "ranker": plan.metadata.get("ranker"),
            },
        )


def generate_clip_plan_from_highlights(
    plan: HighlightPlan,
    *,
    source_video: str,
    project_id: str | None = None,
    max_clips: int | None = None,
) -> ClipPlan:
    return HighlightClipPlanGenerator().generate(
        plan,
        source_video=source_video,
        project_id=project_id,
        max_clips=max_clips,
    )


def _segment_from_highlight(
    *,
    clip_plan_id: str,
    index: int,
    highlight: HighlightSegment,
    source_video: str,
) -> ClipSegment:
    if highlight.start_time is None or highlight.end_time is None:
        raise ValueError(f"highlight {highlight.highlight_id} is missing timestamps")
    return ClipSegment(
        segment_id=f"{clip_plan_id}_seg_{index:03d}",
        source_video=source_video,
        start_sec=highlight.start_time,
        end_sec=highlight.end_time,
        text=highlight.text,
        metadata=_segment_metadata(highlight),
    )


def _segment_metadata(highlight: HighlightSegment) -> dict[str, Any]:
    return {
        "source": GENERATOR_NAME,
        "highlight_id": highlight.highlight_id,
        "highlight_type": highlight.highlight_type,
        "highlight_score": highlight.score,
        "highlight_confidence": highlight.confidence,
        "roi_tags": list(highlight.roi_tags),
        "source_segment_ids": list(highlight.source_segment_ids),
        "ranking_factors": highlight.metadata.get("ranking_factors"),
    }


def _total_duration(segments: list[ClipSegment]) -> float:
    return round(sum(segment.end_sec - segment.start_sec for segment in segments), 6)


def _first_cta_text(highlights: list[HighlightSegment]) -> str | None:
    for highlight in highlights:
        if _canonical_highlight_type(highlight.highlight_type) == "cta":
            return highlight.text
    return None


def _canonical_highlight_type(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized == "call_to_action":
        return "cta"
    return normalized


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "highlight_plan"
