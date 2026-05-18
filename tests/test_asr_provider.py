from __future__ import annotations

import json

import pytest

from narratocut.asr_sop import MockASRProvider, normalize_transcript_payload
from narratocut.audio_sop import AudioArtifact
from narratocut.schemas import Transcript


def test_mock_asr_provider_loads_fixture_as_valid_timestamped_transcript(tmp_path) -> None:
    fixture_path = tmp_path / "transcript_fixture.json"
    fixture_path.write_text(json.dumps(_transcript_payload(source_video=None)), encoding="utf-8")
    audio_artifact = AudioArtifact(
        source_video="input.mp4",
        audio_path="audio/audio.wav",
        status="mocked",
        extraction_mode="mock",
        sample_rate=16000,
        channels=1,
        codec="pcm_s16le",
    )

    transcript = MockASRProvider(fixture_path=fixture_path).transcribe(audio_artifact)

    assert isinstance(transcript, Transcript)
    assert transcript.source_video == "input.mp4"
    assert transcript.metadata["asr_provider"] == "mock"
    assert transcript.metadata["audio_path"] == "audio/audio.wav"
    assert transcript.segments[0].start_time == 0.0
    assert transcript.segments[0].end_time == 3.2


def test_transcript_normalizer_rejects_empty_segments() -> None:
    payload = {
        "transcript_id": "bad",
        "source_video": "input.mp4",
        "language": "en",
        "segments": [],
        "duration": 0,
        "metadata": {},
    }

    with pytest.raises(ValueError, match="Transcript schema validation failed"):
        normalize_transcript_payload(payload, source_video="input.mp4", audio_path="audio/audio.wav")


def _transcript_payload(*, source_video: str | None) -> dict[str, object]:
    return {
        "transcript_id": "fixture_transcript",
        "source_video": source_video,
        "language": "en",
        "duration": 6.8,
        "segments": [
            {
                "segment_id": "seg_001",
                "start_time": 0.0,
                "end_time": 3.2,
                "text": "The first constraint is not speed, but direction.",
                "speaker": "speaker_1",
                "confidence": 0.98,
                "metadata": {},
            },
            {
                "segment_id": "seg_002",
                "start_time": 3.2,
                "end_time": 6.8,
                "text": "Validate demand before investing all resources.",
                "speaker": "speaker_1",
                "confidence": 0.96,
                "metadata": {},
            },
        ],
        "metadata": {},
    }
