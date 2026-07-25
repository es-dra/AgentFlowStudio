from __future__ import annotations

import json
import subprocess
import base64
import hashlib
import wave
from pathlib import Path

import pytest

from agentflow_studio.model_gateway.company_secrets import load_company_provider_secrets
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest, ProviderRegistry
from agentflow_studio.model_gateway.provider_api_relay_images import openai_images_payload
from agentflow_studio.model_gateway import openai_compatible
from agentflow.algorithms.provider_gate_manifest import required_gate_for


def _store(tmp_path, payload: dict):
    path = tmp_path / "providers.local.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return load_company_provider_secrets(path)


def _codex_image_provider_config() -> dict:
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "local_codex": {
                "auth_type": "none",
                "execution_backend": "codex_exec",
                "cli_command": "codex",
                "default_models": {"image": "image2"},
            }
        },
        "account_pools": {
            "codex_image_pool": {
                "accounts": [
                    {
                        "account_id": "local_codex",
                        "service_id": "codex_image",
                        "enabled_capabilities": ["image"],
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
            "codex_image": {
                "provider": "codex_handoff",
                "account_ref": "local_codex",
                "capability": "image",
                "required_gate": "AFS_ALLOW_REMOTE_IMAGE",
                "descriptor": {
                    "schema_version": "provider_descriptor.v0.1",
                    "modality": "image",
                    "execution_mode": "async",
                    "capabilities": ["image"],
                    "account_pool_id": "codex_image_pool",
                    "reference_image_slots": 4,
                    "supported_aspect_ratios": ["1:1", "4:3", "3:4", "16:9", "9:16"],
                    "prompt_char_limit": 4000,
                    "seed_supported": True,
                    "cost_hint": "test-only",
                    "rate_limit_hint": "test-only",
                    "required_gate": "AFS_ALLOW_REMOTE_IMAGE",
                },
            }
        },
    }


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
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(48_000)
        stream.writeframes(b"\0\0" * 480)
    return path.read_bytes()


def _mp3_bytes() -> bytes:
    return b"ID3\x04\x00\x00\x00\x00\x00\x21" + b"\x00" * 64


def test_provider_registry_rejects_missing_descriptor(tmp_path) -> None:
    payload = _codex_image_provider_config()
    payload["services"]["codex_image"].pop("descriptor", None)
    store = _store(tmp_path, payload)

    with pytest.raises(ModelConfigError, match="descriptor"):
        ProviderRegistry.from_store(store)


@pytest.mark.parametrize(
        ("field", "value", "match"),
        [
        ("required_gate", "IMAGE_API_KEY", "required_gate"),
        ("reference_image_slots", -1, "reference_image_slots"),
        ("supported_aspect_ratios", ["wide"], "supported_aspect_ratios"),
    ],
)
def test_provider_registry_rejects_invalid_descriptor_fields(tmp_path, field, value, match) -> None:
    payload = _codex_image_provider_config()
    payload["services"]["codex_image"]["descriptor"][field] = value
    store = _store(tmp_path, payload)

    with pytest.raises(ModelConfigError, match=match):
        ProviderRegistry.from_store(store)


def test_provider_registry_exposes_codex_image_descriptor(tmp_path) -> None:
    store = _store(tmp_path, _codex_image_provider_config())
    registry = ProviderRegistry.from_store(store)

    descriptor = registry.descriptor("codex_image")

    assert descriptor.modality == "image"
    assert descriptor.capabilities == ["image"]
    assert descriptor.execution_mode == "async"
    assert descriptor.account_pool_id == "codex_image_pool"
    assert descriptor.reference_image_slots == 4
    assert descriptor.prompt_char_limit == 4000
    assert descriptor.rate_limit_hint == "test-only"
    assert descriptor.required_gate == "AFS_ALLOW_REMOTE_IMAGE"
    assert descriptor.image_edit_capabilities_present is False
    assert descriptor.image_edit_capabilities.supports_image_edit is False
    assert descriptor.image_edit_capabilities.supports_true_local_edit is False
    assert descriptor.image_edit_capabilities.local_edit_scope_kinds() == []
    assert descriptor.image_edit_capabilities.fallback_modes == []


def test_provider_registry_defaults_absent_image_edit_capabilities_to_blocked(tmp_path) -> None:
    payload = _codex_image_provider_config()
    payload["services"]["codex_image"]["descriptor"].pop("image_edit_capabilities", None)
    store = _store(tmp_path, payload)
    registry = ProviderRegistry.from_store(store)

    descriptor = registry.descriptor("codex_image")
    capabilities = descriptor.image_edit_capabilities

    assert descriptor.schema_version == "provider_descriptor.v0.1"
    assert descriptor.image_edit_capabilities_present is False
    assert capabilities.has_image_edit_claims() is False
    assert capabilities.supports_image_edit is False
    assert capabilities.supports_true_local_edit is False
    assert capabilities.local_edit_scope_kinds() == []
    assert capabilities.fallback_modes == []
    assert capabilities.local_edit_truth_label == "blocked_no_supported_local_edit"


def test_provider_registry_exposes_openai_compatible_tts_descriptor(tmp_path) -> None:
    store = _store(tmp_path, _openai_tts_provider_config())
    registry = ProviderRegistry.from_store(store)

    descriptor = registry.descriptor("tts_relay")

    assert descriptor.modality == "audio"
    assert descriptor.capabilities == ["audio"]
    assert descriptor.execution_mode == "sync"
    assert descriptor.account_pool_id == "audio_relay_pool"
    assert descriptor.reference_image_slots == 0
    assert descriptor.required_gate == "AFS_ALLOW_REMOTE_AUDIO"
    assert required_gate_for("audio") == "AFS_ALLOW_REMOTE_AUDIO"


def test_openai_compatible_tts_dispatch_writes_safe_wav_artifact(tmp_path, monkeypatch) -> None:
    store = _store(tmp_path, _openai_tts_provider_config())
    registry = ProviderRegistry.from_store(store)
    audio_bytes = _wav_bytes(tmp_path / "speech.wav")
    captured: dict[str, object] = {}

    class Response:
        headers = {"Content-Type": "audio/wav"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self) -> bytes:
            return audio_bytes

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["authorization_present"] = request.headers.get("Authorization") == "Bearer test-audio-key"
        return Response()

    monkeypatch.setenv("AFS_ALLOW_REMOTE_AUDIO", "true")
    monkeypatch.setenv("AUDIO_RELAY_API_KEY", "test-audio-key")
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_adapter_impl.urllib.request.urlopen", fake_urlopen)

    result = registry.dispatch(
        "audio",
        "tts_relay",
        ProviderDispatchRequest(
            prompt="Alpha narration line.",
            output_dir=tmp_path / "outputs",
            timeout_sec=7,
        ),
    )

    output = result["outputs"][0]
    written = tmp_path / "outputs" / output["audio_path"]
    serialized = json.dumps(result, ensure_ascii=False).lower()
    assert captured["url"] == "https://audio-provider.example.test/v1/audio/speech"
    assert captured["timeout"] == 7
    assert captured["payload"] == {
        "model": "gpt-4o-mini-tts",
        "voice": "coral",
        "input": "Alpha narration line.",
        "response_format": "wav",
    }
    assert captured["authorization_present"] is True
    assert result["provider_calls_started"] is True
    assert result["provider_raw_response_stored"] is False
    assert result["cost"]["actual_cost_status"] == "unknown_unverified"
    assert output["audio_path"] == "audio_candidates/candidate_001.wav"
    assert output["mime_type"] == "audio/wav"
    assert output["byte_count"] == len(audio_bytes)
    assert output["provider_audio_format"] == "wav"
    assert output["audio_normalization"]["provider_native_wav"] is True
    assert output["audio_normalization"]["normalized_locally"] is False
    assert written.read_bytes() == audio_bytes
    assert "test-audio-key" not in serialized
    assert "signed_url" not in serialized
    assert "/tmp/" not in serialized


def test_openai_compatible_tts_normalizes_mp3_provider_bytes_to_safe_wav(tmp_path, monkeypatch) -> None:
    store = _store(tmp_path, _openai_tts_provider_config())
    registry = ProviderRegistry.from_store(store)
    mp3_bytes = _mp3_bytes()
    normalized_wav = _wav_bytes(tmp_path / "normalized.wav")
    commands: list[list[str]] = []

    class Response:
        headers = {"Content-Type": "audio/mpeg"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self) -> bytes:
            return mp3_bytes

    def fake_urlopen(request, timeout):
        return Response()

    def fake_run(command, **kwargs):
        commands.append(command)
        assert kwargs["shell"] is False
        assert kwargs["timeout"] == 25
        assert "Authorization" not in json.dumps(kwargs)
        source = Path(command[7])
        destination = Path(command[-1])
        assert source.read_bytes() == mp3_bytes
        destination.write_bytes(normalized_wav)
        return subprocess.CompletedProcess(command, 0, "", "")

    normalizer = tmp_path / "ffmpeg-normalizer"
    normalizer.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    normalizer.chmod(0o755)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_AUDIO", "true")
    monkeypatch.setenv("AUDIO_RELAY_API_KEY", "test-audio-key")
    monkeypatch.setenv("AFS_AUDIO_NORMALIZER_FFMPEG", str(normalizer))
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_adapter_impl.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_adapter_impl.subprocess.run", fake_run)

    result = registry.dispatch(
        "audio",
        "tts_relay",
        ProviderDispatchRequest(
            prompt="Alpha narration line.",
            output_dir=tmp_path / "outputs",
            timeout_sec=7,
        ),
    )

    output = result["outputs"][0]
    written = tmp_path / "outputs" / output["audio_path"]
    assert commands and commands[0][0] == str(normalizer.resolve())
    assert written.read_bytes() == normalized_wav
    assert not (tmp_path / "outputs" / "audio_processing").exists()
    assert output["provider_audio_format"] == "mp3"
    assert output["audio_normalization"] == {
        "provider_returned_format": "mp3",
        "provider_content_type": "audio/mpeg",
        "source_sha256": hashlib.sha256(mp3_bytes).hexdigest(),
        "destination_format": "wav",
        "normalized_locally": True,
        "provider_native_wav": False,
        "normalizer": "ffmpeg",
        "destination_sha256": hashlib.sha256(normalized_wav).hexdigest(),
        "duration_sec": output["duration_sec"],
        "sample_rate_hz": 48000,
        "channels": 1,
        "sample_width_bytes": 2,
    }
    serialized = json.dumps(result, ensure_ascii=False).lower()
    assert "test-audio-key" not in serialized
    assert "signed_url" not in serialized
    assert "/tmp/" not in serialized


def test_openai_compatible_tts_fails_closed_when_mp3_normalizer_is_unavailable(tmp_path, monkeypatch) -> None:
    store = _store(tmp_path, _openai_tts_provider_config())
    registry = ProviderRegistry.from_store(store)

    class Response:
        headers = {"Content-Type": "audio/mpeg"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self) -> bytes:
            return _mp3_bytes()

    monkeypatch.setenv("AFS_ALLOW_REMOTE_AUDIO", "true")
    monkeypatch.setenv("AUDIO_RELAY_API_KEY", "test-audio-key")
    monkeypatch.delenv("AFS_AUDIO_NORMALIZER_FFMPEG", raising=False)
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_adapter_impl.shutil.which", lambda _name: None)
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_adapter_impl.urllib.request.urlopen", lambda *_args, **_kwargs: Response())

    with pytest.raises(ModelGatewayError, match="normalization tool is unavailable"):
        registry.dispatch(
            "audio",
            "tts_relay",
            ProviderDispatchRequest(prompt="Alpha narration line.", output_dir=tmp_path / "outputs", timeout_sec=7),
        )


@pytest.mark.parametrize("provider_bytes", [b'{"error":"not audio"}', b"<html>not audio</html>", b"not-audio"])
def test_openai_compatible_tts_fails_closed_for_unsupported_audio_payloads(tmp_path, monkeypatch, provider_bytes) -> None:
    store = _store(tmp_path, _openai_tts_provider_config())
    registry = ProviderRegistry.from_store(store)

    class Response:
        headers = {"Content-Type": "audio/wav"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self) -> bytes:
            return provider_bytes

    monkeypatch.setenv("AFS_ALLOW_REMOTE_AUDIO", "true")
    monkeypatch.setenv("AUDIO_RELAY_API_KEY", "test-audio-key")
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_adapter_impl.urllib.request.urlopen", lambda *_args, **_kwargs: Response())

    with pytest.raises(ModelGatewayError, match="unsupported audio container"):
        registry.dispatch(
            "audio",
            "tts_relay",
            ProviderDispatchRequest(prompt="Alpha narration line.", output_dir=tmp_path / "outputs", timeout_sec=7),
        )


def test_openai_compatible_tts_can_omit_unsupported_instructions(tmp_path, monkeypatch) -> None:
    payload = _openai_tts_provider_config()
    payload["services"]["tts_relay"]["model"] = "tts-1"
    payload["services"]["tts_relay"]["voice"] = "alloy"
    payload["services"]["tts_relay"]["supports_instructions"] = False
    store = _store(tmp_path, payload)
    registry = ProviderRegistry.from_store(store)
    audio_bytes = _wav_bytes(tmp_path / "speech.wav")
    captured: dict[str, object] = {}

    class Response:
        headers = {"Content-Type": "audio/wav"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self) -> bytes:
            return audio_bytes

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return Response()

    monkeypatch.setenv("AFS_ALLOW_REMOTE_AUDIO", "true")
    monkeypatch.setenv("AUDIO_RELAY_API_KEY", "test-audio-key")
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_adapter_impl.urllib.request.urlopen", fake_urlopen)

    registry.dispatch(
        "audio",
        "tts_relay",
        ProviderDispatchRequest(
            prompt="Alpha narration line.",
            output_dir=tmp_path / "outputs",
            timeout_sec=7,
            instructions="Speak with calm energy.",
        ),
    )

    assert captured["payload"] == {
        "model": "tts-1",
        "voice": "alloy",
        "input": "Alpha narration line.",
        "response_format": "wav",
    }


def test_provider_registry_builds_future_image_edit_descriptor_v03(tmp_path) -> None:
    payload = _codex_image_provider_config()
    payload["services"]["codex_image"]["descriptor"].update(
        {
            "schema_version": "provider_descriptor.v0.3",
            "image_edit_capabilities": {
                "supports_image_edit": True,
                "supports_true_local_edit": False,
                "supports_mask_asset": True,
                "supports_semantic_region": True,
                "supports_preserve_locks": "prompt_only",
                "supports_negative_locks": "prompt_only",
                "fallback_modes": ["provider_full_frame_edit", "reference_image_to_image_fallback"],
                "max_mask_count": 1,
                "max_reference_images": 1,
                "input_fidelity_modes": ["low", "high"],
                "local_edit_truth_label": "provider_masked_edit",
            },
        }
    )
    store = _store(tmp_path, payload)
    registry = ProviderRegistry.from_store(store)

    descriptor = registry.descriptor("codex_image")
    capabilities = descriptor.image_edit_capabilities

    assert descriptor.image_edit_capabilities_present is True
    assert capabilities.supports_image_edit is True
    assert capabilities.supports_true_local_edit is False
    assert capabilities.local_edit_scope_kinds() == ["mask_asset", "semantic_region"]
    assert capabilities.fallback_modes == ["provider_full_frame_edit", "reference_image_to_image_fallback"]
    assert capabilities.local_edit_truth_label == "provider_masked_edit"


def test_provider_registry_rejects_image_edit_capabilities_on_v01_descriptor(tmp_path) -> None:
    payload = _codex_image_provider_config()
    payload["services"]["codex_image"]["descriptor"]["image_edit_capabilities"] = {
        "supports_image_edit": True,
        "fallback_modes": ["provider_full_frame_edit"],
    }
    store = _store(tmp_path, payload)

    with pytest.raises(ModelConfigError, match="provider_descriptor.v0.3"):
        ProviderRegistry.from_store(store)


def test_provider_registry_rejects_true_local_edit_as_fallback_mode(tmp_path) -> None:
    payload = _codex_image_provider_config()
    payload["services"]["codex_image"]["descriptor"].update(
        {
            "schema_version": "provider_descriptor.v0.3",
            "image_edit_capabilities": {
                "supports_image_edit": True,
                "fallback_modes": ["true_local_edit"],
            },
        }
    )
    store = _store(tmp_path, payload)

    with pytest.raises(ModelConfigError, match="fallback_modes"):
        ProviderRegistry.from_store(store)


def test_provider_registry_normalizes_legacy_narratocut_gate_prefix(tmp_path) -> None:
    payload = _codex_image_provider_config()
    payload["services"]["codex_image"]["descriptor"]["required_gate"] = "NARRATOCUT_ALLOW_REMOTE_IMAGE"
    store = _store(tmp_path, payload)

    registry = ProviderRegistry.from_store(store)

    assert registry.descriptor("codex_image").required_gate == "AFS_ALLOW_REMOTE_IMAGE"


def test_provider_registry_ignores_company_gateway_aggregate_service(tmp_path) -> None:
    payload = _codex_image_provider_config()
    payload["services"]["company_gateway"] = {
        "provider": "company_gateway",
        "capability": "llm/asr/image/video",
        "required_gate": "task_specific_capability_gate",
        "descriptor": {
            "schema_version": "provider_descriptor.v0.1",
            "modality": "llm/asr/image/video",
            "execution_mode": "sync",
            "capabilities": ["llm", "image", "video", "asr"],
            "reference_image_slots": 0,
            "supported_aspect_ratios": ["1:1"],
            "prompt_char_limit": 12000,
            "seed_supported": False,
            "required_gate": "task_specific_capability_gate",
        },
    }
    store = _store(tmp_path, payload)

    registry = ProviderRegistry.from_store(store)

    assert registry.descriptor("codex_image").modality == "image"
    with pytest.raises(ModelConfigError, match="Provider service not found: company_gateway"):
        registry.descriptor("company_gateway")


def test_provider_registry_rejects_disabled_account_pool_entry(tmp_path, monkeypatch) -> None:
    payload = _codex_image_provider_config()
    payload["account_pools"]["codex_image_pool"]["accounts"][0]["enabled"] = False
    store = _store(tmp_path, payload)
    registry = ProviderRegistry.from_store(store)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")

    with pytest.raises(ModelConfigError, match="No enabled provider account"):
        registry.dispatch(
            "image",
            "codex_image",
            ProviderDispatchRequest(prompt="hello", output_dir=tmp_path, aspect_ratio="9:16"),
        )


def test_provider_registry_ignores_removed_minimax_provider_services(tmp_path) -> None:
    payload = _codex_image_provider_config()
    payload["accounts"]["old_image"] = {
        "auth_type": "api_key",
        "base_url": "https://image-provider.example.invalid",
        "api_key_env": "OLD_IMAGE_API_KEY",
        "default_models": {"image": "retired"},
    }
    payload["account_pools"]["old_image_pool"] = {
        "accounts": [
            {
                "account_id": "old_image",
                "service_id": "old_image",
                "enabled_capabilities": ["image"],
                "enabled": True,
                "priority": 10,
                "weight": 1,
                "concurrency_limit": 1,
                "health_state": "healthy",
            }
        ]
    }
    payload["services"]["old_image"] = {
        "provider": "minimax",
        "account_ref": "old_image",
        "capability": "image",
        "required_gate": "AFS_ALLOW_REMOTE_IMAGE",
        "descriptor": {
            "schema_version": "provider_descriptor.v0.1",
            "modality": "image",
            "execution_mode": "sync",
            "capabilities": ["image"],
            "account_pool_id": "old_image_pool",
            "reference_image_slots": 1,
            "supported_aspect_ratios": ["9:16"],
            "prompt_char_limit": 1500,
            "seed_supported": True,
            "cost_hint": "retired",
            "rate_limit_hint": "retired",
            "required_gate": "AFS_ALLOW_REMOTE_IMAGE",
        },
    }
    store = _store(tmp_path, payload)
    registry = ProviderRegistry.from_store(store)

    with pytest.raises(ModelConfigError, match="Provider service not found: old_image"):
        registry.descriptor("old_image")



def test_provider_registry_dispatches_openai_compatible_llm(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_send(self, payload, api_key):
        captured["payload"] = payload
        captured["api_key"] = api_key
        return {"choices": [{"message": {"content": "enhanced text"}}]}

    monkeypatch.setattr(openai_compatible.OpenAICompatibleProvider, "_send_request", fake_send)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setenv("AFS_TEST_LLM_KEY", "secret-value")
    store = _store(tmp_path, _provider_gateway_config())
    registry = ProviderRegistry.from_store(store)

    result = registry.dispatch(
        "llm",
        "openai_text",
        ProviderDispatchRequest(prompt="Improve this prompt", output_dir=tmp_path, task_type="prompt_enhancement"),
    )

    assert result["text"] == "enhanced text"
    assert result["provider_calls_started"] is True
    assert captured["payload"]["model"] == "gpt-test"
    assert captured["payload"]["messages"][0]["role"] == "system"
    assert "strict prompt formatter" in captured["payload"]["messages"][0]["content"]
    assert captured["payload"]["messages"][1] == {"role": "user", "content": "Improve this prompt"}
    assert captured["api_key"] == "secret-value"


def test_provider_registry_dispatches_codex_local_llm(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(args, **kwargs):
        work_dir = Path(kwargs["cwd"])
        captured["args"] = args
        captured["kwargs"] = kwargs
        captured["request"] = json.loads((work_dir / "request.json").read_text(encoding="utf-8"))
        captured["prompt"] = (work_dir / "prompt.md").read_text(encoding="utf-8")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="优化后的提示词", stderr="")

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_codex_local.subprocess.run", fake_run)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setenv("AFS_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("AFS_CODEX_BOOTSTRAP", "false")
    registry = ProviderRegistry.from_store(_store(tmp_path, _codex_local_provider_config()))

    result = registry.dispatch(
        "llm",
        "prompt_optimizer",
        ProviderDispatchRequest(prompt="优化这个提示词", output_dir=tmp_path, task_type="prompt_enhancement"),
    )

    assert result == {"text": "优化后的提示词", "provider_calls_started": True}
    assert captured["args"][:2] == ["codex", "exec"]
    assert Path(captured["kwargs"]["env"]["CODEX_HOME"]) == tmp_path / "runtime" / "codex-home"
    assert captured["request"]["service_id"] == "prompt_optimizer"
    assert captured["request"]["capability"] == "llm"
    assert "AFS_MODEL_RELAY_API_KEY" not in json.dumps(captured, ensure_ascii=False)


def test_provider_registry_dispatches_codex_local_vision_with_safe_observation(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}
    reference = tmp_path / "reference.png"
    reference.write_bytes(_png_bytes())

    def fake_run(args, **kwargs):
        work_dir = Path(kwargs["cwd"])
        captured["kwargs"] = kwargs
        request = json.loads((work_dir / "request.json").read_text(encoding="utf-8"))
        copied = work_dir / request["reference_images"][0]["path"]
        captured["copied_reference_exists"] = copied.is_file()
        captured["request"] = request
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps(
                {
                    "observation": {
                        "description": "A rain rooftop character reference.",
                        "summary": "Rain rooftop character.",
                        "labels": ["character"],
                        "feature_card": {"identity": "Lin Wan"},
                    }
                }
            ),
            stderr="",
        )

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_codex_local.subprocess.run", fake_run)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VISION", "true")
    monkeypatch.setenv("AFS_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("AFS_CODEX_BOOTSTRAP", "false")
    registry = ProviderRegistry.from_store(_store(tmp_path, _codex_local_provider_config()))

    result = registry.dispatch(
        "vision",
        "vision_image",
        ProviderDispatchRequest(prompt="Describe this image", output_dir=tmp_path, reference_image_paths=(reference,)),
    )

    assert captured["copied_reference_exists"] is True
    assert Path(captured["kwargs"]["env"]["CODEX_HOME"]) == tmp_path / "runtime" / "codex-home"
    assert captured["request"]["service_id"] == "vision_image"
    assert result["status"] == "succeeded"
    assert result["provider_calls_started"] is True
    assert result["provider_raw_response_stored"] is False
    assert result["provider_observation"]["description"] == "A rain rooftop character reference."
    assert result["provider_observation"]["feature_card"] == {"identity": "Lin Wan"}
    assert result["safe_manifest"]["local_paths_returned_by_api"] is False


def test_provider_registry_blocks_llm_before_network_when_gate_closed(tmp_path, monkeypatch) -> None:
    called = {"count": 0}

    def fake_send(self, payload, api_key):
        called["count"] += 1
        return {"choices": [{"message": {"content": "should not happen"}}]}

    monkeypatch.setattr(openai_compatible.OpenAICompatibleProvider, "_send_request", fake_send)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    monkeypatch.setenv("AFS_TEST_LLM_KEY", "secret-value")
    store = _store(tmp_path, _provider_gateway_config())
    registry = ProviderRegistry.from_store(store)

    with pytest.raises(ModelGatewayError, match="AFS_ALLOW_REMOTE_LLM"):
        registry.dispatch(
            "llm",
            "openai_text",
            ProviderDispatchRequest(prompt="hello", output_dir=tmp_path),
        )

    assert called["count"] == 0


def test_provider_registry_supports_fake_vision_descriptor_and_gate(tmp_path, monkeypatch) -> None:
    payload = _provider_gateway_config()
    payload["accounts"]["fake_vision_account"] = {
        "auth_type": "none",
        "base_url": "https://vision.example.test",
        "default_models": {"vision": "fake-vision"},
    }
    payload["account_pools"]["vision_pool"] = {
        "accounts": [
            {
                "account_id": "fake_vision_account",
                "service_id": "fake_vision",
                "enabled_capabilities": ["vision"],
                "enabled": True,
                "priority": 10,
                "weight": 1,
                "concurrency_limit": 1,
                "health_state": "healthy",
            }
        ]
    }
    payload["services"]["fake_vision"] = {
        "provider": "fake",
        "account_ref": "fake_vision_account",
        "capability": "vision",
        "descriptor": {
            "schema_version": "provider_descriptor.v0.1",
            "modality": "vision",
            "execution_mode": "sync",
            "capabilities": ["vision"],
            "account_pool_id": "vision_pool",
            "reference_image_slots": 8,
            "supported_aspect_ratios": ["1:1"],
            "prompt_char_limit": 3000,
            "seed_supported": False,
            "cost_hint": "fake-only",
            "rate_limit_hint": "fake-only",
        },
    }
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VISION", raising=False)
    registry = ProviderRegistry.from_store(_store(tmp_path, payload))

    descriptor = registry.descriptor("fake_vision")
    assert descriptor.modality == "vision"
    assert descriptor.required_gate == "AFS_ALLOW_REMOTE_VISION"
    with pytest.raises(ModelGatewayError, match="AFS_ALLOW_REMOTE_VISION"):
        registry.dispatch(
            "vision",
            "fake_vision",
            ProviderDispatchRequest(prompt="Describe this image", output_dir=tmp_path, reference_image_paths=("img_1",)),
        )

    monkeypatch.setenv("AFS_ALLOW_REMOTE_VISION", "true")
    result = registry.dispatch(
        "vision",
        "fake_vision",
        ProviderDispatchRequest(prompt="Describe this image", output_dir=tmp_path, reference_image_paths=("img_1",)),
    )
    assert result["status"] == "succeeded"
    assert result["provider_calls_started"] is True
    assert result["safe_manifest"]["provider_raw_response_stored"] is False


def test_provider_registry_supports_fake_async_video_lifecycle(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    store = _store(tmp_path, _provider_gateway_config())
    registry = ProviderRegistry.from_store(store)

    result = registry.dispatch(
        "video",
        "fake_video",
        ProviderDispatchRequest(prompt="A calm camera move", output_dir=tmp_path, aspect_ratio="9:16"),
    )

    assert result["status"] == "succeeded"
    assert result["execution_mode"] == "async"
    assert result["task_id"].startswith("fake_video_")
    assert result["provider_calls_started"] is False


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("frame_slots", {"first_frame": "maybe"}, "frame_slots"),
        ("supported_durations_sec", [0], "supported_durations_sec"),
        ("supported_resolutions", ["wide"], "supported_resolutions"),
    ],
)
def test_provider_registry_rejects_invalid_video_descriptor_v02_fields(tmp_path, field, value, match) -> None:
    payload = _seedance_provider_config()
    payload["services"]["seedance_i2v"]["descriptor"][field] = value
    store = _store(tmp_path, payload)

    with pytest.raises(ModelConfigError, match=match):
        ProviderRegistry.from_store(store)


def test_provider_registry_builds_seedance_i2v_adapter_descriptor_v02(tmp_path) -> None:
    store = _store(tmp_path, _seedance_provider_config())
    registry = ProviderRegistry.from_store(store)

    descriptor = registry.descriptor("seedance_i2v")

    assert descriptor.schema_version == "provider_descriptor.v0.2"
    assert descriptor.modality == "video"
    assert descriptor.execution_mode == "async"
    assert descriptor.frame_slots == {"first_frame": "required", "last_frame": "optional"}
    assert descriptor.frame_modes == ["first_frame", "first_last_frame"]
    assert descriptor.supported_durations_sec == [5, 10]
    assert descriptor.supported_resolutions == ["480p", "720p"]
    assert descriptor.prompt_profile == "video_i2v_v1"


def test_provider_registry_uses_deepseek_default_model_when_ref_blank(tmp_path, monkeypatch) -> None:
    payload = _provider_gateway_config()
    payload["accounts"]["deepseek"] = {
        "auth_type": "bearer",
        "base_url": "https://api.deepseek.com",
        "api_key": "fake-deepseek-key",
        "default_models": {"llm": ""},
    }
    payload["services"]["deepseek_llm"] = {
        "provider": "deepseek",
        "account_ref": "deepseek",
        "capability": "llm",
        "default_model_ref": "accounts.deepseek.default_models.llm",
        "required_gate": "AFS_ALLOW_REMOTE_LLM",
        "descriptor": {
            "schema_version": "provider_descriptor.v0.1",
            "modality": "llm",
            "execution_mode": "sync",
            "capabilities": ["llm"],
            "reference_image_slots": 0,
            "supported_aspect_ratios": ["1:1"],
            "prompt_char_limit": 5000,
            "seed_supported": False,
            "cost_hint": "test-only",
            "rate_limit_hint": "test-only",
            "required_gate": "AFS_ALLOW_REMOTE_LLM",
        },
    }
    captured: dict[str, object] = {}

    def fake_send(self, payload, api_key):
        captured["payload"] = payload
        captured["api_key"] = api_key
        return {"choices": [{"message": {"content": "legacy deepseek llm ok"}}]}

    monkeypatch.setattr(openai_compatible.OpenAICompatibleProvider, "_send_request", fake_send)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    store = _store(tmp_path, payload)
    registry = ProviderRegistry.from_store(store)

    result = registry.dispatch(
        "llm",
        "deepseek_llm",
        ProviderDispatchRequest(prompt="Improve this prompt", output_dir=tmp_path, task_type="prompt_enhancement"),
    )

    assert registry.descriptor("deepseek_llm").required_gate == "AFS_ALLOW_REMOTE_LLM"
    assert result["text"] == "legacy deepseek llm ok"
    assert captured["payload"]["model"] == "deepseek-chat"
    assert captured["api_key"] == "fake-deepseek-key"


def test_provider_registry_ignores_legacy_minimax_image_service(tmp_path) -> None:
    payload = _codex_image_provider_config()
    payload["services"]["minimax_image"] = {
        "provider": "minimax",
        "account_ref": "minimax",
        "capability": "image",
        "required_gate": "NARRATO" + "CUT_ALLOW_REMOTE_IMAGE",
    }
    store = _store(tmp_path, payload)
    registry = ProviderRegistry.from_store(store)

    with pytest.raises(ModelConfigError, match="Provider service not found: minimax_image"):
        registry.descriptor("minimax_image")


def test_provider_registry_dispatches_api_relay_llm(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _JsonResponse({"text": "relay enhanced text"})

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_api_relay.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setenv("AFS_MODEL_RELAY_BASE_URL", "https://relay.example.test")
    monkeypatch.setenv("AFS_MODEL_RELAY_API_KEY", "secret-relay-key")
    registry = ProviderRegistry.from_store(_store(tmp_path, _api_relay_provider_config()))

    result = registry.dispatch(
        "llm",
        "prompt_optimizer",
        ProviderDispatchRequest(prompt="Improve this prompt", output_dir=tmp_path, task_type="prompt_enhancement"),
    )

    assert result == {"text": "relay enhanced text", "provider_calls_started": True}
    assert captured["url"] == "https://relay.example.test/v1/afs/llm"
    assert captured["authorization"] == "Bearer secret-relay-key"
    assert captured["payload"]["service_id"] == "prompt_optimizer"
    assert captured["payload"]["capability"] == "llm"
    assert captured["payload"]["prompt"] == "Improve this prompt"


def test_provider_registry_dispatches_api_relay_vision_with_safe_evidence(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _JsonResponse(
            {
                "observation": {
                    "description": "A rain rooftop character reference.",
                    "summary": "Rain rooftop character.",
                    "labels": ["character"],
                    "feature_card": {"identity": "Lin Wan"},
                },
                "safe_evidence": {"relay_trace_id": "trace_001"},
            }
        )

    reference = tmp_path / "reference.png"
    reference.write_bytes(_png_bytes())
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_api_relay.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VISION", "true")
    monkeypatch.setenv("AFS_MODEL_RELAY_BASE_URL", "https://relay.example.test")
    monkeypatch.setenv("AFS_MODEL_RELAY_API_KEY", "secret-relay-key")
    registry = ProviderRegistry.from_store(_store(tmp_path, _api_relay_provider_config()))

    result = registry.dispatch(
        "vision",
        "vision_image",
        ProviderDispatchRequest(prompt="Describe this image", output_dir=tmp_path, reference_image_paths=(reference,)),
    )

    assert result["status"] == "succeeded"
    assert result["provider_calls_started"] is True
    assert result["provider_raw_response_stored"] is False
    assert result["provider_observation"]["description"] == "A rain rooftop character reference."
    assert result["provider_observation"]["feature_card"] == {"identity": "Lin Wan"}
    assert captured["payload"]["reference_images"][0]["mime_type"] == "image/png"
    assert "data_base64" in captured["payload"]["reference_images"][0]
    assert "secret-relay-key" not in json.dumps(result, ensure_ascii=False)


def test_provider_registry_dispatches_api_relay_image_and_writes_candidates(tmp_path, monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        payload = json.loads(request.data.decode("utf-8"))
        assert payload["capability"] == "image"
        assert payload["aspect_ratio"] == "9:16"
        return _JsonResponse({"images": [{"data_base64": base64.b64encode(_png_bytes()).decode("ascii")} ]})

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_api_relay.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setenv("AFS_MODEL_RELAY_BASE_URL", "https://relay.example.test")
    monkeypatch.setenv("AFS_MODEL_RELAY_API_KEY", "secret-relay-key")
    registry = ProviderRegistry.from_store(_store(tmp_path, _api_relay_provider_config(include_image=True)))

    result = registry.dispatch(
        "image",
        "relay_image",
        ProviderDispatchRequest(prompt="Generate a clean keyframe", output_dir=tmp_path / "run", aspect_ratio="9:16"),
    )

    assert result["status"] == "succeeded"
    assert result["provider_calls_started"] is True
    assert result["outputs"][0]["candidate_id"] == "candidate_001"
    assert result["outputs"][0]["image_path"] == "image_candidates/candidate_001.png"
    assert (tmp_path / "run" / "image_candidates" / "candidate_001.png").is_file()
    assert "secret-relay-key" not in json.dumps(result, ensure_ascii=False)


def test_provider_registry_dispatches_api_relay_openai_images_url_response(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        if request.full_url == "https://api.crazyrouter.com/v1/images/generations":
            captured["authorization"] = request.get_header("Authorization")
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return _JsonResponse({"data": [{"url": "https://pub-82fd2ca4648e49a9b89dc6f4b28873ff.r2.dev/task-artifacts/result.png"}]})
        if request.full_url == "https://pub-82fd2ca4648e49a9b89dc6f4b28873ff.r2.dev/task-artifacts/result.png":
            captured["downloaded"] = True
            return _BytesResponse(_png_bytes())
        raise AssertionError(f"unexpected URL: {request.full_url}")

    config = _api_relay_provider_config(include_image=True)
    account = config["accounts"]["model_relay"]
    account["base_url"] = "https://api.crazyrouter.com/v1"
    account["default_models"]["image"] = "gpt-image-2"
    service = config["services"]["relay_image"]
    service["endpoint"] = "/images/generations"
    service["model"] = "gpt-image-2"
    service["request_format"] = "openai_images"
    service["quality"] = "low"
    service["output_format"] = "png"
    service["account_ref"] = "crazyrouter"
    service["descriptor"]["reference_image_slots"] = 16
    service["allowed_artifact_hosts"] = []
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_api_relay.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_api_relay_images.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setenv("AFS_MODEL_RELAY_API_KEY", "secret-relay-key")
    registry = ProviderRegistry.from_store(_store(tmp_path, config))

    assert registry.descriptor("relay_image").reference_image_slots == 16
    result = registry.dispatch(
        "image",
        "relay_image",
        ProviderDispatchRequest(prompt="Generate a clean asset sheet", output_dir=tmp_path / "run", aspect_ratio="9:16"),
    )

    assert captured["authorization"] == "Bearer secret-relay-key"
    assert captured["payload"] == {
        "model": "gpt-image-2",
        "prompt": "Generate a clean asset sheet",
        "n": 1,
        "size": "720x1280",
        "quality": "low",
        "output_format": "png",
    }
    assert captured["downloaded"] is True
    assert captured["timeout"] == 120.0
    assert result["outputs"][0]["image_path"] == "image_candidates/candidate_001.png"
    assert result["outputs"][0]["provider_url_persisted"] is False
    assert (tmp_path / "run" / "image_candidates" / "candidate_001.png").is_file()
    assert "r2.dev" not in json.dumps(result, ensure_ascii=False)
    assert "secret-relay-key" not in json.dumps(result, ensure_ascii=False)


@pytest.mark.parametrize("image_operation", ["generate", "edit"])
def test_openai_images_extra_body_cannot_override_exact_request_model(tmp_path, image_operation: str) -> None:
    source_image = tmp_path / "source.png"
    source_image.write_bytes(_png_bytes())
    request = ProviderDispatchRequest(
        prompt="Preserve the canonical production state.",
        output_dir=tmp_path / "run",
        image_operation=image_operation,
        edit_source_image_path=source_image if image_operation == "edit" else None,
    )

    with pytest.raises(ModelConfigError, match="extra_body cannot override request field: model"):
        openai_images_payload(
            service={"extra_body": {"model": "gpt-image-2-preview"}},
            model="gpt-image-2",
            request=request,
        )


def test_openai_images_extra_body_allows_same_model_and_new_extension_fields(tmp_path) -> None:
    payload = openai_images_payload(
        service={"extra_body": {"model": "gpt-image-2", "background": "opaque"}},
        model="gpt-image-2",
        request=ProviderDispatchRequest(
            prompt="Preserve the canonical production state.",
            output_dir=tmp_path / "run",
        ),
    )

    assert payload["model"] == "gpt-image-2"
    assert payload["background"] == "opaque"


def test_provider_registry_reports_openai_images_download_timeout_stage(tmp_path, monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        if request.full_url == "https://api.crazyrouter.com/v1/images/generations":
            return _JsonResponse({"data": [{"url": "http://251000800.vod2.myqcloud.com/task-artifacts/result.png"}]})
        if request.full_url == "http://251000800.vod2.myqcloud.com/task-artifacts/result.png":
            raise TimeoutError("The read operation timed out")
        raise AssertionError(f"unexpected URL: {request.full_url}")

    config = _api_relay_provider_config(include_image=True)
    account = config["accounts"]["model_relay"]
    account["base_url"] = "https://api.crazyrouter.com/v1"
    account["default_models"]["image"] = "gpt-image-2"
    service = config["services"]["relay_image"]
    service["endpoint"] = "/images/generations"
    service["model"] = "gpt-image-2"
    service["request_format"] = "openai_images"
    service["account_ref"] = "crazyrouter"
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_api_relay.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_api_relay_images.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setenv("AFS_MODEL_RELAY_API_KEY", "secret-relay-key")
    registry = ProviderRegistry.from_store(_store(tmp_path, config))

    with pytest.raises(ModelGatewayError, match="image URL download timed out"):
        registry.dispatch(
            "image",
            "relay_image",
            ProviderDispatchRequest(prompt="Generate a clean asset sheet", output_dir=tmp_path / "run", aspect_ratio="9:16"),
        )


def test_provider_registry_dispatches_api_relay_openai_images_edit_with_source_image_field(
    tmp_path,
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}
    source_image = tmp_path / "robot-source.png"
    source_image.write_bytes(_png_bytes())

    def fake_urlopen(request, timeout):
        if request.full_url == "https://api.crazyrouter.com/v1/images/edits":
            captured["authorization"] = request.get_header("Authorization")
            captured["content_type"] = request.get_header("Content-type")
            captured["body"] = request.data.decode("latin1")
            captured["timeout"] = timeout
            return _JsonResponse({"data": [{"b64_json": base64.b64encode(_png_bytes()).decode("ascii")}]})
        raise AssertionError(f"unexpected URL: {request.full_url}")

    config = _api_relay_provider_config(include_image=True)
    account = config["accounts"]["model_relay"]
    account["base_url"] = "https://api.crazyrouter.com/v1"
    account["default_models"]["image"] = "gpt-image-2"
    service = config["services"]["relay_image"]
    service["endpoint"] = "/images/generations"
    service["model"] = "gpt-image-2"
    service["request_format"] = "openai_images"
    service["quality"] = "low"
    service["output_format"] = "png"
    service["descriptor"].update(
        {
            "schema_version": "provider_descriptor.v0.3",
            "reference_image_slots": 4,
            "image_edit_capabilities": {
                "supports_image_edit": True,
                "supports_true_local_edit": False,
                "supports_preserve_locks": "prompt_only",
                "supports_negative_locks": "prompt_only",
                "fallback_modes": ["provider_full_frame_edit"],
                "max_reference_images": 4,
                "input_fidelity_modes": ["low", "high"],
                "local_edit_truth_label": "provider_full_frame_edit",
            },
        }
    )
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_api_relay_http.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setenv("AFS_MODEL_RELAY_API_KEY", "secret-relay-key")
    registry = ProviderRegistry.from_store(_store(tmp_path, config))
    assert registry.descriptor("relay_image").reference_image_slots == 4

    result = registry.dispatch(
        "image",
        "relay_image",
        ProviderDispatchRequest(
            prompt="Change only the metal body surface into plush fabric while preserving the same robot.",
            output_dir=tmp_path / "run",
            aspect_ratio="16:9",
            image_operation="edit",
            reference_image_paths=(source_image,),
            edit_source_image_path=source_image,
            edit_reference_image_paths=(source_image,),
            image_input_fidelity="high",
        ),
    )

    body = str(captured["body"])
    assert captured["authorization"] == "Bearer secret-relay-key"
    assert "multipart/form-data" in str(captured["content_type"])
    assert 'name="model"' in body and "gpt-image-2" in body
    assert 'name="prompt"' in body and "Change only the metal body surface into plush fabric" in body
    assert 'name="input_fidelity"' in body and "high" in body
    assert 'name="image"; filename="reference_001.png"' in body
    assert captured["timeout"] == 120.0
    assert result["outputs"][0]["image_path"] == "image_candidates/candidate_001.png"
    assert "secret-relay-key" not in json.dumps(result, ensure_ascii=False)


def test_openai_images_edit_preserves_reference_order_and_enforces_safe_limits(
    tmp_path,
    monkeypatch,
) -> None:
    captured: dict[str, str] = {}
    references = []
    for index in range(1, 4):
        path = tmp_path / f"user-name-{index}.png"
        path.write_bytes(_png_bytes())
        references.append(path)

    def fake_urlopen(request, timeout):
        captured["body"] = request.data.decode("latin1")
        return _JsonResponse({"data": [{"b64_json": base64.b64encode(_png_bytes()).decode("ascii")}]})

    config = _api_relay_provider_config(include_image=True)
    account = config["accounts"]["model_relay"]
    account["base_url"] = "https://api.crazyrouter.com/v1"
    account["default_models"]["image"] = "gpt-image-2"
    service = config["services"]["relay_image"]
    service.update(
        {
            "endpoint": "/images/generations",
            "edit_endpoint": "/images/edits",
            "model": "gpt-image-2",
            "request_format": "openai_images",
        }
    )
    service["descriptor"].update(
        {
            "schema_version": "provider_descriptor.v0.3",
            "reference_image_slots": 4,
            "image_edit_capabilities": {
                "supports_image_edit": True,
                "supports_true_local_edit": False,
                "supports_preserve_locks": "prompt_only",
                "supports_negative_locks": "prompt_only",
                "fallback_modes": ["provider_full_frame_edit"],
                "max_reference_images": 4,
                "input_fidelity_modes": ["low", "high"],
                "local_edit_truth_label": "provider_full_frame_edit",
            },
        }
    )
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_api_relay_http.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setenv("AFS_MODEL_RELAY_API_KEY", "test-key")
    registry = ProviderRegistry.from_store(_store(tmp_path, config))

    registry.dispatch(
        "image",
        "relay_image",
        ProviderDispatchRequest(
            prompt="Preserve approved identities and continuity.",
            output_dir=tmp_path / "run",
            image_operation="edit",
            edit_source_image_path=references[0],
            edit_reference_image_paths=tuple(references),
            reference_image_paths=tuple(references),
            image_input_fidelity="high",
        ),
    )
    body = captured["body"]
    first = body.index('filename="reference_001.png"')
    second = body.index('filename="reference_002.png"')
    third = body.index('filename="reference_003.png"')
    assert first < second < third
    assert "user-name-" not in body

    too_many = tuple([*references, tmp_path / "four.png", tmp_path / "five.png"])
    too_many[3].write_bytes(_png_bytes())
    too_many[4].write_bytes(_png_bytes())
    with pytest.raises(ModelConfigError, match="reference_image_slots exceeded"):
        registry.dispatch(
            "image",
            "relay_image",
            ProviderDispatchRequest(
                prompt="Too many references",
                output_dir=tmp_path / "blocked-count",
                image_operation="edit",
                edit_source_image_path=too_many[0],
                edit_reference_image_paths=too_many,
                reference_image_paths=too_many,
            ),
        )

    oversized = tmp_path / "oversized.png"
    oversized.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * (8 * 1024 * 1024))
    with pytest.raises(ModelGatewayError, match="per-file byte limit"):
        registry.dispatch(
            "image",
            "relay_image",
            ProviderDispatchRequest(
                prompt="Oversized reference",
                output_dir=tmp_path / "blocked-size",
                image_operation="edit",
                edit_source_image_path=oversized,
                edit_reference_image_paths=(oversized,),
                reference_image_paths=(oversized,),
            ),
        )


def test_provider_registry_projects_legacy_codex_image_api_relay_to_image_relay(tmp_path) -> None:
    config = _api_relay_provider_config(include_image=True)
    service = config["services"].pop("relay_image")
    service["endpoint"] = "/images/generations"
    service["request_format"] = "openai_images"
    service["model"] = "gpt-image-2"
    service["descriptor"]["account_pool_id"] = "codex_image_pool"
    service["descriptor"]["reference_image_slots"] = 0
    config["services"]["codex_image"] = service
    pool = config["account_pools"].pop("image_pool")
    pool["accounts"][0]["service_id"] = "codex_image"
    config["account_pools"]["codex_image_pool"] = pool

    store = _store(tmp_path, config)
    registry = ProviderRegistry.from_store(store)

    assert "codex_image" not in store.services
    assert "codex_image_pool" not in store.account_pools
    assert store.services["image_relay"]["provider"] == "api_relay"
    assert store.services["image_relay"]["edit_endpoint"] == "/images/edits"
    assert store.account_pools["image_relay_pool"]["accounts"][0]["service_id"] == "image_relay"
    descriptor = registry.descriptor("image_relay")
    assert descriptor.account_pool_id == "image_relay_pool"
    assert descriptor.schema_version == "provider_descriptor.v0.3"
    assert descriptor.reference_image_slots == 4
    assert descriptor.image_edit_capabilities.supports_image_edit is True
    assert descriptor.image_edit_capabilities.max_reference_images == 4
    assert descriptor.image_edit_capabilities.input_fidelity_modes == []
    with pytest.raises(ModelConfigError, match="Provider service not found: codex_image"):
        registry.descriptor("codex_image")


def test_projected_gpt_image_2_relay_uses_edits_ordered_files_and_omits_fixed_fidelity(
    tmp_path,
    monkeypatch,
) -> None:
    captured: dict[str, str] = {}
    references = []
    for index in range(1, 3):
        suffix = ".png" if index == 1 else ".untrusted"
        path = tmp_path / f"private-reference-{index}{suffix}"
        path.write_bytes(_png_bytes())
        references.append(path)

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = request.data.decode("latin1")
        captured["content_type"] = request.get_header("Content-type")
        return _JsonResponse({"data": [{"b64_json": base64.b64encode(_png_bytes()).decode("ascii")}]})

    config = _api_relay_provider_config(include_image=True)
    config["accounts"]["model_relay"]["base_url"] = "https://api.crazyrouter.com/v1"
    service = config["services"].pop("relay_image")
    service.update(
        {
            "endpoint": "/images/generations",
            "request_format": "openai_images",
            "model": "gpt-image-2",
        }
    )
    service["descriptor"]["account_pool_id"] = "codex_image_pool"
    service["descriptor"]["reference_image_slots"] = 0
    config["services"]["codex_image"] = service
    pool = config["account_pools"].pop("image_pool")
    pool["accounts"][0]["service_id"] = "codex_image"
    config["account_pools"]["codex_image_pool"] = pool

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_api_relay_http.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setenv("AFS_MODEL_RELAY_API_KEY", "test-key")
    registry = ProviderRegistry.from_store(_store(tmp_path, config))
    descriptor = registry.descriptor("image_relay")

    registry.dispatch(
        "image",
        "image_relay",
        ProviderDispatchRequest(
            prompt="Preserve approved identities and continuity.",
            output_dir=tmp_path / "run",
            image_operation="edit",
            edit_source_image_path=references[0],
            edit_reference_image_paths=tuple(references),
            reference_image_paths=tuple(references),
            image_input_fidelity=None,
        ),
    )

    assert descriptor.image_edit_capabilities.input_fidelity_modes == []
    assert captured["url"] == "https://api.crazyrouter.com/v1/images/edits"
    assert "multipart/form-data" in captured["content_type"]
    assert 'name="input_fidelity"' not in captured["body"]
    first = captured["body"].index('filename="reference_001.png"')
    second = captured["body"].index('filename="reference_002.png"')
    assert first < second
    assert "private-reference-" not in captured["body"]


def test_provider_example_config_builds_registry_without_secret_values() -> None:
    store = load_company_provider_secrets("configs/providers.example.json")
    registry = ProviderRegistry.from_store(store)
    serialized = json.dumps(store.model_dump(mode="json"), ensure_ascii=False).lower()

    assert registry.descriptor("prompt_optimizer").modality == "llm"
    assert registry.descriptor("prompt_optimizer").account_pool_id == "prompt_optimizer_pool"
    assert store.services["prompt_optimizer"]["provider"] == "codex_local"
    assert registry.descriptor("image_relay").execution_mode == "sync"
    assert registry.descriptor("image_relay").account_pool_id == "image_relay_pool"
    assert store.services["image_relay"]["provider"] == "api_relay"
    assert "codex_image" not in store.services
    assert registry.descriptor("vision_image").modality == "vision"
    assert store.services["vision_image"]["provider"] == "codex_local"
    assert registry.descriptor("vision_video").reference_image_slots == 8
    assert registry.descriptor("fake_video").execution_mode == "async"
    assert registry.descriptor("seedance_i2v").prompt_profile == "video_i2v_v1"
    assert "model_relay" not in serialized
    assert "afs_model_relay" not in serialized
    assert "minimax_image" not in serialized
    assert "minimax_m3" not in serialized
    assert "image-01" not in serialized
    assert "bearer " not in serialized
    assert "sk-" not in serialized
    assert "fk-" not in serialized


class _JsonResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class _BytesResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, *_args) -> bytes:
        return self.payload


def _png_bytes() -> bytes:
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )


def _api_relay_provider_config(*, include_image: bool = False) -> dict:
    services = {
        "prompt_optimizer": _api_relay_service("llm", "prompt_optimizer", "llm_pool", "/v1/afs/llm"),
        "vision_image": _api_relay_service("vision", "vision_image", "vision_pool", "/v1/afs/vision"),
    }
    pools = {
        "llm_pool": {"accounts": [_api_relay_pool_entry("prompt_optimizer", "llm")]},
        "vision_pool": {"accounts": [_api_relay_pool_entry("vision_image", "vision")]},
    }
    if include_image:
        services["relay_image"] = _api_relay_service("image", "relay_image", "image_pool", "/v1/afs/image")
        pools["image_pool"] = {"accounts": [_api_relay_pool_entry("relay_image", "image")]}
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "model_relay": {
                "auth_type": "api_key",
                "base_url": "https://relay.invalid",
                "base_url_env": "AFS_MODEL_RELAY_BASE_URL",
                "api_key_env": "AFS_MODEL_RELAY_API_KEY",
                "default_models": {"llm": "relay-llm", "vision": "relay-vision", "image": "relay-image"},
            }
        },
        "account_pools": pools,
        "services": services,
    }


def _api_relay_pool_entry(service_id: str, capability: str) -> dict:
    return {
        "account_id": "model_relay",
        "service_id": service_id,
        "credential_env": "AFS_MODEL_RELAY_API_KEY",
        "enabled_capabilities": [capability],
        "enabled": True,
        "priority": 10,
        "weight": 1,
        "concurrency_limit": 1,
        "health_state": "healthy",
    }


def _api_relay_service(capability: str, service_id: str, pool_id: str, endpoint: str) -> dict:
    return {
        "provider": "api_relay",
        "account_ref": "model_relay",
        "capability": capability,
        "model": "server-configured",
        "endpoint": endpoint,
        "required_gate": f"AFS_ALLOW_REMOTE_{capability.upper()}",
        "descriptor": {
            "schema_version": "provider_descriptor.v0.1",
            "modality": capability,
            "execution_mode": "sync",
            "capabilities": [capability],
            "account_pool_id": pool_id,
            "reference_image_slots": 8 if capability == "vision" else 4 if capability == "image" else 0,
            "supported_aspect_ratios": ["1:1", "4:3", "3:4", "16:9", "9:16"],
            "prompt_char_limit": 5000,
            "seed_supported": capability == "image",
            "cost_hint": "test-only",
            "rate_limit_hint": "test-only",
            "required_gate": f"AFS_ALLOW_REMOTE_{capability.upper()}",
        },
    }


def _codex_local_provider_config() -> dict:
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "local_codex": {
                "auth_type": "none",
                "execution_backend": "codex_exec",
                "cli_command": "codex",
                "default_models": {"llm": "codex-local", "vision": "codex-local", "image": "image2"},
            }
        },
        "account_pools": {
            "prompt_optimizer_pool": {"accounts": [_codex_pool_entry("prompt_optimizer", "llm")]},
            "vision_pool": {"accounts": [_codex_pool_entry("vision_image", "vision")]},
        },
        "services": {
            "prompt_optimizer": _codex_local_service("llm", "prompt_optimizer", "prompt_optimizer_pool", ["1:1"], 0),
            "vision_image": _codex_local_service("vision", "vision_image", "vision_pool", ["1:1"], 8),
        },
    }


def _codex_pool_entry(service_id: str, capability: str) -> dict:
    return {
        "account_id": "local_codex",
        "service_id": service_id,
        "enabled_capabilities": [capability],
        "enabled": True,
        "priority": 10,
        "weight": 1,
        "concurrency_limit": 1,
        "health_state": "healthy",
    }


def _codex_local_service(
    capability: str,
    service_id: str,
    pool_id: str,
    aspect_ratios: list[str],
    reference_image_slots: int,
) -> dict:
    return {
        "provider": "codex_local",
        "account_ref": "local_codex",
        "capability": capability,
        "required_gate": f"AFS_ALLOW_REMOTE_{capability.upper()}",
        "descriptor": {
            "schema_version": "provider_descriptor.v0.1",
            "modality": capability,
            "execution_mode": "sync",
            "capabilities": [capability],
            "account_pool_id": pool_id,
            "reference_image_slots": reference_image_slots,
            "supported_aspect_ratios": aspect_ratios,
            "prompt_char_limit": 5000,
            "seed_supported": False,
            "cost_hint": "local-codex",
            "rate_limit_hint": "local-codex",
            "required_gate": f"AFS_ALLOW_REMOTE_{capability.upper()}",
        },
    }


def _provider_gateway_config() -> dict:
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "openai_account": {
                "auth_type": "api_key",
                "base_url": "https://example.test/v1",
                "api_key_env": "AFS_TEST_LLM_KEY",
                "default_models": {"llm": "gpt-test"},
            },
            "fake_video_account": {
                "auth_type": "none",
                "base_url": "https://video.example.test",
                "default_models": {"video": "fake-video"},
            },
        },
        "account_pools": {
            "llm_pool": {
                "accounts": [
                    {
                        "account_id": "openai_account",
                        "service_id": "openai_text",
                        "credential_env": "AFS_TEST_LLM_KEY",
                        "enabled_capabilities": ["llm"],
                        "enabled": True,
                        "priority": 10,
                        "weight": 1,
                        "concurrency_limit": 1,
                        "health_state": "healthy",
                    }
                ]
            },
            "video_pool": {
                "accounts": [
                    {
                        "account_id": "fake_video_account",
                        "service_id": "fake_video",
                        "enabled_capabilities": ["video"],
                        "enabled": True,
                        "priority": 10,
                        "weight": 1,
                        "concurrency_limit": 1,
                        "health_state": "healthy",
                    }
                ]
            },
        },
        "services": {
            "openai_text": {
                "provider": "openai_compatible",
                "account_ref": "openai_account",
                "capability": "llm",
                "model": "gpt-test",
                "required_gate": "AFS_ALLOW_REMOTE_LLM",
                "descriptor": {
                    "schema_version": "provider_descriptor.v0.1",
                    "modality": "llm",
                    "execution_mode": "sync",
                    "capabilities": ["llm"],
                    "account_pool_id": "llm_pool",
                    "reference_image_slots": 0,
                    "supported_aspect_ratios": ["1:1"],
                    "prompt_char_limit": 5000,
                    "seed_supported": False,
                    "cost_hint": "test-only",
                    "rate_limit_hint": "test-only",
                    "required_gate": "AFS_ALLOW_REMOTE_LLM",
                },
            },
            "fake_video": {
                "provider": "fake",
                "account_ref": "fake_video_account",
                "capability": "video",
                "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
                "descriptor": {
                    "schema_version": "provider_descriptor.v0.1",
                    "modality": "video",
                    "execution_mode": "async",
                    "capabilities": ["video"],
                    "account_pool_id": "video_pool",
                    "reference_image_slots": 1,
                    "supported_aspect_ratios": ["16:9", "9:16"],
                    "prompt_char_limit": 2000,
                    "seed_supported": False,
                    "cost_hint": "fake-only",
                    "rate_limit_hint": "fake-only",
                    "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
                },
            },
        },
    }


def _seedance_provider_config() -> dict:
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "volc_seedance_relay": {
                "auth_type": "api_key",
                "base_url": "https://relay.test",
                "api_key_env": "AFS_VIDEO_RELAY_API_KEY",
                "default_models": {"video": "doubao-seedance-2-0"},
            }
        },
        "account_pools": {
            "seedance_video_pool": {
                "accounts": [
                    {
                        "account_id": "volc_seedance_relay",
                        "service_id": "seedance_i2v",
                        "credential_env": "AFS_VIDEO_RELAY_API_KEY",
                        "enabled_capabilities": ["video"],
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
            "seedance_i2v": {
                "provider": "volc_seedance",
                "account_ref": "volc_seedance_relay",
                "capability": "video",
                "endpoint": "/volc/v1/contents/generations/tasks",
                "model": "doubao-seedance-2-0",
                "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
                "reference_roles": ["first_frame", "last_frame"],
                "watermark": False,
                "descriptor": {
                    "schema_version": "provider_descriptor.v0.2",
                    "modality": "video",
                    "execution_mode": "async",
                    "capabilities": ["video"],
                    "account_pool_id": "seedance_video_pool",
                    "reference_image_slots": 2,
                    "supported_aspect_ratios": ["16:9", "9:16"],
                    "prompt_char_limit": 5000,
                    "seed_supported": True,
                    "cost_hint": "Seedance I2V live usage is billed by selected duration and model.",
                    "rate_limit_hint": "Use one live Seedance video task at a time during MVP validation.",
                    "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
                    "frame_slots": {"first_frame": "required", "last_frame": "optional"},
                    "frame_modes": ["first_frame", "first_last_frame"],
                    "supported_durations_sec": [5, 10],
                    "supported_resolutions": ["480p", "720p"],
                    "async_poll_interval_sec": 5,
                    "async_timeout_sec": 900,
                    "async_max_polls": 180,
                    "prompt_profile": "video_i2v_v1",
                    "cost_estimate": {"unit": "task", "currency": "CNY", "disclaimer": "local estimate only"},
                },
            }
        },
    }
