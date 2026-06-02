from __future__ import annotations

import json
from types import SimpleNamespace
import urllib.error

import pytest

from agentflow_studio.asr_sop import (
    FasterWhisperASRProvider,
    MockASRProvider,
    OpenAICompatibleASRProvider,
    normalize_transcript_payload,
)
from agentflow_studio.asr_sop import openai_compatible_provider
from agentflow_studio.asr_sop import faster_whisper_provider
from agentflow_studio.audio_sop import AudioArtifact
from agentflow_studio.schemas import Transcript


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
    monkeypatch.delenv("AFS_ALLOW_REMOTE_ASR", raising=False)
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"fake wav")

    provider = OpenAICompatibleASRProvider(
        base_url="https://example.test/v1",
        api_key="fake-key",
        model="fake-asr",
    )

    with pytest.raises(ValueError, match="AFS_ALLOW_REMOTE_ASR"):
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
    monkeypatch.setenv("AFS_ALLOW_REMOTE_ASR", "true")

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
    monkeypatch.setenv("AFS_ALLOW_REMOTE_ASR", "true")

    provider = OpenAICompatibleASRProvider(
        base_url="https://example.test/v1",
        api_key="fake-key",
        model="fake-asr",
    )

    with pytest.raises(ValueError, match="request failed"):
        provider.transcribe(_audio_artifact(audio_path))


def test_faster_whisper_asr_provider_transcribes_locally_without_remote_opt_in(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_ASR", raising=False)
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"fake wav")
    captured = {}

    class FakeWhisperModel:
        def __init__(self, model_size_or_path, **kwargs) -> None:
            captured["model_size_or_path"] = model_size_or_path
            captured["kwargs"] = kwargs

        def transcribe(self, audio, **kwargs):
            captured["audio"] = audio
            captured["transcribe_kwargs"] = kwargs
            segments = [
                SimpleNamespace(start=1.0, end=2.5, text=" First local highlight. "),
                SimpleNamespace(start=4.0, end=6.0, text=" Second local highlight. "),
            ]
            info = SimpleNamespace(language="en", language_probability=0.97, duration=6.0)
            return segments, info

    monkeypatch.setattr(faster_whisper_provider, "_load_whisper_model_class", lambda: FakeWhisperModel)

    provider = FasterWhisperASRProvider(
        model="base",
        device="cpu",
        compute_type="int8",
        download_root=str(tmp_path / "models"),
        beam_size=3,
        vad_filter=True,
    )

    transcript = provider.transcribe(_audio_artifact(audio_path), language="en")

    assert transcript.source_video == "input.mp4"
    assert transcript.language == "en"
    assert transcript.duration == 6.0
    assert transcript.metadata["asr_provider"] == "faster_whisper"
    assert transcript.metadata["model"] == "base"
    assert transcript.metadata["device"] == "cpu"
    assert transcript.segments[0].segment_id == "seg_001"
    assert transcript.segments[0].start_time == 1.0
    assert transcript.segments[0].text == "First local highlight."
    assert captured["kwargs"]["compute_type"] == "int8"
    assert captured["kwargs"]["download_root"] == str(tmp_path / "models")
    assert captured["transcribe_kwargs"]["beam_size"] == 3
    assert captured["transcribe_kwargs"]["vad_filter"] is True


def test_faster_whisper_asr_provider_reports_missing_optional_dependency(monkeypatch, tmp_path) -> None:
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"fake wav")

    def missing_dependency():
        raise ImportError("No module named faster_whisper")

    monkeypatch.setattr(faster_whisper_provider, "_load_whisper_model_class", missing_dependency)

    provider = FasterWhisperASRProvider(model="tiny")

    with pytest.raises(ValueError, match="Install local ASR dependencies"):
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
