from __future__ import annotations

ALGORITHM_LIBRARY_VERSION = "afs_algorithm_library_v0.2"

CORE_AGENT_ALGORITHMS = (
    "prompt_intelligence_optimization",
    "context_intelligence_scheduling",
    "visual_understanding_assetization",
    "asset_memory_continuity",
    "model_request_projection",
    "quality_feedback_drift_control",
)

CORE_AGENT_ALGORITHM_MODULES = (
    "runtime_prompt_memory_engine",
    "context_resolver",
    "visual_understanding",
    "fixed_asset_memory",
    "request_projection",
    "quality_feedback_scoring",
    "content_quality_evaluation",
    "production_graph",
    "revision_drift_control",
)

AUXILIARY_ENGINEERING_MODULES = (
    "provider_gate_manifest",
    "artifact_lineage",
    "skill_action_selection",
)

__all__ = (
    "ALGORITHM_LIBRARY_VERSION",
    "AUXILIARY_ENGINEERING_MODULES",
    "CORE_AGENT_ALGORITHM_MODULES",
    "CORE_AGENT_ALGORITHMS",
)
