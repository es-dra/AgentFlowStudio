from __future__ import annotations

from pathlib import Path
from typing import Any

from narratocut.utils import write_json

from agentflow.memory.loulan_decision_template import build_loulan_decision_template
from agentflow.memory.loulan_human_review_support import SCHEMA_VERSION, reject_unsafe_output, safe_ref


LOCAL_B01_DECISION_TYPE = "loulan_b01_human_review_decision_template"
PENDING_DECISION = "pending_human_review"
READY_DECISIONS = {"approve_anchor", "request_repair", "reject"}


def build_loulan_b01_decision_import(
    review_pack: dict[str, Any],
    local_b01_decisions: dict[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    """Overlay explicit local B01 decisions onto an AFS promotion decision file."""
    _validate_local_b01_decisions(local_b01_decisions)
    imported = build_loulan_decision_template(review_pack, created_at=created_at)
    by_ref = {str(item.get("target_ref") or ""): item for item in imported["decisions"]}
    imported_ready = 0
    skipped = 0
    for local_item in local_b01_decisions.get("decision_items") or []:
        target_ref = _target_ref(local_item)
        target = by_ref.get(target_ref)
        if target is None:
            skipped += 1
            continue
        if _overlay_local_decision(target, local_item):
            imported_ready += 1
    pending = sum(1 for item in imported["decisions"] if item.get("decision") == PENDING_DECISION)
    imported["template_status"] = (
        "ready_for_decision_intake" if pending == 0 else "partially_imported_pending_human_input"
    )
    imported["source_decision_artifact_type"] = LOCAL_B01_DECISION_TYPE
    imported["source_block_id"] = local_b01_decisions.get("block_id", "")
    imported["import_summary"] = {
        "required_decisions": len(imported["decisions"]),
        "imported_ready_decisions": imported_ready,
        "pending_decisions": pending,
        "skipped_local_items": skipped,
    }
    imported["instructions"] = "B01 shot decisions were imported from an explicit local file; fill remaining pending decisions before context projection."
    imported["claim_boundaries"] = {
        "provider_calls": "not_started",
        "media_generation": "not_run",
        "media_copy": "not_run",
        "human_acceptance": "not_recorded",
        "durable_memory_runtime": "not_implemented",
    }
    reject_unsafe_output(imported)
    return imported


def write_loulan_b01_decision_import(imported: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "loulan_b01_decisions.imported.json", imported)
    report_path = output_root / "loulan_b01_decisions.imported.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_loulan_b01_decision_import_report(imported), encoding="utf-8")
    return [json_path, report_path]


def render_loulan_b01_decision_import_report(imported: dict[str, Any]) -> str:
    summary = imported.get("import_summary") or {}
    return "\n".join(
        [
            "# Loulan B01 Decision Import",
            "",
            f"- Review pack: `{imported['review_pack_id']}`",
            f"- Status: `{imported['template_status']}`",
            f"- Imported ready decisions: {summary.get('imported_ready_decisions', 0)}",
            f"- Pending decisions: {summary.get('pending_decisions', 0)}",
            f"- Skipped local items: {summary.get('skipped_local_items', 0)}",
            "- Human acceptance: not recorded",
            "- Provider calls: not started",
            "- Durable Memory runtime: not implemented",
            "",
        ]
    )


def _validate_local_b01_decisions(local_b01_decisions: dict[str, Any]) -> None:
    if local_b01_decisions.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Loulan B01 decision import requires local schema_version 0.1.0")
    if local_b01_decisions.get("artifact_type") != LOCAL_B01_DECISION_TYPE:
        raise ValueError(f"Loulan B01 decision import requires artifact_type {LOCAL_B01_DECISION_TYPE}")
    if local_b01_decisions.get("block_id") != "B01":
        raise ValueError("Loulan B01 decision import requires block_id B01")
    if local_b01_decisions.get("provider_calls_started") is not False:
        raise ValueError("local B01 decisions must not have provider calls started")
    if local_b01_decisions.get("writes_long_term_memory") is not False:
        raise ValueError("local B01 decisions must not write long-term memory")
    if local_b01_decisions.get("human_acceptance_recorded") is not False:
        raise ValueError("local B01 decisions must not record product acceptance")


def _overlay_local_decision(target: dict[str, Any], local_item: dict[str, Any]) -> bool:
    decision = str(local_item.get("decision") or "")
    if decision in {"", PENDING_DECISION}:
        return False
    if decision not in READY_DECISIONS:
        raise ValueError(f"local B01 decision {decision} is not supported for B01 import")
    allowed = set(target.get("allowed_decisions") or [])
    if decision not in allowed:
        raise ValueError(f"local B01 decision {decision} is not allowed for {target['target_ref']}")
    review_note = str(local_item.get("repair_note") or "").strip()
    if decision == "request_repair" and not review_note:
        raise ValueError(f"request_repair requires repair_note for {target['target_ref']}")
    evidence_refs = _evidence_refs(local_item)
    if not evidence_refs:
        raise ValueError(f"local B01 decision requires evidence refs for {target['target_ref']}")
    target["decision"] = decision
    target["decided_by"] = "human"
    target["evidence_refs"] = evidence_refs
    target["review_note"] = review_note or f"Imported explicit B01 human decision: {decision}."
    return True


def _target_ref(local_item: dict[str, Any]) -> str:
    shot_id = str(local_item.get("target_shot_id") or "")
    return f"shot:{shot_id}" if shot_id else ""


def _evidence_refs(local_item: dict[str, Any]) -> list[str]:
    refs = []
    for key in ("candidate_ref", "registry_memory_ref"):
        ref = safe_ref(local_item.get(key))
        if ref:
            refs.append(ref)
    return refs
