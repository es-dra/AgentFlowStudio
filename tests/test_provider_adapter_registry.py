from __future__ import annotations

import json

import pytest

from agentflow_studio.model_gateway.company_secrets import load_company_provider_secrets
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest, ProviderRegistry
from agentflow_studio.model_gateway import openai_compatible
from tests.minimax_image_test_helpers import provider_config


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


def test_provider_example_config_builds_registry_without_secret_values() -> None:
    store = load_company_provider_secrets("configs/providers.example.json")
    registry = ProviderRegistry.from_store(store)
    serialized = json.dumps(store.model_dump(mode="json"), ensure_ascii=False).lower()

    assert registry.descriptor("minimax_image").account_pool_id == "minimax_image_pool"
    assert registry.descriptor("minimax_m3").modality == "llm"
    assert registry.descriptor("fake_video").execution_mode == "async"
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
