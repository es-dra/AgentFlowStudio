from __future__ import annotations

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS


ALGORITHM_ID = "afs.branch_workflow_package.v0.1"
INPUT_CONTRACT = "repo-local SPEC2 branch_workflow_package fixture backed by the T53 branch package contract"
OUTPUT_CONTRACT = "deterministic readiness report for branch workflow package handoff and implementation evidence"
FAILURE_MODES = (
    "missing_branch_workflow_package_object",
    "source_branch_package_contract_failed",
    "unresolved_reference",
    "asset_scope_collapse",
    "unconfirmed_candidate_in_implementation_ready_evidence",
    "evidence_completeness_gap",
    "graph_node_write_claim",
    "unsafe_payload_marker",
    "claim_state_collapse",
)
EVIDENCE_BOUNDARY = (
    "deterministic branch workflow package readiness wrapper only; reuses T53 structure "
    "contract and makes no Runtime, Studio, provider, media, or product readiness claim"
)

REFERENCE_POLICY = "reference_only_no_node_write"
PACKAGE_STAGES = {"draft", "review_ready", "accepted_for_generation_planning", "blocked", "archived"}
SHARED_ASSET_SCOPES = {"shared_across_package", "shared_across_paths"}
BRANCH_ASSET_SCOPES = {"branch_specific", "shot_specific"}
UNCONFIRMED_ASSET_STATES = {"candidate", "needs_human_confirmation", "blocked"}
IMPLEMENTATION_READY_ASSET_STATES = {"fixed_asset_available", "owner_decision_recorded"}
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
REQUIRED_MAPPED_REF_FIELDS = (
    "storyboard_refs",
    "production_graph_artifact_refs",
    "asset_refs",
    "candidate_asset_refs",
    "evidence_refs",
    "handoff_envelope_refs",
)
UNSAFE_MARKERS = tuple(
    fragment.lower()
    for fragment in (
        *AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS,
        "provider_raw",
        "provider raw",
        "raw_provider_response",
        "signed_url",
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
    load_branch_workflow_package_fixture,
    load_json_fixture,
    validate_branch_workflow_package_fixture,
)

__all__ = (
    "ALGORITHM_ID",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "OUTPUT_CONTRACT",
    "PROTECTED_NON_CLAIMS",
    "REFERENCE_POLICY",
    "load_branch_workflow_package_fixture",
    "load_json_fixture",
    "validate_branch_workflow_package_fixture",
)
