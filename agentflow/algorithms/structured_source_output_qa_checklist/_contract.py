from __future__ import annotations


ALGORITHM_ID = "afs.structured_source_output_qa_checklist.v0.1"
SCHEMA_VERSION = "0.1.0"
INPUT_CONTRACT = "project id, target id, safe source inventory, safe output refs, checklist items, optional waivers"
OUTPUT_CONTRACT = "safe structured source-vs-output QA checklist packet with item outcomes, summary counts, and waiver validation"
EVIDENCE_BOUNDARY = "per-source/per-requirement evidence only; no provider call, final media decision, human acceptance, or memory promotion"
PACKET_STATES = (
    "checklist_ready_for_review",
    "checklist_completed",
    "blocked_missing_evidence",
    "blocked_unsafe",
    "blocked_project_scope",
    "blocked_conflict",
    "unverifiable",
)
ITEM_OUTCOMES = (
    "followed",
    "partially_followed",
    "ignored",
    "blocked_missing_evidence",
    "blocked_unsafe",
    "blocked_project_scope",
    "blocked_conflict",
    "not_applicable",
    "unverifiable",
)
FAILURE_MODES = (
    "unsafe_input_payload",
    "project_or_target_mismatch",
    "missing_required_source_evidence",
    "missing_required_output_ref",
    "missing_safe_preview_ref",
    "active_runtime_state",
    "runtime_state_not_stable_reviewable",
    "equal_rank_reference_conflict",
    "invalid_waiver_scope",
)
NON_CLAIMS = [
    "source-output checklist only",
    "no final media decision",
    "no provider result decision",
    "no generated media judgement",
    "no memory promotion",
    "no company knowledge promotion",
]
CRITICAL_CATEGORIES = {
    "identity",
    "continuity",
    "fixed_asset",
    "source_evidence",
    "target_output",
    "output_presence",
    "first_frame_provenance",
    "video_first_frame_provenance",
}
SAFETY_CATEGORIES = {"safety", "unsafe_content", "leakage"}
SCOPE_CATEGORIES = {"project_scope", "scope", "target_scope"}
ACTIVE_RUNTIME_STATES = {"queued", "submitted", "pending", "running", "retrying", "active"}
