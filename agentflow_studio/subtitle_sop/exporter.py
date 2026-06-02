from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentflow_studio.schemas import SubtitleCue, SubtitleManifest, Transcript


SUBTITLE_MANIFEST = "subtitle_manifest.json"
SUBTITLES_SRT = "subtitles.srt"


@dataclass(frozen=True)
class SubtitleExport:
    srt_text: str
    manifest: SubtitleManifest


def transcript_to_srt(transcript: Transcript | dict[str, Any]) -> str:
    normalized = _normalize_transcript(transcript)
    cues = _build_cues(normalized)
    return "\n\n".join(_format_srt_block(cue) for cue in cues) + "\n"


def build_subtitle_export(
    transcript: Transcript | dict[str, Any],
    *,
    subtitle_path: str = SUBTITLES_SRT,
) -> SubtitleExport:
    normalized = _normalize_transcript(transcript)
    cues = _build_cues(normalized)
    srt_text = "\n\n".join(_format_srt_block(cue) for cue in cues) + "\n"
    manifest = SubtitleManifest(
        status="succeeded",
        subtitle_path=subtitle_path,
        source_transcript_id=normalized.transcript_id,
        source_video=normalized.source_video,
        language=normalized.language,
        segment_count=len(cues),
        duration_sec=_duration_sec(normalized, cues),
        cues=cues,
        errors=[],
        warnings=[],
        manifest_path=SUBTITLE_MANIFEST,
    )
    return SubtitleExport(srt_text=srt_text, manifest=manifest)


def build_failed_subtitle_manifest(
    transcript: Transcript | dict[str, Any] | None,
    *,
    subtitle_path: str = SUBTITLES_SRT,
    errors: list[str] | None = None,
) -> SubtitleManifest:
    normalized = _normalize_transcript(transcript) if transcript is not None else None
    return SubtitleManifest(
        status="failed",
        subtitle_path=subtitle_path,
        source_transcript_id=normalized.transcript_id if normalized else None,
        source_video=normalized.source_video if normalized else None,
        language=normalized.language if normalized else None,
        segment_count=0,
        duration_sec=normalized.duration if normalized else None,
        cues=[],
        errors=errors or ["subtitle_export_failed"],
        warnings=[],
        manifest_path=SUBTITLE_MANIFEST,
    )


def _normalize_transcript(transcript: Transcript | dict[str, Any]) -> Transcript:
    if isinstance(transcript, Transcript):
        return transcript
    return Transcript.model_validate(transcript)


def _build_cues(transcript: Transcript) -> list[SubtitleCue]:
    cues: list[SubtitleCue] = []
    previous_end: float | None = None
    for index, segment in enumerate(transcript.segments, start=1):
        text = _normalize_text(segment.text)
        if not text:
            raise ValueError("subtitle_text_empty")
        if previous_end is not None and segment.start_time < previous_end:
            raise ValueError("subtitle_segments_not_monotonic")
        cue = SubtitleCue(
            index=index,
            segment_id=segment.segment_id,
            start_time=segment.start_time,
            end_time=segment.end_time,
            start_timestamp=format_srt_timestamp(segment.start_time),
            end_timestamp=format_srt_timestamp(segment.end_time),
            text=text,
        )
        cues.append(cue)
        previous_end = segment.end_time
    return cues


def format_srt_timestamp(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_srt_block(cue: SubtitleCue) -> str:
    return f"{cue.index}\n{cue.start_timestamp} --> {cue.end_timestamp}\n{cue.text}"


def _normalize_text(value: str) -> str:
    lines = [line.strip() for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return "\n".join(line for line in lines if line)


def _duration_sec(transcript: Transcript, cues: list[SubtitleCue]) -> float | None:
    if transcript.duration is not None:
        return transcript.duration
    if not cues:
        return None
    return max(cue.end_time for cue in cues)
