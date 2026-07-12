from __future__ import annotations

from typing import Any

from agentflow.algorithms.structured_source_output_qa_checklist._contract import (
    ACTIVE_RUNTIME_STATES,
    ALGORITHM_ID,
    CRITICAL_CATEGORIES,
    EVIDENCE_BOUNDARY,
    FAILURE_MODES,
    INPUT_CONTRACT,
    ITEM_OUTCOMES,
    NON_CLAIMS,
    OUTPUT_CONTRACT,
    PACKET_STATES,
    SAFETY_CATEGORIES,
    SCHEMA_VERSION,
    SCOPE_CATEGORIES,
)
from agentflow.algorithms.structured_source_output_qa_checklist._safety import (
    dicts as _dicts,
    has_unsafe_payload as _has_unsafe_payload,
    minimal_blocked_packet as _minimal_blocked_packet,
    project_mismatch as _project_mismatch,
    safe_enum as _safe_enum,
    safe_list as _list,
    safe_note as _safe_note,
    safe_output_ref as _safe_output_ref,
    safe_source_ref as _safe_source_ref,
    safe_token as _safe_token,
    target_mismatch as _target_mismatch,
)


def build_structured_source_output_qa_checklist(
    *,
    project_id: str,
    target_id: str,
    checklist_items: list[dict[str, Any]] | None,
    source_inventory: list[dict[str, Any]] | None = None,
    observed_outputs: list[dict[str, Any]] | None = None,
    waivers: list[dict[str, Any]] | None = None,
    checklist_id: str = "",
    runtime_state: str = "",
) -> dict[str, Any]:
    sources = [_safe_source_ref(item) for item in _dicts(source_inventory)]
    outputs = [_safe_output_ref(item) for item in _dicts(observed_outputs)]
    unsafe_input = _has_unsafe_payload(
        {
            "checklist_items": checklist_items or [],
            "source_inventory": source_inventory or [],
            "observed_outputs": observed_outputs or [],
            "waivers": waivers or [],
        }
    )
    source_ids = {item["source_ref_id"] for item in sources if item["source_ref_id"]}
    output_ids = {item["output_ref_id"] for item in outputs if item["output_ref_id"]}
    project_or_target_mismatch = _project_mismatch(project_id, [*sources, *outputs, *_dicts(checklist_items), *_dicts(waivers)])
    project_or_target_mismatch = project_or_target_mismatch or _target_mismatch(target_id, [*outputs, *_dicts(checklist_items)])
    missing_safe_preview = any(not item["safe_preview_ref"] for item in outputs) if outputs else True
    active_runtime = _safe_token(runtime_state) in ACTIVE_RUNTIME_STATES or any(
        item["runtime_state"] in ACTIVE_RUNTIME_STATES for item in outputs
    )
    missing_target_output = not outputs or any(item["target_id"] != _safe_token(target_id) for item in outputs)
    item_records = [
        _checklist_item(
            item,
            project_id=_safe_token(project_id),
            target_id=_safe_token(target_id),
            source_ids=source_ids,
            output_ids=output_ids,
            global_outcome=_global_item_outcome(unsafe_input, project_or_target_mismatch),
        )
        for item in _dicts(checklist_items)
    ]
    waiver_result = _validate_waivers(
        _dicts(waivers),
        item_records,
        unsafe_input=unsafe_input,
        project_or_target_mismatch=project_or_target_mismatch,
        missing_target_output=missing_target_output,
        missing_safe_preview=missing_safe_preview,
        active_runtime=active_runtime,
    )
    summary = _summary_counts(item_records, waiver_result)
    packet = {
        "artifact_type": "agentflow_structured_source_output_qa_checklist",
        "schema_version": SCHEMA_VERSION,
        "algorithm_id": ALGORITHM_ID,
        "project_id": _safe_token(project_id),
        "target_id": _safe_token(target_id),
        "checklist_id": _safe_token(checklist_id) or f"checklist:{_safe_token(target_id)}",
        "packet_state": _packet_state(
            item_records,
            summary,
            unsafe_input=unsafe_input,
            project_or_target_mismatch=project_or_target_mismatch,
            missing_target_output=missing_target_output,
            missing_safe_preview=missing_safe_preview,
            active_runtime=active_runtime,
        ),
        "packet_policy": {
            "fail_closed": True,
            "safe_surface_only": True,
            "waivers_allowed_for_noncritical_evidence_only": True,
            "runtime_complete_means_reviewable_not_decided": True,
        },
        "source_inventory": sources,
        "observed_output_refs": outputs,
        "checklist_items": item_records,
        "summary_counts": summary,
        "waiver_validation": waiver_result,
        "runtime_state_review": {
            "active_runtime_state_present": active_runtime,
            "reason_code": "runtime_state_not_stable_reviewable" if active_runtime else "",
            "noncompletion_required": active_runtime,
        },
        "safety_boundary": {
            "provider_calls_started": any(item["provider_calls_started"] for item in outputs),
            "writes_long_term_memory": False,
            "writes_company_kb": False,
        },
        "non_claims": NON_CLAIMS,
    }
    if _has_unsafe_payload(packet):
        return _minimal_blocked_packet(project_id, target_id, checklist_id)
    return packet


def _checklist_item(
    item: dict[str, Any],
    *,
    project_id: str,
    target_id: str,
    source_ids: set[str],
    output_ids: set[str],
    global_outcome: str,
) -> dict[str, Any]:
    item_id = _safe_token(item.get("item_id")) or "checklist_item"
    category = _safe_token(item.get("category")) or "source_output_requirement"
    expected_refs = [_safe_token(value) for value in _list(item.get("expected_source_refs"))]
    observed_refs = [_safe_token(value) for value in _list(item.get("observed_output_refs"))]
    missing_sources = [value for value in expected_refs if value and value not in source_ids]
    missing_outputs = [value for value in observed_refs if value and value not in output_ids]
    severity = _safe_token(item.get("severity")) or "medium"
    critical = bool(item.get("critical")) or severity == "critical" or category in CRITICAL_CATEGORIES
    required = item.get("required") is not False
    outcome = global_outcome or _safe_enum(item.get("outcome"), ITEM_OUTCOMES, "")
    if not outcome:
        if missing_sources or missing_outputs or (required and not observed_refs and category != "not_applicable"):
            outcome = "blocked_missing_evidence" if critical else "partially_followed"
        else:
            outcome = "followed"
    if item.get("conflict") is True:
        outcome = "blocked_conflict"
    if category in SAFETY_CATEGORIES and outcome not in {"followed", "not_applicable"}:
        outcome = "blocked_unsafe"
    if category in SCOPE_CATEGORIES and outcome not in {"followed", "not_applicable"}:
        outcome = "blocked_project_scope"
    return {
        "item_id": item_id,
        "project_id": project_id,
        "target_id": target_id,
        "category": category,
        "required": required,
        "severity": severity,
        "critical": critical,
        "expected_source_refs": expected_refs,
        "observed_output_refs": observed_refs,
        "safe_evidence_refs": [
            *[{"ref_kind": "source", "ref_id": value} for value in expected_refs if value],
            *[{"ref_kind": "output", "ref_id": value} for value in observed_refs if value],
        ],
        "outcome": outcome,
        "blocker": outcome.startswith("blocked_") or (critical and outcome in {"ignored", "partially_followed", "unverifiable"}),
        "missing_source_ref_count": len(missing_sources),
        "missing_output_ref_count": len(missing_outputs),
        "reviewer_note": _safe_note(item.get("reviewer_note")),
        "suggested_local_action": _safe_note(item.get("suggested_local_action")),
        "closed_by_waiver": False,
    }


def _validate_waivers(
    waivers: list[dict[str, Any]],
    items: list[dict[str, Any]],
    *,
    unsafe_input: bool,
    project_or_target_mismatch: bool,
    missing_target_output: bool,
    missing_safe_preview: bool,
    active_runtime: bool,
) -> dict[str, Any]:
    by_id = {item["item_id"]: item for item in items}
    records = []
    for waiver in waivers:
        item_id = _safe_token(waiver.get("item_id"))
        item = by_id.get(item_id)
        reasons: list[str] = []
        if item is None:
            reasons.append("unknown_item")
        if not _safe_token(waiver.get("reviewer_role")):
            reasons.append("missing_reviewer_role")
        for active, reason in (
            (unsafe_input, "unsafe_input_payload"),
            (project_or_target_mismatch, "project_or_target_mismatch"),
            (missing_target_output, "missing_target_output"),
            (missing_safe_preview, "missing_safe_preview_ref"),
            (active_runtime, "runtime_state_not_stable_reviewable"),
        ):
            if active:
                reasons.append(reason)
        if item is not None:
            category = item["category"]
            if item["critical"] or category in SAFETY_CATEGORIES or category in SCOPE_CATEGORIES:
                reasons.append("waiver_not_allowed_for_item")
            if item["outcome"] in {"blocked_unsafe", "blocked_project_scope", "blocked_conflict"}:
                reasons.append("waiver_not_allowed_for_blocker")
        valid = not reasons
        if valid and item is not None:
            item["closed_by_waiver"] = True
        records.append(
            {
                "waiver_id": _safe_token(waiver.get("waiver_id")) or f"waiver:{item_id or 'unknown'}",
                "item_id": item_id,
                "reviewer_role": _safe_token(waiver.get("reviewer_role")),
                "waiver_state": "valid" if valid else "invalid",
                "invalid_reasons": reasons,
                "reviewer_note": _safe_note(waiver.get("reviewer_note")),
            }
        )
    return {
        "valid_waiver_count": sum(1 for item in records if item["waiver_state"] == "valid"),
        "invalid_waiver_count": sum(1 for item in records if item["waiver_state"] == "invalid"),
        "waivers": records,
    }


def _summary_counts(items: list[dict[str, Any]], waiver_result: dict[str, Any]) -> dict[str, int]:
    closed = {item["item_id"] for item in items if item["closed_by_waiver"]}
    required = [item for item in items if item["required"]]
    blocked = {"blocked_missing_evidence", "blocked_unsafe", "blocked_project_scope", "blocked_conflict", "ignored"}
    waiver_needed = [
        item
        for item in required
        if not item["critical"] and item["item_id"] not in closed and item["outcome"] in {"partially_followed", "blocked_missing_evidence", "unverifiable"}
    ]
    return {
        "total_item_count": len(items),
        "required_item_count": len(required),
        "required_items_followed_count": sum(1 for item in required if item["outcome"] in {"followed", "not_applicable"}),
        "required_items_blocked_count": sum(1 for item in required if item["item_id"] not in closed and item["outcome"] in blocked),
        "critical_fail_count": sum(1 for item in items if item["critical"] and item["outcome"] not in {"followed", "not_applicable"}),
        "waiver_required_count": len(waiver_needed),
        "waiver_applied_count": int(waiver_result["valid_waiver_count"]),
        "invalid_waiver_count": int(waiver_result["invalid_waiver_count"]),
        "unverifiable_count": sum(1 for item in items if item["outcome"] == "unverifiable"),
        "conflict_count": sum(1 for item in items if item["outcome"] == "blocked_conflict"),
    }


def _packet_state(
    items: list[dict[str, Any]],
    summary: dict[str, int],
    *,
    unsafe_input: bool,
    project_or_target_mismatch: bool,
    missing_target_output: bool,
    missing_safe_preview: bool,
    active_runtime: bool,
) -> str:
    outcomes = {item["outcome"] for item in items if not item["closed_by_waiver"]}
    if unsafe_input or "blocked_unsafe" in outcomes:
        return "blocked_unsafe"
    if project_or_target_mismatch or "blocked_project_scope" in outcomes:
        return "blocked_project_scope"
    if "blocked_conflict" in outcomes:
        return "blocked_conflict"
    if active_runtime:
        return "blocked_missing_evidence"
    if missing_target_output or missing_safe_preview or "blocked_missing_evidence" in outcomes or summary["critical_fail_count"]:
        return "blocked_missing_evidence"
    if "unverifiable" in outcomes:
        return "unverifiable"
    if summary["waiver_required_count"] or summary["invalid_waiver_count"] or "partially_followed" in outcomes or "ignored" in outcomes:
        return "checklist_ready_for_review"
    return "checklist_completed"


def _global_item_outcome(unsafe_input: bool, project_or_target_mismatch: bool) -> str:
    if unsafe_input:
        return "blocked_unsafe"
    if project_or_target_mismatch:
        return "blocked_project_scope"
    return ""


__all__ = ("ALGORITHM_ID", "EVIDENCE_BOUNDARY", "FAILURE_MODES", "INPUT_CONTRACT", "ITEM_OUTCOMES", "NON_CLAIMS", "OUTPUT_CONTRACT", "PACKET_STATES", "SCHEMA_VERSION", "build_structured_source_output_qa_checklist")
