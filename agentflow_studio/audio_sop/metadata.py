from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


AUDIO_MANIFEST = "audio_manifest.json"


@dataclass(frozen=True)
class AudioArtifact:
    source_video: str
    audio_path: str
    status: str
    extraction_mode: str
    sample_rate: int
    channels: int
    codec: str
    manifest_path: str = AUDIO_MANIFEST
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_video": self.source_video,
            "audio_path": self.audio_path,
            "status": self.status,
            "extraction_mode": self.extraction_mode,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "codec": self.codec,
            "manifest_path": self.manifest_path,
            "error": self.error,
            "metadata": self.metadata,
        }
