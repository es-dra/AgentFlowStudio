from __future__ import annotations

from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.memory.production_asset_profile_constants import (
    ASSET_PROFILE_SEED_KIND,
    CONTEXT_ELIGIBILITY,
    PROFILE_KINDS,
    PROFILE_STATUSES,
)
from agentflow.memory.production_loop import SCHEMA_VERSION


def validate_asset_profile_seed(seed: dict[str, Any]) -> None:
    if seed.get("kind") != ASSET_PROFILE_SEED_KIND:
        raise ValueError(f"asset profile seed requires kind {ASSET_PROFILE_SEED_KIND}")
    if seed.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"asset profile seed requires schema_version {SCHEMA_VERSION}")
    if has_private_fragment(seed):
        raise ValueError("asset profile seed must not include private paths or secrets")
    profiles = list_value(seed.get("profiles"))
    if not profiles:
        raise ValueError("asset profile seed requires at least one profile")
    for profile in profiles:
        validate_profile_seed(dict_value(profile))


def validate_profile_seed(profile: dict[str, Any]) -> None:
    if not profile.get("profile_id"):
        raise ValueError("asset profile seed profile requires profile_id")
    if profile.get("profile_kind") not in PROFILE_KINDS:
        raise ValueError("asset profile seed profile_kind must be character or scene")
    if profile.get("profile_status") not in PROFILE_STATUSES:
        raise ValueError("asset profile seed profile_status is unsupported")
    if profile.get("context_eligibility") not in CONTEXT_ELIGIBILITY:
        raise ValueError("asset profile seed context_eligibility is unsupported")
    if not list_value(profile.get("allowed_variations")):
        raise ValueError("asset profile seed requires allowed_variations")
    if not list_value(profile.get("negative_constraints")):
        raise ValueError("asset profile seed requires negative_constraints")
    if not list_value(profile.get("evidence_refs")):
        raise ValueError("asset profile seed requires evidence_refs")


def has_private_fragment(payload: Any) -> bool:
    raw_text = str(payload).lower()
    return any(fragment.lower() in raw_text for fragment in AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS)


def dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
