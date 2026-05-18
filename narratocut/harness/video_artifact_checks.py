from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from narratocut.schemas import Transcript


def audio_execution_is_consistent(mode: str, status: str, executed: object, command: object) -> bool:
    if mode == "mock":
        return status == "mocked" and executed is False and command == []
    if mode == "ffmpeg" and status == "succeeded":
        return executed is True and isinstance(command, list) and len(command) > 0
    return status != "succeeded"


def transcript_schema_valid(transcript: dict[str, Any]) -> bool:
    try:
        Transcript.model_validate(transcript)
    except ValidationError:
        return False
    return True


def segment_time_range_valid(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    start = number(item.get("start_time"))
    end = number(item.get("end_time"))
    return start is not None and end is not None and start >= 0.0 and end > start


def segments_monotonic(segments: list[Any]) -> bool:
    previous_end: float | None = None
    for item in segments:
        if not segment_time_range_valid(item):
            return False
        start = float(item["start_time"])
        end = float(item["end_time"])
        if previous_end is not None and start < previous_end:
            return False
        previous_end = end
    return True


def transcript_segment_ids(transcript: dict[str, Any] | None) -> set[str]:
    segments = transcript.get("segments") if isinstance(transcript, dict) else None
    if not isinstance(segments, list):
        return set()
    return {
        str(item.get("segment_id"))
        for item in segments
        if isinstance(item, dict) and text_non_empty(item.get("segment_id"))
    }


def all_source_ids_known(items: list[Any], transcript_ids: set[str]) -> bool:
    return all(source_ids(item) and source_ids(item).issubset(transcript_ids) for item in items if isinstance(item, dict))


def all_clip_source_ids_known(items: list[Any], transcript_ids: set[str]) -> bool:
    for item in items:
        metadata = item.get("metadata") if isinstance(item, dict) else None
        ids = source_ids(metadata)
        if not ids or not ids.issubset(transcript_ids):
            return False
    return True


def source_ids(item: Any) -> set[str]:
    values = item.get("source_segment_ids") if isinstance(item, dict) else None
    return {str(value) for value in values} if isinstance(values, list) and values else set()


def transcript_provider(transcript: dict[str, Any] | None) -> str | None:
    metadata = transcript.get("metadata") if isinstance(transcript, dict) else None
    provider = metadata.get("asr_provider") if isinstance(metadata, dict) else None
    return str(provider) if text_non_empty(provider) else None


def number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def text_non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
