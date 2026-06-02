from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError

from agentflow_studio.model_gateway.errors import ModelConfigError


ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class ProviderConfig(BaseModel):
    type: Literal["mock", "openai_compatible"]
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    api_key_env: str | None = None
    timeout_sec: float = Field(default=30.0, gt=0)


class ModelGatewayConfig(BaseModel):
    default_provider: str
    providers: dict[str, ProviderConfig] = Field(min_length=1)


def load_model_gateway_config(path: str | Path) -> ModelGatewayConfig:
    config_path = Path(path)
    if not config_path.is_file():
        raise ModelConfigError(f"Model gateway config file not found: {config_path}")
    try:
        payload: Any = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ModelConfigError(f"Model gateway config YAML is invalid: {config_path}") from exc
    if not isinstance(payload, dict):
        raise ModelConfigError(f"Model gateway config must contain a mapping: {config_path}")

    payload = _expand_env_values(payload)
    try:
        config = ModelGatewayConfig.model_validate(payload)
    except ValidationError as exc:
        raise ModelConfigError(f"Model gateway config is invalid: {config_path}: {exc}") from exc

    if config.default_provider not in config.providers:
        raise ModelConfigError(
            f"default_provider '{config.default_provider}' is not defined in providers"
        )
    return config


def _expand_env_values(value: Any) -> Any:
    if isinstance(value, str):
        return ENV_PATTERN.sub(lambda match: os.environ.get(match.group(1), ""), value)
    if isinstance(value, list):
        return [_expand_env_values(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_env_values(item) for key, item in value.items()}
    return value
