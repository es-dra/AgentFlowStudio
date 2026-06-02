from __future__ import annotations

from pathlib import Path

from agentflow_studio.model_gateway.config import (
    ModelGatewayConfig,
    ProviderConfig,
    load_model_gateway_config,
)
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.mock_provider import MockLLMProvider
from agentflow_studio.model_gateway.openai_compatible import OpenAICompatibleProvider


class ModelGateway:
    """Create and invoke configured LLM providers."""

    def __init__(self, config: ModelGatewayConfig) -> None:
        self.config = config

    @classmethod
    def from_config_path(cls, path: str | Path) -> "ModelGateway":
        return cls(load_model_gateway_config(path))

    def generate(
        self,
        prompt: str,
        *,
        task_type: str | None = None,
        provider_name: str | None = None,
    ) -> str:
        name = provider_name or self.config.default_provider
        provider_config = self.config.providers.get(name)
        if provider_config is None:
            raise ModelGatewayError(f"Unknown model provider: {name}")
        provider = self._create_provider(provider_config)
        return provider.generate(prompt, task_type=task_type)

    def _create_provider(self, config: ProviderConfig):
        if config.type == "mock":
            return MockLLMProvider()
        if config.type == "openai_compatible":
            return OpenAICompatibleProvider(
                base_url=config.base_url or "",
                api_key=config.api_key,
                api_key_env=config.api_key_env,
                model=config.model or "",
                timeout_sec=config.timeout_sec,
            )
        raise ModelGatewayError(f"Unsupported model provider type: {config.type}")
