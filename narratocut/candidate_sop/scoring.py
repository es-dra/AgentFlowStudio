from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from narratocut.candidate_sop.signals import (
    CONFLICT_TERMS,
    HOOK_TERMS,
    PAYOFF_TERMS,
    keyword_score,
    specificity_score,
)
from narratocut.schemas import HighlightPlan


HIGHLIGHT_SCORE_REPORT = "highlight_score_report.json"
SCORER_NAME = "deterministic_viral_scorer_v0"


def score_candidate_windows(
    candidate_manifest: dict[str, Any],
    *,
    max_selected: int = 4,
    max_overlap_ratio: float = 0.5,
) -> tuple[dict[str, Any], HighlightPlan]:
    if max_selected <= 0:
        raise ValueError("max_selected must be greater than 0")
    if not 0 <= max_overlap_ratio <= 1:
        raise ValueError("max_overlap_ratio must be between 0 and 1")
    candidates = candidate_manifest.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("candidate_windows_empty")

    scored = [_score_candidate(candidate, candidate_manifest) for candidate in candidates if isinstance(candidate, dict)]
    scored.sort(key=lambda item: (-item["selection_score"], item["start_sec"], item["candidate_id"]))
    selected: list[dict[str, Any]] = []
    selected_source_windows: set[tuple[float, float]] = set()
    for item in scored:
        overlap = max((_overlap_ratio(item, picked) for picked in selected), default=0.0)
        source_window = _source_window_key(item)
        if overlap > max_overlap_ratio:
            item["decision"] = "rejected"
            item["rejection_reasons"].append("overlap")
        elif source_window is not None and source_window in selected_source_windows:
            item["decision"] = "rejected"
            item["rejection_reasons"].append("duplicate_source_window")
        elif len(selected) >= max_selected:
            item["decision"] = "rejected"
            item["rejection_reasons"].append("selection_limit")
        else:
            item["decision"] = "selected"
            selected.append(item)
            if source_window is not None:
                selected_source_windows.add(source_window)

    ordered = selected + [item for item in scored if item["decision"] != "selected"]
    report = {
        "schema_version": "0.1",
        "status": "succeeded",
        "source": "phase14_2c_candidate_scoring",
        "scorer": SCORER_NAME,
        "source_candidate_manifest": candidate_manifest.get("manifest_path") or "candidate_windows.json",
        "source_transcript_id": candidate_manifest.get("source_transcript_id"),
        "source_video": candidate_manifest.get("source_video"),
        "content_channel": candidate_manifest.get("content_channel"),
        "candidate_count": len(scored),
        "selected_count": len(selected),
        "max_selected": max_selected,
        "max_overlap_ratio": max_overlap_ratio,
        "candidates": ordered,
        "warnings": [],
        "errors": [],
        "manifest_path": HIGHLIGHT_SCORE_REPORT,
    }
    return report, _highlight_plan_from_selected(report, selected)


def _score_candidate(candidate: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    text = str(candidate.get("text") or "")
    content_channel = _content_channel(candidate, manifest)
    duration = float(candidate.get("duration_sec") or 0.0)
    transcript_confidence = _transcript_confidence(candidate.get("asr_confidence"))
    breakdown = {
        "hook_strength": keyword_score(text, HOOK_TERMS),
        "conflict_intensity": keyword_score(text, CONFLICT_TERMS),
        "clarity_without_context": _clarity_score(text),
        "payoff_or_reversal": keyword_score(text, PAYOFF_TERMS),
        "duration_fit": _duration_fit(duration),
        "transcript_confidence": transcript_confidence,
        "on_screen_hook_strength": keyword_score(text, HOOK_TERMS) if content_channel == "ocr_subtitle" else 0.0,
        "asr_ocr_consistency": 0.5,
        "script_alignment_confidence": _script_alignment_confidence(candidate),
        "platform_fit": _platform_fit(duration),
        "specificity_or_novelty": specificity_score(text),
    }
    total = round(
        0.18 * breakdown["hook_strength"]
        + 0.15 * breakdown["conflict_intensity"]
        + 0.10 * breakdown["clarity_without_context"]
        + 0.14 * breakdown["payoff_or_reversal"]
        + 0.10 * breakdown["duration_fit"]
        + 0.07 * breakdown["transcript_confidence"]
        + 0.12 * breakdown["on_screen_hook_strength"]
        + 0.03 * breakdown["asr_ocr_consistency"]
        + 0.05 * breakdown["script_alignment_confidence"]
        + 0.04 * breakdown["platform_fit"]
        + 0.02 * breakdown["specificity_or_novelty"],
        6,
    )
    source_position_penalty = _source_window_position_penalty(candidate)
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "decision": "pending",
        "rejection_reasons": [],
        "start_sec": float(candidate.get("start_sec") or 0.0),
        "end_sec": float(candidate.get("end_sec") or 0.0),
        "duration_sec": duration,
        "segment_ids": list(candidate.get("segment_ids") or []),
        "text": text,
        "content_channel": content_channel,
        "total_score": total,
        "selection_score": round(total - _coverage_penalty(duration) - source_position_penalty, 6),
        "score_breakdown": breakdown,
        "reasons": _reasons(breakdown, content_channel),
        "script_alignment": candidate.get("script_alignment") if isinstance(candidate.get("script_alignment"), dict) else None,
        "source_candidate": candidate,
    }


def _highlight_plan_from_selected(report: dict[str, Any], selected: list[dict[str, Any]]) -> HighlightPlan:
    if not selected:
        raise ValueError("no_candidate_selected")
    highlights = []
    timeline_selected = sorted(selected, key=lambda item: (item["start_sec"], item["end_sec"], item["candidate_id"]))
    for index, item in enumerate(timeline_selected, start=1):
        highlights.append(
            {
                "highlight_id": f"hl_candidate_{index:03d}",
                "source_type": "transcript",
                "highlight_type": _highlight_type(item),
                "title": "Scored candidate",
                "text": item["text"],
                "reason": "; ".join(item["reasons"]) or "Selected by deterministic candidate scoring.",
                "score": item["total_score"],
                "confidence": min(max(item["score_breakdown"]["transcript_confidence"], 0.0), 1.0),
                "roi_tags": item["reasons"],
                "source_segment_ids": item["segment_ids"],
                "start_time": item["start_sec"],
                "end_time": item["end_sec"],
                "suggested_duration": item["duration_sec"],
                "metadata": {
                    "candidate_id": item["candidate_id"],
                    "content_channel": item["content_channel"],
                    "scorer": SCORER_NAME,
                    "score_breakdown": item["score_breakdown"],
                    "script_alignment": item.get("script_alignment"),
                    "ranking_factors": {
                        "ranker": SCORER_NAME,
                        "final_score": item["total_score"],
                    },
                },
            }
        )
    return HighlightPlan.model_validate(
        {
            "plan_id": f"highlight_plan_{report.get('source_transcript_id') or 'candidate_windows'}",
            "input_mode": "timestamped_transcript",
            "source_id": report.get("source_transcript_id") or "candidate_windows",
            "highlights": highlights,
            "summary": f"Selected {len(selected)} candidate(s) with {SCORER_NAME}.",
            "metadata": {
                "source": "candidate_scoring",
                "score_report": HIGHLIGHT_SCORE_REPORT,
                "scorer": SCORER_NAME,
                "created_at": datetime.now(UTC).isoformat(),
            },
        }
    )


def _content_channel(candidate: dict[str, Any], manifest: dict[str, Any]) -> str:
    evidence = candidate.get("evidence")
    if isinstance(evidence, dict) and isinstance(evidence.get("content_channel"), str):
        return evidence["content_channel"]
    if isinstance(manifest.get("content_channel"), str):
        return manifest["content_channel"]
    return "transcript"


def _transcript_confidence(value: Any) -> float:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return min(max(float(value), 0.0), 1.0)
    return 0.7


def _clarity_score(text: str) -> float:
    length = len(text.strip())
    if length <= 0:
        return 0.0
    if 12 <= length <= 80:
        return 0.85
    if 6 <= length < 12 or 80 < length <= 140:
        return 0.65
    return 0.4


def _duration_fit(duration: float) -> float:
    if 4 <= duration <= 6:
        return 1.0
    if 3 <= duration < 4 or 6 < duration <= 8:
        return 0.65
    if 8 < duration <= 12:
        return 0.25
    return 0.05


def _platform_fit(duration: float) -> float:
    return 0.9 if 4 <= duration <= 8 else 0.35


def _coverage_penalty(duration: float) -> float:
    if 4 <= duration <= 6:
        return 0.0
    if duration < 4:
        return 0.06
    if duration <= 8:
        return 0.08
    if duration <= 12:
        return 0.24
    return 0.36


def _source_window_position_penalty(candidate: dict[str, Any]) -> float:
    evidence = candidate.get("evidence")
    if not isinstance(evidence, dict):
        return 0.0
    source_start = _optional_float(evidence.get("source_window_start_sec"))
    source_end = _optional_float(evidence.get("source_window_end_sec"))
    start_sec = _optional_float(candidate.get("start_sec"))
    if source_start is None or source_end is None or start_sec is None or source_end <= source_start:
        return 0.0
    ratio = max(0.0, min((start_sec - source_start) / (source_end - source_start), 1.0))
    if ratio < 0.05:
        return 0.0
    return round(0.03 * ratio, 6)


def _script_alignment_confidence(candidate: dict[str, Any]) -> float:
    alignment = candidate.get("script_alignment")
    if isinstance(alignment, dict) and isinstance(alignment.get("confidence"), int | float):
        return min(max(float(alignment["confidence"]), 0.0), 1.0)
    return 0.0


def _reasons(breakdown: dict[str, float], content_channel: str) -> list[str]:
    reasons: list[str] = []
    if breakdown["hook_strength"] >= 0.5:
        reasons.append("strong_hook")
    if breakdown["conflict_intensity"] >= 0.5:
        reasons.append("conflict")
    if breakdown["payoff_or_reversal"] >= 0.5:
        reasons.append("payoff_or_reversal")
    if breakdown["on_screen_hook_strength"] >= 0.5 and content_channel == "ocr_subtitle":
        reasons.append("ocr_hook")
    if breakdown.get("specificity_or_novelty", 0.0) >= 0.5:
        reasons.append("specificity")
    if breakdown["duration_fit"] >= 0.8:
        reasons.append("duration_fit")
    return reasons


def _highlight_type(item: dict[str, Any]) -> str:
    breakdown = item["score_breakdown"]
    if breakdown["hook_strength"] >= 0.5:
        return "hook"
    if breakdown["conflict_intensity"] >= 0.5:
        return "conflict"
    if breakdown["payoff_or_reversal"] >= 0.5:
        return "reversal"
    return "other"


def _overlap_ratio(left: dict[str, Any], right: dict[str, Any]) -> float:
    start = max(left["start_sec"], right["start_sec"])
    end = min(left["end_sec"], right["end_sec"])
    overlap = max(0.0, end - start)
    shortest = max(min(left["duration_sec"], right["duration_sec"]), 0.000001)
    return overlap / shortest


def _source_window_key(item: dict[str, Any]) -> tuple[float, float] | None:
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
    start = _optional_float(evidence.get("source_window_start_sec"))
    end = _optional_float(evidence.get("source_window_end_sec"))
    if start is None or end is None or end <= start:
        return None
    return (round(start, 3), round(end, 3))


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
