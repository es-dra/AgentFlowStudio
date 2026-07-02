from __future__ import annotations

from typing import Any


READINESS_KEYS = (
    "service_ready",
    "auth_ready_for_public_edge",
    "public_edge_verified",
    "runtime_three_end_alignment_evidence",
    "acceptance_ready",
    "product_readiness",
)


def safe_readiness_projection(value: Any) -> dict[str, bool | str]:
    if not isinstance(value, dict):
        value = {}
    projection: dict[str, bool | str] = {key: bool(value.get(key)) for key in READINESS_KEYS}
    projection["runtime_loaded_code_freshness_claim"] = str(value.get("runtime_loaded_code_freshness_claim") or "not_claimed")
    return projection
