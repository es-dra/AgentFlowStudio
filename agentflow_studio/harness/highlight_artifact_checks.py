from __future__ import annotations

from typing import Any


def ids_are_unique(highlights: list[Any]) -> bool:
    ids = [item.get("highlight_id") for item in highlights if isinstance(item, dict)]
    return len(ids) == len(highlights) and len(set(ids)) == len(ids)


def numeric_fields_valid(items: list[Any], field_name: str) -> bool:
    values = [number(item.get(field_name)) for item in items if isinstance(item, dict)]
    return len(values) == len(items) and all(value is not None and 0.0 <= value <= 1.0 for value in values)


def all_have_ranking_factors(highlights: list[Any]) -> bool:
    return all(ranking_factors(item) is not None for item in highlights if isinstance(item, dict)) and len(highlights) > 0


def final_scores_valid(highlights: list[Any]) -> bool:
    scores = [final_score(item) for item in highlights if isinstance(item, dict)]
    return len(scores) == len(highlights) and all(score is not None and 0.0 <= score <= 1.0 for score in scores)


def final_score(item: Any) -> float | None:
    factors = ranking_factors(item)
    return number(factors.get("final_score")) if factors is not None else None


def has_time_range(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    return item.get("start_time") is not None or item.get("end_time") is not None


def has_valid_time_range(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    start = number(item.get("start_time"))
    end = number(item.get("end_time"))
    return start is not None and end is not None and start >= 0.0 and end > start


def has_source_segment_ids(item: Any) -> bool:
    ids = item.get("source_segment_ids") if isinstance(item, dict) else None
    return isinstance(ids, list) and len(ids) > 0 and all(isinstance(value, str) and value for value in ids)


def segment_has_valid_time_range(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    start = number(item.get("start_sec"))
    end = number(item.get("end_sec"))
    return start is not None and end is not None and start >= 0.0 and end > start


def segment_has_highlight_id(item: Any) -> bool:
    metadata = item.get("metadata") if isinstance(item, dict) else None
    return isinstance(metadata, dict) and isinstance(metadata.get("highlight_id"), str) and bool(metadata["highlight_id"])


def segment_has_ranking_factors(item: Any) -> bool:
    metadata = item.get("metadata") if isinstance(item, dict) else None
    factors = metadata.get("ranking_factors") if isinstance(metadata, dict) else None
    score = factors.get("final_score") if isinstance(factors, dict) else None
    value = number(score)
    return value is not None and 0.0 <= value <= 1.0


def clip_order_matches_highlights(highlight_plan: dict[str, Any], segments: list[Any]) -> bool:
    highlights = highlight_plan.get("highlights")
    if not isinstance(highlights, list):
        return False
    highlight_ids = [
        item.get("highlight_id")
        for item in highlights
        if isinstance(item, dict)
    ]
    segment_ids = [
        item.get("metadata", {}).get("highlight_id")
        for item in segments
        if isinstance(item, dict) and isinstance(item.get("metadata"), dict)
    ]
    return bool(highlight_ids) and segment_ids == highlight_ids[: len(segment_ids)]


def type_distribution(highlights: list[Any]) -> dict[str, int]:
    distribution: dict[str, int] = {}
    for item in highlights:
        if not isinstance(item, dict):
            continue
        highlight_type = str(item.get("highlight_type") or "unknown")
        distribution[highlight_type] = distribution.get(highlight_type, 0) + 1
    return distribution


def range_values(values: Any) -> dict[str, float | None]:
    numbers = [value for value in values if value is not None]
    if not numbers:
        return {"min": None, "max": None}
    return {"min": min(numbers), "max": max(numbers)}


def ranking_factors(item: Any) -> dict[str, Any] | None:
    metadata = item.get("metadata") if isinstance(item, dict) else None
    factors = metadata.get("ranking_factors") if isinstance(metadata, dict) else None
    return factors if isinstance(factors, dict) else None


def number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
