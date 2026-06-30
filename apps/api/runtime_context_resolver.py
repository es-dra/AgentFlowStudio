from __future__ import annotations

from typing import Any

from agentflow.algorithms.context_resolver import (
    RESOLVER_VERSION,
    provider_prompt_from_bundle,
    resolve_context_bundle_core,
)
from apps.api.runtime_director_compiler import compile_director_setup
from apps.api.runtime_feedback_context import attach_feedback_context_overlays
from apps.api.runtime_models import AssetExclusion, ContextSubgraph, DirectorSetup2D, TemporaryLockOverride
from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_visual_assets import fixed_visual_assets_by_id


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
    bundle = resolve_context_bundle_core(
        assets_by_id=fixed_visual_assets_by_id(store, project_id),
        mode=mode,
        visible_prompt=visible_prompt,
        context_subgraph=context_subgraph,
        temporary_lock_overrides=temporary_lock_overrides,
        temporary_asset_exclusions=temporary_asset_exclusions,
        include_fixed_assets=include_fixed_assets,
        style_preference=style_preference,
        prompt_char_limit=prompt_char_limit,
        reference_image_slots=reference_image_slots,
        director_setup=director_setup,
        director_compile_fn=compile_director_setup,
    )
    return attach_feedback_context_overlays(store, project_id, bundle, context_subgraph)


__all__ = ("RESOLVER_VERSION", "provider_prompt_from_bundle", "resolve_context_bundle")
