from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from narratocut.schemas import Transcript


def normalize_transcript_payload(
    payload: dict[str, Any],
    *,
    source_video: str,
    audio_path: str,
    provider_name: str = "mock",
    language: str | None = None,
) -> Transcript:
    normalized = deepcopy(payload)
    if not normalized.get("source_video"):
        normalized["source_video"] = source_video
    if language and not normalized.get("language"):
        normalized["language"] = language

    metadata = normalized.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    metadata.setdefault("asr_provider", provider_name)
    metadata.setdefault("audio_path", audio_path)
    metadata.setdefault("transcript_source", "fixture")
    normalized["metadata"] = metadata

    try:
        return Transcript.model_validate(normalized)
    except ValidationError as exc:
        raise ValueError("Transcript schema validation failed") from exc
