from __future__ import annotations

from typing import Any


def content_channel(candidate: dict[str, Any], manifest: dict[str, Any]) -> str:
    evidence = candidate.get("evidence")
    if isinstance(evidence, dict) and isinstance(evidence.get("content_channel"), str):
        return evidence["content_channel"]
    if isinstance(manifest.get("content_channel"), str):
        return manifest["content_channel"]
    return "transcript"


def transcript_confidence(value: Any) -> float:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return min(max(float(value), 0.0), 1.0)
    return 0.7


def clarity_score(text: str) -> float:
    length = len(text.strip())
    if length <= 0:
        return 0.0
    if 12 <= length <= 80:
        return 0.85
    if 6 <= length < 12 or 80 < length <= 140:
        return 0.65
    return 0.4


def duration_fit(duration: float) -> float:
    if 4 <= duration <= 6:
        return 1.0
    if 3 <= duration < 4 or 6 < duration <= 8:
        return 0.65
    if 8 < duration <= 12:
        return 0.25
    return 0.05


def platform_fit(duration: float) -> float:
    return 0.9 if 4 <= duration <= 8 else 0.35


def coverage_penalty(duration: float) -> float:
    if 4 <= duration <= 6:
        return 0.0
    if duration < 4:
        return 0.06
    if duration <= 8:
        return 0.08
    if duration <= 12:
        return 0.24
    return 0.36


def source_window_position_penalty(candidate: dict[str, Any]) -> float:
    evidence = candidate.get("evidence")
    if not isinstance(evidence, dict):
        return 0.0
    source_start = optional_float(evidence.get("source_window_start_sec"))
    source_end = optional_float(evidence.get("source_window_end_sec"))
    start_sec = optional_float(candidate.get("start_sec"))
    if source_start is None or source_end is None or start_sec is None or source_end <= source_start:
        return 0.0
    ratio = max(0.0, min((start_sec - source_start) / (source_end - source_start), 1.0))
    if ratio < 0.05:
        return 0.0
    return round(0.03 * ratio, 6)


def script_alignment_confidence(candidate: dict[str, Any]) -> float:
    alignment = candidate.get("script_alignment")
    if isinstance(alignment, dict) and isinstance(alignment.get("confidence"), int | float):
        return min(max(float(alignment["confidence"]), 0.0), 1.0)
    return 0.0


def reasons(breakdown: dict[str, float], content_channel: str) -> list[str]:
    result: list[str] = []
    if breakdown["hook_strength"] >= 0.5:
        result.append("strong_hook")
    if breakdown["conflict_intensity"] >= 0.5:
        result.append("conflict")
    if breakdown["payoff_or_reversal"] >= 0.5:
        result.append("payoff_or_reversal")
    if breakdown["on_screen_hook_strength"] >= 0.5 and content_channel == "ocr_subtitle":
        result.append("ocr_hook")
    if breakdown.get("specificity_or_novelty", 0.0) >= 0.5:
        result.append("specificity")
    if breakdown["duration_fit"] >= 0.8:
        result.append("duration_fit")
    return result


def highlight_type(item: dict[str, Any]) -> str:
    breakdown = item["score_breakdown"]
    if breakdown["hook_strength"] >= 0.5:
        return "hook"
    if breakdown["conflict_intensity"] >= 0.5:
        return "conflict"
    if breakdown["payoff_or_reversal"] >= 0.5:
        return "reversal"
    return "other"


def overlap_ratio(left: dict[str, Any], right: dict[str, Any]) -> float:
    start = max(left["start_sec"], right["start_sec"])
    end = min(left["end_sec"], right["end_sec"])
    overlap = max(0.0, end - start)
    shortest = max(min(left["duration_sec"], right["duration_sec"]), 0.000001)
    return overlap / shortest


def source_window_key(item: dict[str, Any]) -> tuple[float, float] | None:
    source_candidate = item.get("source_candidate")
    if not isinstance(source_candidate, dict):
        return None
    evidence = source_candidate.get("evidence")
    if not isinstance(evidence, dict):
        return None
    boundary_strategy = evidence.get("boundary_strategy")
    base_boundary_strategy = evidence.get("base_boundary_strategy")
    if boundary_strategy not in {
        "fixed_duration_split",
        "elastic_duration_split",
        "elastic_duration_trim",
    } and not (
        boundary_strategy == "audio_boundary_refined"
        and base_boundary_strategy in {"fixed_duration_split", "elastic_duration_split", "elastic_duration_trim"}
    ):
        return None
    start = optional_float(evidence.get("source_window_start_sec"))
    end = optional_float(evidence.get("source_window_end_sec"))
    if start is None or end is None or end <= start:
        return None
    return (round(start, 3), round(end, 3))


def optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
