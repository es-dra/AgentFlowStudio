from __future__ import annotations

from typing import Any


def promotion_gate(request: Any) -> dict[str, Any] | None:
    human_gate_id = safe_ref(getattr(request, "source_human_gate_id", None))
    candidate_id = safe_ref(getattr(request, "source_asset_card_candidate_id", None))
    if not human_gate_id and not candidate_id:
        return None
    gate = {
        "scope": "manual_fixed_asset_promotion",
        "source_contract": "runtime_human_gate_decision",
        "provider_calls_started": False,
        "generated_media_claimed": False,
        "human_creative_acceptance_claimed": False,
        "business_validation_claimed": False,
    }
    if human_gate_id:
        gate["source_human_gate_id"] = human_gate_id
    if candidate_id:
        gate["source_asset_card_candidate_id"] = candidate_id
    return gate


def public_promotion_gate(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    keys = (
        "scope",
        "source_contract",
        "source_human_gate_id",
        "source_asset_card_candidate_id",
        "provider_calls_started",
        "generated_media_claimed",
        "human_creative_acceptance_claimed",
        "business_validation_claimed",
    )
    return {key: value.get(key) for key in keys if key in value}


def safe_ref(value: Any) -> str:
    text = str(value or "").strip()
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-"
    return "".join(char if char in allowed else "_" for char in text).strip("_")[:160]
