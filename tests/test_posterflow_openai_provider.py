from __future__ import annotations

import io
import json
import urllib.error

import pytest

from agentflow_studio.model_gateway import ModelProviderError
from agentflow_studio.production.posterflow import provider as poster_provider
from agentflow_studio.production.posterflow.provider import OpenAICompatibleImageProvider
from tests.posterflow_provider_helpers import FakeResponse, PNG_B64, prompt_pack


def test_openai_compatible_image_provider_requires_remote_image_opt_in(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    provider = OpenAICompatibleImageProvider(
        base_url="https://example.test/v1",
        api_key="fake-key",
        model="fake-image-model",
    )

    with pytest.raises(ModelProviderError, match="AFS_ALLOW_REMOTE_IMAGE"):
        provider.generate(prompt_pack(), tmp_path, candidate_count=1)


def test_openai_compatible_image_provider_checks_remote_gate_before_api_key(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    monkeypatch.delenv("AFS_IMAGE_API_KEY", raising=False)
    provider = OpenAICompatibleImageProvider(
        base_url="https://example.test/v1",
        api_key=None,
        api_key_env="AFS_IMAGE_API_KEY",
        model="fake-image-model",
    )

    with pytest.raises(ModelProviderError, match="AFS_ALLOW_REMOTE_IMAGE"):
        provider.generate(prompt_pack(), tmp_path, candidate_count=1)


def test_openai_compatible_image_provider_requires_configuration() -> None:
    with pytest.raises(ModelProviderError, match="base_url"):
        OpenAICompatibleImageProvider(base_url="", api_key="fake-key", model="fake-image-model")

    with pytest.raises(ModelProviderError, match="model"):
        OpenAICompatibleImageProvider(base_url="https://example.test/v1", api_key="fake-key", model="")

    with pytest.raises(ModelProviderError, match="API key"):
        OpenAICompatibleImageProvider(base_url="https://example.test/v1", api_key="", model="fake-image-model")


def test_openai_compatible_image_provider_writes_three_images_without_secrets(monkeypatch, tmp_path) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["headers"] = dict(request.header_items())
        captured["timeout"] = timeout
        return FakeResponse({"data": [{"b64_json": PNG_B64}, {"b64_json": PNG_B64}, {"b64_json": PNG_B64}]})

    monkeypatch.setattr(poster_provider.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    provider = OpenAICompatibleImageProvider(
        base_url="https://example.test/v1",
        api_key="secret-key",
        model="fake-image-model",
        timeout_sec=12.5,
    )

    manifest, invocations = provider.generate(prompt_pack(), tmp_path, candidate_count=3)

    assert captured["url"] == "https://example.test/v1/images/generations"
    assert captured["payload"]["model"] == "fake-image-model"
    assert captured["payload"]["n"] == 3
    assert captured["headers"]["Authorization"] == "Bearer secret-key"
    assert captured["timeout"] == 12.5
    assert len(manifest.candidates) == 3
    assert all((tmp_path / candidate.image_path).is_file() for candidate in manifest.candidates)

    serialized_invocations = json.dumps(invocations.model_dump(mode="json"), ensure_ascii=False)
    assert "secret-key" not in serialized_invocations
    assert "https://example.test" not in serialized_invocations


def test_openai_compatible_image_provider_wraps_request_errors(monkeypatch, tmp_path) -> None:
    def fake_urlopen(request, timeout):
        raise urllib.error.URLError("network down")

    monkeypatch.setattr(poster_provider.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    provider = OpenAICompatibleImageProvider(
        base_url="https://example.test/v1",
        api_key="fake-key",
        model="fake-image-model",
    )

    with pytest.raises(ModelProviderError, match="request failed"):
        provider.generate(prompt_pack(), tmp_path, candidate_count=1)


def test_openai_compatible_image_provider_does_not_expose_http_error_body(monkeypatch, tmp_path) -> None:
    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            url=request.full_url,
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=io.BytesIO(b'{"error":"secret-key should not enter trace artifacts"}'),
        )

    monkeypatch.setattr(poster_provider.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    provider = OpenAICompatibleImageProvider(
        base_url="https://example.test/v1",
        api_key="fake-key",
        model="fake-image-model",
    )

    with pytest.raises(ModelProviderError) as exc_info:
        provider.generate(prompt_pack(), tmp_path, candidate_count=1)

    message = str(exc_info.value)
    assert "HTTP error 401" in message
    assert "secret-key" not in message
