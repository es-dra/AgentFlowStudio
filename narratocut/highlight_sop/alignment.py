from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from narratocut.schemas import HighlightPlan, HighlightSegment, Transcript, TranscriptSegment


ALIGNMENT_MANIFEST = "script_highlight_alignment.json"
ALIGNER_NAME = "phase14_script_highlight_transcript_aligner"
DEFAULT_MIN_CONFIDENCE = 0.25


@dataclass(frozen=True)
class ScriptHighlightAlignmentResult:
    highlight_plan: HighlightPlan | None
    manifest: dict[str, Any]


def align_script_highlights_to_transcript(
    script_plan: HighlightPlan,
    transcript: Transcript,
    *,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> ScriptHighlightAlignmentResult:
    if script_plan.input_mode != "script_only":
        raise ValueError("script_plan must be script_only")
    if not 0.0 <= min_confidence <= 1.0:
        raise ValueError("min_confidence must be between 0 and 1")

    aligned: list[HighlightSegment] = []
    alignments: list[dict[str, Any]] = []
    warnings: list[str] = []

    for highlight in script_plan.highlights:
        match = _best_segment_match(highlight, transcript.segments)
        record = _alignment_record(highlight.highlight_id, match)
        if match["confidence"] < min_confidence:
            record["status"] = "skipped"
            warning = f"alignment_low_confidence: {highlight.highlight_id}"
            record["warning"] = warning
            warnings.append(warning)
            alignments.append(record)
            continue
        record["status"] = "aligned"
        alignments.append(record)
        aligned.append(_aligned_highlight(highlight, match))

    manifest = {
        "schema_version": "0.1",
        "status": "succeeded" if len(aligned) == len(script_plan.highlights) else "partial",
        "source_highlight_plan_id": script_plan.plan_id,
        "source_transcript_id": transcript.transcript_id,
        "source_video": transcript.source_video,
        "min_confidence": min_confidence,
        "aligned_count": len(aligned),
        "skipped_count": len(script_plan.highlights) - len(aligned),
        "alignments": alignments,
        "warnings": warnings,
        "errors": [],
        "manifest_path": ALIGNMENT_MANIFEST,
    }
    if not aligned:
        return ScriptHighlightAlignmentResult(highlight_plan=None, manifest=manifest)

    timestamped = HighlightPlan(
        plan_id=f"aligned_{script_plan.plan_id}",
        input_mode="timestamped_transcript",
        source_id=transcript.transcript_id,
        roi_profile=script_plan.roi_profile,
        highlights=aligned,
        summary=script_plan.summary,
        warnings=warnings,
        metadata={
            **script_plan.metadata,
            "source": ALIGNER_NAME,
            "source_highlight_plan_id": script_plan.plan_id,
            "source_transcript_id": transcript.transcript_id,
            "source_video": transcript.source_video,
        },
    )
    return ScriptHighlightAlignmentResult(highlight_plan=timestamped, manifest=manifest)


def _best_segment_match(
    highlight: HighlightSegment,
    segments: list[TranscriptSegment],
) -> dict[str, Any]:
    best: dict[str, Any] | None = None
    highlight_tokens = _tokens(highlight.text)
    for candidate_segments in _candidate_segment_windows(segments):
        matched_text = " ".join(segment.text for segment in candidate_segments)
        confidence = _similarity(highlight_tokens, _tokens(matched_text))
        candidate = {
            "confidence": confidence,
            "matched_segment_ids": [segment.segment_id for segment in candidate_segments],
            "start_time": candidate_segments[0].start_time,
            "end_time": candidate_segments[-1].end_time,
            "matched_text": matched_text,
        }
        if best is None or confidence > best["confidence"] or (
            confidence == best["confidence"]
            and len(candidate["matched_segment_ids"]) > len(best["matched_segment_ids"])
        ):
            best = candidate
    if best is None:
        return {
            "confidence": 0.0,
            "matched_segment_ids": [],
            "start_time": None,
            "end_time": None,
            "matched_text": "",
        }
    return best


def _candidate_segment_windows(segments: list[TranscriptSegment]) -> list[list[TranscriptSegment]]:
    windows: list[list[TranscriptSegment]] = []
    max_window_size = min(4, len(segments))
    for start_index in range(len(segments)):
        for window_size in range(1, max_window_size + 1):
            end_index = start_index + window_size
            if end_index > len(segments):
                break
            windows.append(segments[start_index:end_index])
    return windows


def _aligned_highlight(highlight: HighlightSegment, match: dict[str, Any]) -> HighlightSegment:
    metadata = dict(highlight.metadata)
    metadata["alignment"] = {
        "source": ALIGNER_NAME,
        "confidence": round(float(match["confidence"]), 6),
        "matched_segment_ids": list(match["matched_segment_ids"]),
        "matched_text": match["matched_text"],
    }
    return highlight.model_copy(
        update={
            "source_type": "transcript",
            "source_segment_ids": list(match["matched_segment_ids"]),
            "start_time": match["start_time"],
            "end_time": match["end_time"],
            "suggested_duration": round(float(match["end_time"]) - float(match["start_time"]), 6),
            "metadata": metadata,
        }
    )


def _alignment_record(highlight_id: str, match: dict[str, Any]) -> dict[str, Any]:
    return {
        "highlight_id": highlight_id,
        "confidence": round(float(match["confidence"]), 6),
        "matched_segment_ids": list(match["matched_segment_ids"]),
        "start_time": match["start_time"],
        "end_time": match["end_time"],
    }


def _similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    overlap = len(left & right)
    if overlap == 0:
        return 0.0
    return overlap / max(len(left), len(right))


def _tokens(text: str) -> set[str]:
    normalized = text.lower()
    tokens = {
        token
        for token in re.findall(r"[A-Za-z0-9]+", normalized)
        if len(token) > 1 and token not in _STOPWORDS
    }
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", normalized)
    tokens.update(chinese_chars)
    tokens.update("".join(pair) for pair in zip(chinese_chars, chinese_chars[1:]))
    return tokens


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "before",
    "but",
    "for",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
}
