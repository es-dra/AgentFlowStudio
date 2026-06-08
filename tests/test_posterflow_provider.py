from __future__ import annotations

import io
import json
import urllib.error

import pytest

from agentflow_studio.model_gateway import ModelProviderError
from agentflow_studio.production.posterflow import minimax_provider
from agentflow_studio.production.posterflow.minimax_provider import MiniMaxImageProvider
from agentflow_studio.production.posterflow.provider import create_image_provider_from_env
from tests.posterflow_provider_helpers import FakeResponse, JPEG_B64, JPEG_BYTES, PNG_B64, prompt_pack


def test_minimax_image_provider_writes_base64_images_without_secrets(monkeypatch, tmp_path) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["headers"] = dict(request.header_items())
        captured["timeout"] = timeout
        return FakeResponse(
            {
                "id": "minimax_task_001",
                "data": {"image_base64": [PNG_B64, PNG_B64, PNG_B64]},
                "metadata": {"success_count": "3", "failed_count": "0"},
                "base_resp": {"status_code": 0, "status_msg": "success"},
            }
        )

    monkeypatch.setattr(minimax_provider.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    provider = MiniMaxImageProvider(
        base_url="https://api.minimax.io",
        api_key="secret-key",
        model="image-01",
        timeout_sec=12.5,
    )

    manifest, invocations = provider.generate(prompt_pack(), tmp_path, candidate_count=3)

    assert captured["url"] == "https://api.minimax.io/v1/image_generation"
    assert captured["payload"]["model"] == "image-01"
    assert captured["payload"]["n"] == 3
    assert captured["payload"]["response_format"] == "base64"
    assert captured["payload"]["aspect_ratio"] == "3:4"
    assert captured["headers"]["Authorization"] == "Bearer secret-key"
    assert captured["timeout"] == 12.5
    assert len(manifest.candidates) == 3
    assert all(candidate.provider == "minimax_image" for candidate in manifest.candidates)
    assert all((tmp_path / candidate.image_path).is_file() for candidate in manifest.candidates)

    serialized_invocations = json.dumps(invocations.model_dump(mode="json"), ensure_ascii=False)
    assert "secret-key" not in serialized_invocations
    assert "api.minimax.io" not in serialized_invocations


def test_minimax_image_provider_uses_jpg_extension_for_jpeg_base64(monkeypatch, tmp_path) -> None:
    def fake_urlopen(request, timeout):
        return FakeResponse(
            {
                "data": {"image_base64": [JPEG_B64]},
                "base_resp": {"status_code": 0, "status_msg": "success"},
            }
        )

    monkeypatch.setattr(minimax_provider.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    provider = MiniMaxImageProvider(
        base_url="https://api.minimax.io",
        api_key="secret-key",
        model="image-01",
    )

    manifest, _invocations = provider.generate(prompt_pack(), tmp_path, candidate_count=1)

    assert manifest.candidates[0].image_path == "image_candidates/candidate_001.jpg"
    assert (tmp_path / "image_candidates" / "candidate_001.jpg").read_bytes() == JPEG_BYTES


def test_minimax_image_provider_accepts_v1_base_url_without_double_v1(monkeypatch, tmp_path) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        return FakeResponse(
            {
                "data": {"image_base64": [PNG_B64]},
                "base_resp": {"status_code": 0, "status_msg": "success"},
            }
        )

    monkeypatch.setattr(minimax_provider.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    provider = MiniMaxImageProvider(
        base_url="https://api.minimax.io/v1",
        api_key="secret-key",
        model="image-01",
    )

    provider.generate(prompt_pack(), tmp_path, candidate_count=1)

    assert captured["url"] == "https://api.minimax.io/v1/image_generation"


def test_minimax_image_provider_rejects_candidate_count_outside_api_range(monkeypatch, tmp_path) -> None:
    def fake_urlopen(request, timeout):  # pragma: no cover - must not call provider
        raise AssertionError("MiniMax provider should validate n before remote calls")

    monkeypatch.setattr(minimax_provider.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    provider = MiniMaxImageProvider(
        base_url="https://api.minimax.io",
        api_key="secret-key",
        model="image-01",
    )

    with pytest.raises(ModelProviderError, match="candidate_count must be between 1 and 9"):
        provider.generate(prompt_pack(), tmp_path, candidate_count=10)


def test_minimax_image_provider_does_not_expose_http_error_body(monkeypatch, tmp_path) -> None:
    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            url=request.full_url,
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=io.BytesIO(b'{"status_msg":"secret-key should not enter trace artifacts"}'),
        )

    monkeypatch.setattr(minimax_provider.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    provider = MiniMaxImageProvider(
        base_url="https://api.minimax.io",
        api_key="secret-key",
        model="image-01",
    )

    with pytest.raises(ModelProviderError) as exc_info:
        provider.generate(prompt_pack(), tmp_path, candidate_count=1)

    message = str(exc_info.value)
    assert "MiniMax image HTTP error 401" in message
    assert "secret-key" not in message


def test_minimax_image_provider_rejects_nonzero_base_response_without_leaking_message(monkeypatch, tmp_path) -> None:
    def fake_urlopen(request, timeout):
        return FakeResponse(
            {
                "data": {},
                "base_resp": {
                    "status_code": 1004,
                    "status_msg": "secret-key should not enter trace artifacts",
                },
            }
        )

    monkeypatch.setattr(minimax_provider.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    provider = MiniMaxImageProvider(
        base_url="https://api.minimax.io",
        api_key="secret-key",
        model="image-01",
    )

    with pytest.raises(ModelProviderError) as exc_info:
        provider.generate(prompt_pack(), tmp_path, candidate_count=1)

    message = str(exc_info.value)
    assert "MiniMax image response status_code 1004" in message
    assert "secret-key" not in message


def test_create_image_provider_from_env_selects_minimax(monkeypatch) -> None:
    monkeypatch.setenv("AFS_IMAGE_PROVIDER", "minimax")
    monkeypatch.setenv("AFS_IMAGE_API_KEY", "secret-key")
    monkeypatch.delenv("AFS_IMAGE_BASE_URL", raising=False)
    monkeypatch.delenv("AFS_IMAGE_MODEL", raising=False)

    provider = create_image_provider_from_env()

    assert isinstance(provider, MiniMaxImageProvider)
    assert provider.base_url == "https://api.minimax.io"
    assert provider.model == "image-01"
