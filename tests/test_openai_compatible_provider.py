from __future__ import annotations

import json
import urllib.error

import pytest

from agentflow_studio.model_gateway import ModelProviderError, OpenAICompatibleProvider
from agentflow_studio.model_gateway import openai_compatible


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_openai_compatible_provider_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("AFS_TEST_KEY", raising=False)
    provider = OpenAICompatibleProvider(
        base_url="https://example.test/v1",
        api_key_env="AFS_TEST_KEY",
        model="fake-model",
    )

    with pytest.raises(ModelProviderError, match="API key"):
        provider.generate("prompt")


def test_openai_compatible_provider_requires_base_url_or_model() -> None:
    with pytest.raises(ModelProviderError, match="base_url"):
        OpenAICompatibleProvider(base_url="", api_key="fake", model="fake-model")

    with pytest.raises(ModelProviderError, match="model"):
        OpenAICompatibleProvider(base_url="https://example.test/v1", api_key="fake", model="")


def test_openai_compatible_provider_requires_remote_call_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    provider = OpenAICompatibleProvider(
        base_url="https://example.test/v1",
        api_key="fake-key",
        model="fake-model",
    )

    with pytest.raises(ModelProviderError, match="AFS_ALLOW_REMOTE_LLM"):
        provider.generate("hello")


def test_openai_compatible_provider_returns_chat_completion(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["headers"] = dict(request.header_items())
        captured["timeout"] = timeout
        return FakeResponse({"choices": [{"message": {"content": "model text"}}]})

    monkeypatch.setattr(openai_compatible.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")

    provider = OpenAICompatibleProvider(
        base_url="https://example.test/v1",
        api_key="fake-key",
        model="fake-model",
        timeout_sec=12.5,
    )

    assert provider.generate("hello") == "model text"
    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert captured["payload"]["model"] == "fake-model"
    assert captured["payload"]["messages"] == [{"role": "user", "content": "hello"}]
    assert captured["headers"]["Authorization"] == "Bearer fake-key"
    assert captured["timeout"] == 12.5


def test_openai_compatible_provider_rejects_missing_choices(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeResponse({"choices": []})

    monkeypatch.setattr(openai_compatible.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    provider = OpenAICompatibleProvider(
        base_url="https://example.test/v1",
        api_key="fake-key",
        model="fake-model",
    )

    with pytest.raises(ModelProviderError, match="choices"):
        provider.generate("hello")


def test_openai_compatible_provider_wraps_request_errors(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        raise urllib.error.URLError("network down")

    monkeypatch.setattr(openai_compatible.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    provider = OpenAICompatibleProvider(
        base_url="https://example.test/v1",
        api_key="fake-key",
        model="fake-model",
    )

    with pytest.raises(ModelProviderError, match="request failed"):
        provider.generate("hello")
