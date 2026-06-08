from __future__ import annotations


DEFAULT_MINIMAX_BASE_URL = "https://api.minimax.io"
DEFAULT_MINIMAX_IMAGE_MODEL = "image-01"


class ModelGatewayError(Exception):
    """Base error for model gateway and provider boundary failures."""


class ModelConfigError(ModelGatewayError):
    """Raised when model or provider configuration is invalid."""


class ModelProviderError(ModelGatewayError):
    """Raised when a provider cannot generate a response."""
