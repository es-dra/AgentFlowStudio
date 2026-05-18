from __future__ import annotations

from typing import Protocol

from narratocut.audio_sop import AudioArtifact
from narratocut.schemas import Transcript


class ASRProvider(Protocol):
    def transcribe(self, audio_artifact: AudioArtifact, *, language: str | None = None) -> Transcript:
        ...
