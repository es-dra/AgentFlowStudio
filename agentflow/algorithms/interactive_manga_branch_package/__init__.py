from __future__ import annotations

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS


ALGORITHM_ID = "afs.interactive_manga_branch_package.v0.1"
INPUT_CONTRACT = "repo-local Interactive Manga branch package fixture with shared-object evidence refs"
OUTPUT_CONTRACT = "deterministic validation report for choice paths, branch shots, assets, continuity, evidence, and handoff"
FAILURE_MODES = (
    "missing_choice_point_or_branch_path",
    "unresolved_reference",
    "branch_shot_mapping_gap",
    "asset_scope_collapse",
    "continuity_scope_gap",
    "graph_node_write_claim",
    "unsafe_payload_marker",
    "claim_state_collapse",
)
EVIDENCE_BOUNDARY = (
    "deterministic branch package structure only; no reader playback, Runtime route, "
    "Studio UI, provider prompt inclusion, generated media, or product readiness claim"
)

REFERENCE_POLICY = "reference_only_no_node_write"
REQUIRED_EVIDENCE_MAPPING_FIELDS = (
    "storyboard_refs",
    "production_graph_artifact_refs",
    "asset_refs",
    "evidence_refs",
    "handoff_envelope_refs",
)
SHARED_ASSET_SCOPES = {"shared_across_package", "shared_across_paths"}
BRANCH_ASSET_SCOPES = {"branch_specific", "shot_specific"}
PROTECTED_NON_CLAIMS = {
    "reader_playback",
    "public_interactive_runtime",
    "runtime_implemented",
    "runtime_route",
    "openapi_path",
    "studio_ui",
    "provider_prompt_inclusion",
    "provider_smoke",
    "generated_media",
    "generated_media_quality",
    "human_creative_acceptance",
    "business_validation",
    "public_release",
    "public_legal_patent_readiness",
    "deploy_runtime_health",
    "companyos_projection",
    "durable_memory_promotion",
    "cos_active_rule_promotion",
    "final_schema_acceptance",
    "product_readiness",
}
UNSAFE_MARKERS = tuple(
    fragment.lower()
    for fragment in (
        *AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS,
        "provider_raw",
        "provider raw",
        "raw_provider_response",
        "signed url",
        "data_base64",
        "generated_media_bytes",
        ".obsidian",
        "week planner",
        "/users/",
        "/home/",
        "/tmp/",
        "customer_private",
        "real_cost",
    )
)

from ._validator import (  # noqa: E402
    load_branch_package_fixture,
    load_json_fixture,
    validate_branch_package_fixture,
)

__all__ = (
    "ALGORITHM_ID",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "OUTPUT_CONTRACT",
    "PROTECTED_NON_CLAIMS",
    "REFERENCE_POLICY",
    "load_branch_package_fixture",
    "load_json_fixture",
    "validate_branch_package_fixture",
)
