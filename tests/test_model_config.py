from __future__ import annotations

import pytest

from agentflow_studio.model_gateway import (
    MODEL_GATEWAY_CONFIG_ENV,
    ModelConfigError,
    load_model_gateway_config,
    resolve_model_gateway_config_path,
)


def test_load_model_gateway_config_reads_example() -> None:
    config = load_model_gateway_config("configs/models.example.yaml")

    assert config.default_provider == "mock"
    assert config.providers["mock"].type == "mock"
    assert config.providers["mock"].model == "mock-local"
    assert "openai_compatible" in config.providers
    assert config.providers["minimax_m3"].base_url == "https://api.minimaxi.com/v1"
    assert config.providers["minimax_m3"].api_key_env == "MINIMAX_API_KEY"
    assert config.providers["minimax_m3"].model == "MiniMax-M3"
    assert config.providers["minimax_m3"].extra_body == {"thinking": {"type": "disabled"}}


def test_resolve_model_gateway_config_path_reads_env(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "models.yaml"
    monkeypatch.setenv(MODEL_GATEWAY_CONFIG_ENV, str(config_path))

    assert resolve_model_gateway_config_path() == config_path


def test_model_gateway_config_rejects_missing_default_provider(tmp_path) -> None:
    config_path = tmp_path / "models.yaml"
    config_path.write_text(
        """
default_provider: missing
providers:
  mock:
    type: mock
""",
        encoding="utf-8",
    )

    with pytest.raises(ModelConfigError, match="default_provider"):
        load_model_gateway_config(config_path)


def test_model_gateway_config_rejects_empty_providers(tmp_path) -> None:
    config_path = tmp_path / "models.yaml"
    config_path.write_text(
        """
default_provider: mock
providers: {}
""",
        encoding="utf-8",
    )

    with pytest.raises(ModelConfigError, match="providers"):
        load_model_gateway_config(config_path)


def test_model_gateway_config_rejects_invalid_yaml(tmp_path) -> None:
    config_path = tmp_path / "models.yaml"
    config_path.write_text("default_provider: [", encoding="utf-8")

    with pytest.raises(ModelConfigError, match="YAML is invalid"):
        load_model_gateway_config(config_path)
