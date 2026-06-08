from __future__ import annotations

from typing import Any

from agentflow.harness.constants import AGENTFLOW_VALIDATION_SCHEMA_VERSION, FAILED, PASSED

SCHEMA_VERSION = AGENTFLOW_VALIDATION_SCHEMA_VERSION


def validate_agentflow_production_asset_feedback_sources(
    *,
    production_handoff: dict[str, Any],
    memory_candidates: dict[str, Any],
    feedback_signal_log: dict[str, Any],
    cost_quality_trace: dict[str, Any],
) -> dict[str, Any]:
    """Validate AgentFlow Production source payloads before asset-feedback mapping."""
    candidates = memory_candidates.get("candidates")
    candidate_statuses = {
        item.get("promotion_status")
        for item in candidates
        if isinstance(item, dict)
    } if isinstance(candidates, list) else set()
    checks = [
        _check(
            "schema_version_0_1_0",
            all(
                payload.get("schema_version") == SCHEMA_VERSION
                for payload in (production_handoff, memory_candidates, feedback_signal_log, cost_quality_trace)
            ),
            "all AgentFlow Production source artifacts use schema_version 0.1.0",
        ),
        _check(
            "production_handoff_type",
            production_handoff.get("artifact_type") == "production_handoff",
            "production_handoff artifact_type is production_handoff",
        ),
        _check(
            "memory_candidates_type",
            memory_candidates.get("artifact_type") == "memory_candidates",
            "memory_candidates artifact_type is memory_candidates",
        ),
        _check(
            "feedback_signal_log_type",
            feedback_signal_log.get("artifact_type") == "feedback_signal_log",
            "feedback_signal_log artifact_type is feedback_signal_log",
        ),
        _check(
            "cost_quality_trace_type",
            cost_quality_trace.get("artifact_type") == "cost_quality_trace",
            "cost_quality_trace artifact_type is cost_quality_trace",
        ),
        _check(
            "production_handoff_has_prompt_pack_ref",
            _artifact_ref_matches(production_handoff, "prompt_pack", "prompt_pack.json"),
            "production handoff references prompt_pack.json",
        ),
        _check(
            "memory_candidates_candidate_only",
            isinstance(candidates, list) and bool(candidates) and candidate_statuses == {"candidate"},
            "memory candidates remain candidate-only",
        ),
        _check(
            "memory_candidates_have_mapping_fields",
            _candidates_have_mapping_fields(candidates),
            "memory candidates include fields required for asset-feedback mapping",
        ),
        _check(
            "feedback_signal_log_source_of_truth",
            feedback_signal_log.get("source_of_truth") == "feedback.jsonl",
            "feedback signal log keeps feedback.jsonl as source of truth",
        ),
        _check(
            "feedback_signal_log_is_derived",
            feedback_signal_log.get("is_primary_feedback_store") is False,
            "feedback signal log is derived, not the primary feedback store",
        ),
        _check(
            "cost_quality_trace_local_deterministic",
            cost_quality_trace.get("provider") == "local_deterministic"
            and cost_quality_trace.get("execution_mode") == "local_deterministic"
            and cost_quality_trace.get("estimated_cost") == 0,
            "cost-quality trace remains local deterministic evidence",
        ),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "agentflow_production_asset_feedback_source_validation",
        "validation_scope": "agentflow_production_asset_feedback_sources",
        "runtime_status": "not_implemented",
        "does_not_execute": True,
        "writes_long_term_memory": False,
        "handoff_id": production_handoff.get("handoff_id"),
        "run_id": memory_candidates.get("run_id") or feedback_signal_log.get("run_id") or cost_quality_trace.get("run_id"),
        "overall_status": FAILED if any(check["status"] == FAILED for check in checks) else PASSED,
        "checks": checks,
    }


def _artifact_ref_matches(payload: dict[str, Any], key: str, expected: str) -> bool:
    refs = payload.get("artifact_refs")
    return isinstance(refs, dict) and refs.get(key) == expected


def _candidates_have_mapping_fields(candidates: Any) -> bool:
    return (
        isinstance(candidates, list)
        and bool(candidates)
        and all(
            isinstance(candidate, dict)
            and _non_empty_str(candidate.get("id"))
            and _non_empty_str(candidate.get("statement"))
            and isinstance(candidate.get("evidence_refs"), list)
            for candidate in candidates
        )
    )


def _non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _check(check_id: str, passed: bool, message: str) -> dict[str, str]:
    return {"check_id": check_id, "status": PASSED if passed else FAILED, "message": message}
