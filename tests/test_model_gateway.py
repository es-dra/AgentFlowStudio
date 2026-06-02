from __future__ import annotations

import json

import pytest

from agentflow_studio.model_gateway import ModelGateway, ModelGatewayError


def test_model_gateway_default_provider_uses_mock_hooks() -> None:
    gateway = ModelGateway.from_config_path("configs/models.example.yaml")

    payload = json.loads(gateway.generate("prompt", task_type="hook_analysis"))

    assert isinstance(payload, list)
    assert payload
    assert payload[0]["hook_id"]


def test_model_gateway_default_provider_uses_mock_scripts() -> None:
    gateway = ModelGateway.from_config_path("configs/models.example.yaml")

    payload = json.loads(gateway.generate("prompt", task_type="short_video_script"))

    assert isinstance(payload, list)
    assert payload
    assert payload[0]["script_id"]


def test_model_gateway_rejects_unknown_provider_name() -> None:
    gateway = ModelGateway.from_config_path("configs/models.example.yaml")

    with pytest.raises(ModelGatewayError, match="Unknown model provider"):
        gateway.generate("prompt", task_type="hook_analysis", provider_name="missing")


def test_model_gateway_can_load_openai_compatible_config_without_network() -> None:
    gateway = ModelGateway.from_config_path("configs/models.example.yaml")

    assert "openai_compatible" in gateway.config.providers
    assert gateway.config.default_provider == "mock"
