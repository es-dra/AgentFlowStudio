from __future__ import annotations

from typing import Any

from apps.api.runtime_attribute_vocabulary import ATTRIBUTE_GROUPS
from apps.api.runtime_context_assets import (
    MAX_GENERATE_FULL_CHARACTER_ASSETS,
    MAX_GENERATE_FULL_SCENE_ASSETS,
    apply_label_arbitration,
    asset_detail_levels,
    available_assets,
    degraded_asset_exclusions,
    duplicate_label_candidates,
    excluded_assets,
    hash_payload,
    included_asset,
    optimize_asset_ids,
    reference_image_channel,
    subject_reference_asset,
    temporary_asset_exclusion_records,
)
from apps.api.runtime_context_budget import apply_context_budget, context_warnings
from apps.api.runtime_context_subgraph import connected_asset_refs, sort_asset_ids, upstream_summary_lines, validate_subgraph
from apps.api.runtime_context_text import (
    director_compile_result,
    override_pairs,
    provider_prompt_from_bundle,
    text_channel,
)
from apps.api.runtime_models import AssetExclusion, ContextSubgraph, DirectorSetup2D, TemporaryLockOverride
from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_visual_assets import fixed_visual_assets_by_id


RESOLVER_VERSION = "context_resolver_v0.2"


def resolve_context_bundle(
    store: RuntimeStore,
    project_id: str,
    *,
    mode: str,
    visible_prompt: str,
    context_subgraph: ContextSubgraph,
    temporary_lock_overrides: list[TemporaryLockOverride] | None = None,
    temporary_asset_exclusions: list[AssetExclusion] | None = None,
    include_fixed_assets: bool = True,
    style_preference: str | None = None,
    prompt_char_limit: int = 1500,
    reference_image_slots: int = 1,
    director_setup: DirectorSetup2D | None = None,
) -> dict[str, Any]:
    validate_subgraph(context_subgraph)
    assets = fixed_visual_assets_by_id(store, project_id)
    connected, node_hops = connected_asset_refs(context_subgraph)
    sorted_connected_ids = sort_asset_ids(assets, connected)
    overrides = override_pairs(temporary_lock_overrides or [])
    excluded_by_user = {item.asset_id for item in (temporary_asset_exclusions or []) if item.asset_id}

    if mode == "optimize":
        candidate_ids = optimize_asset_ids(assets, sorted_connected_ids, visible_prompt)
    elif mode == "generate":
        candidate_ids = sorted_connected_ids if include_fixed_assets else []
    else:
        raise ValueError("context resolver mode must be optimize or generate")

    candidate_ids = [asset_id for asset_id in candidate_ids if asset_id not in excluded_by_user]
    included_ids, arbitration_exclusions = apply_label_arbitration(assets, candidate_ids)
    detail_levels = asset_detail_levels(assets, included_ids, mode)
    degraded_exclusions = degraded_asset_exclusions(assets, included_ids, detail_levels) if mode == "generate" else []
    temporary_exclusions = temporary_asset_exclusion_records(assets, excluded_by_user)
    included = [
        included_asset(assets[asset_id], connected.get(asset_id), mode, detail_levels.get(asset_id, "signature_only"))
        for asset_id in included_ids
        if asset_id in assets
    ]
    excluded = excluded_assets(
        assets,
        included_ids,
        connected,
        mode,
        include_fixed_assets,
        extra_exclusions=[*temporary_exclusions, *arbitration_exclusions, *degraded_exclusions],
    )
    available = available_assets(assets, included_ids, connected, visible_prompt)
    upstream_lines = upstream_summary_lines(context_subgraph, node_hops)
    director_compile = director_compile_result(director_setup, assets)
    text = text_channel(
        mode,
        visible_prompt,
        [(assets[item], detail_levels.get(item, "signature_only")) for item in included_ids if item in assets],
        overrides,
        upstream_lines=upstream_lines,
        style_preference=style_preference,
        director_compile=director_compile,
    )
    included_full_card_assets = [
        assets[item]
        for item in included_ids
        if item in assets and detail_levels.get(item) == "full_card"
    ]
    subject_asset = subject_reference_asset(included_full_card_assets, connected)
    reference_channel = reference_image_channel(included_full_card_assets, connected, reference_image_slots)
    text, budget = apply_context_budget(mode, text, total_prompt_budget=prompt_char_limit)
    warning_assets = {asset_id: asset for asset_id, asset in assets.items() if asset_id not in excluded_by_user}
    warnings = context_warnings(warning_assets, connected, visible_prompt, overrides)
    asset_conflicts = [item for item in warnings if item.get("warning_id") == "best_effort_lock_conflict"]

    return {
        "schema_version": "0.1.0",
        "resolver_version": RESOLVER_VERSION,
        "vocabulary_hash": hash_payload(ATTRIBUTE_GROUPS),
        "mode": mode,
        "included_assets": included,
        "excluded_assets": excluded,
        "available_project_assets": available,
        "text_channel": text,
        "reference_image_channel": reference_channel,
        "subject_reference_asset_id": subject_asset.get("asset_id") if subject_asset else None,
        "warnings": warnings,
        "asset_conflicts": asset_conflicts,
        "budget": budget,
        "temporary_lock_overrides": [
            {"asset_id": item.asset_id, "lock_text": item.lock_text, "reason": item.reason}
            for item in (temporary_lock_overrides or [])
        ],
        "temporary_asset_exclusions": [
            {"asset_id": item.asset_id, "reason": item.reason or "one_run_asset_exclusion"}
            for item in (temporary_asset_exclusions or [])
        ],
        "director_compile_result": director_compile,
        "trace_summary": {
            "context_subgraph_assertion": "client_supplied_not_security_boundary",
            "asset_truth_source": "runtime_visual_asset_store_by_id",
            "duplicate_label_candidates": duplicate_label_candidates(assets, included_ids),
            "selection_rule": "label_version_terminal_then_hop_then_reference_director_generation_then_asset_id",
            "generate_full_card_limits": {
                "character": MAX_GENERATE_FULL_CHARACTER_ASSETS,
                "scene": MAX_GENERATE_FULL_SCENE_ASSETS,
            },
        },
    }


__all__ = ("provider_prompt_from_bundle", "resolve_context_bundle")
