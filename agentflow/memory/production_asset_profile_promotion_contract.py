from __future__ import annotations

from typing import Any

from agentflow.memory.production_asset_profile_constants import ASSET_PROFILE_KIND
from agentflow.memory.production_asset_profile_promotion_utils import (
    dict_value,
    list_value,
    reject_unsafe_asset_profile_promotion,
    require_text,
)
from agentflow.memory.production_asset_profile_update_candidate import ASSET_PROFILE_UPDATE_CANDIDATE_KIND


def validate_asset_profiles(asset_profiles: dict[str, Any]) -> None:
    profiles = list_value(asset_profiles.get("profiles"))
    if not profiles:
        raise ValueError("asset profile promotion requires asset_profiles.profiles")
    for profile in profiles:
        item = dict_value(profile)
        if item.get("kind") != ASSET_PROFILE_KIND:
            raise ValueError(f"asset profile promotion profile requires kind {ASSET_PROFILE_KIND}")
        require_text(item, "profile_id")
        require_text(item, "profile_kind")
        if item.get("writes_long_term_memory") is not False:
            raise ValueError("asset profile promotion requires profile writes_long_term_memory false")
        if item.get("writes_company_kb") is not False:
            raise ValueError("asset profile promotion requires profile writes_company_kb false")
    reject_unsafe_asset_profile_promotion(asset_profiles)


def validate_asset_profile_update_candidate(candidate: dict[str, Any]) -> None:
    if candidate.get("kind") != ASSET_PROFILE_UPDATE_CANDIDATE_KIND:
        raise ValueError(f"asset profile promotion requires kind {ASSET_PROFILE_UPDATE_CANDIDATE_KIND}")
    for field in ("candidate_id", "project_id", "profile_id", "profile_kind"):
        require_text(candidate, field)
    if candidate.get("provider_mode") != "no-provider":
        raise ValueError("asset profile promotion requires no-provider candidate")
    if candidate.get("provider_calls_started") is not False:
        raise ValueError("asset profile promotion requires provider_calls_started false")
    if candidate.get("writes_long_term_memory") is not False:
        raise ValueError("asset profile promotion requires writes_long_term_memory false")
    if candidate.get("writes_company_kb") is not False:
        raise ValueError("asset profile promotion requires writes_company_kb false")
    if candidate.get("candidate_is_promoted_profile") is not False:
        raise ValueError("asset profile promotion requires unpromoted source candidate")
    if candidate.get("creates_promotion_decision") is not False:
        raise ValueError("asset profile promotion requires candidate to create no promotion decision")
    if candidate.get("applies_profile_version") is not False:
        raise ValueError("asset profile promotion requires unapplied source candidate")
    reject_unsafe_asset_profile_promotion(candidate)


def candidate_patch_ops(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    return list_value(dict_value(candidate.get("proposed_profile_patch")).get("patch_ops"))


def profile_by_id(asset_profiles: dict[str, Any], profile_id: str) -> dict[str, Any]:
    for profile in list_value(asset_profiles.get("profiles")):
        item = dict_value(profile)
        if item.get("profile_id") == profile_id:
            return item
    raise ValueError(f"profile_id does not exist in asset_profiles: {profile_id}")


__all__ = (
    "candidate_patch_ops",
    "profile_by_id",
    "validate_asset_profile_update_candidate",
    "validate_asset_profiles",
)
