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
    "asset_card_candidates",
    "production_graph",
    "evidence_ledger",
    "generation_bridge",
    "human_gate",
    "feedback_candidate_promotion",
    "feedback_candidate_context_overlay",
    "shared_object_evidence",
    "revision_drift_control",
)

AUXILIARY_ENGINEERING_MODULES = (
    "provider_gate_manifest",
    "feedback_overlay_prompt_policy",
    "artifact_lineage",
    "skill_action_selection",
)

__all__ = (
    "ALGORITHM_LIBRARY_VERSION",
    "AUXILIARY_ENGINEERING_MODULES",
    "CORE_AGENT_ALGORITHM_MODULES",
    "CORE_AGENT_ALGORITHMS",
)
