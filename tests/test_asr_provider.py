from __future__ import annotations

import json
import urllib.error

import pytest

from narratocut.asr_sop import MockASRProvider, OpenAICompatibleASRProvider, normalize_transcript_payload
from narratocut.asr_sop import openai_compatible_provider
from narratocut.audio_sop import AudioArtifact
from narratocut.schemas import Transcript


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


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


def test_openai_compatible_asr_provider_requires_remote_opt_in(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_ASR", raising=False)
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"fake wav")

    provider = OpenAICompatibleASRProvider(
        base_url="https://example.test/v1",
        api_key="fake-key",
        model="fake-asr",
    )

    with pytest.raises(ValueError, match="NARRATOCUT_ALLOW_REMOTE_ASR"):
        provider.transcribe(_audio_artifact(audio_path))


def test_openai_compatible_asr_provider_posts_audio_and_normalizes_transcript(monkeypatch, tmp_path) -> None:
    captured = {}
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"fake wav")

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = request.data
        captured["timeout"] = timeout
        return FakeResponse(_transcript_payload(source_video=None))

    monkeypatch.setattr(openai_compatible_provider.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("NARRATOCUT_ALLOW_REMOTE_ASR", "true")

    provider = OpenAICompatibleASRProvider(
        base_url="https://example.test/v1",
        api_key="fake-key",
        model="fake-asr",
        timeout_sec=9.5,
    )

    transcript = provider.transcribe(_audio_artifact(audio_path), language="en")

    assert transcript.source_video == "input.mp4"
    assert transcript.metadata["asr_provider"] == "openai_compatible"
    assert transcript.metadata["audio_path"] == str(audio_path)
    assert captured["url"] == "https://example.test/v1/audio/transcriptions"
    assert captured["headers"]["Authorization"] == "Bearer fake-key"
    assert b'name="model"' in captured["body"]
    assert b"fake-asr" in captured["body"]
    assert b'name="file"; filename="audio.wav"' in captured["body"]
    assert captured["timeout"] == 9.5


def test_openai_compatible_asr_provider_wraps_request_errors(monkeypatch, tmp_path) -> None:
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"fake wav")

    def fake_urlopen(request, timeout):
        raise urllib.error.URLError("network down")

    monkeypatch.setattr(openai_compatible_provider.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("NARRATOCUT_ALLOW_REMOTE_ASR", "true")

    provider = OpenAICompatibleASRProvider(
        base_url="https://example.test/v1",
        api_key="fake-key",
        model="fake-asr",
    )

    with pytest.raises(ValueError, match="request failed"):
        provider.transcribe(_audio_artifact(audio_path))


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


def _audio_artifact(audio_path) -> AudioArtifact:
    return AudioArtifact(
        source_video="input.mp4",
        audio_path="audio/audio.wav",
        status="succeeded",
        extraction_mode="ffmpeg",
        sample_rate=16000,
        channels=1,
        codec="pcm_s16le",
        metadata={"absolute_audio_path": str(audio_path)},
    )
