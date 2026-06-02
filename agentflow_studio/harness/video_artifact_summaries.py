from __future__ import annotations

from typing import Any

from agentflow_studio.harness.video_artifact_checks import (
    segment_time_range_valid,
    segments_monotonic,
    text_non_empty,
    transcript_provider,
)


def audio_summary(audio_manifest: dict[str, Any] | None) -> dict[str, Any]:
    metadata = _metadata(audio_manifest)
    return {
        "artifact_type": "audio_manifest",
        "status": audio_manifest.get("status") if audio_manifest else None,
        "extraction_mode": audio_manifest.get("extraction_mode") if audio_manifest else None,
        "executed": metadata.get("executed"),
        "has_ffmpeg_command": bool(metadata.get("ffmpeg_command")),
        "audio_path": audio_manifest.get("audio_path") if audio_manifest else None,
    }


def transcript_summary(transcript: dict[str, Any] | None) -> dict[str, Any]:
    segments = transcript.get("segments") if isinstance(transcript, dict) else None
    segment_list = segments if isinstance(segments, list) else []
    return {
        "artifact_type": "transcript",
        "transcript_id": transcript.get("transcript_id") if transcript else None,
        "source_video": transcript.get("source_video") if transcript else None,
        "language": transcript.get("language") if transcript else None,
        "provider": transcript_provider(transcript),
        "segment_count": len(segment_list),
        "duration": transcript.get("duration") if transcript else None,
        "timestamp_ranges_valid": bool(segment_list) and all(segment_time_range_valid(item) for item in segment_list),
        "segments_monotonic": bool(segment_list) and segments_monotonic(segment_list),
        "text_non_empty": bool(segment_list) and all(
            text_non_empty(item.get("text")) for item in segment_list if isinstance(item, dict)
        ),
    }


def highlight_plan_summary(highlight_plan: dict[str, Any] | None) -> dict[str, Any] | None:
    if highlight_plan is None:
        return None
    highlights = highlight_plan.get("highlights")
    return {
        "artifact_type": "highlight_plan",
        "input_mode": highlight_plan.get("input_mode"),
        "highlight_count": len(highlights) if isinstance(highlights, list) else 0,
    }


def clip_plan_summary(clip_plan: dict[str, Any] | None) -> dict[str, Any] | None:
    if clip_plan is None:
        return None
    segments = clip_plan.get("segments")
    return {
        "artifact_type": "clip_plan",
        "segment_count": len(segments) if isinstance(segments, list) else 0,
    }


def _metadata(audio_manifest: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(audio_manifest, dict) and isinstance(audio_manifest.get("metadata"), dict):
        return audio_manifest["metadata"]
    return {}
