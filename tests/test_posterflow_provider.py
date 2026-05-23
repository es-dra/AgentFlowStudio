from __future__ import annotations

import base64
import io
import json
import urllib.error

import pytest

from narratocut.model_gateway import ModelProviderError
from narratostudio.posterflow import provider as poster_provider
from narratostudio.posterflow.provider import OpenAICompatibleImageProvider
from narratostudio.posterflow.schemas import PosterPromptPack


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)
PNG_B64 = base64.b64encode(PNG_BYTES).decode("ascii")


class FakeResponse:
    def __init__(self, payload: dict | bytes) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    def read(self) -> bytes:
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode("utf-8")


def test_openai_compatible_image_provider_requires_remote_image_opt_in(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_IMAGE", raising=False)
    provider = OpenAICompatibleImageProvider(
        base_url="https://example.test/v1",
        api_key="fake-key",
        model="fake-image-model",
    )

    with pytest.raises(ModelProviderError, match="NARRATOCUT_ALLOW_REMOTE_IMAGE"):
        provider.generate(_prompt_pack(), tmp_path, candidate_count=1)


def test_openai_compatible_image_provider_checks_remote_gate_before_api_key(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_IMAGE", raising=False)
    monkeypatch.delenv("NARRATOCUT_IMAGE_API_KEY", raising=False)
    provider = OpenAICompatibleImageProvider(
        base_url="https://example.test/v1",
        api_key=None,
        api_key_env="NARRATOCUT_IMAGE_API_KEY",
        model="fake-image-model",
    )

    with pytest.raises(ModelProviderError, match="NARRATOCUT_ALLOW_REMOTE_IMAGE"):
        provider.generate(_prompt_pack(), tmp_path, candidate_count=1)


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
    monkeypatch.setenv("NARRATOCUT_ALLOW_REMOTE_IMAGE", "true")
    provider = OpenAICompatibleImageProvider(
        base_url="https://example.test/v1",
        api_key="secret-key",
        model="fake-image-model",
        timeout_sec=12.5,
    )

    manifest, invocations = provider.generate(_prompt_pack(), tmp_path, candidate_count=3)

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
    monkeypatch.setenv("NARRATOCUT_ALLOW_REMOTE_IMAGE", "true")
    provider = OpenAICompatibleImageProvider(
        base_url="https://example.test/v1",
        api_key="fake-key",
        model="fake-image-model",
    )

    with pytest.raises(ModelProviderError, match="request failed"):
        provider.generate(_prompt_pack(), tmp_path, candidate_count=1)


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
    monkeypatch.setenv("NARRATOCUT_ALLOW_REMOTE_IMAGE", "true")
    provider = OpenAICompatibleImageProvider(
        base_url="https://example.test/v1",
        api_key="fake-key",
        model="fake-image-model",
    )

    with pytest.raises(ModelProviderError) as exc_info:
        provider.generate(_prompt_pack(), tmp_path, candidate_count=1)

    message = str(exc_info.value)
    assert "HTTP error 401" in message
    assert "secret-key" not in message


def _prompt_pack() -> PosterPromptPack:
    return PosterPromptPack(
        project_id="cyber_xianxia_001",
        run_id="run_001",
        prompt_id="poster_prompt_001",
        target_model_family="openai_compatible_image",
        prompt_language="en",
        positive_prompt="cinematic poster, low saturation, premium composition",
        negative_prompt="cheap mobile game ad, oversaturated neon",
        prompt_sections={"style": "cinematic", "composition": "centered"},
        model_params={"aspect_ratio": "3:4", "num_candidates": 3},
        context_usage={"project_prefix_used": False, "preference_profile_used": False},
        source_refs={"poster_plan": "poster_plan.json"},
    )
