from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from narratocut.schemas import Transcript


OCR_TRANSCRIPT_MANIFEST = "ocr_transcript_manifest.json"


def build_ocr_transcript_from_frames(
    frames: list[dict[str, Any]],
    *,
    video_path: str | None = None,
    language: str | None = None,
    frame_interval_sec: float = 1.0,
    dedupe_similarity: float = 0.85,
    merge_gap_sec: float = 0.8,
    min_text_chars: int = 2,
) -> tuple[Transcript, dict[str, Any]]:
    if frame_interval_sec <= 0:
        raise ValueError("frame_interval_sec must be greater than 0")
    if not 0 <= dedupe_similarity <= 1:
        raise ValueError("dedupe_similarity must be between 0 and 1")
    if merge_gap_sec < 0:
        raise ValueError("merge_gap_sec must be non-negative")
    if min_text_chars <= 0:
        raise ValueError("min_text_chars must be greater than 0")

    normalized_frames, dropped_count = _normalized_frames(frames, min_text_chars=min_text_chars)
    groups = _group_frames(
        normalized_frames,
        frame_interval_sec=frame_interval_sec,
        dedupe_similarity=dedupe_similarity,
        merge_gap_sec=merge_gap_sec,
    )
    segments = [_segment_payload(index, group, frame_interval_sec) for index, group in enumerate(groups, start=1)]
    if not segments:
        raise ValueError("ocr_transcript_empty")

    transcript = Transcript.model_validate(
        {
            "transcript_id": _transcript_id(video_path),
            "source_video": video_path,
            "language": language,
            "duration": max(segment["end_time"] for segment in segments),
            "segments": segments,
            "metadata": {
                "content_channel": "ocr_subtitle",
                "transcript_source": "video_subtitle_ocr",
                "frame_interval_sec": frame_interval_sec,
                "dedupe_similarity": dedupe_similarity,
                "merge_gap_sec": merge_gap_sec,
            },
        }
    )
    manifest = {
        "schema_version": "0.1",
        "status": "succeeded",
        "source": "video_subtitle_ocr_timeline",
        "source_video": video_path,
        "transcript_path": "ocr_transcript.json",
        "content_channel": "ocr_subtitle",
        "frame_count": len(frames),
        "dropped_frame_count": dropped_count,
        "segment_count": len(transcript.segments),
        "frame_interval_sec": frame_interval_sec,
        "dedupe_similarity": dedupe_similarity,
        "merge_gap_sec": merge_gap_sec,
        "min_text_chars": min_text_chars,
        "warnings": [],
        "errors": [],
        "manifest_path": OCR_TRANSCRIPT_MANIFEST,
    }
    return transcript, manifest


def _normalized_frames(frames: list[dict[str, Any]], *, min_text_chars: int) -> tuple[list[dict[str, Any]], int]:
    normalized: list[dict[str, Any]] = []
    dropped = 0
    for frame in sorted(frames, key=lambda item: float(item.get("time_sec") or 0.0)):
        text = _clean_text(str(frame.get("text") or ""))
        if len(_compact(text)) < min_text_chars:
            dropped += 1
            continue
        normalized.append(
            {
                "time_sec": float(frame.get("time_sec") or 0.0),
                "text": text,
                "normalized_text": _compact(text),
                "confidence": _confidence(frame.get("confidence")),
            }
        )
    return normalized, dropped


def _group_frames(
    frames: list[dict[str, Any]],
    *,
    frame_interval_sec: float,
    dedupe_similarity: float,
    merge_gap_sec: float,
) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_texts: list[str] = []
    for frame in frames:
        if not current:
            current = [frame]
            current_texts = [frame["normalized_text"]]
            continue
        previous = current[-1]
        gap = float(frame["time_sec"]) - float(previous["time_sec"]) - frame_interval_sec
        similar = _similarity(frame["normalized_text"], previous["normalized_text"]) >= dedupe_similarity
        if gap <= merge_gap_sec:
            if not similar and all(frame["normalized_text"] != text for text in current_texts):
                current_texts.append(frame["normalized_text"])
            current.append(frame)
            continue
        groups.append(current)
        current = [frame]
        current_texts = [frame["normalized_text"]]
    if current:
        groups.append(current)
    return groups


def _segment_payload(index: int, group: list[dict[str, Any]], frame_interval_sec: float) -> dict[str, Any]:
    unique_texts: list[str] = []
    for frame in group:
        if not unique_texts or _similarity(_compact(unique_texts[-1]), frame["normalized_text"]) < 0.85:
            unique_texts.append(str(frame["text"]))
    confidence_values = [float(frame["confidence"]) for frame in group if frame["confidence"] is not None]
    return {
        "segment_id": f"ocr_seg_{index:03d}",
        "start_time": float(group[0]["time_sec"]),
        "end_time": round(float(group[-1]["time_sec"]) + frame_interval_sec, 6),
        "text": " ".join(unique_texts),
        "confidence": round(sum(confidence_values) / len(confidence_values), 6) if confidence_values else None,
        "metadata": {
            "content_channel": "ocr_subtitle",
            "source_frames": [
                {
                    "time_sec": frame["time_sec"],
                    "text": frame["text"],
                    "confidence": frame["confidence"],
                }
                for frame in group
            ],
        },
    }


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u3000", " ")).strip()


def _compact(value: str) -> str:
    return re.sub(r"[\s，。！？,.!?：:；;、\"'“”‘’（）()\[\]【】]+", "", value).lower()


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    return SequenceMatcher(None, left, right).ratio()


def _confidence(value: Any) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    return min(max(numeric, 0.0), 1.0)


def _transcript_id(video_path: str | None) -> str:
    if not video_path:
        return "ocr_transcript"
    stem = Path(video_path).stem
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("_") or "video"
    return f"ocr_transcript_{safe}"
