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


def build_agentflow_production_asset_memory_contract_set(
    *,
    production_handoff: dict[str, Any],
    memory_candidates: dict[str, Any],
    feedback_signal_log: dict[str, Any],
    cost_quality_trace: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build a smoke-test contract set from AgentFlow Production run artifacts.

    This is a pure contract adapter: it does not execute durable memory
    promotion, create persisted asset profiles, run workflows, or write state.
    """
    candidate = _first_memory_candidate(memory_candidates)
    handoff_id = _required_str(production_handoff, "handoff_id", "production handoff")
    candidate_id = _candidate_id(candidate)
    asset_id = f"agentflow_production_intermediate_asset:{handoff_id}"
    promotion_decision_id = f"agentflow_production_promotion_decision:{candidate_id}"
    asset_profile_id = f"agentflow_production_reusable_asset_profile:{handoff_id}"

    intermediate_asset = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "agentflow_intermediate_asset",
        "asset_id": asset_id,
        "asset_kind": "production_handoff_signal",
        "module_origin": "AgentFlow Production",
        "created_by": "agent",
        "source_artifact_refs": _source_artifact_refs(production_handoff),
        "evidence_refs": _evidence_refs(candidate, feedback_signal_log, cost_quality_trace),
        "summary": _asset_summary(production_handoff, candidate),
        "reuse_status": "candidate",
        "metadata": {
            "source_handoff_id": handoff_id,
            "smoke_contract": True,
        },
    }
    memory_candidate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "agentflow_memory_candidate",
        "candidate_id": candidate_id,
        "project_id": production_handoff.get("source_brief_id", "agentflow_production_project"),
        "module_owner": "AgentFlow Production",
        "source_artifact": "memory_candidates.json",
        "source_of_truth": feedback_signal_log.get("source_of_truth"),
        "derived_from_feedback_signal": "feedback_signal_log.json",
        "promotion_status": candidate.get("promotion_status"),
        "memory_type": candidate.get("memory_type", "production_preference"),
        "statement": _required_str(candidate, "statement", "memory candidate"),
        "evidence_refs": _candidate_evidence_refs(candidate),
        "confidence": candidate.get("confidence", 0),
        "suggested_promotion_condition": (
            "Promote only after human-reviewed repeated use confirms the same production preference."
        ),
        "metadata": {
            "source_handoff_id": handoff_id,
            "smoke_contract": True,
        },
    }
    memory_promotion_decision = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "agentflow_memory_promotion_decision",
        "decision_id": promotion_decision_id,
        "project_id": memory_candidate["project_id"],
        "source_candidate_id": candidate_id,
        "decision": "promoted",
        "promotion_mode": "human_reviewed",
        "writes_long_term_memory": False,
        "evidence_refs": memory_candidate["evidence_refs"],
        "reason_tags": [
            "smoke_contract",
            "requires_human_review",
        ],
        "review_note": "Smoke contract only; no durable memory store is written.",
        "decided_by": "human_review_gate",
        "decided_at": "not_persisted",
        "metadata": {
            "source_handoff_id": handoff_id,
            "smoke_contract": True,
        },
    }
    reusable_asset_profile = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "agentflow_reusable_asset_profile",
        "asset_profile_id": asset_profile_id,
        "source_intermediate_asset_ids": [asset_id],
        "promotion_decision_ref": f"agentflow_memory_promotion_decision:{promotion_decision_id}",
        "reuse_policy": {
            "allowed_modules": ["AgentFlow Production"],
            "requires_human_review": True,
            "allowed_task_types": [production_handoff.get("content_mode", "episodic_story_production")],
        },
        "active_status": "active",
        "metadata": {
            "source_handoff_id": handoff_id,
            "smoke_contract": True,
        },
    }
    asset_reuse_decision = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "agentflow_asset_reuse_decision",
        "decision_id": f"agentflow_production_asset_reuse_decision:{handoff_id}",
        "target_task": "agentflow_production_brief_to_production_handoff",
        "selected_asset_profile_ids": [asset_profile_id],
        "rejected_asset_profile_ids": [],
        "reason": "Selected the smoke asset profile to validate the AgentFlow Production asset-feedback contract loop.",
        "does_not_execute": True,
        "metadata": {
            "source_handoff_id": handoff_id,
            "smoke_contract": True,
        },
    }
    return {
        "intermediate_asset": intermediate_asset,
        "reusable_asset_profile": reusable_asset_profile,
        "asset_reuse_decision": asset_reuse_decision,
        "memory_candidate": memory_candidate,
        "memory_promotion_decision": memory_promotion_decision,
    }


def _first_memory_candidate(memory_candidates: dict[str, Any]) -> dict[str, Any]:
    candidates = memory_candidates.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("AgentFlow Production asset-memory smoke requires at least one memory candidate")
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        raise ValueError("AgentFlow Production memory candidate must be an object")
    return candidate


def _candidate_id(candidate: dict[str, Any]) -> str:
    return _required_str(candidate, "id", "memory candidate")


def _required_str(payload: dict[str, Any], key: str, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} missing required {key}")
    return value


def _source_artifact_refs(production_handoff: dict[str, Any]) -> list[str]:
    refs = production_handoff.get("artifact_refs")
    if not isinstance(refs, dict):
        return ["production_handoff.json"]
    return sorted({str(value) for value in refs.values() if isinstance(value, str)} | {"production_handoff.json"})


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


def _evidence_refs(
    candidate: dict[str, Any],
    feedback_signal_log: dict[str, Any],
    cost_quality_trace: dict[str, Any],
) -> list[str]:
    refs = set(_candidate_evidence_refs(candidate))
    if feedback_signal_log.get("source_of_truth") == "feedback.jsonl":
        refs.add("feedback.jsonl")
    if cost_quality_trace.get("provider"):
        refs.add("cost_quality_trace.json")
    refs.add("feedback_signal_log.json")
    return sorted(refs)


def _candidate_evidence_refs(candidate: dict[str, Any]) -> list[str]:
    refs = candidate.get("evidence_refs")
    if not isinstance(refs, list):
        return ["memory_candidates.json"]
    values = [str(value) for value in refs if isinstance(value, str) and value]
    return values or ["memory_candidates.json"]


def _asset_summary(production_handoff: dict[str, Any], candidate: dict[str, Any]) -> str:
    title = production_handoff.get("project_title") or production_handoff.get("handoff_id") or "AgentFlow Production handoff"
    statement = candidate.get("statement") or "candidate production preference"
    return f"Smoke intermediate asset from {title}: {statement}"


def _non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _check(check_id: str, passed: bool, message: str) -> dict[str, str]:
    return {"check_id": check_id, "status": PASSED if passed else FAILED, "message": message}


__all__ = (
    "SCHEMA_VERSION",
    "build_agentflow_production_asset_memory_contract_set",
    "validate_agentflow_production_asset_feedback_sources",
)
