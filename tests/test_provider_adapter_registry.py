from __future__ import annotations

import json
import subprocess

import pytest

from agentflow_studio.model_gateway.company_secrets import load_company_provider_secrets
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest, ProviderRegistry
from agentflow_studio.model_gateway import openai_compatible
from tests.minimax_image_test_helpers import provider_config
from tests.provider_smoke_helpers import provider_config as legacy_kling_provider_config


def _store(tmp_path, payload: dict):
    path = tmp_path / "providers.local.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return load_company_provider_secrets(path)


def test_provider_registry_rejects_missing_descriptor(tmp_path) -> None:
    payload = provider_config()
    payload["services"]["minimax_image"].pop("descriptor", None)
    store = _store(tmp_path, payload)

    with pytest.raises(ModelConfigError, match="descriptor"):
        ProviderRegistry.from_store(store)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("required_gate", "MINIMAX_API_KEY", "required_gate"),
        ("reference_image_slots", -1, "reference_image_slots"),
        ("supported_aspect_ratios", ["wide"], "supported_aspect_ratios"),
    ],
)
def test_provider_registry_rejects_invalid_descriptor_fields(tmp_path, field, value, match) -> None:
    payload = provider_config()
    payload["services"]["minimax_image"]["descriptor"][field] = value
    store = _store(tmp_path, payload)

    with pytest.raises(ModelConfigError, match=match):
        ProviderRegistry.from_store(store)


def test_provider_registry_exposes_minimax_descriptor(tmp_path) -> None:
    store = _store(tmp_path, provider_config())
    registry = ProviderRegistry.from_store(store)

    descriptor = registry.descriptor("minimax_image")

    assert descriptor.modality == "image"
    assert descriptor.capabilities == ["image"]
    assert descriptor.execution_mode == "sync"
    assert descriptor.account_pool_id == "minimax_image_pool"
    assert descriptor.reference_image_slots == 1
    assert descriptor.prompt_char_limit == 1500
    assert descriptor.rate_limit_hint == "test-only"
    assert descriptor.required_gate == "AFS_ALLOW_REMOTE_IMAGE"


def test_provider_registry_rejects_disabled_account_pool_entry(tmp_path, monkeypatch) -> None:
    payload = provider_config()
    payload["account_pools"]["minimax_image_pool"]["accounts"][0]["enabled"] = False
    store = _store(tmp_path, payload)
    registry = ProviderRegistry.from_store(store)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")

    with pytest.raises(ModelConfigError, match="No enabled provider account"):
        registry.dispatch(
            "image",
            "minimax_image",
            ProviderDispatchRequest(prompt="hello", output_dir=tmp_path, aspect_ratio="9:16"),
        )


def test_provider_registry_reports_missing_credential_env_without_secret_value(tmp_path, monkeypatch) -> None:
    payload = provider_config(use_env_key=True)
    store = _store(tmp_path, payload)
    registry = ProviderRegistry.from_store(store)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)

    with pytest.raises(ModelGatewayError) as exc:
        registry.dispatch(
            "image",
            "minimax_image",
            ProviderDispatchRequest(prompt="hello", output_dir=tmp_path, aspect_ratio="9:16"),
        )

    message = str(exc.value)
    assert "MINIMAX_API_KEY" in message
    assert "fk-" not in message


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
    assert captured["payload"]["messages"] == [{"role": "user", "content": "Improve this prompt"}]
    assert captured["api_key"] == "secret-value"


def test_provider_registry_dispatches_minimax_cli_llm_from_token_plan(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps(
                {
                    "content": [
                        {"type": "thinking", "thinking": "internal chain"},
                        {"type": "text", "text": "enhanced by minimax cli"},
                    ]
                },
                ensure_ascii=False,
            ),
            stderr="",
        )

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_adapter_impl.subprocess.run", fake_run)
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_adapter_impl.shutil.which", lambda value: value)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    store = _store(tmp_path, _provider_gateway_config())
    registry = ProviderRegistry.from_store(store)

    result = registry.dispatch(
        "llm",
        "minimax_m3",
        ProviderDispatchRequest(prompt="Improve this prompt", output_dir=tmp_path, task_type="prompt_enhancement"),
    )

    assert result["text"] == "enhanced by minimax cli"
    assert result["provider_calls_started"] is True
    args = list(captured["args"])
    assert args[:3] == ["mmx", "text", "chat"]
    assert "--message" in args
    assert args[args.index("--message") + 1] == "Improve this prompt"
    assert "--output" in args
    assert args[args.index("--output") + 1] == "json"
    assert "--non-interactive" in args
    assert "secret" not in json.dumps(captured, ensure_ascii=False).lower()


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
    payload = _kling_provider_config()
    payload["services"]["kling_i2v"]["descriptor"][field] = value
    store = _store(tmp_path, payload)

    with pytest.raises(ModelConfigError, match=match):
        ProviderRegistry.from_store(store)


def test_provider_registry_builds_kling_i2v_adapter_descriptor_v02(tmp_path) -> None:
    store = _store(tmp_path, _kling_provider_config())
    registry = ProviderRegistry.from_store(store)

    descriptor = registry.descriptor("kling_i2v")

    assert descriptor.schema_version == "provider_descriptor.v0.2"
    assert descriptor.modality == "video"
    assert descriptor.execution_mode == "async"
    assert descriptor.frame_slots == {"first_frame": "required", "last_frame": "optional"}
    assert descriptor.frame_modes == ["first_frame", "first_last_frame"]
    assert descriptor.supported_durations_sec == [5, 10]
    assert descriptor.supported_resolutions == ["720p", "1080p"]
    assert descriptor.prompt_profile == "video_i2v_v1"


def test_provider_registry_derives_legacy_kling_i2v_descriptor(tmp_path) -> None:
    store = _store(tmp_path, legacy_kling_provider_config())
    registry = ProviderRegistry.from_store(store)

    descriptor = registry.descriptor("kling_i2v")

    assert descriptor.schema_version == "provider_descriptor.v0.2"
    assert descriptor.modality == "video"
    assert descriptor.execution_mode == "async"
    assert descriptor.frame_slots["first_frame"] == "required"
    assert descriptor.prompt_profile == "video_i2v_v1"


def test_provider_registry_blocks_kling_before_network_when_gate_closed(tmp_path, monkeypatch) -> None:
    called = {"count": 0}

    def fake_run_kling_i2v_smoke(*args, **kwargs):
        called["count"] += 1
        return {"status": "succeeded"}

    first_frame = tmp_path / "first.png"
    first_frame.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    monkeypatch.setattr(
        "agentflow_studio.model_gateway.provider_adapter_impl.run_kling_i2v_smoke",
        fake_run_kling_i2v_smoke,
    )
    store = _store(tmp_path, _kling_provider_config())
    registry = ProviderRegistry.from_store(store)

    with pytest.raises(ModelGatewayError, match="AFS_ALLOW_REMOTE_VIDEO"):
        registry.dispatch(
            "video",
            "kling_i2v",
            ProviderDispatchRequest(
                prompt="A slow camera push in.",
                output_dir=tmp_path / "run",
                aspect_ratio="9:16",
                subject_reference_image_path=first_frame,
                duration_sec=5,
                resolution="720p",
            ),
        )

    assert called["count"] == 0


def test_provider_registry_dispatches_kling_i2v_through_adapter(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_kling_i2v_smoke(*args, **kwargs):
        captured["kwargs"] = kwargs
        return {
            "status": "succeeded",
            "service_id": kwargs["service_id"],
            "provider": "kling",
            "outputs": [{"video_path": "video_candidates/candidate_001.mp4"}],
        }

    first_frame = tmp_path / "first.png"
    first_frame.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setattr(
        "agentflow_studio.model_gateway.provider_adapter_impl.run_kling_i2v_smoke",
        fake_run_kling_i2v_smoke,
    )
    store = _store(tmp_path, _kling_provider_config())
    registry = ProviderRegistry.from_store(store)

    result = registry.dispatch(
        "video",
        "kling_i2v",
        ProviderDispatchRequest(
            prompt="A slow camera push in.",
            output_dir=tmp_path / "run",
            aspect_ratio="9:16",
            subject_reference_image_path=first_frame,
            duration_sec=5,
            resolution="720p",
        ),
    )

    assert result["status"] == "succeeded"
    assert result["service_id"] == "kling_i2v"
    assert captured["kwargs"]["service_id"] == "kling_i2v"
    assert captured["kwargs"]["prompt"] == "A slow camera push in."
    assert captured["kwargs"]["image_path"] == first_frame
    assert captured["kwargs"]["duration"] == "5"
    assert "secret" not in json.dumps(result, ensure_ascii=False).lower()


def test_provider_example_config_builds_registry_without_secret_values() -> None:
    store = load_company_provider_secrets("configs/providers.example.json")
    registry = ProviderRegistry.from_store(store)
    serialized = json.dumps(store.model_dump(mode="json"), ensure_ascii=False).lower()

    assert registry.descriptor("minimax_image").account_pool_id == "minimax_image_pool"
    assert registry.descriptor("minimax_m3").modality == "llm"
    assert registry.descriptor("fake_video").execution_mode == "async"
    assert registry.descriptor("kling_i2v").prompt_profile == "video_i2v_v1"
    assert "api_key" in serialized
    assert "bearer " not in serialized
    assert "sk-" not in serialized
    assert "fk-" not in serialized


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
            "minimax_cli_account": {
                "auth_type": "token_plan",
                "execution_backend": "mmx_cli",
                "cli_command": "mmx",
                "region": "cn",
                "default_models": {"llm": "MiniMax-M2.7"},
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
            "minimax_llm_pool": {
                "accounts": [
                    {
                        "account_id": "minimax_cli_account",
                        "service_id": "minimax_m3",
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
            "minimax_m3": {
                "provider": "minimax_cli",
                "account_ref": "minimax_cli_account",
                "capability": "llm",
                "model": "MiniMax-M2.7",
                "temperature": 0.2,
                "max_completion_tokens": 900,
                "required_gate": "AFS_ALLOW_REMOTE_LLM",
                "descriptor": {
                    "schema_version": "provider_descriptor.v0.1",
                    "modality": "llm",
                    "execution_mode": "sync",
                    "capabilities": ["llm"],
                    "account_pool_id": "minimax_llm_pool",
                    "reference_image_slots": 0,
                    "supported_aspect_ratios": ["1:1"],
                    "prompt_char_limit": 5000,
                    "seed_supported": False,
                    "cost_hint": "token-plan",
                    "rate_limit_hint": "local mmx cli",
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


def _kling_provider_config() -> dict:
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "kling": {
                "auth_type": "jwt_hs256_from_ak_sk",
                "base_url": "https://api-beijing.klingai.com",
                "access_key": "fake-access-key",
                "secret_key": "fake-secret-key",
                "jwt": {"ttl_seconds": 1800, "nbf_skew_seconds": -5},
                "default_models": {"i2v": "kling-v3"},
                "endpoints": {
                    "i2v_create": "/v1/videos/image2video",
                    "i2v_query": "/v1/videos/image2video/{id}",
                },
            }
        },
        "account_pools": {
            "kling_video_pool": {
                "accounts": [
                    {
                        "account_id": "kling",
                        "service_id": "kling_i2v",
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
            "kling_i2v": {
                "provider": "kling",
                "account_ref": "kling",
                "capability": "video",
                "api_family": "i2v",
                "default_model_ref": "accounts.kling.default_models.i2v",
                "create_endpoint_ref": "accounts.kling.endpoints.i2v_create",
                "query_endpoint_ref": "accounts.kling.endpoints.i2v_query",
                "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
                "descriptor": {
                    "schema_version": "provider_descriptor.v0.2",
                    "modality": "video",
                    "execution_mode": "async",
                    "capabilities": ["video"],
                    "account_pool_id": "kling_video_pool",
                    "reference_image_slots": 2,
                    "supported_aspect_ratios": ["16:9", "9:16"],
                    "prompt_char_limit": 2500,
                    "seed_supported": False,
                    "cost_hint": "Kling I2V live usage is billed by selected duration and mode.",
                    "rate_limit_hint": "Use one live Kling video task at a time during MVP validation.",
                    "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
                    "frame_slots": {"first_frame": "required", "last_frame": "optional"},
                    "frame_modes": ["first_frame", "first_last_frame"],
                    "supported_durations_sec": [5, 10],
                    "supported_resolutions": ["720p", "1080p"],
                    "async_poll_interval_sec": 5,
                    "async_timeout_sec": 600,
                    "async_max_polls": 120,
                    "prompt_profile": "video_i2v_v1",
                    "cost_estimate": {"unit": "task", "currency": "CNY", "disclaimer": "local estimate only"},
                },
            }
        },
    }
