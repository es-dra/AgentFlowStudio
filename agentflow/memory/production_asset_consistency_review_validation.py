from __future__ import annotations

from typing import Any

from agentflow.memory.production_asset_feedback import (
    FAILURE_ATTRIBUTIONS,
    REVIEW_DIMENSIONS,
    REVIEW_RESULTS,
    SUGGESTED_NEXT_STATES,
    SUPPORTED_FEEDBACK_INPUT_TYPES,
)
from agentflow.memory.production_asset_profile_constants import PROFILE_KINDS
from agentflow.memory.production_asset_profile_context_projection import ASSET_PROFILE_CONTEXT_PROJECTION_KIND
from agentflow.memory.production_asset_profile_promotion_utils import (
    list_value,
    reject_unsafe_asset_profile_promotion,
)
from agentflow.memory.production_loop import SCHEMA_VERSION

ASSET_CONSISTENCY_REVIEW_FIXTURE_KIND = "agentflow_production_memory_asset_consistency_review_fixture"
COMPARISON_SCOPES = frozenset({"single_scene", "cross_scene", "cross_shot", "cross_scene_or_shot"})


def validate_asset_profile_context_projection(projection: dict[str, Any]) -> None:
    if projection.get("kind") != ASSET_PROFILE_CONTEXT_PROJECTION_KIND:
        raise ValueError(f"asset consistency review requires projection kind {ASSET_PROFILE_CONTEXT_PROJECTION_KIND}")
    if projection.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"asset consistency review requires projection schema_version {SCHEMA_VERSION}")
    require_text(projection, "projection_id")
    require_text(projection, "project_id")
    if projection.get("provider_mode") != "no-provider" or projection.get("provider_calls_started") is not False:
        raise ValueError("asset consistency review projection must be no-provider")
    if projection.get("writes_long_term_memory") is not False or projection.get("writes_company_kb") is not False:
        raise ValueError("asset consistency review projection must not write memory or Company KB")
    reject_unsafe(projection)


def validate_asset_consistency_review_fixture(fixture: dict[str, Any]) -> None:
    if fixture.get("kind") != ASSET_CONSISTENCY_REVIEW_FIXTURE_KIND:
        raise ValueError(f"asset consistency review fixture requires kind {ASSET_CONSISTENCY_REVIEW_FIXTURE_KIND}")
    if fixture.get("artifact_type") != ASSET_CONSISTENCY_REVIEW_FIXTURE_KIND:
        raise ValueError("asset consistency review fixture artifact_type must match kind")
    if fixture.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"asset consistency review fixture requires schema_version {SCHEMA_VERSION}")
    for field in ("fixture_id", "project_id", "source_context_projection_ref", "source_result_ref"):
        require_text(fixture, field)
    if fixture.get("source_feedback_input_type") not in SUPPORTED_FEEDBACK_INPUT_TYPES:
        raise ValueError("asset consistency review fixture source_feedback_input_type is unsupported")
    if fixture.get("comparison_scope") not in COMPARISON_SCOPES:
        raise ValueError("asset consistency review fixture comparison_scope is unsupported")
    items = list_value(fixture.get("review_items"))
    if not items:
        raise ValueError("asset consistency review fixture requires review_items")
    for item in items:
        validate_review_item(dict_value(item))
    reject_unsafe(fixture)


def validate_review_item(item: dict[str, Any]) -> None:
    for field in ("profile_ref", "profile_kind"):
        require_text(item, field)
    if item.get("profile_kind") not in PROFILE_KINDS:
        raise ValueError("asset consistency review item profile_kind is unsupported")
    if not list_value(item.get("output_refs")):
        raise ValueError("asset consistency review item requires output_refs")
    if item.get("review_dimension") not in REVIEW_DIMENSIONS:
        raise ValueError("asset consistency review item review_dimension is unsupported")
    if item.get("review_result") not in REVIEW_RESULTS:
        raise ValueError("asset consistency review item review_result is unsupported")
    if item.get("failure_attribution") not in FAILURE_ATTRIBUTIONS:
        raise ValueError("asset consistency review item failure_attribution is unsupported")
    if item.get("suggested_next_state") not in SUGGESTED_NEXT_STATES:
        raise ValueError("asset consistency review item suggested_next_state is unsupported")


def reject_unsafe(value: Any) -> None:
    try:
        reject_unsafe_asset_profile_promotion(value)
    except ValueError as exc:
        raise ValueError("asset consistency review contains unsafe private path, media, provider URL, or secret") from exc


def require_text(payload: dict[str, Any], field: str) -> None:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"asset consistency review requires {field}")


def dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
