from __future__ import annotations

from typing import Any

NEXT_PASS_BUNDLE_KIND = "agentflow_production_memory_next_pass_bundle"


def build_next_pass_bundle(
    payload: dict[str, Any],
    context_bundle: dict[str, Any],
    pass_readiness: dict[str, Any],
) -> dict[str, Any]:
    """Build a no-provider next-pass planning artifact from included context refs."""
    requested = _dict(payload.get("next_pass_request"))
    included_refs = list(context_bundle.get("included_refs", []))
    blocked_refs = list(context_bundle.get("blocked_refs", []))
    ready = pass_readiness.get("ready") is True
    return {
        "kind": NEXT_PASS_BUNDLE_KIND,
        "artifact_type": NEXT_PASS_BUNDLE_KIND,
        "schema_version": context_bundle.get("schema_version", "production-memory-loop/v1"),
        "task_id": requested.get("task_id", "next-pass:unassigned"),
        "project_id": context_bundle.get("project_id", "unknown"),
        "context_bundle_id": context_bundle.get("bundle_id", "unknown"),
        "provider_mode": "no-provider",
        "execution_status": "planned" if ready else "blocked",
        "does_not_execute": True,
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "context_refs": included_refs,
        "blocked_ref_count": len(blocked_refs),
        "readiness_status": pass_readiness.get("overall_status", "failed"),
        "operator_instruction": _operator_instruction(payload, included_refs, blocked_refs, ready),
        "claim_boundaries": {
            "human_acceptance": "not_reviewed",
            "business_validation": "not_validated",
            "provider_success": "not_attempted",
            "durable_memory_runtime": "not_implemented",
        },
    }


def _operator_instruction(
    payload: dict[str, Any],
    included_refs: list[dict[str, Any]],
    blocked_refs: list[dict[str, Any]],
    ready: bool,
) -> str:
    goal = _dict(payload.get("project_input")).get("operator_goal", "Prepare the next production pass.")
    if not ready:
        return f"Resolve blocked production-memory refs before the next pass. Goal: {goal}"
    return (
        f"Prepare the next production pass using only {len(included_refs)} included context refs; "
        f"do not use {len(blocked_refs)} blocked refs. Goal: {goal}"
    )


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


__all__ = ("NEXT_PASS_BUNDLE_KIND", "build_next_pass_bundle")
