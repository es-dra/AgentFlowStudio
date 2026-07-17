from __future__ import annotations

import json
import wave
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def test_audio_generation_dispatch_writes_safe_wav_manifest_and_replays_idempotently(tmp_path, monkeypatch) -> None:
    config_path = _provider_config(tmp_path)
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config_path))
    monkeypatch.setenv("AFS_ALLOW_REMOTE_AUDIO", "true")
    monkeypatch.setenv("AUDIO_RELAY_API_KEY", "test-audio-key")
    audio_bytes = _wav_bytes(tmp_path / "speech.wav")
    calls: list[dict[str, object]] = []

    class Response:
        headers = {"Content-Type": "audio/wav"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return audio_bytes

    def fake_urlopen(request, timeout):
        calls.append(
            {
                "url": request.full_url,
                "timeout": timeout,
                "payload": json.loads(request.data.decode("utf-8")),
                "authorization_present": request.headers.get("Authorization") == "Bearer test-audio-key",
            }
        )
        return Response()

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_adapter_impl.urllib.request.urlopen", fake_urlopen)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    client.post("/projects", json={"project_id": "audio-project", "goal": "音频生成"})
    body = {
        "node_id": "audio-node-1",
        "episode_id": "episode-001",
        "scene_id": "scene-001",
        "shot_id": "shot-001",
        "prompt_text": "一句安静、清晰的中文旁白。",
        "generated_at": "2026-07-17T09:30:00Z",
        "cost_cap_cny": 5,
    }
    headers = {"X-Client-Request-ID": "audio-once-001"}

    first = client.post("/projects/audio-project/audio-generations", json=body, headers=headers)
    replay = client.post("/projects/audio-project/audio-generations", json=body, headers=headers)

    assert first.status_code == 200, first.text
    assert replay.status_code == 200, replay.text
    payload = first.json()
    replay_payload = replay.json()
    assert len(calls) == 1
    assert calls[0]["url"] == "https://audio-provider.example.test/v1/audio/speech"
    assert calls[0]["payload"] == {
        "model": "gpt-4o-mini-tts",
        "voice": "coral",
        "input": "一句安静、清晰的中文旁白。",
        "response_format": "wav",
    }
    assert calls[0]["authorization_present"] is True
    assert replay_payload["job"]["job_id"] == payload["job"]["job_id"]
    assert payload["status"] == "succeeded"
    assert payload["provider_calls_started"] is True
    assert payload["call_accounting"] == {
        "planned_calls": 1,
        "actual_calls": 1,
        "retry_count": 0,
        "max_paid_requests": 1,
        "double_dispatch_detected": False,
    }
    candidate = payload["candidate_previews"][0]
    assert candidate["audio_url"].startswith("/projects/audio-project/audio-generations/")
    assert candidate["mime_type"] == "audio/wav"
    assert candidate["byte_count"] == len(audio_bytes)
    assert candidate["duration_sec"] > 0
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert "test-audio-key" not in serialized
    assert "signed_url" not in serialized
    assert "/tmp/" not in serialized
    audio = client.get(candidate["audio_url"])
    assert audio.status_code == 200
    assert audio.headers["content-type"].startswith("audio/wav")
    assert audio.content == audio_bytes


def test_audio_generation_closed_gate_blocks_before_provider_dispatch(tmp_path, monkeypatch) -> None:
    config_path = _provider_config(tmp_path)
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config_path))
    monkeypatch.delenv("AFS_ALLOW_REMOTE_AUDIO", raising=False)
    monkeypatch.setenv("AUDIO_RELAY_API_KEY", "test-audio-key")

    def fail_urlopen(*_args, **_kwargs):
        raise AssertionError("provider dispatch should not start when audio gate is closed")

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_adapter_impl.urllib.request.urlopen", fail_urlopen)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    client.post("/projects", json={"project_id": "audio-gated", "goal": "音频关闭"})

    response = client.post(
        "/projects/audio-gated/audio-generations",
        json={"prompt_text": "不会发送给 provider", "generated_at": "2026-07-17T09:31:00Z"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["provider_calls_started"] is False
    assert payload["provider_gate"]["status"] == "blocked"
    assert payload["call_accounting"]["actual_calls"] == 0
    assert payload["safe_manifest"]["blocks"][0]["provider_calls_started"] is False


def test_audio_generation_is_project_auth_scoped_before_provider_dispatch(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_AUTH_ALLOW_OPEN_SIGNUP", "true")
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(_provider_config(tmp_path)))
    monkeypatch.setenv("AFS_ALLOW_REMOTE_AUDIO", "true")
    monkeypatch.setenv("AUDIO_RELAY_API_KEY", "test-audio-key")
    calls: list[object] = []

    def fake_urlopen(*_args, **_kwargs):
        calls.append(object())
        raise AssertionError("cross-user request must fail before provider dispatch")

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_adapter_impl.urllib.request.urlopen", fake_urlopen)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    owner_headers = _register(client, "owner@example.com")
    other_headers = _register(client, "other@example.com")
    created = client.post(
        "/projects",
        headers=owner_headers,
        json={"project_id": "owned-audio", "project_type": "studio_creator_authoring", "goal": "音频权限"},
    )
    assert created.status_code == 200

    denied = client.post(
        "/projects/owned-audio/audio-generations",
        headers=other_headers,
        json={"prompt_text": "越权音频", "generated_at": "2026-07-17T09:32:00Z"},
    )

    assert denied.status_code == 403
    assert calls == []


def _register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "strong-password-123", "display_name": email.split("@", 1)[0]},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['session_token']}"}


def _provider_config(tmp_path: Path) -> Path:
    path = tmp_path / "providers.local.json"
    path.write_text(json.dumps(_openai_tts_provider_config()), encoding="utf-8")
    return path


def _openai_tts_provider_config() -> dict:
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "audio_relay": {
                "auth_type": "api_key",
                "base_url": "https://audio-provider.example.test/v1",
                "api_key_env": "AUDIO_RELAY_API_KEY",
                "default_models": {"audio": "gpt-4o-mini-tts"},
            }
        },
        "account_pools": {
            "audio_relay_pool": {
                "accounts": [
                    {
                        "account_id": "audio_relay",
                        "service_id": "tts_relay",
                        "credential_env": "AUDIO_RELAY_API_KEY",
                        "enabled_capabilities": ["audio"],
                        "enabled": True,
                        "priority": 10,
                        "weight": 1,
                        "concurrency_limit": 1,
                        "health_state": "healthy",
                    }
                ]
            }
        },
        "services": {
            "tts_relay": {
                "provider": "openai_compatible_tts",
                "account_ref": "audio_relay",
                "capability": "audio",
                "endpoint": "/audio/speech",
                "model": "gpt-4o-mini-tts",
                "voice": "coral",
                "response_format": "wav",
                "required_gate": "AFS_ALLOW_REMOTE_AUDIO",
                "descriptor": {
                    "schema_version": "provider_descriptor.v0.1",
                    "modality": "audio",
                    "execution_mode": "sync",
                    "capabilities": ["audio"],
                    "account_pool_id": "audio_relay_pool",
                    "reference_image_slots": 0,
                    "supported_aspect_ratios": ["1:1"],
                    "prompt_char_limit": 4000,
                    "seed_supported": False,
                    "cost_hint": "test-only",
                    "rate_limit_hint": "test-only",
                    "required_gate": "AFS_ALLOW_REMOTE_AUDIO",
                },
            }
        },
    }


def _wav_bytes(path: Path) -> bytes:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16_000)
        handle.writeframes(b"\x00\x00" * 16_000)
    return path.read_bytes()
