from __future__ import annotations

from typing import Any

from narratocut.schemas import Transcript, TranscriptSegment


CANDIDATE_WINDOWS_MANIFEST = "candidate_windows.json"


def generate_candidate_windows(
    transcript: Transcript,
    *,
    max_window_size: int = 4,
    min_duration_sec: float | None = None,
    max_duration_sec: float | None = None,
    target_window_sec: float | None = None,
    script_highlight_alignment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if max_window_size <= 0:
        raise ValueError("max_window_size must be greater than 0")
    if min_duration_sec is not None and min_duration_sec < 0:
        raise ValueError("min_duration_sec must be non-negative")
    if max_duration_sec is not None and max_duration_sec <= 0:
        raise ValueError("max_duration_sec must be greater than 0")
    if (
        min_duration_sec is not None
        and max_duration_sec is not None
        and min_duration_sec > max_duration_sec
    ):
        raise ValueError("min_duration_sec must be less than or equal to max_duration_sec")
    if target_window_sec is not None and target_window_sec <= 0:
        raise ValueError("target_window_sec must be greater than 0")

    candidates: list[dict[str, Any]] = []
    content_channel = _content_channel(transcript)
    alignment_index = _alignment_index(script_highlight_alignment)
    for window in _segment_windows(transcript.segments, max_window_size=max_window_size):
        duration = round(window[-1].end_time - window[0].start_time, 6)
        if max_duration_sec is not None and duration > max_duration_sec and target_window_sec is not None:
            candidates.extend(
                _subwindow_candidates(
                    start_index=len(candidates) + 1,
                    window=window,
                    transcript_duration=transcript.duration,
                    content_channel=content_channel,
                    alignment_index=alignment_index,
                    min_duration_sec=min_duration_sec,
                    max_duration_sec=max_duration_sec,
                    target_window_sec=target_window_sec,
                )
            )
            continue
        if max_duration_sec is not None and duration > max_duration_sec:
            continue
        if min_duration_sec is not None and duration < min_duration_sec:
            continue
        candidates.append(
            _candidate_payload(
                index=len(candidates) + 1,
                window=window,
                transcript_duration=transcript.duration,
                content_channel=content_channel,
                alignment_index=alignment_index,
            )
        )

    return {
        "schema_version": "0.1",
        "status": "succeeded",
        "source": "phase14_2a_candidate_windows",
        "source_transcript_id": transcript.transcript_id,
        "source_video": transcript.source_video,
        "content_channel": content_channel,
        "max_window_size": max_window_size,
        "min_duration_sec": min_duration_sec,
        "max_duration_sec": max_duration_sec,
        "target_window_sec": target_window_sec,
        "script_alignment_source": script_highlight_alignment.get("manifest_path") if script_highlight_alignment else None,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "warnings": [],
        "errors": [],
        "manifest_path": CANDIDATE_WINDOWS_MANIFEST,
    }


def _segment_windows(
    segments: list[TranscriptSegment],
    *,
    max_window_size: int,
) -> list[list[TranscriptSegment]]:
    windows: list[list[TranscriptSegment]] = []
    capped_window_size = min(max_window_size, len(segments))
    for start_index in range(len(segments)):
        for window_size in range(1, capped_window_size + 1):
            end_index = start_index + window_size
            if end_index > len(segments):
                break
            windows.append(segments[start_index:end_index])
    return windows


def _candidate_payload(
    *,
    index: int,
    window: list[TranscriptSegment],
    transcript_duration: float | None,
    content_channel: str,
    alignment_index: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    start_sec = window[0].start_time
    end_sec = window[-1].end_time
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
    if script_alignment is not None:
        evidence["script_highlight_id"] = script_alignment["highlight_id"]
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


def _subwindow_candidates(
    *,
    start_index: int,
    window: list[TranscriptSegment],
    transcript_duration: float | None,
    content_channel: str,
    alignment_index: list[dict[str, Any]],
    min_duration_sec: float | None,
    max_duration_sec: float,
    target_window_sec: float | None,
) -> list[dict[str, Any]]:
    segment_start = window[0].start_time
    segment_end = window[-1].end_time
    target = min(target_window_sec or max_duration_sec, max_duration_sec)
    candidates: list[dict[str, Any]] = []
    cursor = segment_start
    while cursor < segment_end:
        end = min(cursor + target, segment_end)
        duration = round(end - cursor, 6)
        if min_duration_sec is not None and duration < min_duration_sec:
            if candidates:
                previous = candidates[-1]
                previous["end_sec"] = segment_end
                previous["duration_sec"] = round(previous["end_sec"] - previous["start_sec"], 6)
            break
        if duration <= 0:
            break
        candidates.append(
            _subwindow_payload(
                index=start_index + len(candidates),
                window=window,
                start_sec=round(cursor, 6),
                end_sec=round(end, 6),
                transcript_duration=transcript_duration,
                content_channel=content_channel,
                alignment_index=alignment_index,
            )
        )
        cursor = end
    return candidates


def _subwindow_payload(
    *,
    index: int,
    window: list[TranscriptSegment],
    start_sec: float,
    end_sec: float,
    transcript_duration: float | None,
    content_channel: str,
    alignment_index: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = _candidate_payload(
        index=index,
        window=window,
        transcript_duration=transcript_duration,
        content_channel=content_channel,
        alignment_index=alignment_index,
    )
    payload["source"] = "transcript_subwindow"
    payload["start_sec"] = start_sec
    payload["end_sec"] = end_sec
    payload["duration_sec"] = round(end_sec - start_sec, 6)
    payload["evidence"]["boundary_strategy"] = "fixed_duration_split"
    payload["evidence"]["source_window_start_sec"] = window[0].start_time
    payload["evidence"]["source_window_end_sec"] = window[-1].end_time
    return payload


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


def _content_channel(transcript: Transcript) -> str:
    for key in ("content_channel", "transcript_source", "source_type"):
        value = transcript.metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "transcript"


def _alignment_index(script_highlight_alignment: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(script_highlight_alignment, dict):
        return []
    alignments = script_highlight_alignment.get("alignments")
    if not isinstance(alignments, list):
        return []
    indexed: list[dict[str, Any]] = []
    for item in alignments:
        if not isinstance(item, dict) or item.get("status") not in {None, "aligned"}:
            continue
        start = _optional_float(item.get("start_time"))
        end = _optional_float(item.get("end_time"))
        if start is None or end is None or end <= start:
            continue
        indexed.append(
            {
                "highlight_id": str(item.get("highlight_id") or ""),
                "confidence": _optional_float(item.get("confidence")) or 0.0,
                "matched_segment_ids": [str(value) for value in item.get("matched_segment_ids") or []],
                "start_time": start,
                "end_time": end,
            }
        )
    return indexed


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


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
