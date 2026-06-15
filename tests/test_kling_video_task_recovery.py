from __future__ import annotations

import json

import pytest

from agentflow_studio.model_gateway import ModelProviderError
from agentflow_studio.model_gateway import kling_video_smoke
from tests.kling_video_smoke_helpers import Completed, curl_response, store


def test_i2v_curl_poll_failure_preserves_safe_task_state(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    image_path = tmp_path / "candidate.png"
    image_path.write_bytes(b"image-bytes")
    provider_store = store(tmp_path)

    def fake_run(command, *, input=None, capture_output=None, check=None):
        assert command == ["curl.exe", "-sS", "-i", "--config", "-"]
        assert capture_output is True
        assert check is False
        assert input is not None
        config_text = input.decode("utf-8")
        if 'url = "https://api-beijing.klingai.com/v1/videos/image2video"' in config_text:
            return Completed(
                stdout=curl_response(
                    {
                        "code": 0,
                        "data": {"task_id": "recoverable_i2v_task_123", "task_status": "submitted"},
                    }
                )
            )
        if 'url = "https://api-beijing.klingai.com/v1/videos/image2video/recoverable_i2v_task_123"' in config_text:
            return Completed(
                stdout=b"",
                stderr=(
                    b"curl: (35) schannel failure token=fake-secret-key "
                    b"https://signed.example/video.mp4?token=provider-secret-url"
                ),
                returncode=35,
            )
        raise AssertionError(f"unexpected curl config: {config_text}")

    monkeypatch.setattr("agentflow_studio.model_gateway.kling_transport.subprocess.run", fake_run)

    with pytest.raises(ModelProviderError) as exc_info:
        kling_video_smoke.run_kling_i2v_smoke(
            provider_store,
            service_id="kling_i2v",
            prompt="slow push-in over the memory architecture board",
            image_path=image_path,
            output_dir=tmp_path / "run",
            poll_interval_sec=0,
            max_polls=1,
            transport="curl",
        )

    message = str(exc_info.value)
    assert "GET request failed: CurlError(35)" in message
    assert "fake-secret-key" not in message
    assert "provider-secret-url" not in message
    assert "https://signed.example" not in message

    state_path = tmp_path / "run" / "kling_i2v_task_state.json"
    assert state_path.is_file()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["schema_version"] == "kling_video_task_state.v1"
    assert state["status"] == "poll_failed"
    assert state["service_id"] == "kling_i2v"
    assert state["api_family"] == "i2v"
    assert state["model"] == "kling-v3"
    assert state["task"]["task_id"] == "recoverable_i2v_task_123"
    assert state["input_image"]["path_persisted"] is False
    assert state["input_image"]["byte_count"] == len(b"image-bytes")

    serialized = json.dumps(state, ensure_ascii=False)
    assert "Bearer " not in serialized
    assert "fake-access-key" not in serialized
    assert "fake-secret-key" not in serialized
    assert "provider-secret-url" not in serialized
    assert "https://signed.example" not in serialized
    assert str(image_path) not in serialized
    assert not (tmp_path / "run" / "kling_i2v_smoke_manifest.json").exists()
    assert not (tmp_path / "run" / "video_candidates" / "candidate_001.mp4").exists()


def test_kling_video_resume_polls_safe_state_and_writes_manifest(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    provider_store = store(tmp_path)
    output_dir = tmp_path / "run"
    output_dir.mkdir()
    state_path = output_dir / "kling_i2v_task_state.json"
    state_path.write_text(
        json.dumps(
            {
                "schema_version": "kling_video_task_state.v1",
                "status": "poll_failed",
                "provider": "kling",
                "service_id": "kling_i2v",
                "api_family": "i2v",
                "capability": "video",
                "model": "kling-v3",
                "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
                "gate_status": "enabled",
                "input_image": {
                    "path_persisted": False,
                    "byte_count": 11,
                    "sha256": "safe-source-image-hash",
                },
                "task": {
                    "task_id": "recoverable_i2v_task_123",
                    "task_status": "submitted",
                    "task_status_msg_present": False,
                },
                "artifact_policy": {
                    "provider_urls_persisted": False,
                    "authorization_header_persisted": False,
                    "jwt_persisted": False,
                    "source_image_path_persisted": False,
                    "writes_long_term_memory": False,
                },
                "timestamps": {
                    "created_at": "2026-05-29T00:00:00Z",
                    "updated_at": "2026-05-29T00:00:00Z",
                },
                "claim_boundary": "provider_task_recovery_state_only_not_creative_quality",
            }
        ),
        encoding="utf-8",
    )
    video_bytes = b"fake-resumed-i2v-mp4-bytes"

    def fake_run(command, *, input=None, capture_output=None, check=None):
        assert command == ["curl.exe", "-sS", "-i", "--config", "-"]
        assert capture_output is True
        assert check is False
        assert input is not None
        config_text = input.decode("utf-8")
        if 'url = "https://api-beijing.klingai.com/v1/videos/image2video/recoverable_i2v_task_123"' in config_text:
            return Completed(
                stdout=curl_response(
                    {
                        "code": 0,
                        "data": {
                            "task_id": "recoverable_i2v_task_123",
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

    manifest = kling_video_smoke.resume_kling_video_task(
        provider_store,
        task_state_path=state_path,
        poll_interval_sec=0,
        max_polls=1,
        transport="curl",
    )

    assert manifest["status"] == "succeeded"
    assert manifest["api_family"] == "i2v"
    assert manifest["resumed_from_task_state"] is True
    assert manifest["task"]["task_id"] == "recoverable_i2v_task_123"
    assert (output_dir / "video_candidates" / "candidate_001.mp4").read_bytes() == video_bytes

    updated_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert updated_state["status"] == "succeeded"
    assert updated_state["task"]["task_status"] == "succeed"
    serialized = json.dumps(
        {
            "manifest": json.loads((output_dir / "kling_i2v_smoke_manifest.json").read_text(encoding="utf-8")),
            "state": updated_state,
        },
        ensure_ascii=False,
    )
    assert "Bearer " not in serialized
    assert "fake-access-key" not in serialized
    assert "fake-secret-key" not in serialized
    assert "provider-secret-url" not in serialized
    assert "https://signed.example" not in serialized


def test_i2v_runtime_single_poll_falls_back_to_curl_for_transient_httpx_error(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    provider_store = store(tmp_path)
    output_dir = tmp_path / "run"
    output_dir.mkdir()
    state = {
        "schema_version": "kling_video_task_state.v1",
        "status": "running",
        "provider": "kling",
        "service_id": "kling_i2v",
        "api_family": "i2v",
        "capability": "video",
        "model": "kling-v3",
        "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
        "task": {
            "task_id": "recoverable_i2v_task_456",
            "task_status": "submitted",
        },
    }
    calls: list[str] = []

    def fake_request_json_with_transport(transport: str):
        def fake_request(url, *, method, authorization, timeout_sec, payload=None):
            calls.append(transport)
            assert method == "GET"
            assert authorization.startswith("Bearer ")
            assert url.endswith("/v1/videos/image2video/recoverable_i2v_task_456")
            if transport == "httpx":
                raise ModelProviderError("Kling video request failed: ConnectError")
            return {
                "code": 0,
                "data": {
                    "task_id": "recoverable_i2v_task_456",
                    "task_status": "processing",
                },
            }

        return fake_request

    monkeypatch.setattr(kling_video_smoke, "request_json_with_transport", fake_request_json_with_transport)

    manifest = kling_video_smoke.poll_kling_i2v_task_once(
        provider_store,
        output_dir=output_dir,
        state=state,
        timeout_sec=1,
        transport="httpx",
    )

    assert calls == ["httpx", "curl"]
    assert manifest["status"] == "running"
    updated_state = json.loads((output_dir / "kling_i2v_task_state.json").read_text(encoding="utf-8"))
    assert updated_state["status"] == "running"
    assert updated_state["task"]["task_id"] == "recoverable_i2v_task_456"
