from __future__ import annotations

from typing import Any

from agentflow.algorithms.final_media_acceptance_decision._contract import (
    ALGORITHM_ID,
    ARTIFACT_TYPE,
    CHECKLIST_ARTIFACT_TYPE,
    CHECKLIST_SCHEMA_VERSION,
    DECISION_STATES,
    DEFAULT_MAX_PACKET_AGE_SECONDS,
    EVIDENCE_BOUNDARY,
    FAILURE_MODES,
    INPUT_CONTRACT,
    NON_CLAIMS,
    OUTPUT_CONTRACT,
    PASSING_PACKET_STATE,
    SCHEMA_VERSION,
    STUDIO_ACTION_WIRING,
    SUPPORTED_REVIEWER_ROLES,
    SUPPORTED_TARGET_ENTITY_TYPES,
)
from agentflow.algorithms.final_media_acceptance_decision._support import (
    blocked_state as _blocked_state,
    checklist_packet_ref as _checklist_packet_ref,
    decision_packet as _decision_packet,
    default_decision_reasons as _default_decision_reasons,
    output_ref_summary as _output_ref_summary,
    packet_is_stale as _packet_is_stale,
    packet_state_reason as _packet_state_reason,
    parse_timestamp as _parse_timestamp,
    reviewer_action_id as _reviewer_action,
    runtime_review_active as _runtime_review_active,
    safe_token_list as _safe_token_list,
    summary_counts as _summary_counts,
    unique as _unique,
)
from agentflow.algorithms.structured_source_output_qa_checklist._safety import (
    has_unsafe_payload as _has_unsafe_payload,
    safe_token as _safe_token,
)


def build_final_media_acceptance_decision(
    *,
    project_id: str,
    target_id: str,
    checklist_packet_ref: dict[str, Any] | None,
    decision_requested_at: str,
    reviewer_action: str = "",
    reviewer_role: str = "",
    target_entity_type: str = "video_revision",
    expected_checklist_id: str = "",
    max_packet_age_seconds: int = DEFAULT_MAX_PACKET_AGE_SECONDS,
) -> dict[str, Any]:
    project = _safe_token(project_id)
    target = _safe_token(target_id)
    packet = checklist_packet_ref if isinstance(checklist_packet_ref, dict) else {}
    if _has_unsafe_payload(packet):
        return _decision_packet(
            project_id=project,
            target_id=target,
            target_entity_type=target_entity_type,
            packet_ref={},
            summary_counts={},
            output_ref_summary={},
            blocker_ids=[],
            decision_state="blocked_unsafe",
            qa_passed=False,
            accepted=False,
            reviewer_action=reviewer_action,
            reviewer_role=reviewer_role,
            decision_requested_at=decision_requested_at,
            decision_reasons=["unsafe_checklist_packet_payload"],
        )

    packet_ref = _checklist_packet_ref(packet)
    summary_counts, summary_malformed = _summary_counts(packet.get("summary_counts"))
    output_ref_summary = _output_ref_summary(packet)
    blocker_ids = _safe_token_list(packet.get("blocker_ids") or packet.get("safe_blocker_ids"))
    decision_time = _parse_timestamp(decision_requested_at)
    packet_time = _parse_timestamp(packet.get("created_at") or packet.get("packet_created_at"))
    action = _reviewer_action(reviewer_action)
    role = _safe_token(reviewer_role)
    entity_type = _safe_token(target_entity_type) or "video_revision"

    reasons = _blocking_reasons(
        project_id=project,
        target_id=target,
        expected_checklist_id=_safe_token(expected_checklist_id),
        entity_type=entity_type,
        packet_ref=packet_ref,
        summary_counts=summary_counts,
        summary_malformed=summary_malformed,
        output_ref_summary=output_ref_summary,
        blocker_ids=blocker_ids,
        packet=packet,
        packet_time=packet_time,
        decision_time=decision_time,
        max_packet_age_seconds=max_packet_age_seconds,
        reviewer_action=action,
        reviewer_role=role,
    )
    qa_reasons = [reason for reason in reasons if reason not in {"missing_reviewer_action", "reviewer_rejected"}]
    qa_passed = not qa_reasons
    if not qa_passed:
        decision_state = _blocked_state(qa_reasons)
        accepted = False
    elif action == "reject":
        decision_state = "rejected_for_local_final_media"
        accepted = False
    elif action == "accept":
        decision_state = "accepted_for_local_final_media"
        accepted = True
    else:
        decision_state = "qa_passed_pending_reviewer_action"
        accepted = False

    decision_reasons = reasons or _default_decision_reasons(action, decision_state)
    return _decision_packet(
        project_id=project,
        target_id=target,
        target_entity_type=entity_type,
        packet_ref=packet_ref,
        summary_counts=summary_counts,
        output_ref_summary=output_ref_summary,
        blocker_ids=blocker_ids,
        decision_state=decision_state,
        qa_passed=qa_passed,
        accepted=accepted,
        reviewer_action=action,
        reviewer_role=role,
        decision_requested_at=decision_requested_at,
        decision_reasons=decision_reasons,
    )


def _blocking_reasons(
    *,
    project_id: str,
    target_id: str,
    expected_checklist_id: str,
    entity_type: str,
    packet_ref: dict[str, Any],
    summary_counts: dict[str, int],
    summary_malformed: bool,
    output_ref_summary: dict[str, Any],
    blocker_ids: list[str],
    packet: dict[str, Any],
    packet_time: datetime | None,
    decision_time: datetime | None,
    max_packet_age_seconds: int,
    reviewer_action: str,
    reviewer_role: str,
) -> list[str]:
    reasons: list[str] = []
    if packet_ref.get("artifact_type") != CHECKLIST_ARTIFACT_TYPE or packet_ref.get("schema_version") != CHECKLIST_SCHEMA_VERSION:
        reasons.append("malformed_checklist_packet_ref")
    if packet_ref.get("project_id") != project_id or packet_ref.get("target_id") != target_id:
        reasons.append("project_or_target_mismatch")
    if expected_checklist_id and packet_ref.get("checklist_id") != expected_checklist_id:
        reasons.append("checklist_ref_mismatch")
    if not packet_ref.get("artifact_id") or not packet_ref.get("checklist_id") or summary_malformed:
        reasons.append("malformed_checklist_packet_ref")
    if entity_type not in SUPPORTED_TARGET_ENTITY_TYPES:
        reasons.append("unsupported_target_entity_type")
    if packet_time is None or decision_time is None or _packet_is_stale(packet_time, decision_time, max_packet_age_seconds):
        reasons.append("stale_checklist_packet_ref")
    if packet_ref.get("packet_state") != PASSING_PACKET_STATE:
        reasons.append(_packet_state_reason(packet_ref.get("packet_state")))
    if output_ref_summary.get("output_count", 0) < 1:
        reasons.append("missing_output_ref")
    if output_ref_summary.get("safe_preview_ref_count", 0) < output_ref_summary.get("output_count", 0):
        reasons.append("missing_safe_preview_ref")
    if output_ref_summary.get("project_or_target_mismatch"):
        reasons.append("project_or_target_mismatch")
    if output_ref_summary.get("active_runtime_state_present") or _runtime_review_active(packet):
        reasons.append("active_runtime_state")
    if summary_counts.get("critical_fail_count", 0) > 0:
        reasons.append("critical_fail_count_present")
    if summary_counts.get("required_items_blocked_count", 0) > 0 or summary_counts.get("conflict_count", 0) > 0:
        reasons.append("scope_safety_or_conflict_blocker")
    if summary_counts.get("invalid_waiver_count", 0) > 0 or (
        summary_counts.get("waiver_applied_count", 0) > 0 and packet_ref.get("packet_state") != PASSING_PACKET_STATE
    ):
        reasons.append("invalid_noncritical_waiver_state")
    if (summary_counts.get("critical_fail_count", 0) or summary_counts.get("required_items_blocked_count", 0)) and not blocker_ids:
        reasons.append("missing_blocker_ids")
    if reviewer_action in {"accept", "reject"} and reviewer_role not in SUPPORTED_REVIEWER_ROLES:
        reasons.append("unsupported_reviewer_role")
    return _unique(reasons)


__all__ = (
    "ALGORITHM_ID",
    "ARTIFACT_TYPE",
    "CHECKLIST_ARTIFACT_TYPE",
    "CHECKLIST_SCHEMA_VERSION",
    "DECISION_STATES",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "NON_CLAIMS",
    "OUTPUT_CONTRACT",
    "SCHEMA_VERSION",
    "STUDIO_ACTION_WIRING",
    "SUPPORTED_REVIEWER_ROLES",
    "SUPPORTED_TARGET_ENTITY_TYPES",
    "build_final_media_acceptance_decision",
)
