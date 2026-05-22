from __future__ import annotations

from typing import Any

from agentflow.harness.constants import AGENTFLOW_VALIDATION_SCHEMA_VERSION

SCHEMA_VERSION = AGENTFLOW_VALIDATION_SCHEMA_VERSION


def build_narratostudio_asset_memory_contract_set(
    *,
    production_handoff: dict[str, Any],
    memory_candidates: dict[str, Any],
    feedback_signal_log: dict[str, Any],
    cost_quality_trace: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build a smoke-test contract set from NarratoStudio run artifacts.

    This is a pure contract adapter: it does not execute durable memory
    promotion, create persisted asset profiles, run workflows, or write state.
    """
    candidate = _first_memory_candidate(memory_candidates)
    handoff_id = _required_str(production_handoff, "handoff_id", "production handoff")
    candidate_id = _candidate_id(candidate)
    asset_id = f"narratostudio_intermediate_asset:{handoff_id}"
    promotion_decision_id = f"narratostudio_promotion_decision:{candidate_id}"
    asset_profile_id = f"narratostudio_reusable_asset_profile:{handoff_id}"

    intermediate_asset = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "agentflow_intermediate_asset",
        "asset_id": asset_id,
        "asset_kind": "production_handoff_signal",
        "module_origin": "NarratoStudio",
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
        "project_id": production_handoff.get("source_brief_id", "narratostudio_project"),
        "module_owner": "NarratoStudio",
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
            "allowed_modules": ["NarratoStudio"],
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
        "decision_id": f"narratostudio_asset_reuse_decision:{handoff_id}",
        "target_task": "narratostudio_brief_to_production_handoff",
        "selected_asset_profile_ids": [asset_profile_id],
        "rejected_asset_profile_ids": [],
        "reason": "Selected the smoke asset profile to validate the NarratoStudio asset-feedback contract loop.",
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
        raise ValueError("NarratoStudio asset-memory smoke requires at least one memory candidate")
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        raise ValueError("NarratoStudio memory candidate must be an object")
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
    title = production_handoff.get("project_title") or production_handoff.get("handoff_id") or "NarratoStudio handoff"
    statement = candidate.get("statement") or "candidate production preference"
    return f"Smoke intermediate asset from {title}: {statement}"


__all__ = (
    "SCHEMA_VERSION",
    "build_narratostudio_asset_memory_contract_set",
)
