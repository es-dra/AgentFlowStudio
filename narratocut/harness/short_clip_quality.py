from __future__ import annotations

from typing import Any


TARGET_CLIP_MIN_SEC = 4.0
TARGET_CLIP_MAX_SEC = 6.0
HARD_CLIP_MAX_SEC = 8.0
TARGET_FINAL_MAX_SEC = 24.0
HARD_FINAL_MAX_SEC = 30.0


def add_short_clip_product_checks(
    *,
    primary_duration: float | None,
    clip_plan: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    warnings: list[str],
    add_warning: Any,
) -> None:
    if primary_duration is not None and primary_duration > HARD_FINAL_MAX_SEC:
        add_warning(
            checks,
            warnings,
            "product_quality_final_video_too_long",
            {
                "duration_sec": primary_duration,
                "hard_max_sec": HARD_FINAL_MAX_SEC,
                "target_max_sec": TARGET_FINAL_MAX_SEC,
            },
        )
    if clip_plan is None:
        return

    segments = clip_plan.get("segments")
    segment_list = segments if isinstance(segments, list) else []
    long_segments = [segment for segment in segment_list if segment_duration(segment) > HARD_CLIP_MAX_SEC]
    if long_segments:
        add_warning(
            checks,
            warnings,
            "product_quality_clip_too_long",
            {
                "hard_max_sec": HARD_CLIP_MAX_SEC,
                "target_min_sec": TARGET_CLIP_MIN_SEC,
                "target_max_sec": TARGET_CLIP_MAX_SEC,
                "segments": [segment_ref(segment) for segment in long_segments],
            },
        )
    if has_duplicate_clip_windows(segment_list):
        add_warning(checks, warnings, "product_quality_duplicate_clip_window", {})
    if not uses_candidate_scoring(clip_plan):
        add_warning(checks, warnings, "product_quality_candidate_scoring_not_used", {})


def uses_candidate_scoring(clip_plan: dict[str, Any] | None) -> bool:
    if not isinstance(clip_plan, dict):
        return False
    segments = clip_plan.get("segments")
    if not isinstance(segments, list):
        return False
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        metadata = segment.get("metadata")
        if not isinstance(metadata, dict):
            continue
        ranking = metadata.get("ranking_factors")
        if metadata.get("candidate_id") or metadata.get("scorer") == "deterministic_viral_scorer_v0":
            return True
        if isinstance(ranking, dict) and ranking.get("ranker") == "deterministic_viral_scorer_v0":
            return True
    return False


def has_duplicate_clip_windows(segments: list[Any]) -> bool:
    normalized: list[tuple[float, float]] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        start = optional_float(segment.get("start_sec"))
        end = optional_float(segment.get("end_sec"))
        if start is None or end is None:
            continue
        current = (start, end)
        if any(overlap_ratio(current, other) > 0.6 for other in normalized):
            return True
        normalized.append(current)
    return False


def segment_duration(segment: Any) -> float:
    if not isinstance(segment, dict):
        return 0.0
    start = optional_float(segment.get("start_sec"))
    end = optional_float(segment.get("end_sec"))
    if start is None or end is None:
        return 0.0
    return max(0.0, end - start)


def segment_ref(segment: Any) -> dict[str, Any]:
    if not isinstance(segment, dict):
        return {}
    return {
        "segment_id": segment.get("segment_id"),
        "start_sec": segment.get("start_sec"),
        "end_sec": segment.get("end_sec"),
        "duration_sec": segment_duration(segment),
    }


def overlap_ratio(left: tuple[float, float], right: tuple[float, float]) -> float:
    start = max(left[0], right[0])
    end = min(left[1], right[1])
    overlap = max(0.0, end - start)
    shortest = max(min(left[1] - left[0], right[1] - right[0]), 0.000001)
    return overlap / shortest


def optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
