from __future__ import annotations

import pytest

from agentflow_studio.candidate_sop import generate_candidate_windows
from agentflow_studio.schemas import Transcript


def test_generate_candidate_windows_attaches_nearest_audio_boundary_evidence() -> None:
    transcript = Transcript.model_validate(
        {
            "transcript_id": "demo_transcript",
            "duration": 12.0,
            "segments": [
                {
                    "segment_id": "seg_001",
                    "start_time": 1.8,
                    "end_time": 6.0,
                    "text": "The hook starts near a silence boundary.",
                },
            ],
        }
    )
    boundary_manifest = {
        "status": "succeeded",
        "manifest_path": "boundary_signal_manifest.json",
        "boundary_points": [
            {"time_sec": 2.0, "kind": "silence_end", "confidence": 0.93},
            {"time_sec": 5.7, "kind": "silence_start", "confidence": 0.88},
        ],
    }

    manifest = generate_candidate_windows(
        transcript,
        max_window_size=1,
        min_duration_sec=4.1,
        max_duration_sec=6.0,
        boundary_signal_manifest=boundary_manifest,
    )

    evidence = manifest["candidates"][0]["evidence"]
    assert evidence["audio_boundary"] == {
        "source": "boundary_signal_manifest.json",
        "start": {"time_sec": 2.0, "kind": "silence_end", "confidence": 0.93, "distance_sec": 0.2},
        "end": {"time_sec": 5.7, "kind": "silence_start", "confidence": 0.88, "distance_sec": 0.3},
    }


def test_generate_candidate_windows_refines_short_window_with_audio_boundaries() -> None:
    transcript = Transcript.model_validate(
        {
            "transcript_id": "demo_transcript",
            "duration": 12.0,
            "segments": [
                {
                    "segment_id": "seg_001",
                    "start_time": 1.8,
                    "end_time": 6.1,
                    "text": "The best promo beat starts and ends near silence.",
                },
            ],
        }
    )
    boundary_manifest = {
        "status": "succeeded",
        "manifest_path": "boundary_signal_manifest.json",
        "boundary_points": [
            {"time_sec": 2.0, "kind": "silence_end", "confidence": 0.93},
            {"time_sec": 5.9, "kind": "silence_start", "confidence": 0.88},
        ],
    }

    manifest = generate_candidate_windows(
        transcript,
        max_window_size=1,
        min_duration_sec=3.5,
        max_duration_sec=6.0,
        boundary_signal_manifest=boundary_manifest,
    )

    candidate = manifest["candidates"][0]
    assert candidate["start_sec"] == 2.0
    assert candidate["end_sec"] == 5.9
    assert candidate["duration_sec"] == 3.9
    assert candidate["evidence"]["boundary_strategy"] == "audio_boundary_refined"
    assert candidate["evidence"]["audio_boundary_refinement"]["applied"] == ["start", "end"]


def test_generate_candidate_windows_rejects_invalid_window_size() -> None:
    transcript = Transcript.model_validate(
        {
            "transcript_id": "demo_transcript",
            "segments": [{"segment_id": "seg_001", "start_time": 0.0, "end_time": 1.0, "text": "one"}],
        }
    )

    with pytest.raises(ValueError, match="max_window_size"):
        generate_candidate_windows(transcript, max_window_size=0)


def test_generate_candidate_windows_defaults_to_generic_transcript_channel() -> None:
    transcript = Transcript.model_validate(
        {
            "transcript_id": "ocr_transcript",
            "segments": [{"segment_id": "ocr_seg_001", "start_time": 3.0, "end_time": 5.0, "text": "screen text"}],
        }
    )

    manifest = generate_candidate_windows(transcript)

    assert manifest["content_channel"] == "transcript"
    assert manifest["candidates"][0]["evidence"]["content_channel"] == "transcript"
