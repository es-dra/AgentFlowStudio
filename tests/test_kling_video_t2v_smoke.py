from __future__ import annotations

import json

import httpx
import pytest
from typer.testing import CliRunner

from apps.cli.main import app
from narratocut.model_gateway import ModelConfigError
from narratocut.model_gateway.company_secrets import COMPANY_PROVIDER_CONFIG_ENV
from narratocut.model_gateway.kling_video_smoke import run_kling_t2v_smoke
from tests.kling_video_smoke_helpers import json_response, provider_config, store


def test_kling_t2v_smoke_success_writes_video_and_safe_manifest(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("NARRATOCUT_ALLOW_REMOTE_VIDEO", "true")
    provider_store = store(tmp_path)
    calls: list[str] = []
    video_bytes = b"fake-t2v-mp4-bytes"

    def fake_request(client, method, url, **kwargs):
        calls.append(str(url))
        if str(url).endswith("/v1/videos/text2video"):
            assert method == "POST"
            assert kwargs["headers"]["Authorization"].startswith("Bearer ")
            payload = kwargs["json"]
            assert payload["model_name"] == "kling-v3"
            assert payload["prompt"] == "memory architecture demo video"
            assert payload["duration"] == "5"
            assert payload["mode"] == "pro"
            assert payload["aspect_ratio"] == "9:16"
            return json_response(
                {
                    "code": 0,
                    "message": "success",
                    "data": {
                        "task_id": "t2v_task_123",
                        "task_status": "submitted",
                        "task_result": None,
                    },
                }
            )
        if str(url).endswith("/v1/videos/text2video/t2v_task_123"):
            assert method == "GET"
            assert kwargs["headers"]["Authorization"].startswith("Bearer ")
            return json_response(
                {
                    "code": 0,
                    "message": "success",
                    "data": {
                        "task_id": "t2v_task_123",
                        "task_status": "succeed",
                        "task_result": {
                            "videos": [
                                {
                                    "id": "video_1",
                                    "url": "https://signed.example/video.mp4?token=provider-secret-url",
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

    monkeypatch.setattr("narratocut.model_gateway.kling_video_runtime.httpx.Client.request", fake_request)

    manifest = run_kling_t2v_smoke(
        provider_store,
        service_id="kling_t2v",
        prompt="memory architecture demo video",
        output_dir=tmp_path / "run",
        poll_interval_sec=0,
        max_polls=2,
    )

    assert calls == [
        "https://api-beijing.klingai.com/v1/videos/text2video",
        "https://api-beijing.klingai.com/v1/videos/text2video/t2v_task_123",
        "https://signed.example/video.mp4?token=provider-secret-url",
    ]
    assert (tmp_path / "run" / "video_candidates" / "candidate_001.mp4").read_bytes() == video_bytes
    manifest_path = tmp_path / "run" / "kling_t2v_smoke_manifest.json"
    assert manifest_path.is_file()
    assert manifest["status"] == "succeeded"
    assert manifest["service_id"] == "kling_t2v"
    assert manifest["api_family"] == "t2v"
    assert manifest["outputs"][0]["provider_url_persisted"] is False

    serialized = json.dumps(json.loads(manifest_path.read_text(encoding="utf-8")), ensure_ascii=False)
    assert "https://signed.example" not in serialized
    assert "provider-secret-url" not in serialized
    assert "Bearer " not in serialized
    assert "fake-access-key" not in serialized
    assert "fake-secret-key" not in serialized


def test_kling_t2v_smoke_rejects_i2v_service(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("NARRATOCUT_ALLOW_REMOTE_VIDEO", "true")
    provider_store = store(tmp_path)

    with pytest.raises(ModelConfigError, match="t2v api_family"):
        run_kling_t2v_smoke(
            provider_store,
            service_id="kling_i2v",
            prompt="memory architecture demo video",
            output_dir=tmp_path / "run",
            poll_interval_sec=0,
            max_polls=1,
        )


def test_kling_t2v_smoke_cli_provider_config_help_uses_env_fallback() -> None:
    result = CliRunner().invoke(app, ["kling-t2v-smoke", "--help"])

    assert result.exit_code == 0, result.output
    assert "--provider-config" in result.output
    assert COMPANY_PROVIDER_CONFIG_ENV in result.output


def test_kling_t2v_smoke_cli_gate_failure_is_clean(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_VIDEO", raising=False)
    config_path = tmp_path / "providers.local.json"
    config_path.write_text(json.dumps(provider_config()), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "kling-t2v-smoke",
            "--prompt",
            "memory architecture demo video",
            "--provider-config",
            str(config_path),
            "--output",
            str(tmp_path / "run"),
        ],
    )

    assert result.exit_code == 1
    assert "Kling T2V smoke failed" in result.output
    assert "NARRATOCUT_ALLOW_REMOTE_VIDEO" in result.output
    assert "Traceback" not in result.output
    assert "fake-access-key" not in result.output
    assert "fake-secret-key" not in result.output
