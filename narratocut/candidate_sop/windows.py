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

    candidates: list[dict[str, Any]] = []
    content_channel = _content_channel(transcript)
    for window in _segment_windows(transcript.segments, max_window_size=max_window_size):
        duration = round(window[-1].end_time - window[0].start_time, 6)
        if min_duration_sec is not None and duration < min_duration_sec:
            continue
        if max_duration_sec is not None and duration > max_duration_sec:
            continue
        candidates.append(
            _candidate_payload(
                index=len(candidates) + 1,
                window=window,
                transcript_duration=transcript.duration,
                content_channel=content_channel,
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
) -> dict[str, Any]:
    start_sec = window[0].start_time
    end_sec = window[-1].end_time
    return {
        "candidate_id": f"cand_{index:03d}",
        "source": "transcript_window",
        "start_sec": start_sec,
        "end_sec": end_sec,
        "duration_sec": round(end_sec - start_sec, 6),
        "segment_ids": [segment.segment_id for segment in window],
        "text": " ".join(segment.text for segment in window),
        "asr_confidence": _average_confidence(window),
        "script_alignment": None,
        "evidence": {
            "window_size": len(window),
            "source_position": _source_position(start_sec, transcript_duration),
            "content_channel": content_channel,
            "keyword_hits": [],
        },
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


def _content_channel(transcript: Transcript) -> str:
    for key in ("content_channel", "transcript_source", "source_type"):
        value = transcript.metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "transcript"
