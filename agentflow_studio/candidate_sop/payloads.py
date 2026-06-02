from __future__ import annotations

from typing import Any

from agentflow_studio.candidate_sop.audio_boundaries import (
    apply_audio_boundary_refinement,
    nearest_audio_boundary_evidence,
)
from agentflow_studio.schemas import TranscriptSegment


def candidate_payload(
    *,
    index: int,
    window: list[TranscriptSegment],
    transcript_duration: float | None,
    content_channel: str,
    alignment_index: list[dict[str, Any]] | None = None,
    boundary_index: list[dict[str, Any]] | None = None,
    candidate_start_sec: float | None = None,
    candidate_end_sec: float | None = None,
    min_duration_sec: float | None = None,
    max_duration_sec: float | None = None,
) -> dict[str, Any]:
    source_start_sec = window[0].start_time
    source_end_sec = window[-1].end_time
    start_sec = source_start_sec if candidate_start_sec is None else candidate_start_sec
    end_sec = source_end_sec if candidate_end_sec is None else candidate_end_sec
    refinement = apply_audio_boundary_refinement(
        start_sec=start_sec,
        end_sec=end_sec,
        source_start_sec=source_start_sec,
        source_end_sec=source_end_sec,
        boundary_index=boundary_index or [],
        min_duration_sec=min_duration_sec,
        max_duration_sec=max_duration_sec,
    )
    start_sec = refinement["start_sec"]
    end_sec = refinement["end_sec"]
    script_alignment = _best_alignment(
        start_sec=start_sec,
        end_sec=end_sec,
        segment_ids=[segment.segment_id for segment in window],
        alignment_index=alignment_index or [],
    )
    evidence = {
        "window_size": len(window),
        "source_position": _source_position(start_sec, transcript_duration),
        "content_channel": content_channel,
        "keyword_hits": [],
    }
    evidence.update(refinement["evidence"])
    if "audio_boundary_refinement" in evidence:
        evidence["boundary_strategy"] = "audio_boundary_refined"
    if script_alignment is not None:
        evidence["script_highlight_id"] = script_alignment["highlight_id"]
    audio_boundary = nearest_audio_boundary_evidence(
        start_sec=start_sec,
        end_sec=end_sec,
        boundary_index=boundary_index or [],
    )
    if audio_boundary is not None:
        evidence["audio_boundary"] = audio_boundary
    return {
        "candidate_id": f"cand_{index:03d}",
        "source": "transcript_window",
        "start_sec": start_sec,
        "end_sec": end_sec,
        "duration_sec": round(end_sec - start_sec, 6),
        "segment_ids": [segment.segment_id for segment in window],
        "text": " ".join(segment.text for segment in window),
        "asr_confidence": _average_confidence(window),
        "script_alignment": script_alignment,
        "evidence": evidence,
    }


def _average_confidence(window: list[TranscriptSegment]) -> float | None:
    values = [segment.confidence for segment in window if segment.confidence is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _source_position(start_sec: float, transcript_duration: float | None) -> str:
    if transcript_duration is None or transcript_duration <= 0:
        return "unknown"
    ratio = start_sec / transcript_duration
    if ratio < 0.25:
        return "early"
    if ratio < 0.6:
        return "middle"
    return "late"


def _best_alignment(
    *,
    start_sec: float,
    end_sec: float,
    segment_ids: list[str],
    alignment_index: list[dict[str, Any]],
) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_score = 0.0
    for alignment in alignment_index:
        overlap = _time_overlap_ratio(
            start_sec,
            end_sec,
            float(alignment["start_time"]),
            float(alignment["end_time"]),
        )
        matched = set(alignment["matched_segment_ids"])
        segment_overlap = len(set(segment_ids) & matched) / max(len(set(segment_ids) | matched), 1) if matched else 0.0
        score = max(overlap, segment_overlap)
        if score > best_score:
            best_score = score
            best = alignment
    if best is None or best_score <= 0:
        return None
    return {
        "highlight_id": best["highlight_id"],
        "confidence": round(float(best["confidence"]), 6),
        "matched_segment_ids": list(best["matched_segment_ids"]),
        "overlap_ratio": round(best_score, 6),
    }


def _time_overlap_ratio(left_start: float, left_end: float, right_start: float, right_end: float) -> float:
    overlap = max(0.0, min(left_end, right_end) - max(left_start, right_start))
    shortest = max(min(left_end - left_start, right_end - right_start), 0.000001)
    return overlap / shortest
