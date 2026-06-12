from __future__ import annotations

import time
from typing import Any

from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError


def dispatch_provider_with_retry(
    registry: Any,
    capability: str,
    service_id: str,
    request: Any,
    *,
    retry_delay_sec: float = 2.0,
) -> tuple[dict[str, Any], int]:
    try:
        return registry.dispatch(capability, service_id, request), 0
    except ModelGatewayError as exc:
        if not retryable_provider_error(exc):
            raise
        time.sleep(retry_delay_sec)
        try:
            manifest = registry.dispatch(capability, service_id, request)
        except ModelGatewayError as retry_exc:
            setattr(retry_exc, "retry_count", 1)
            raise
        return manifest, 1


def retryable_provider_error(error: ModelGatewayError) -> bool:
    if isinstance(error, ModelConfigError):
        return False
    lowered = str(error).lower()
    if any(code in lowered for code in (" 400", " 401", " 403", " 404", " 409", " 422", "invalid api key", "invalid parameter")):
        return False
    return any(
        term in lowered
        for term in (
            "timeout",
            "timed out",
            "connection",
            "network",
            "temporarily",
            "readiness",
            "not ready",
            "502",
            "503",
            "504",
        )
    )


__all__ = ("dispatch_provider_with_retry", "retryable_provider_error")
