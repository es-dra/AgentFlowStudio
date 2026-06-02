from __future__ import annotations

import pytest

from agentflow_studio.model_gateway import ModelConfigError, load_model_gateway_config


def test_load_model_gateway_config_reads_example() -> None:
    config = load_model_gateway_config("configs/models.example.yaml")

    assert config.default_provider == "mock"
    assert config.providers["mock"].type == "mock"
    assert config.providers["mock"].model == "mock-local"
    assert "openai_compatible" in config.providers


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
