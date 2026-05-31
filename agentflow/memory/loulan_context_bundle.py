from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narratocut.utils import write_json

from agentflow.memory.loulan_human_review_support import SCHEMA_VERSION, reject_unsafe_output


PROJECTION_TYPE = "agentflow_loulan_context_bundle_projection"
REVIEW_PACK_TYPE = "agentflow_loulan_human_review_pack"
DECISIONS_TYPE = "agentflow_loulan_promotion_decisions"
DECISION_INTAKE_REPORT_TYPE = "agentflow_loulan_decision_intake_report"
ASSET_REUSE_DECISIONS = frozenset({"promoted", "merged"})
ASSET_BLOCK_DECISIONS = frozenset({"rejected", "expired"})
SHOT_REUSE_DECISIONS = frozenset({"approve_anchor"})
SHOT_BLOCK_DECISIONS = frozenset({"reject", "request_repair"})


def build_loulan_context_bundle_projection(
    review_pack: dict[str, Any],
    decisions: dict[str, Any],
    *,
    created_at: str,
    decision_intake_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project explicit human decisions into a no-call next context bundle."""
    _validate_review_pack(review_pack)
    _validate_decisions(decisions, review_pack)
    intake_gate = _decision_intake_gate(review_pack, decisions, decision_intake_report)
    audit = _decision_audit(review_pack, decisions)
    bundle = _context_bundle(review_pack, decisions, audit, created_at)
    projection = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": PROJECTION_TYPE,
        "projection_id": f"{review_pack['review_pack_id']}_context_projection_v0",
        "created_at": created_at,
        "review_pack_id": review_pack["review_pack_id"],
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "decision_intake_gate": intake_gate,
        "decision_audit": audit,
        "context_bundle": bundle,
        "next_prompt_draft": _next_prompt_draft(bundle, audit, created_at),
        "claim_boundaries": _claim_boundaries(),
    }
    reject_unsafe_output(projection)
    return projection


def write_loulan_context_bundle_projection(projection: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    paths = [
        write_json(output_root / "loulan_context_bundle_projection.json", projection),
        write_json(output_root / "context_bundle.json", projection["context_bundle"]),
        write_json(output_root / "next_prompt_draft.json", projection["next_prompt_draft"]),
        write_json(output_root / "decision_audit.json", projection["decision_audit"]),
    ]
    report_path = output_root / "loulan_context_bundle_projection.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_loulan_context_bundle_projection_report(projection), encoding="utf-8")
    paths.append(report_path)
    return paths


def render_loulan_context_bundle_projection_report(projection: dict[str, Any]) -> str:
    audit = projection["decision_audit"]
    bundle = projection["context_bundle"]
    return "\n".join(
        [
            "# Loulan Context Bundle Projection",
            "",
            f"- Projection: `{projection['projection_id']}`",
            f"- Decision audit: `{audit['status']}`",
            f"- Context bundle: `{bundle['status']}`",
            f"- Memory refs: {len(bundle['memory_refs'])}",
            f"- Shot anchors: {len(bundle['shot_anchor_refs'])}",
            "- Provider calls: not started",
            "- Durable Memory runtime: not implemented",
            "",
        ]
    )


def _validate_review_pack(review_pack: dict[str, Any]) -> None:
    if review_pack.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Loulan context bundle requires review pack schema_version 0.1.0")
    if review_pack.get("artifact_type") != REVIEW_PACK_TYPE:
        raise ValueError(f"Loulan context bundle requires review pack artifact_type {REVIEW_PACK_TYPE}")
    if review_pack.get("provider_calls_started") is not False:
        raise ValueError("review pack must not have provider calls started")
    if review_pack.get("writes_long_term_memory") is not False:
        raise ValueError("review pack must not write long-term memory")
    if review_pack.get("human_acceptance_recorded") is not False:
        raise ValueError("review pack must not record human acceptance")


def _validate_decisions(decisions: dict[str, Any], review_pack: dict[str, Any]) -> None:
    if decisions.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Loulan decisions require schema_version 0.1.0")
    if decisions.get("artifact_type") != DECISIONS_TYPE:
        raise ValueError(f"Loulan decisions artifact_type must be {DECISIONS_TYPE}")
    if decisions.get("review_pack_id") != review_pack.get("review_pack_id"):
        raise ValueError("Loulan decisions review_pack_id must match review pack")
    if decisions.get("writes_long_term_memory") is not False:
        raise ValueError("Loulan decisions must not write long-term memory")


def _decision_intake_gate(
    review_pack: dict[str, Any],
    decisions: dict[str, Any],
    report: dict[str, Any] | None,
) -> dict[str, Any]:
    if report is None:
        return {
            "status": "not_supplied",
            "intake_report_id": "",
            "context_bundle_command_ready": False,
        }
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("decision intake report must use schema_version 0.1.0")
    if report.get("artifact_type") != DECISION_INTAKE_REPORT_TYPE:
        raise ValueError(f"decision intake report artifact_type must be {DECISION_INTAKE_REPORT_TYPE}")
    if report.get("review_pack_id") != review_pack.get("review_pack_id"):
        raise ValueError("decision intake report review_pack_id must match review pack")
    if report.get("provider_calls_started") is not False:
        raise ValueError("decision intake report must not have provider calls started")
    if report.get("writes_long_term_memory") is not False:
        raise ValueError("decision intake report must not write long-term memory")
    if report.get("human_acceptance_recorded") is not False:
        raise ValueError("decision intake report must not record human acceptance")
    if report.get("intake_status") != "ready_for_context_bundle" or report.get("context_bundle_command_ready") is not True:
        raise ValueError("decision intake report must be ready_for_context_bundle")
    if _decision_signature_from_report(report) != _decision_signature_from_decisions(decisions):
        raise ValueError("decision intake report must match decisions")
    return {
        "status": "ready_for_context_bundle",
        "intake_report_id": str(report.get("intake_report_id") or ""),
        "context_bundle_command_ready": True,
    }


def _decision_signature_from_report(report: dict[str, Any]) -> list[tuple[str, str, str, str, tuple[str, ...]]]:
    return sorted(_decision_signature(row) for row in report.get("decision_rows") or [])


def _decision_signature_from_decisions(decisions: dict[str, Any]) -> list[tuple[str, str, str, str, tuple[str, ...]]]:
    return sorted(_decision_signature(item) for item in decisions.get("decisions") or [])


def _decision_signature(item: dict[str, Any]) -> tuple[str, str, str, str, tuple[str, ...]]:
    return (
        str(item.get("decision_id") or ""),
        str(item.get("target_ref") or ""),
        str(item.get("decision") or ""),
        str(item.get("decided_by") or ""),
        tuple(str(ref) for ref in item.get("evidence_refs") or []),
    )


def _decision_audit(review_pack: dict[str, Any], decisions: dict[str, Any]) -> dict[str, Any]:
    required = list(review_pack.get("next_pass_readiness", {}).get("required_decisions") or [])
    by_ref = {str(item.get("target_ref")): item for item in decisions.get("decisions") or []}
    missing = [ref for ref in required if ref not in by_ref]
    invalid = [_invalid_decision(item) for item in by_ref.values()]
    invalid = [item for item in invalid if item]
    reusable = _reusable_refs(by_ref)
    blocked = _blocked_refs(by_ref)
    status = _audit_status(missing, invalid, reusable, blocked)
    return {
        "status": status,
        "required_decision_refs": required,
        "missing_decision_refs": missing,
        "invalid_decisions": invalid,
        "accepted_decision_ids": [str(item.get("decision_id")) for item in by_ref.values() if item.get("target_ref") in reusable],
        "blocked_refs": blocked,
        "writes_long_term_memory": False,
    }


def _audit_status(missing: list[str], invalid: list[dict[str, str]], reusable: list[str], blocked: list[str]) -> str:
    if missing:
        return "blocked_missing_decisions"
    if invalid:
        return "blocked_invalid_decisions"
    if blocked and reusable:
        return "partial_ready"
    return "ready" if reusable else "blocked_no_reusable_context"


def _invalid_decision(item: dict[str, Any]) -> dict[str, str] | None:
    target = str(item.get("target_ref") or "")
    decision = str(item.get("decision") or "")
    decided_by = str(item.get("decided_by") or "")
    if decided_by != "human":
        return {"target_ref": target, "reason": "decision_not_human"}
    if target.startswith("shot:") and decision not in SHOT_REUSE_DECISIONS | SHOT_BLOCK_DECISIONS:
        return {"target_ref": target, "reason": "invalid_shot_decision"}
    if _is_asset_target(target) and decision not in ASSET_REUSE_DECISIONS | ASSET_BLOCK_DECISIONS:
        return {"target_ref": target, "reason": "invalid_asset_decision"}
    if not item.get("evidence_refs"):
        return {"target_ref": target, "reason": "missing_evidence_refs"}
    return None


def _reusable_refs(by_ref: dict[str, dict[str, Any]]) -> list[str]:
    refs = []
    for target, item in by_ref.items():
        decision = str(item.get("decision") or "")
        if _is_asset_target(target) and decision in ASSET_REUSE_DECISIONS:
            refs.append(target)
        if target.startswith("shot:") and decision in SHOT_REUSE_DECISIONS:
            refs.append(target)
    return sorted(refs)


def _blocked_refs(by_ref: dict[str, dict[str, Any]]) -> list[str]:
    refs = []
    for target, item in by_ref.items():
        decision = str(item.get("decision") or "")
        if _is_asset_target(target) and decision in ASSET_BLOCK_DECISIONS:
            refs.append(target)
        if target.startswith("shot:") and decision in SHOT_BLOCK_DECISIONS:
            refs.append(target)
    return sorted(refs)


def _context_bundle(
    review_pack: dict[str, Any],
    decisions: dict[str, Any],
    audit: dict[str, Any],
    created_at: str,
) -> dict[str, Any]:
    reusable = _reusable_refs({str(item.get("target_ref")): item for item in decisions.get("decisions") or []})
    return {
        "bundle_id": f"{review_pack['review_pack_id']}_context_bundle_v0",
        "status": "blocked" if audit["status"].startswith("blocked") else audit["status"],
        "created_at": created_at,
        "source_review_pack_id": review_pack["review_pack_id"],
        "source_decision_ids": [str(item.get("decision_id")) for item in decisions.get("decisions") or []],
        "memory_refs": [ref for ref in reusable if _is_asset_target(ref)],
        "shot_anchor_refs": [ref for ref in reusable if ref.startswith("shot:")],
        "blocked_refs": audit["blocked_refs"],
        "writes_long_term_memory": False,
    }


def _next_prompt_draft(bundle: dict[str, Any], audit: dict[str, Any], created_at: str) -> dict[str, Any]:
    return {
        "prompt_id": f"{bundle['bundle_id']}_next_prompt_draft",
        "status": audit["status"],
        "created_at": created_at,
        "context_bundle_ref": bundle["bundle_id"],
        "memory_refs": bundle["memory_refs"],
        "shot_anchor_refs": bundle["shot_anchor_refs"],
        "blocked_refs": bundle["blocked_refs"],
        "writes_long_term_memory": False,
    }


def _claim_boundaries() -> dict[str, str]:
    return {
        "structure_verification": "context_bundle_projection_only",
        "runtime_verification": "not_run",
        "provider_smoke": "not_run",
        "human_acceptance": "decision_records_only_not_product_acceptance",
        "business_validation": "not_validated",
        "durable_memory_runtime": "not_implemented",
    }


def _is_asset_target(target_ref: str) -> bool:
    return target_ref.startswith(("character:", "asset:"))
