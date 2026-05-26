from __future__ import annotations

from typing import Any


FAILURE_CATEGORY_BY_CHECK = {
    "posterflow_candidate_images_exist": "generated_artifact_failure",
    "posterflow_feedback_source_of_truth_is_raw_jsonl": "feedback_contract_failure",
    "posterflow_raw_feedback_candidate_refs_known": "feedback_reference_failure",
    "posterflow_feedback_candidate_refs_known": "feedback_reference_failure",
    "posterflow_memory_jsonl_candidate_only": "memory_candidate_contract_failure",
    "posterflow_memory_json_jsonl_match": "memory_candidate_contract_failure",
    "posterflow_memory_candidate_only": "memory_candidate_contract_failure",
    "posterflow_memory_review_refs_candidates": "memory_review_contract_failure",
    "posterflow_memory_review_no_long_term_write": "memory_review_policy_failure",
    "posterflow_profile_uses_accepted_memory": "memory_profile_contract_failure",
    "posterflow_context_trace_refs_bundle": "context_trace_contract_failure",
    "posterflow_context_trace_cache_key_matches": "context_trace_contract_failure",
    "posterflow_context_does_not_write_long_term_memory": "context_policy_failure",
    "posterflow_evidence_chain_stages_complete": "evidence_chain_contract_failure",
    "posterflow_evidence_chain_review_decision_refs_review": "evidence_chain_contract_failure",
    "posterflow_evidence_chain_context_refs_bundle": "evidence_chain_contract_failure",
    "posterflow_evidence_chain_no_long_term_write": "evidence_chain_policy_failure",
}


def build_quality_feedback_signals(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for check in checks:
        if check.get("status") != "fail":
            continue
        check_name = str(check.get("name", "unknown_check"))
        signals.append(
            {
                "signal_id": f"quality_feedback::{check_name}",
                "source_check_id": check_name,
                "failure_category": FAILURE_CATEGORY_BY_CHECK.get(check_name, "posterflow_quality_failure"),
                "status": "candidate",
                "severity": _severity(check_name),
                "summary": f"{check_name} failed",
                "evidence_refs": ["quality_report.json"],
                "writes_long_term_memory": False,
                "details": check.get("details", {}),
            }
        )
    return signals


def _severity(check_name: str) -> str:
    if check_name.endswith("_exists") or check_name in {
        "posterflow_candidate_images_exist",
        "posterflow_memory_review_no_long_term_write",
        "posterflow_context_does_not_write_long_term_memory",
    }:
        return "blocking"
    return "review_required"
