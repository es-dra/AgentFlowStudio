from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from agentflow_studio.model_gateway.errors import ModelProviderError


ALLOW_REMOTE_ENV = "AFS_ALLOW_REMOTE_LLM"
REMOTE_TRUE_VALUES = {"1", "true", "yes", "on"}


class OpenAICompatibleProvider:
    """Minimal OpenAI-compatible chat completions provider."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        api_key_env: str | None = None,
        timeout_sec: float = 30.0,
        temperature: float | None = None,
        max_completion_tokens: int | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> None:
        if not base_url:
            raise ModelProviderError("OpenAI-compatible provider requires base_url")
        if not model:
            raise ModelProviderError("OpenAI-compatible provider requires model")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.api_key_env = api_key_env
        self.timeout_sec = timeout_sec
        self.temperature = temperature
        self.max_completion_tokens = max_completion_tokens
        self.extra_body = dict(extra_body or {})

    def generate(self, prompt: str, *, task_type: str | None = None) -> str:
        api_key = self._resolve_api_key()
        self._ensure_remote_calls_allowed()
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2 if self.temperature is None else self.temperature,
        }
        if self.max_completion_tokens is not None:
            payload["max_completion_tokens"] = self.max_completion_tokens
        payload.update(self.extra_body)
        response = self._send_request(payload, api_key)
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelProviderError("OpenAI-compatible response missing choices[0].message.content") from exc
        if not isinstance(content, str):
            raise ModelProviderError("OpenAI-compatible response content is not a string")
        return content

    def _resolve_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            env_value = os.environ.get(self.api_key_env)
            if env_value:
                return env_value
        raise ModelProviderError("OpenAI-compatible provider requires an API key")

    def _ensure_remote_calls_allowed(self) -> None:
        value = os.environ.get(ALLOW_REMOTE_ENV, "").strip().lower()
        if value not in REMOTE_TRUE_VALUES:
            raise ModelProviderError(
                f"Remote LLM calls are disabled; set {ALLOW_REMOTE_ENV}=true to enable them"
            )

    def _send_request(self, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise ModelProviderError(
                f"OpenAI-compatible HTTP error {exc.code}: {error_body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ModelProviderError(f"OpenAI-compatible request failed: {exc.reason}") from exc

        try:
            decoded = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ModelProviderError("OpenAI-compatible response is not valid JSON") from exc
        if not isinstance(decoded, dict):
            raise ModelProviderError("OpenAI-compatible response JSON must be an object")
        return decoded
