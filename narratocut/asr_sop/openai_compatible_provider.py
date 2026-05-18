from __future__ import annotations

import json
import os
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from narratocut.asr_sop.transcript_normalizer import normalize_transcript_payload
from narratocut.audio_sop import AudioArtifact
from narratocut.schemas import Transcript


ALLOW_REMOTE_ASR_ENV = "NARRATOCUT_ALLOW_REMOTE_ASR"
REMOTE_TRUE_VALUES = {"1", "true", "yes", "on"}


class OpenAICompatibleASRProvider:
    """Minimal OpenAI-compatible audio transcription provider."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        api_key_env: str | None = None,
        timeout_sec: float = 60.0,
    ) -> None:
        if not base_url:
            raise ValueError("OpenAI-compatible ASR provider requires base_url")
        if not model:
            raise ValueError("OpenAI-compatible ASR provider requires model")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.api_key_env = api_key_env
        self.timeout_sec = timeout_sec

    def transcribe(self, audio_artifact: AudioArtifact, *, language: str | None = None) -> Transcript:
        if audio_artifact.status == "failed":
            raise ValueError(audio_artifact.error or "audio_artifact_failed")
        audio_path = _resolve_audio_path(audio_artifact)
        if not audio_path.is_file():
            raise ValueError(f"audio artifact does not exist: {audio_path}")

        api_key = self._resolve_api_key()
        self._ensure_remote_calls_allowed()
        response = self._send_request(audio_path, api_key, language=language)
        return normalize_transcript_payload(
            response,
            source_video=audio_artifact.source_video,
            audio_path=str(audio_path),
            provider_name="openai_compatible",
            language=language,
        )

    def _resolve_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            env_value = os.environ.get(self.api_key_env)
            if env_value:
                return env_value
        raise ValueError("OpenAI-compatible ASR provider requires an API key")

    def _ensure_remote_calls_allowed(self) -> None:
        value = os.environ.get(ALLOW_REMOTE_ASR_ENV, "").strip().lower()
        if value not in REMOTE_TRUE_VALUES:
            raise ValueError(f"Remote ASR calls are disabled; set {ALLOW_REMOTE_ASR_ENV}=true to enable them")

    def _send_request(self, audio_path: Path, api_key: str, *, language: str | None) -> dict[str, Any]:
        boundary = f"----NarratoCutASR{uuid.uuid4().hex}"
        body = _multipart_body(
            boundary=boundary,
            fields={
                "model": self.model,
                **({"language": language} if language else {}),
                "response_format": "json",
            },
            file_field="file",
            file_path=audio_path,
        )
        request = urllib.request.Request(
            f"{self.base_url}/audio/transcriptions",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise ValueError(f"OpenAI-compatible ASR HTTP error {exc.code}: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise ValueError(f"OpenAI-compatible ASR request failed: {exc.reason}") from exc

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("OpenAI-compatible ASR response is not valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("OpenAI-compatible ASR response JSON must be an object")
        return payload


def _multipart_body(
    *,
    boundary: str,
    fields: dict[str, str],
    file_field: str,
    file_path: Path,
) -> bytes:
    lines: list[bytes] = []
    for name, value in fields.items():
        lines.extend(
            [
                f"--{boundary}".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"'.encode("utf-8"),
                b"",
                value.encode("utf-8"),
            ]
        )
    lines.extend(
        [
            f"--{boundary}".encode("utf-8"),
            f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"'.encode("utf-8"),
            b"Content-Type: audio/wav",
            b"",
            file_path.read_bytes(),
            f"--{boundary}--".encode("utf-8"),
            b"",
        ]
    )
    return b"\r\n".join(lines)


def _resolve_audio_path(audio_artifact: AudioArtifact) -> Path:
    absolute_ref = audio_artifact.metadata.get("absolute_audio_path")
    if isinstance(absolute_ref, str) and absolute_ref.strip():
        return Path(absolute_ref)
    return Path(audio_artifact.audio_path)
