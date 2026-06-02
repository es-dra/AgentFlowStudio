from __future__ import annotations

from typing import Any

from agentflow_studio.candidate_sop.audio_boundaries import build_boundary_index
from agentflow_studio.candidate_sop.boundaries import elastic_time_windows
from agentflow_studio.candidate_sop.payloads import candidate_payload
from agentflow_studio.schemas import Transcript, TranscriptSegment


CANDIDATE_WINDOWS_MANIFEST = "candidate_windows.json"


def generate_candidate_windows(
    transcript: Transcript,
    *,
    max_window_size: int = 4,
    min_duration_sec: float | None = None,
    max_duration_sec: float | None = None,
    target_window_sec: float | None = None,
    script_highlight_alignment: dict[str, Any] | None = None,
    boundary_signal_manifest: dict[str, Any] | None = None,
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
    boundary_index = build_boundary_index(boundary_signal_manifest)
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
                    boundary_index=boundary_index,
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
            candidate_payload(
                index=len(candidates) + 1,
                window=window,
                transcript_duration=transcript.duration,
                content_channel=content_channel,
                alignment_index=alignment_index,
                boundary_index=boundary_index,
                min_duration_sec=min_duration_sec,
                max_duration_sec=max_duration_sec,
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
        "boundary_signal_source": boundary_signal_manifest.get("manifest_path") if boundary_signal_manifest else None,
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


def _subwindow_candidates(
    *,
    start_index: int,
    window: list[TranscriptSegment],
    transcript_duration: float | None,
    content_channel: str,
    alignment_index: list[dict[str, Any]],
    boundary_index: list[dict[str, Any]],
    min_duration_sec: float | None,
    max_duration_sec: float,
    target_window_sec: float | None,
) -> list[dict[str, Any]]:
    segment_start = window[0].start_time
    segment_end = window[-1].end_time
    windows = elastic_time_windows(
        segment_start,
        segment_end,
        min_duration_sec=min_duration_sec,
        max_duration_sec=max_duration_sec,
        target_window_sec=target_window_sec,
    )
    candidates: list[dict[str, Any]] = []
    for start_sec, end_sec, boundary_strategy in windows:
        candidates.append(
            _subwindow_payload(
                index=start_index + len(candidates),
                window=window,
                start_sec=start_sec,
                end_sec=end_sec,
                transcript_duration=transcript_duration,
                content_channel=content_channel,
                alignment_index=alignment_index,
                boundary_index=boundary_index,
                target_window_sec=target_window_sec,
                boundary_strategy=boundary_strategy,
                min_duration_sec=min_duration_sec,
                max_duration_sec=max_duration_sec,
            )
        )
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
    boundary_index: list[dict[str, Any]],
    target_window_sec: float | None,
    boundary_strategy: str,
    min_duration_sec: float | None,
    max_duration_sec: float,
) -> dict[str, Any]:
    payload = candidate_payload(
        index=index,
        window=window,
        transcript_duration=transcript_duration,
        content_channel=content_channel,
        alignment_index=alignment_index,
        boundary_index=boundary_index,
        candidate_start_sec=start_sec,
        candidate_end_sec=end_sec,
        min_duration_sec=min_duration_sec,
        max_duration_sec=max_duration_sec,
    )
    payload["source"] = "transcript_subwindow"
    if payload["evidence"].get("boundary_strategy") == "audio_boundary_refined":
        payload["evidence"]["base_boundary_strategy"] = boundary_strategy
    else:
        payload["evidence"]["boundary_strategy"] = boundary_strategy
    payload["evidence"]["source_window_start_sec"] = window[0].start_time
    payload["evidence"]["source_window_end_sec"] = window[-1].end_time
    payload["evidence"]["target_duration_sec"] = target_window_sec
    return payload


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

def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
