from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agentflow.algorithms.final_media_acceptance_decision._contract import (
    ALGORITHM_ID,
    ARTIFACT_TYPE,
    DEFAULT_MAX_PACKET_AGE_SECONDS,
    NON_CLAIMS,
    REQUIRED_SUMMARY_COUNT_KEYS,
    SCHEMA_VERSION,
    STUDIO_ACTION_WIRING,
)
from agentflow.algorithms.structured_source_output_qa_checklist._contract import ACTIVE_RUNTIME_STATES
from agentflow.algorithms.structured_source_output_qa_checklist._safety import (
    safe_int as _safe_int,
    safe_list as _safe_list,
    safe_route as _safe_route,
    safe_token as _safe_token,
)


def decision_packet(
    *,
    project_id: str,
    target_id: str,
    target_entity_type: str,
    packet_ref: dict[str, Any],
    summary_counts: dict[str, int],
    output_ref_summary: dict[str, Any],
    blocker_ids: list[str],
    decision_state: str,
    qa_passed: bool,
    accepted: bool,
    reviewer_action: str,
    reviewer_role: str,
    decision_requested_at: str,
    decision_reasons: list[str],
) -> dict[str, Any]:
    entity_type = _safe_token(target_entity_type) or "video_revision"
    action = reviewer_action_id(reviewer_action)
    return {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "algorithm_id": ALGORITHM_ID,
        "project_id": project_id,
        "target_id": target_id,
        "target_entity_type": entity_type,
        "decision_id": f"final_media_decision:{target_id}:{packet_ref.get('checklist_id', 'unknown')}",
        "decision_state": decision_state,
        "qa_passed": qa_passed,
        "accepted_for_local_final_media": accepted,
        "reviewer_action_required": qa_passed and not action,
        "reviewer_action": {
            "action_id": action,
            "studio_action_id": action if action in {"accept", "reject"} else "",
            "reviewer_role": _safe_token(reviewer_role),
            "explicit_action_received": action in {"accept", "reject"},
            "action_applied": accepted or decision_state == "rejected_for_local_final_media",
        },
        "checklist_packet_ref": packet_ref,
        "source_checklist_summary": {key: _safe_int(summary_counts.get(key)) for key in REQUIRED_SUMMARY_COUNT_KEYS},
        "output_ref_summary": output_ref_summary,
        "blocker_ids": blocker_ids,
        "decision_reasons": unique(safe_token_list(decision_reasons)),
        "packet_policy": {
            "fail_closed": True,
            "consumes_checklist_truth_without_recalculation": True,
            "copies_checklist_item_arrays": False,
            "qa_passed_does_not_accept_without_reviewer_action": True,
            "noncritical_waivers_allowed_only_when_source_checklist_completed": True,
        },
        "studio_action_wiring": {
            **STUDIO_ACTION_WIRING,
            "applies_to_entity_type": entity_type,
            "acceptance_requires_qa_passed": True,
            "acceptance_requires_explicit_reviewer_action": True,
            "preserves_existing_status_vocabulary": True,
        },
        "safety_boundary": {
            "provider_calls_started": bool(output_ref_summary.get("provider_calls_started")),
            "writes_long_term_memory": False,
            "writes_company_kb": False,
        },
        "decision_requested_at": _safe_token(decision_requested_at),
        "non_claims": NON_CLAIMS,
    }


def checklist_packet_ref(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": _safe_token(packet.get("artifact_type")),
        "schema_version": _safe_token(packet.get("schema_version")),
        "artifact_id": _safe_token(packet.get("artifact_id") or packet.get("packet_id") or packet.get("checklist_packet_id")),
        "project_id": _safe_token(packet.get("project_id")),
        "target_id": _safe_token(packet.get("target_id")),
        "checklist_id": _safe_token(packet.get("checklist_id")),
        "packet_state": _safe_token(packet.get("packet_state")),
        "created_at": _safe_token(packet.get("created_at") or packet.get("packet_created_at")),
    }


def summary_counts(value: Any) -> tuple[dict[str, int], bool]:
    raw = value if isinstance(value, dict) else {}
    counts = {key: _safe_int(raw.get(key)) for key in REQUIRED_SUMMARY_COUNT_KEYS}
    malformed = not isinstance(value, dict) or any(key not in raw for key in REQUIRED_SUMMARY_COUNT_KEYS)
    return counts, malformed


def output_ref_summary(packet: dict[str, Any]) -> dict[str, Any]:
    explicit = packet.get("output_ref_summary") if isinstance(packet.get("output_ref_summary"), dict) else {}
    refs = [item for item in _safe_list(packet.get("observed_output_refs")) if isinstance(item, dict)]
    output_ids = safe_token_list(explicit.get("output_ref_ids")) or [
        _safe_token(item.get("output_ref_id")) for item in refs if _safe_token(item.get("output_ref_id"))
    ]
    runtime_states = safe_token_list(explicit.get("runtime_states")) or [
        _safe_token(item.get("runtime_state") or item.get("status")) for item in refs if _safe_token(item.get("runtime_state") or item.get("status"))
    ]
    output_count = _safe_int(explicit.get("output_count")) or len(output_ids) or len(refs)
    preview_count = _safe_int(explicit.get("safe_preview_ref_count")) or sum(1 for item in refs if _safe_route(item.get("safe_preview_ref")))
    target_id = _safe_token(packet.get("target_id"))
    project_id = _safe_token(packet.get("project_id"))
    mismatch = any(
        _safe_token(item.get("project_id")) not in {"", project_id} or _safe_token(item.get("target_id")) not in {"", target_id}
        for item in refs
    )
    return {
        "output_count": output_count,
        "safe_preview_ref_count": preview_count,
        "output_ref_ids": output_ids[:12],
        "runtime_states": runtime_states[:12],
        "active_runtime_state_present": any(state in ACTIVE_RUNTIME_STATES for state in runtime_states),
        "project_or_target_mismatch": mismatch,
        "provider_calls_started": bool(explicit.get("provider_calls_started")) or any(bool(item.get("provider_calls_started")) for item in refs),
    }


def runtime_review_active(packet: dict[str, Any]) -> bool:
    review = packet.get("runtime_state_review") if isinstance(packet.get("runtime_state_review"), dict) else {}
    return bool(review.get("active_runtime_state_present") or review.get("noncompletion_required"))


def reviewer_action_id(value: Any) -> str:
    action = _safe_token(value)
    if action == "accepted_for_local_final_media":
        return "accept"
    if action in {"accept", "reject"}:
        return action
    return ""


def packet_state_reason(packet_state: str) -> str:
    if packet_state == "blocked_unsafe":
        return "checklist_blocked_unsafe"
    if packet_state == "blocked_project_scope":
        return "project_or_target_mismatch"
    if packet_state == "blocked_conflict":
        return "scope_safety_or_conflict_blocker"
    return "missing_output_ref"


def blocked_state(reasons: list[str]) -> str:
    if any(reason == "unsupported_reviewer_role" for reason in reasons):
        return "blocked_unsupported_reviewer_role"
    if any(reason in {"unsafe_checklist_packet_payload", "checklist_blocked_unsafe"} for reason in reasons):
        return "blocked_unsafe"
    if any(reason == "stale_checklist_packet_ref" for reason in reasons):
        return "blocked_stale_packet"
    if any(reason in {"malformed_checklist_packet_ref", "unsupported_target_entity_type"} for reason in reasons):
        return "blocked_malformed_packet"
    if any(reason in {"project_or_target_mismatch", "checklist_ref_mismatch"} for reason in reasons):
        return "blocked_project_scope"
    if any(reason == "scope_safety_or_conflict_blocker" for reason in reasons):
        return "blocked_conflict"
    return "blocked_missing_evidence"


def default_decision_reasons(action: str, decision_state: str) -> list[str]:
    if decision_state == "accepted_for_local_final_media":
        return ["explicit_reviewer_accept_after_qa_passed"]
    if decision_state == "rejected_for_local_final_media":
        return ["explicit_reviewer_reject_after_qa_passed"]
    if not action:
        return ["qa_passed_requires_explicit_reviewer_action"]
    return ["qa_passed"]


def parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def packet_is_stale(packet_time: datetime, decision_time: datetime, max_age_seconds: int) -> bool:
    max_age = max(DEFAULT_MAX_PACKET_AGE_SECONDS, _safe_int(max_age_seconds))
    age = (decision_time - packet_time).total_seconds()
    return age < -60 or age > max_age


def safe_token_list(value: Any) -> list[str]:
    return [token for token in (_safe_token(item) for item in _safe_list(value)) if token]


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
