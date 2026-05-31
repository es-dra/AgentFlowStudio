"""Model gateway adapters for mock and OpenAI-compatible providers."""

from narratocut.model_gateway.base import LLMProvider, LLMResponse
from narratocut.model_gateway.config import (
    ModelGatewayConfig,
    ProviderConfig,
    load_model_gateway_config,
)
from narratocut.model_gateway.company_secrets import (
    CompanyProviderSecrets,
    load_company_provider_secrets,
)
from narratocut.model_gateway.errors import ModelConfigError, ModelGatewayError, ModelProviderError
from narratocut.model_gateway.gateway import ModelGateway
from narratocut.model_gateway.kling_plan import build_kling_request_plan
from narratocut.model_gateway.kling_video_smoke import run_kling_i2v_smoke, run_kling_t2v_smoke
from narratocut.model_gateway.minimax_image_smoke import (
    build_minimax_image_request_plan,
    run_minimax_image_smoke,
)
from narratocut.model_gateway.mock_provider import MockLLMProvider
from narratocut.model_gateway.openai_compatible import OpenAICompatibleProvider

__all__ = [
    "CompanyProviderSecrets",
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
    "build_kling_request_plan",
    "build_minimax_image_request_plan",
    "load_company_provider_secrets",
    "load_model_gateway_config",
    "run_kling_i2v_smoke",
    "run_minimax_image_smoke",
    "run_kling_t2v_smoke",
]
