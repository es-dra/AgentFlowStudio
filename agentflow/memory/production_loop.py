from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import FAILED, PASSED
from agentflow.memory.production_next_pass import NEXT_PASS_BUNDLE_KIND, build_next_pass_bundle
from agentflow.memory.production_loop_support import (
    check as _check,
    dict_value as _dict,
    has_private_fragment as _has_private_fragment,
    indexes as _indexes,
    list_value as _list,
    missing_references as _missing_references,
    project_id as _project_id,
    promoted_memory_has_decision as _promoted_memory_has_decision,
    promotion_decisions_supported as _promotion_decisions_supported,
    provider_mode as _provider_mode,
    record_ids_unique as _record_ids_unique,
    reference_message as _reference_message,
    remote_provider_required as _remote_provider_required,
    requested_refs as _requested_refs,
    source_sections_present as _source_sections_present,
    source_sections_typed as _source_sections_typed,
)
from agentflow.harness.json_io import write_json

KIND = "agentflow_production_memory_loop"
SCHEMA_VERSION = "production-memory-loop/v1"
RUN_KIND = "agentflow_production_memory_loop_run"
CONTEXT_BUNDLE_KIND = "agentflow_production_memory_context_bundle"
PASS_READINESS_KIND = "agentflow_production_memory_pass_readiness"

INCLUDABLE_ARTIFACT_STATUSES = frozenset({"approved", "accepted", "ready", "promoted"})
BLOCKED_STATUSES = frozenset({"rejected", "pending", "blocked", "expired"})
PROMOTION_DECISIONS_ALLOWING_CONTEXT = frozenset({"promoted", "merged"})


def load_production_memory_loop(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("production memory loop input must be a JSON object")
    return payload


def validate_production_memory_loop(payload: dict[str, Any]) -> dict[str, Any]:
    checks = [
        _check("root_kind", payload.get("kind") == KIND, "kind is agentflow_production_memory_loop"),
        _check("root_artifact_type", payload.get("artifact_type") == KIND, "artifact_type matches the loop kind"),
        _check("schema_version", payload.get("schema_version") == SCHEMA_VERSION, "schema_version is production-memory-loop/v1"),
        _check("source_sections_present", _source_sections_present(payload), "all production-memory source sections are present"),
        _check("source_sections_typed", _source_sections_typed(payload), "source sections have the expected object/list shapes"),
        _check("record_ids_unique", _record_ids_unique(payload), "source record ids are unique within each ledger"),
        _check("references_resolve", not _missing_references(payload), _reference_message(payload)),
        _check(
            "promoted_memory_has_decision",
            _promoted_memory_has_decision(payload),
            "memory marked promoted has an explicit promotion decision",
        ),
        _check(
            "promotion_decisions_supported",
            _promotion_decisions_supported(payload),
            "promotion decisions use supported statuses",
        ),
        _check("no_provider_mode", _provider_mode(payload) == "no-provider", "loop is configured for no-provider mode"),
        _check("no_remote_provider_required", not _remote_provider_required(payload), "no-provider mode requires no remote provider"),
        _check(
            "no_long_term_memory_write",
            payload.get("writes_long_term_memory") is False,
            "the loop does not write durable memory",
        ),
        _check("no_private_paths_or_secrets", not _has_private_fragment(payload), "example avoids private paths and secrets"),
    ]
    return {
        "kind": "agentflow_production_memory_loop_validation",
        "artifact_type": "agentflow_production_memory_loop_validation",
        "schema_version": SCHEMA_VERSION,
        "loop_id": payload.get("loop_id", "unknown"),
        "provider_mode": _provider_mode(payload),
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "overall_status": FAILED if any(check["status"] == FAILED for check in checks) else PASSED,
        "checks": checks,
    }


def build_production_memory_loop_run(payload: dict[str, Any]) -> dict[str, Any]:
    validation = validate_production_memory_loop(payload)
    context_bundle = build_context_bundle(payload)
    pass_readiness = build_pass_readiness(validation, context_bundle)
    next_pass_bundle = build_next_pass_bundle(payload, context_bundle, pass_readiness)
    return {
        "kind": RUN_KIND,
        "artifact_type": RUN_KIND,
        "schema_version": SCHEMA_VERSION,
        "loop_id": payload.get("loop_id", "unknown"),
        "project_id": _project_id(payload),
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "validation": validation,
        "context_bundle": context_bundle,
        "pass_readiness": pass_readiness,
        "next_pass_bundle": next_pass_bundle,
    }


def build_context_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    indexes = _indexes(payload)
    included_refs: list[dict[str, Any]] = []
    blocked_refs: list[dict[str, Any]] = []
    for ref_id in _requested_refs(payload):
        included, blocked = _classify_ref(ref_id, indexes)
        if included:
            included_refs.append(included)
        if blocked:
            blocked_refs.append(blocked)
    return {
        "kind": CONTEXT_BUNDLE_KIND,
        "artifact_type": CONTEXT_BUNDLE_KIND,
        "schema_version": SCHEMA_VERSION,
        "bundle_id": f"context:{payload.get('loop_id', 'production-memory-loop')}:no-provider",
        "project_id": _project_id(payload),
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "included_refs": included_refs,
        "blocked_refs": blocked_refs,
        "generated_from": {
            "project_input_ref": _project_id(payload),
            "artifact_ledger_count": len(indexes["artifacts"]),
            "feedback_event_count": len(indexes["feedback"]),
            "memory_candidate_count": len(indexes["candidates"]),
            "promotion_decision_count": len(indexes["decisions"]),
        },
    }


def build_pass_readiness(validation: dict[str, Any], context_bundle: dict[str, Any]) -> dict[str, Any]:
    checks = [
        _check("validation_passed", validation.get("overall_status") == PASSED, "source contract validation passed"),
        _check("provider_mode_no_provider", context_bundle.get("provider_mode") == "no-provider", "provider mode is no-provider"),
        _check(
            "provider_calls_not_started",
            context_bundle.get("provider_calls_started") is False,
            "no remote provider calls were started",
        ),
        _check(
            "context_bundle_has_included_refs",
            bool(context_bundle.get("included_refs")),
            "context bundle includes at least one eligible ref",
        ),
        _check(
            "context_bundle_lists_blocked_refs",
            isinstance(context_bundle.get("blocked_refs"), list),
            "context bundle lists blocked refs",
        ),
    ]
    ready = all(check["status"] == PASSED for check in checks)
    return {
        "kind": PASS_READINESS_KIND,
        "artifact_type": PASS_READINESS_KIND,
        "schema_version": SCHEMA_VERSION,
        "project_id": context_bundle.get("project_id", "unknown"),
        "context_bundle_id": context_bundle.get("bundle_id", "unknown"),
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "ready": ready,
        "overall_status": PASSED if ready else FAILED,
        "checks": checks,
    }


def write_production_memory_loop_run(run: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    return [
        write_json(output_root / "production_memory_loop_run.json", run),
        write_json(output_root / "context_bundle.json", run["context_bundle"]),
        write_json(output_root / "pass_readiness.json", run["pass_readiness"]),
        write_json(output_root / "next_pass_bundle.json", run["next_pass_bundle"]),
    ]


def _classify_ref(ref_id: str, indexes: dict[str, dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if ref_id in indexes["artifacts"]:
        artifact = indexes["artifacts"][ref_id]
        status = str(artifact.get("status", "unknown"))
        if artifact.get("eligible_for_next_context") is True and status in INCLUDABLE_ARTIFACT_STATUSES:
            return _included_artifact(ref_id, artifact), None
        reason = f"artifact_status_{status}" if status in BLOCKED_STATUSES else "artifact_not_eligible"
        return None, _blocked(ref_id, "artifact", reason, status)
    if ref_id in indexes["feedback"]:
        return None, _blocked(ref_id, "feedback_event", "feedback_is_not_memory", indexes["feedback"][ref_id].get("decision"))
    if ref_id in indexes["candidates"]:
        return _classify_memory_candidate(ref_id, indexes)
    if ref_id in indexes["decisions"]:
        return None, _blocked(ref_id, "promotion_decision", "promotion_decision_is_not_context", indexes["decisions"][ref_id].get("decision"))
    return None, _blocked(ref_id, "missing", "missing_reference", "missing")


def _classify_memory_candidate(ref_id: str, indexes: dict[str, dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    candidate = indexes["candidates"][ref_id]
    status = str(candidate.get("status", "candidate"))
    decision = indexes["decisions_by_candidate"].get(ref_id)
    if status in BLOCKED_STATUSES:
        return None, _blocked(ref_id, "memory_candidate", f"memory_candidate_{status}", status)
    if not decision:
        return None, _blocked(ref_id, "memory_candidate", "memory_candidate_without_promotion_decision", status)
    decision_status = str(decision.get("decision", "unknown"))
    if decision_status in PROMOTION_DECISIONS_ALLOWING_CONTEXT:
        return _included_memory(ref_id, candidate, decision), None
    return None, _blocked(ref_id, "memory_candidate", f"promotion_decision_{decision_status}", decision_status)


def _included_artifact(ref_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "ref_id": ref_id,
        "source_record_type": "artifact",
        "status": artifact.get("status", "unknown"),
        "title": artifact.get("title", ref_id),
        "summary": artifact.get("summary", ""),
    }


def _included_memory(ref_id: str, candidate: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "ref_id": ref_id,
        "source_record_type": "memory_candidate",
        "status": candidate.get("status", "candidate"),
        "decision_id": decision.get("decision_id"),
        "promotion_decision": decision.get("decision"),
        "source_feedback_ids": list(candidate.get("source_feedback_ids", [])),
        "summary": candidate.get("statement", ""),
    }


def _blocked(ref_id: str, source_type: str, reason: str, status: Any) -> dict[str, Any]:
    return {"ref_id": ref_id, "source_record_type": source_type, "reason": reason, "status": str(status)}


__all__ = (
    "CONTEXT_BUNDLE_KIND",
    "KIND",
    "NEXT_PASS_BUNDLE_KIND",
    "PASS_READINESS_KIND",
    "RUN_KIND",
    "SCHEMA_VERSION",
    "build_context_bundle",
    "build_pass_readiness",
    "build_production_memory_loop_run",
    "load_production_memory_loop",
    "validate_production_memory_loop",
    "write_production_memory_loop_run",
)
