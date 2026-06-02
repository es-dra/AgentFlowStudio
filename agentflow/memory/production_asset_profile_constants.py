from __future__ import annotations

ASSET_PROFILE_SEED_KIND = "agentflow_production_memory_asset_profile_seed"
ASSET_PROFILE_KIND = "agentflow_production_memory_asset_profile"
ASSET_PROFILE_READINESS_KIND = "agentflow_production_memory_asset_profile_readiness"
ASSET_TEST_PACKAGE_KIND = "agentflow_production_memory_asset_test_package"
PROVIDER_VALIDATION_PLAN_KIND = "agentflow_production_memory_asset_provider_validation_plan"
PROVIDER_VALIDATION_BLOCKERS_KIND = "agentflow_production_memory_asset_provider_validation_blockers"
PROVIDER_VALIDATION_RESULT_KIND = "agentflow_production_memory_asset_provider_validation_result"

PROFILE_KINDS = frozenset({"character", "scene"})
PROFILE_STATUSES = frozenset({"candidate", "promoted", "blocked", "retired"})
CONTEXT_ELIGIBILITY = frozenset({"included", "blocked", "not_requested"})

__all__ = (
    "ASSET_PROFILE_KIND",
    "ASSET_PROFILE_READINESS_KIND",
    "ASSET_PROFILE_SEED_KIND",
    "ASSET_TEST_PACKAGE_KIND",
    "CONTEXT_ELIGIBILITY",
    "PROFILE_KINDS",
    "PROFILE_STATUSES",
    "PROVIDER_VALIDATION_BLOCKERS_KIND",
    "PROVIDER_VALIDATION_PLAN_KIND",
    "PROVIDER_VALIDATION_RESULT_KIND",
)
