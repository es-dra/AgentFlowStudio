from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from narratocut.asr_sop.transcript_normalizer import normalize_transcript_payload
from narratocut.audio_sop import AudioArtifact
from narratocut.schemas import Transcript


@dataclass(frozen=True)
class MockASRProvider:
    fixture_path: str | Path
    provider_name: str = "mock"

    def transcribe(self, audio_artifact: AudioArtifact, *, language: str | None = None) -> Transcript:
        if audio_artifact.status == "failed":
            raise ValueError(audio_artifact.error or "audio_artifact_failed")
        payload = _load_fixture(Path(self.fixture_path))
        return normalize_transcript_payload(
            payload,
            source_video=audio_artifact.source_video,
            audio_path=audio_artifact.audio_path,
            provider_name=self.provider_name,
            language=language,
        )


def _load_fixture(path: Path) -> dict[str, Any]:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"asr_fixture_path does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"ASR fixture JSON is invalid: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"ASR fixture must contain a JSON object: {path}")
    return payload
