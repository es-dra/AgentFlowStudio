from __future__ import annotations

import re


ALGORITHM_ID = "afs.node_reference_stack.v0.1"
SCHEMA_VERSION = "0.1.0"
INPUT_CONTRACT = "project id, node id, explicit node references, optional asset auto-binding graph"
OUTPUT_CONTRACT = "safe ordered node reference stack with priority, conflict, explainability, and reversal boundaries"
FAILURE_MODES = (
    "unsupported_reference_type",
    "unsupported_reference_scope",
    "status_not_in_studio_entity_vocabulary",
    "reference_state_not_usable",
    "missing_target_ref",
    "unsafe_target_ref",
    "asset_binding_missing_fixed_asset_id",
    "asset_binding_missing_established_relationship",
    "asset_binding_missing_source_relationship",
    "unresolved_equal_rank_conflict",
)
EVIDENCE_BOUNDARY = "reference stack planning only; no provider call, generated-media QA, human acceptance, or memory promotion"

ASSET_AUTO_BINDING_RELATIONSHIP_TYPE = "asset_auto_binding_established"
ASSET_AUTO_BINDING_REFERENCE_PRIORITY_FLOOR = 82
STUDIO_REFERENCE_ENTITIES = (
    "project_asset",
    "reference_input",
    "generation_candidate",
    "keyframe_version",
    "video_revision",
    "binding",
    "lineage",
)
STUDIO_REFERENCE_ACTIONS = (
    "reference",
    "bind",
    "unbind",
    "replace",
    "reject",
    "view_lineage",
    "view_evidence",
)
SUPPORTED_REFERENCE_SCOPES = ("node", "shot", "scene", "project", "request", "lineage")
USABLE_STATES = ("draft", "fixed", "bound", "available", "succeeded", "partial", "accepted")
NON_CLAIMS = [
    "not provider smoke",
    "not generated media QA",
    "not human acceptance",
    "not business validation",
    "not durable memory promotion",
    "not CompanyOS/COS promotion",
]

ALLOWED_STATES_BY_TYPE = {
    "project_asset": ("draft", "fixed", "rejected", "retired", "blocked", "needs_attention"),
    "reference_input": ("draft", "bound", "unbound", "blocked", "needs_attention", "rejected"),
    "generation_candidate": (
        "queued",
        "submitted",
        "running",
        "succeeded",
        "partial",
        "failed",
        "retryable",
        "cancelled",
        "blocked",
        "needs_attention",
        "accepted",
        "rejected",
    ),
    "keyframe_version": ("draft", "succeeded", "partial", "failed", "retryable", "blocked", "needs_attention", "accepted", "rejected"),
    "video_revision": (
        "queued",
        "submitted",
        "running",
        "succeeded",
        "partial",
        "failed",
        "retryable",
        "cancelled",
        "blocked",
        "needs_attention",
        "accepted",
        "rejected",
    ),
    "binding": ("bound", "unbound", "replaced", "blocked", "needs_attention"),
    "lineage": ("available", "partial", "blocked", "needs_attention"),
}
DEFAULT_STATE_BY_TYPE = {
    "project_asset": "draft",
    "reference_input": "draft",
    "generation_candidate": "succeeded",
    "keyframe_version": "succeeded",
    "video_revision": "succeeded",
    "binding": "bound",
    "lineage": "available",
}
SCOPE_PRECEDENCE = {"node": 60, "shot": 50, "scene": 40, "project": 30, "request": 20, "lineage": 10}
TYPE_PRECEDENCE = {
    "binding": 70,
    "reference_input": 60,
    "project_asset": 50,
    "keyframe_version": 40,
    "generation_candidate": 30,
    "video_revision": 20,
    "lineage": 10,
}
REVERSAL_ACTION_BY_REFERENCE_TYPE = {
    "project_asset": "replace",
    "reference_input": "replace",
    "generation_candidate": "reject",
    "keyframe_version": "replace",
    "video_revision": "replace",
    "binding": "unbind",
    "lineage": "replace",
}
SAFE_TOKEN_RE = re.compile(r"[^0-9A-Za-z_.:-]+")
UNSAFE_REF_MARKERS = ("api_key", "token", "secret", "signed", "http://", "https://", "data:", ";base64,", "base64,", "data_base64", "\\")
