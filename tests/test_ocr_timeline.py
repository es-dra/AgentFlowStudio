from __future__ import annotations

from agentflow_studio.ocr_sop import build_ocr_transcript_from_frames


def test_build_ocr_transcript_dedupes_and_merges_frame_text() -> None:
    transcript, manifest = build_ocr_transcript_from_frames(
        [
            {"time_sec": 1.0, "text": "90%的人都剪错了", "confidence": 0.91},
            {"time_sec": 1.5, "text": "90% 的人都剪错了", "confidence": 0.89},
            {"time_sec": 2.0, "text": "因为他们只看开头", "confidence": 0.86},
            {"time_sec": 4.0, "text": "最后这个反转才是关键", "confidence": 0.88},
        ],
        video_path="data/raw/demo.mp4",
        language="zh",
        frame_interval_sec=0.5,
        dedupe_similarity=0.85,
        merge_gap_sec=0.8,
        min_text_chars=3,
    )

    assert transcript.transcript_id == "ocr_transcript_demo"
    assert transcript.source_video == "data/raw/demo.mp4"
    assert transcript.metadata["content_channel"] == "ocr_subtitle"
    assert len(transcript.segments) == 2
    assert transcript.segments[0].start_time == 1.0
    assert transcript.segments[0].end_time == 2.5
    assert "90%的人都剪错了" in transcript.segments[0].text
    assert "因为他们只看开头" in transcript.segments[0].text
    assert transcript.segments[0].metadata["source_frames"][0]["time_sec"] == 1.0
    assert manifest["status"] == "succeeded"
    assert manifest["segment_count"] == 2
    assert manifest["frame_count"] == 4


def test_build_ocr_transcript_filters_short_or_empty_text() -> None:
    transcript, manifest = build_ocr_transcript_from_frames(
        [
            {"time_sec": 0.0, "text": "片", "confidence": 0.8},
            {"time_sec": 1.0, "text": "真正的问题不是剪辑", "confidence": 0.9},
        ],
        min_text_chars=3,
    )

    assert len(transcript.segments) == 1
    assert transcript.segments[0].text == "真正的问题不是剪辑"
    assert manifest["dropped_frame_count"] == 1
