from __future__ import annotations


class ModelGatewayError(Exception):
    """Base error for model gateway and provider boundary failures."""


class ModelConfigError(ModelGatewayError):
    """Raised when model or provider configuration is invalid."""


class ModelProviderError(ModelGatewayError):
    """Raised when a provider cannot generate a response."""
