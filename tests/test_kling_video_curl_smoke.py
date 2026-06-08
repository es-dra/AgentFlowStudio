from __future__ import annotations

import json

from agentflow_studio.model_gateway.kling_video_smoke import run_kling_i2v_smoke, run_kling_t2v_smoke
from tests.kling_video_smoke_helpers import Completed, curl_response, store


def test_kling_t2v_smoke_can_use_curl_transport_without_persisting_token(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    provider_store = store(tmp_path)
    video_bytes = b"fake-curl-t2v-mp4-bytes"
    commands: list[list[str]] = []

    def fake_run(command, *, input=None, capture_output=None, check=None):
        commands.append(command)
        assert capture_output is True
        assert check is False
        assert command == ["curl.exe", "-sS", "-i", "--config", "-"]
        joined = " ".join(command)
        assert "fake-access-key" not in joined
        assert "fake-secret-key" not in joined
        assert "Bearer " not in joined
        assert input is not None
        config_text = input.decode("utf-8")
        if 'url = "https://api-beijing.klingai.com/v1/videos/text2video"' in config_text:
            assert b"memory architecture demo video" in input
            return Completed(
                stdout=curl_response(
                    {
                        "code": 0,
                        "data": {"task_id": "curl_t2v_task_123", "task_status": "submitted"},
                    }
                )
            )
        if 'url = "https://api-beijing.klingai.com/v1/videos/text2video/curl_t2v_task_123"' in config_text:
            return Completed(
                stdout=curl_response(
                    {
                        "code": 0,
                        "data": {
                            "task_id": "curl_t2v_task_123",
                            "task_status": "succeed",
                            "task_result": {
                                "videos": [
                                    {"url": "https://signed.example/video.mp4?token=provider-secret-url"}
                                ]
                            },
                        },
                    }
                )
            )
        if 'url = "https://signed.example/video.mp4?token=provider-secret-url"' in config_text:
            return Completed(stdout=b"HTTP/1.1 200 OK\r\nContent-Type: video/mp4\r\n\r\n" + video_bytes)
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr("agentflow_studio.model_gateway.kling_transport.subprocess.run", fake_run)

    manifest = run_kling_t2v_smoke(
        provider_store,
        service_id="kling_t2v",
        prompt="memory architecture demo video",
        output_dir=tmp_path / "run",
        poll_interval_sec=0,
        max_polls=2,
        transport="curl",
    )

    assert len(commands) == 3
    assert (tmp_path / "run" / "video_candidates" / "candidate_001.mp4").read_bytes() == video_bytes
    serialized = json.dumps(json.loads((tmp_path / "run" / "kling_t2v_smoke_manifest.json").read_text(encoding="utf-8")))
    assert "https://signed.example" not in serialized
    assert "provider-secret-url" not in serialized
    assert "Bearer " not in serialized
    assert manifest["outputs"][0]["provider_url_persisted"] is False


def test_kling_i2v_smoke_can_use_curl_transport_without_persisting_token(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    image_path = tmp_path / "candidate.png"
    image_path.write_bytes(b"image-bytes")
    provider_store = store(tmp_path)
    video_bytes = b"fake-curl-i2v-mp4-bytes"
    commands: list[list[str]] = []

    def fake_run(command, *, input=None, capture_output=None, check=None):
        commands.append(command)
        assert capture_output is True
        assert check is False
        assert command == ["curl.exe", "-sS", "-i", "--config", "-"]
        joined = " ".join(command)
        assert "fake-access-key" not in joined
        assert "fake-secret-key" not in joined
        assert "Bearer " not in joined
        assert input is not None
        config_text = input.decode("utf-8")
        if 'url = "https://api-beijing.klingai.com/v1/videos/image2video"' in config_text:
            assert b"slow push-in over the memory architecture board" in input
            return Completed(stdout=curl_response({"code": 0, "data": {"task_id": "curl_i2v_task_123"}}))
        if 'url = "https://api-beijing.klingai.com/v1/videos/image2video/curl_i2v_task_123"' in config_text:
            return Completed(
                stdout=curl_response(
                    {
                        "code": 0,
                        "data": {
                            "task_id": "curl_i2v_task_123",
                            "task_status": "succeed",
                            "task_result": {
                                "videos": [
                                    {"url": "https://signed.example/i2v.mp4?token=provider-secret-url"}
                                ]
                            },
                        },
                    }
                )
            )
        if 'url = "https://signed.example/i2v.mp4?token=provider-secret-url"' in config_text:
            return Completed(stdout=b"HTTP/1.1 200 OK\r\nContent-Type: video/mp4\r\n\r\n" + video_bytes)
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr("agentflow_studio.model_gateway.kling_transport.subprocess.run", fake_run)

    manifest = run_kling_i2v_smoke(
        provider_store,
        service_id="kling_i2v",
        prompt="slow push-in over the memory architecture board",
        image_path=image_path,
        output_dir=tmp_path / "run",
        poll_interval_sec=0,
        max_polls=2,
        transport="curl",
    )

    assert len(commands) == 3
    assert (tmp_path / "run" / "video_candidates" / "candidate_001.mp4").read_bytes() == video_bytes
    serialized = json.dumps(json.loads((tmp_path / "run" / "kling_i2v_smoke_manifest.json").read_text(encoding="utf-8")))
    assert "https://signed.example" not in serialized
    assert "provider-secret-url" not in serialized
    assert "Bearer " not in serialized
    assert str(image_path) not in serialized
    assert manifest["outputs"][0]["provider_url_persisted"] is False


def test_kling_i2v_curl_transport_retries_tls_handshake_failure(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    image_path = tmp_path / "candidate.png"
    image_path.write_bytes(b"image-bytes")
    provider_store = store(tmp_path)
    video_bytes = b"fake-curl-i2v-mp4-bytes"
    create_attempts = 0

    def fake_run(command, *, input=None, capture_output=None, check=None):
        nonlocal create_attempts
        assert command == ["curl.exe", "-sS", "-i", "--config", "-"]
        assert capture_output is True
        assert check is False
        assert input is not None
        config_text = input.decode("utf-8")
        if 'url = "https://api-beijing.klingai.com/v1/videos/image2video"' in config_text:
            create_attempts += 1
            if create_attempts == 1:
                return Completed(
                    stdout=b"",
                    stderr=b"curl: (35) schannel: failed to receive handshake token=fake-secret-key",
                    returncode=35,
                )
            return Completed(stdout=curl_response({"code": 0, "data": {"task_id": "curl_i2v_task_456"}}))
        if 'url = "https://api-beijing.klingai.com/v1/videos/image2video/curl_i2v_task_456"' in config_text:
            return Completed(
                stdout=curl_response(
                    {
                        "code": 0,
                        "data": {
                            "task_id": "curl_i2v_task_456",
                            "task_status": "succeed",
                            "task_result": {
                                "videos": [
                                    {"url": "https://signed.example/i2v.mp4?token=provider-secret-url"}
                                ]
                            },
                        },
                    }
                )
            )
        if 'url = "https://signed.example/i2v.mp4?token=provider-secret-url"' in config_text:
            return Completed(stdout=b"HTTP/1.1 200 OK\r\nContent-Type: video/mp4\r\n\r\n" + video_bytes)
        raise AssertionError(f"unexpected curl config: {config_text}")

    monkeypatch.setattr("agentflow_studio.model_gateway.kling_transport.subprocess.run", fake_run)

    manifest = run_kling_i2v_smoke(
        provider_store,
        service_id="kling_i2v",
        prompt="slow push-in over the memory architecture board",
        image_path=image_path,
        output_dir=tmp_path / "run",
        poll_interval_sec=0,
        max_polls=2,
        transport="curl",
    )

    assert create_attempts == 2
    assert manifest["status"] == "succeeded"
    serialized = json.dumps(json.loads((tmp_path / "run" / "kling_i2v_smoke_manifest.json").read_text(encoding="utf-8")))
    assert "fake-secret-key" not in serialized
    assert "provider-secret-url" not in serialized
    assert "https://signed.example" not in serialized
