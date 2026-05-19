from __future__ import annotations

import pytest

from narratocut.candidate_sop import generate_candidate_windows
from narratocut.schemas import Transcript


def test_generate_candidate_windows_from_transcript_segment_windows() -> None:
    transcript = Transcript.model_validate(
        {
            "transcript_id": "demo_transcript",
            "source_video": "input.mp4",
            "language": "zh",
            "duration": 20.0,
            "metadata": {"content_channel": "asr_transcript"},
            "segments": [
                {"segment_id": "seg_001", "start_time": 0.0, "end_time": 2.0, "text": "开场提出问题"},
                {"segment_id": "seg_002", "start_time": 2.0, "end_time": 5.0, "text": "主角遭遇冲突"},
                {"segment_id": "seg_003", "start_time": 5.0, "end_time": 9.0, "text": "真相突然反转"},
                {"segment_id": "seg_004", "start_time": 9.0, "end_time": 12.0, "text": "给出行动承诺"},
            ],
        }
    )

    manifest = generate_candidate_windows(transcript, max_window_size=3)

    assert manifest["schema_version"] == "0.1"
    assert manifest["status"] == "succeeded"
    assert manifest["source_transcript_id"] == "demo_transcript"
    assert manifest["source_video"] == "input.mp4"
    assert manifest["content_channel"] == "asr_transcript"
    assert manifest["candidate_count"] == 9
    first = manifest["candidates"][0]
    assert first == {
        "candidate_id": "cand_001",
        "source": "transcript_window",
        "start_sec": 0.0,
        "end_sec": 2.0,
        "duration_sec": 2.0,
        "segment_ids": ["seg_001"],
        "text": "开场提出问题",
        "asr_confidence": None,
        "script_alignment": None,
        "evidence": {
            "window_size": 1,
            "source_position": "early",
            "content_channel": "asr_transcript",
            "keyword_hits": [],
        },
    }
    three_segment = manifest["candidates"][2]
    assert three_segment["segment_ids"] == ["seg_001", "seg_002", "seg_003"]
    assert three_segment["duration_sec"] == 9.0
    assert "真相突然反转" in three_segment["text"]


def test_generate_candidate_windows_respects_duration_bounds() -> None:
    transcript = Transcript.model_validate(
        {
            "transcript_id": "demo_transcript",
            "duration": 30.0,
            "segments": [
                {"segment_id": "seg_001", "start_time": 0.0, "end_time": 1.0, "text": "too short"},
                {"segment_id": "seg_002", "start_time": 1.0, "end_time": 7.0, "text": "good middle"},
                {"segment_id": "seg_003", "start_time": 7.0, "end_time": 20.0, "text": "too long alone"},
            ],
        }
    )

    manifest = generate_candidate_windows(
        transcript,
        max_window_size=2,
        min_duration_sec=2.0,
        max_duration_sec=8.0,
    )

    assert [candidate["segment_ids"] for candidate in manifest["candidates"]] == [
        ["seg_001", "seg_002"],
        ["seg_002"],
    ]
    assert manifest["candidate_count"] == 2


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
