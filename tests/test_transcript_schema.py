from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentflow_studio.schemas import Transcript, TranscriptSegment


def test_valid_transcript_segment_can_be_created() -> None:
    segment = TranscriptSegment(
        segment_id="seg_001",
        start_time=0.0,
        end_time=4.2,
        text="很多人以为努力就一定会成功，但真相可能完全相反。",
        speaker="speaker_1",
        confidence=0.98,
    )

    assert segment.duration_sec == 4.2
    assert segment.speaker == "speaker_1"


def test_transcript_segment_requires_end_after_start() -> None:
    with pytest.raises(ValidationError):
        TranscriptSegment(
            segment_id="seg_bad",
            start_time=3.0,
            end_time=3.0,
            text="bad range",
        )


def test_transcript_segment_rejects_negative_start_time() -> None:
    with pytest.raises(ValidationError):
        TranscriptSegment(
            segment_id="seg_bad",
            start_time=-0.1,
            end_time=1.0,
            text="bad start",
        )


def test_transcript_segment_confidence_must_be_between_zero_and_one() -> None:
    with pytest.raises(ValidationError):
        TranscriptSegment(
            segment_id="seg_bad",
            start_time=0.0,
            end_time=1.0,
            text="bad confidence",
            confidence=1.2,
        )


def test_transcript_requires_non_empty_segments() -> None:
    with pytest.raises(ValidationError):
        Transcript(transcript_id="tx_empty", segments=[])


def test_valid_transcript_can_be_created() -> None:
    transcript = Transcript(
        transcript_id="demo_transcript_001",
        source_video=None,
        language="zh-CN",
        duration=12.0,
        segments=[
            TranscriptSegment(
                segment_id="seg_001",
                start_time=0.0,
                end_time=4.2,
                text="很多人以为努力就一定会成功，但真相可能完全相反。",
                confidence=0.98,
            ),
            TranscriptSegment(
                segment_id="seg_002",
                start_time=4.2,
                end_time=8.5,
                text="真正决定结果的，往往不是你做了多少，而是你有没有选对方向。",
                confidence=0.97,
            ),
        ],
    )

    assert transcript.segments[1].segment_id == "seg_002"
    assert transcript.duration == 12.0


def test_transcript_rejects_segment_after_declared_duration() -> None:
    with pytest.raises(ValueError, match="duration"):
        Transcript(
            transcript_id="tx_bad_duration",
            duration=3.0,
            segments=[
                TranscriptSegment(
                    segment_id="seg_001",
                    start_time=0.0,
                    end_time=4.2,
                    text="too long",
                )
            ],
        )
