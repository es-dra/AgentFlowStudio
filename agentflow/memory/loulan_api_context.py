from __future__ import annotations

from typing import Any


CONTEXT_PROJECTION_TYPE = "agentflow_loulan_context_bundle_projection"
READY_CONTEXT_STATUSES = frozenset({"ready", "partial_ready"})


def validate_context_projection(context_projection: dict[str, Any], *, schema_version: str) -> None:
    if context_projection.get("schema_version") != schema_version:
        raise ValueError("Loulan context projection schema_version must be 0.1.0")
    if context_projection.get("artifact_type") != CONTEXT_PROJECTION_TYPE:
        raise ValueError(f"Loulan context projection artifact_type must be {CONTEXT_PROJECTION_TYPE}")
    if context_projection.get("provider_calls_started") is not False:
        raise ValueError("Loulan context projection must not have provider calls started")
    if context_projection.get("writes_long_term_memory") is not False:
        raise ValueError("Loulan context projection must not write long-term memory")
    if context_projection.get("context_bundle", {}).get("writes_long_term_memory") is not False:
        raise ValueError("Loulan context bundle must not write long-term memory")
    _validate_decision_intake_gate(context_projection)


def context_reference_pack_entries(
    assets: list[dict[str, Any]],
    context_projection: dict[str, Any],
) -> list[dict[str, str]]:
    if not context_projection_ready(context_projection):
        return []
    assets_by_ref = {str(asset.get("memory_ref") or ""): asset for asset in assets}
    entries = []
    for memory_ref in sorted(context_projection.get("context_bundle", {}).get("memory_refs") or []):
        asset = assets_by_ref.get(str(memory_ref))
        sha = str((asset or {}).get("sha256") or "")
        if not asset or not sha:
            continue
        entries.append(
            {
                "memory_ref": str(memory_ref),
                "asset_id": str(asset.get("asset_id") or ""),
                "label": str(asset.get("label") or asset.get("asset_id") or memory_ref),
                "sha256": sha,
                "source_status": str(asset.get("status") or ""),
                "decision_source": str(context_projection.get("projection_id") or ""),
            }
        )
    return entries


def context_projection_summary(context_projection: dict[str, Any] | None) -> dict[str, Any]:
    if context_projection is None:
        return {"status": "not_provided", "projection_id": None}
    bundle = context_projection.get("context_bundle") or {}
    audit = context_projection.get("decision_audit") or {}
    return {
        "status": str(audit.get("status") or bundle.get("status") or ""),
        "context_bundle_status": str(bundle.get("status") or ""),
        "projection_id": context_projection_id(context_projection),
        "decision_intake_gate": decision_intake_gate_summary(context_projection),
        "memory_refs": list(bundle.get("memory_refs") or []),
        "shot_anchor_refs": list(bundle.get("shot_anchor_refs") or []),
        "blocked_refs": list(bundle.get("blocked_refs") or []),
    }


def context_projection_id(context_projection: dict[str, Any] | None) -> str | None:
    if context_projection is None:
        return None
    return str(context_projection.get("projection_id") or "")


def context_projection_ready(context_projection: dict[str, Any]) -> bool:
    status = str(context_projection.get("context_bundle", {}).get("status") or "")
    return status in READY_CONTEXT_STATUSES


def decision_intake_gate_summary(context_projection: dict[str, Any] | None) -> dict[str, Any]:
    gate = (context_projection or {}).get("decision_intake_gate") or {}
    return {
        "status": str(gate.get("status") or "not_recorded"),
        "context_bundle_command_ready": gate.get("context_bundle_command_ready") is True,
        "intake_report_id": str(gate.get("intake_report_id") or ""),
    }


def _validate_decision_intake_gate(context_projection: dict[str, Any]) -> None:
    if "decision_intake_gate" not in context_projection:
        return
    gate = decision_intake_gate_summary(context_projection)
    if gate["status"] == "not_supplied":
        return
    if gate["status"] == "ready_for_context_bundle" and gate["context_bundle_command_ready"] is True:
        return
    raise ValueError("Loulan context projection decision intake gate must be ready or not_supplied")


def context_blocking_reasons(
    references: list[dict[str, str]],
    context_projection: dict[str, Any] | None,
) -> list[str]:
    if references:
        return []
    if context_projection is not None and not context_projection_ready(context_projection):
        return ["context_projection_not_ready"]
    return ["no_approved_reference_hashes"]
