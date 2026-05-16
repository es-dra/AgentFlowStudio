"""Model gateway adapters for mock and OpenAI-compatible providers."""

from narratocut.model_gateway.base import LLMProvider, LLMResponse
from narratocut.model_gateway.config import (
    ModelGatewayConfig,
    ProviderConfig,
    load_model_gateway_config,
)
from narratocut.model_gateway.errors import ModelConfigError, ModelGatewayError, ModelProviderError
from narratocut.model_gateway.gateway import ModelGateway
from narratocut.model_gateway.mock_provider import MockLLMProvider
from narratocut.model_gateway.openai_compatible import OpenAICompatibleProvider

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "MockLLMProvider",
    "ModelConfigError",
    "ModelGateway",
    "ModelGatewayConfig",
    "ModelGatewayError",
    "ModelProviderError",
    "OpenAICompatibleProvider",
    "ProviderConfig",
    "load_model_gateway_config",
]
