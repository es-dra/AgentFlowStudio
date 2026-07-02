from __future__ import annotations

from typing import Any


READINESS_KEYS = (
    "service_ready",
    "auth_ready_for_public_edge",
    "public_edge_verified",
    "runtime_freshness_verified",
    "acceptance_ready",
    "product_readiness",
)


def safe_readiness_projection(value: Any) -> dict[str, bool]:
    if not isinstance(value, dict):
        value = {}
    return {key: bool(value.get(key)) for key in READINESS_KEYS}
