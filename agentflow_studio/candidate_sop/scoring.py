from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from agentflow_studio.candidate_sop.signals import (
    CONFLICT_TERMS,
    HOOK_TERMS,
    PAYOFF_TERMS,
    keyword_score,
    specificity_score,
)
from agentflow_studio.candidate_sop.scoring_features import (
    clarity_score,
    content_channel as _content_channel,
    coverage_penalty,
    duration_fit,
    highlight_type,
    overlap_ratio,
    platform_fit,
    reasons,
    script_alignment_confidence,
    source_window_key,
    source_window_position_penalty,
    transcript_confidence,
)
from agentflow_studio.schemas import HighlightPlan


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
        overlap = max((overlap_ratio(item, picked) for picked in selected), default=0.0)
        source_window = source_window_key(item)
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
    transcript_confidence_value = transcript_confidence(candidate.get("asr_confidence"))
    breakdown = {
        "hook_strength": keyword_score(text, HOOK_TERMS),
        "conflict_intensity": keyword_score(text, CONFLICT_TERMS),
        "clarity_without_context": clarity_score(text),
        "payoff_or_reversal": keyword_score(text, PAYOFF_TERMS),
        "duration_fit": duration_fit(duration),
        "transcript_confidence": transcript_confidence_value,
        "on_screen_hook_strength": keyword_score(text, HOOK_TERMS) if content_channel == "ocr_subtitle" else 0.0,
        "asr_ocr_consistency": 0.5,
        "script_alignment_confidence": script_alignment_confidence(candidate),
        "platform_fit": platform_fit(duration),
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
    source_position_penalty = source_window_position_penalty(candidate)
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
        "selection_score": round(total - coverage_penalty(duration) - source_position_penalty, 6),
        "score_breakdown": breakdown,
        "reasons": reasons(breakdown, content_channel),
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
                "highlight_type": highlight_type(item),
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
