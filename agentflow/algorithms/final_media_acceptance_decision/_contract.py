from __future__ import annotations


ALGORITHM_ID = "afs.final_media_acceptance_decision.v0.1"
SCHEMA_VERSION = "0.1.0"
ARTIFACT_TYPE = "agentflow_final_media_acceptance_decision"
CHECKLIST_ARTIFACT_TYPE = "agentflow_structured_source_output_qa_checklist"
CHECKLIST_SCHEMA_VERSION = "0.1.0"
REQUIRED_SUMMARY_COUNT_KEYS = (
    "total_item_count",
    "required_item_count",
    "required_items_followed_count",
    "required_items_blocked_count",
    "critical_fail_count",
    "waiver_required_count",
    "waiver_applied_count",
    "invalid_waiver_count",
    "unverifiable_count",
    "conflict_count",
)
PASSING_PACKET_STATE = "checklist_completed"
DEFAULT_MAX_PACKET_AGE_SECONDS = 24 * 60 * 60
INPUT_CONTRACT = "project id, target id, checklist packet ref summary, output ref summary, and explicit reviewer action"
OUTPUT_CONTRACT = "safe local final-media acceptance decision packet linked to one structured QA checklist packet"
EVIDENCE_BOUNDARY = "local final-media decision only; consumes checklist packet refs and safe counts without rechecking generated media"
DECISION_STATES = (
    "qa_passed_pending_reviewer_action",
    "accepted_for_local_final_media",
    "rejected_for_local_final_media",
    "blocked_missing_evidence",
    "blocked_unsafe",
    "blocked_project_scope",
    "blocked_conflict",
    "blocked_malformed_packet",
    "blocked_stale_packet",
    "blocked_unsupported_reviewer_role",
)
SUPPORTED_REVIEWER_ROLES = (
    "qa_reviewer",
    "media_reviewer",
    "studio_operator",
    "operator",
    "owner",
    "product_steward",
)
SUPPORTED_TARGET_ENTITY_TYPES = ("generation_candidate", "keyframe_version", "video_revision")
STUDIO_ACTION_WIRING = {
    "acceptance_action_id": "accept",
    "rejection_action_id": "reject",
    "evidence_action_id": "view_evidence",
    "uses_existing_action_vocabulary": True,
}
NON_CLAIMS = [
    "local final-media decision only",
    "not human creative acceptance",
    "not generated media QA",
    "not provider success certification",
    "not business readiness",
    "not public readiness",
    "not legal readiness",
    "not memory promotion",
    "not company knowledge promotion",
]
FAILURE_MODES = (
    "malformed_checklist_packet_ref",
    "stale_checklist_packet_ref",
    "unsafe_checklist_packet_payload",
    "project_or_target_mismatch",
    "checklist_ref_mismatch",
    "active_runtime_state",
    "missing_output_ref",
    "missing_safe_preview_ref",
    "critical_fail_count_present",
    "scope_safety_or_conflict_blocker",
    "invalid_noncritical_waiver_state",
    "unsupported_reviewer_role",
)
