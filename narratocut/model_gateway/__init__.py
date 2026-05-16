"""Model gateway adapters for mock and future OpenAI-compatible providers."""

from narratocut.model_gateway.base import LLMProvider
from narratocut.model_gateway.mock_provider import MockLLMProvider

__all__ = ["LLMProvider", "MockLLMProvider"]
