from __future__ import annotations

import json

import httpx
import pytest
from typer.testing import CliRunner

from apps.cli.main import app
from agentflow_studio.model_gateway import ModelProviderError
from agentflow_studio.model_gateway.company_secrets import COMPANY_PROVIDER_CONFIG_ENV
from agentflow_studio.model_gateway.kling_video_smoke import run_kling_i2v_smoke
from tests.kling_video_smoke_helpers import json_response, provider_config, store


def test_kling_i2v_smoke_gate_disabled_fails_before_network(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    image_path = tmp_path / "candidate.png"
    image_path.write_bytes(b"image-bytes")
    provider_store = store(tmp_path)

    def fake_request(*args, **kwargs):  # pragma: no cover - must not call provider
        raise AssertionError("network should not be called when video gate is disabled")

    monkeypatch.setattr("agentflow_studio.model_gateway.kling_video_runtime.httpx.Client.request", fake_request)

    with pytest.raises(ModelProviderError, match="AFS_ALLOW_REMOTE_VIDEO"):
        run_kling_i2v_smoke(
            provider_store,
            service_id="kling_i2v",
            prompt="slow push-in over the memory architecture board",
            image_path=image_path,
            output_dir=tmp_path / "run",
            poll_interval_sec=0,
            max_polls=1,
        )

    assert not (tmp_path / "run" / "kling_i2v_smoke_manifest.json").exists()


def test_kling_i2v_smoke_success_writes_video_and_safe_manifest(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    image_path = tmp_path / "candidate.png"
    image_path.write_bytes(b"image-bytes")
    provider_store = store(tmp_path)
    calls: list[str] = []
    video_bytes = b"fake-mp4-bytes"

    def fake_request(client, method, url, **kwargs):
        calls.append(str(url))
        if str(url).endswith("/v1/videos/image2video"):
            assert method == "POST"
            assert kwargs["headers"]["Authorization"].startswith("Bearer ")
            payload = kwargs["json"]
            assert payload["model_name"] == "kling-v3"
            assert payload["image"] == "aW1hZ2UtYnl0ZXM="
            assert payload["prompt"] == "slow push-in over the memory architecture board"
            assert payload["duration"] == "5"
            assert payload["mode"] == "pro"
            return json_response(
                {
                    "code": 0,
                    "message": "success",
                    "data": {
                        "task_id": "video_task_123",
                        "task_status": "submitted",
                        "task_result": None,
                    },
                }
            )
        if str(url).endswith("/v1/videos/image2video/video_task_123"):
            assert method == "GET"
            assert kwargs["headers"]["Authorization"].startswith("Bearer ")
            return json_response(
                {
                    "code": 0,
                    "message": "success",
                    "data": {
                        "task_id": "video_task_123",
                        "task_status": "succeed",
                        "task_status_msg": "",
                        "task_result": {
                            "videos": [
                                {
                                    "id": "video_1",
                                    "url": "https://signed.example/video.mp4?token=provider-secret-url",
                                    "duration": "5",
                                }
                            ]
                        },
                    },
                }
            )
        if str(url).startswith("https://signed.example/video.mp4"):
            return httpx.Response(
                200,
                content=video_bytes,
                headers={"Content-Type": "video/mp4"},
                request=httpx.Request("GET", str(url)),
            )
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("agentflow_studio.model_gateway.kling_video_runtime.httpx.Client.request", fake_request)

    manifest = run_kling_i2v_smoke(
        provider_store,
        service_id="kling_i2v",
        prompt="slow push-in over the memory architecture board",
        image_path=image_path,
        output_dir=tmp_path / "run",
        poll_interval_sec=0,
        max_polls=2,
    )

    assert calls == [
        "https://api-beijing.klingai.com/v1/videos/image2video",
        "https://api-beijing.klingai.com/v1/videos/image2video/video_task_123",
        "https://signed.example/video.mp4?token=provider-secret-url",
    ]
    assert (tmp_path / "run" / "video_candidates" / "candidate_001.mp4").read_bytes() == video_bytes
    manifest_path = tmp_path / "run" / "kling_i2v_smoke_manifest.json"
    assert manifest_path.is_file()
    assert manifest["status"] == "succeeded"
    assert manifest["api_family"] == "i2v"
    assert manifest["task"]["task_id"] == "video_task_123"
    assert manifest["outputs"][0]["video_path"] == "video_candidates/candidate_001.mp4"
    assert manifest["outputs"][0]["provider_url_persisted"] is False
    assert manifest["input_image"]["path_persisted"] is False
    assert manifest["claim_boundary"] == "provider_smoke_only_not_creative_quality"

    serialized = json.dumps(json.loads(manifest_path.read_text(encoding="utf-8")), ensure_ascii=False)
    assert "https://signed.example" not in serialized
    assert "provider-secret-url" not in serialized
    assert "Bearer " not in serialized
    assert "fake-access-key" not in serialized
    assert "fake-secret-key" not in serialized
    assert str(image_path) not in serialized


def test_kling_i2v_smoke_http_error_does_not_expose_response_body(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    image_path = tmp_path / "candidate.png"
    image_path.write_bytes(b"image-bytes")
    provider_store = store(tmp_path)

    def fake_request(client, method, url, **kwargs):
        request = httpx.Request(method, str(url))
        response = httpx.Response(
            429,
            json={
                "code": 1102,
                "message": "fake-secret-key leaked by provider body",
                "request_id": "request-id-should-not-be-printed",
            },
            request=request,
        )
        raise httpx.HTTPStatusError("Unauthorized", request=request, response=response)

    monkeypatch.setattr("agentflow_studio.model_gateway.kling_video_runtime.httpx.Client.request", fake_request)

    with pytest.raises(ModelProviderError) as exc_info:
        run_kling_i2v_smoke(
            provider_store,
            service_id="kling_i2v",
            prompt="slow push-in over the memory architecture board",
            image_path=image_path,
            output_dir=tmp_path / "run",
            poll_interval_sec=0,
            max_polls=1,
        )

    message = str(exc_info.value)
    assert "Kling video HTTP error 429" in message
    assert "provider code 1102" in message
    assert "account resource package exhausted or expired" in message
    assert "fake-secret-key" not in message
    assert "request-id-should-not-be-printed" not in message
    assert not (tmp_path / "run" / "kling_i2v_smoke_manifest.json").exists()


def test_kling_i2v_smoke_cli_provider_config_help_uses_env_fallback() -> None:
    result = CliRunner().invoke(app, ["kling-i2v-smoke", "--help"])

    assert result.exit_code == 0, result.output
    assert "--provider-config" in result.output
    assert COMPANY_PROVIDER_CONFIG_ENV in result.output


def test_kling_i2v_smoke_cli_gate_failure_is_clean(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    image_path = tmp_path / "candidate.png"
    image_path.write_bytes(b"image-bytes")
    config_path = tmp_path / "providers.local.json"
    config_path.write_text(json.dumps(provider_config()), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "kling-i2v-smoke",
            "--prompt",
            "slow push-in over the memory architecture board",
            "--image",
            str(image_path),
            "--provider-config",
            str(config_path),
            "--output",
            str(tmp_path / "run"),
        ],
    )

    assert result.exit_code == 1
    assert "Kling I2V smoke failed" in result.output
    assert "AFS_ALLOW_REMOTE_VIDEO" in result.output
    assert "Traceback" not in result.output
    assert "fake-access-key" not in result.output
    assert "fake-secret-key" not in result.output
