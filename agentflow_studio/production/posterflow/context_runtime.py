from __future__ import annotations

from agentflow_studio.production.posterflow.schemas import (
    ContextAssemblyTrace,
    ContextBundle,
    PosterPreferenceProfile,
    PosterPromptPack,
)


def build_context_bundle(
    prompt_pack: PosterPromptPack,
    profile: PosterPreferenceProfile,
    *,
    project_prefix_path: str = "project_prefix.md",
    preference_profile_path: str = "poster_preference_profile.json",
) -> ContextBundle:
    cache_key = _cache_key(profile)
    return ContextBundle(
        project_id=profile.project_id,
        run_id=prompt_pack.run_id,
        bundle_id=f"{prompt_pack.run_id}_context_bundle_001",
        project_prefix_path=project_prefix_path,
        preference_profile_path=preference_profile_path,
        source_memory_candidates=profile.source_memory_candidates,
        source_promotion_decisions=profile.source_promotion_decisions,
        source_artifacts={
            "prompt_pack": "poster_prompt_pack.json",
            "project_prefix": project_prefix_path,
            "preference_profile": preference_profile_path,
            "memory_candidates": "poster_memory_candidates.jsonl",
            "memory_review": "poster_memory_review.jsonl",
        },
        context_layers={
            "hot": {
                "project_prefix": project_prefix_path,
                "prompt_rules": profile.prompt_rules,
            },
            "warm": {
                "preference_profile": preference_profile_path,
                "memory_refs": profile.source_memory_candidates,
                "promotion_decision_refs": profile.source_promotion_decisions,
                "visual_preferences": profile.visual_preferences,
                "negative_visual_preferences": profile.negative_visual_preferences,
            },
            "cold": {
                "retrieval_refs": [],
                "status": "not_configured",
            },
            "policy": {
                "quality_profile": "posterflow_memory_demo",
                "remote_provider_policy": "explicit_opt_in",
            },
        },
        quality_rules=[
            "Use only human-reviewed project preference candidates.",
            "Do not write long-term memory from this demo context bundle.",
            "Keep raw feedback and derived feedback signals separate.",
        ],
        cache_plan={
            "cache_key": cache_key,
            "prefix_version": profile.profile_version,
            "cacheable_layers": ["hot", "policy"],
            "invalidation_refs": profile.source_memory_candidates + profile.source_promotion_decisions,
        },
    )


def build_context_assembly_trace(bundle: ContextBundle) -> ContextAssemblyTrace:
    return ContextAssemblyTrace(
        project_id=bundle.project_id,
        run_id=bundle.run_id,
        bundle_id=bundle.bundle_id,
        promotion_decision_refs=bundle.source_promotion_decisions,
        cache_key=str(bundle.cache_plan["cache_key"]),
        selection_decisions=[
            {
                "source": "project_prefix",
                "layer": "hot",
                "status": "included",
                "reason": "stable_project_context",
                "artifact_ref": bundle.project_prefix_path,
            },
            {
                "source": "preference_profile",
                "layer": "warm",
                "status": "included",
                "reason": "human_reviewed_memory_refs",
                "artifact_ref": bundle.preference_profile_path,
            },
            {
                "source": "retrieval_memory",
                "layer": "cold",
                "status": "excluded",
                "reason": "no_rag_configured",
                "artifact_ref": None,
            },
            {
                "source": "quality_policy",
                "layer": "policy",
                "status": "included",
                "reason": "posterflow_quality_profile",
                "artifact_ref": "posterflow_memory_demo",
            },
        ],
        budget={
            "mode": "artifact_first_mvp",
            "max_layers": 4,
            "retrieval_budget": 0,
        },
        rejected_context=[
            {
                "source": "retrieval_memory",
                "reason": "no_rag_configured",
            }
        ],
    )


def _cache_key(profile: PosterPreferenceProfile) -> str:
    return f"{profile.project_id}:{profile.profile_version}:posterflow_memory_demo:v0.1"
