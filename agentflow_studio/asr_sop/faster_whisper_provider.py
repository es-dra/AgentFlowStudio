from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow_studio.asr_sop.transcript_normalizer import normalize_transcript_payload
from agentflow_studio.audio_sop import AudioArtifact
from agentflow_studio.schemas import Transcript


class FasterWhisperASRProvider:
    """Local faster-whisper transcription provider."""

    def __init__(
        self,
        *,
        model: str = "tiny",
        device: str = "cpu",
        compute_type: str = "int8",
        download_root: str | None = None,
        beam_size: int = 1,
        vad_filter: bool = False,
    ) -> None:
        if not model:
            raise ValueError("faster-whisper ASR provider requires model")
        self.model = model
        self.device = device or "cpu"
        self.compute_type = compute_type or "int8"
        self.download_root = download_root
        self.beam_size = beam_size
        self.vad_filter = vad_filter

    def transcribe(self, audio_artifact: AudioArtifact, *, language: str | None = None) -> Transcript:
        if audio_artifact.status == "failed":
            raise ValueError(audio_artifact.error or "audio_artifact_failed")
        audio_path = _resolve_audio_path(audio_artifact)
        if not audio_path.is_file():
            raise ValueError(f"audio artifact does not exist: {audio_path}")

        try:
            model_class = _load_whisper_model_class()
        except ImportError as exc:
            raise _missing_dependency_error() from exc
        model_kwargs: dict[str, Any] = {
            "device": self.device,
            "compute_type": self.compute_type,
        }
        if self.download_root:
            model_kwargs["download_root"] = self.download_root

        model = model_class(self.model, **model_kwargs)
        transcribe_kwargs: dict[str, Any] = {
            "beam_size": self.beam_size,
            "vad_filter": self.vad_filter,
        }
        if language:
            transcribe_kwargs["language"] = language
        segments, info = model.transcribe(str(audio_path), **transcribe_kwargs)

        payload = _to_transcript_payload(
            segments=segments,
            info=info,
            requested_language=language,
            source_video=audio_artifact.source_video,
        )
        transcript = normalize_transcript_payload(
            payload,
            source_video=audio_artifact.source_video,
            audio_path=str(audio_path),
            provider_name="faster_whisper",
            language=language,
        )
        transcript.metadata.update(
            {
                "transcript_source": "local_asr",
                "model": self.model,
                "device": self.device,
                "compute_type": self.compute_type,
            }
        )
        return transcript


def _load_whisper_model_class():
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise _missing_dependency_error() from exc
    return WhisperModel


def _missing_dependency_error() -> ValueError:
    return ValueError(
        "Install local ASR dependencies with `python -m pip install faster-whisper` "
        "before using transcribe_audio_faster_whisper"
    )


def _to_transcript_payload(
    *,
    segments,
    info: object,
    requested_language: str | None,
    source_video: str,
) -> dict[str, Any]:
    transcript_segments: list[dict[str, Any]] = []
    for index, segment in enumerate(segments, start=1):
        text = str(getattr(segment, "text", "")).strip()
        if not text:
            continue
        transcript_segments.append(
            {
                "segment_id": f"seg_{index:03d}",
                "start_time": float(getattr(segment, "start")),
                "end_time": float(getattr(segment, "end")),
                "text": text,
                "speaker": None,
                "confidence": None,
                "metadata": {},
            }
        )
    if not transcript_segments:
        raise ValueError("faster-whisper returned no transcript segments")

    detected_language = getattr(info, "language", None)
    duration = getattr(info, "duration", None)
    metadata: dict[str, Any] = {}
    language_probability = getattr(info, "language_probability", None)
    if language_probability is not None:
        metadata["language_probability"] = float(language_probability)

    return {
        "transcript_id": "faster_whisper_transcript",
        "source_video": source_video,
        "language": requested_language or detected_language,
        "duration": float(duration) if duration is not None else max(item["end_time"] for item in transcript_segments),
        "segments": transcript_segments,
        "metadata": metadata,
    }


def _resolve_audio_path(audio_artifact: AudioArtifact) -> Path:
    absolute_ref = audio_artifact.metadata.get("absolute_audio_path")
    if isinstance(absolute_ref, str) and absolute_ref.strip():
        return Path(absolute_ref)
    return Path(audio_artifact.audio_path)
