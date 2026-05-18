from __future__ import annotations

from typing import Any

from narratocut.schemas import SubtitleCue, SubtitleManifest, Transcript, TranscriptSegment
from narratocut.subtitle_sop.exporter import SUBTITLE_MANIFEST, SUBTITLES_SRT, SubtitleExport, format_srt_timestamp


def build_clip_timeline_subtitle_export(
    transcript: Transcript | dict[str, Any],
    real_slice_manifest: dict[str, Any],
    *,
    final_video_manifest: dict[str, Any] | None = None,
    subtitle_path: str = SUBTITLES_SRT,
) -> SubtitleExport:
    normalized = transcript if isinstance(transcript, Transcript) else Transcript.model_validate(transcript)
    clips = _succeeded_clips(real_slice_manifest)
    final_duration = _final_duration(final_video_manifest, clips)
    cues, warnings = _build_final_timeline_cues(normalized, clips, final_duration)
    if not cues:
        raise ValueError("subtitle_timeline_has_no_matching_transcript_segments")

    srt_text = "\n\n".join(_format_srt_block(cue) for cue in cues) + "\n"
    manifest = SubtitleManifest(
        status="succeeded",
        timeline="final_video",
        subtitle_path=subtitle_path,
        source_transcript_id=normalized.transcript_id,
        source_video=normalized.source_video or real_slice_manifest.get("source_video"),
        language=normalized.language,
        segment_count=len(cues),
        duration_sec=final_duration,
        cues=cues,
        errors=[],
        warnings=warnings,
        manifest_path=SUBTITLE_MANIFEST,
    )
    return SubtitleExport(srt_text=srt_text, manifest=manifest)


def _succeeded_clips(real_slice_manifest: dict[str, Any]) -> list[dict[str, float | str]]:
    clips: list[dict[str, float | str]] = []
    output_offset = 0.0
    for clip in real_slice_manifest.get("clips", []):
        if not isinstance(clip, dict) or clip.get("status") not in {"succeeded", "passed"}:
            continue
        start = _required_float(clip, "start_sec")
        end = _required_float(clip, "end_sec")
        duration = float(clip.get("duration_sec") or end - start)
        if end <= start or duration <= 0:
            continue
        clips.append(
            {
                "clip_id": str(clip.get("clip_id") or ""),
                "source_start": start,
                "source_end": end,
                "output_start": output_offset,
                "output_end": output_offset + duration,
            }
        )
        output_offset += duration
    return clips


def _build_final_timeline_cues(
    transcript: Transcript,
    clips: list[dict[str, float | str]],
    final_duration: float,
) -> tuple[list[SubtitleCue], list[str]]:
    cues: list[SubtitleCue] = []
    warnings: list[str] = []
    clipped = _clips_total_duration(clips) > final_duration
    for clip in clips:
        source_start = float(clip["source_start"])
        source_end = float(clip["source_end"])
        output_start = float(clip["output_start"])
        for segment in transcript.segments:
            mapped = _map_segment(segment, source_start, source_end, output_start, final_duration)
            if mapped is None:
                continue
            start, end = mapped
            if end >= final_duration and _segment_exceeds_final(segment, source_start, output_start, final_duration):
                clipped = True
            if end <= start:
                continue
            cues.append(
                SubtitleCue(
                    index=len(cues) + 1,
                    segment_id=segment.segment_id,
                    start_time=round(start, 6),
                    end_time=round(end, 6),
                    start_timestamp=format_srt_timestamp(start),
                    end_timestamp=format_srt_timestamp(end),
                    text=segment.text.strip(),
                )
            )
    if clipped:
        warnings.append("clipped_to_final_duration")
    return cues, warnings


def _map_segment(
    segment: TranscriptSegment,
    source_start: float,
    source_end: float,
    output_start: float,
    final_duration: float,
) -> tuple[float, float] | None:
    overlap_start = max(segment.start_time, source_start)
    overlap_end = min(segment.end_time, source_end)
    if overlap_end <= overlap_start:
        return None
    mapped_start = output_start + (overlap_start - source_start)
    mapped_end = output_start + (overlap_end - source_start)
    if mapped_start >= final_duration:
        return None
    return mapped_start, min(mapped_end, final_duration)


def _segment_exceeds_final(
    segment: TranscriptSegment,
    source_start: float,
    output_start: float,
    final_duration: float,
) -> bool:
    mapped_end = output_start + (segment.end_time - source_start)
    return mapped_end > final_duration


def _final_duration(final_video_manifest: dict[str, Any] | None, clips: list[dict[str, float | str]]) -> float:
    if final_video_manifest is not None and final_video_manifest.get("duration_sec") is not None:
        return float(final_video_manifest["duration_sec"])
    return _clips_total_duration(clips)


def _clips_total_duration(clips: list[dict[str, float | str]]) -> float:
    return sum(float(clip["output_end"]) - float(clip["output_start"]) for clip in clips)


def _required_float(item: dict[str, Any], key: str) -> float:
    value = item.get(key)
    if value is None:
        raise ValueError(f"clip_missing_{key}")
    return float(value)


def _format_srt_block(cue: SubtitleCue) -> str:
    return f"{cue.index}\n{cue.start_timestamp} --> {cue.end_timestamp}\n{cue.text}"
