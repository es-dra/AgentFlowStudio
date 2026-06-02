from __future__ import annotations

from typing import Protocol

from agentflow_studio.audio_sop import AudioArtifact
from agentflow_studio.schemas import Transcript


class ASRProvider(Protocol):
    def transcribe(self, audio_artifact: AudioArtifact, *, language: str | None = None) -> Transcript:
        ...
