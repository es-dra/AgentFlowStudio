from __future__ import annotations

from pathlib import Path
from typing import Any

from narratocut.utils import write_json

from agentflow.memory.loulan_context_bundle import DECISIONS_TYPE
from agentflow.memory.loulan_human_review_support import SCHEMA_VERSION, reject_unsafe_output


DECISION_REVIEW_PACK_TYPE = "agentflow_loulan_decision_review_pack"
DECISION_WORKSHEET_TYPE = "agentflow_loulan_decision_worksheet"


def build_loulan_decision_worksheet(
    decision_review_pack: dict[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    """Build a copy-only manual worksheet from a Loulan decision review pack."""
    _validate_decision_review_pack(decision_review_pack)
    rows = [_decision_row(card) for card in decision_review_pack.get("decision_cards") or []]
    worksheet = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": DECISION_WORKSHEET_TYPE,
        "decision_review_pack_id": decision_review_pack["decision_review_pack_id"],
        "review_pack_id": decision_review_pack["review_pack_id"],
        "worksheet_id": f"{decision_review_pack['decision_review_pack_id']}_worksheet_v0",
        "created_at": created_at,
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "human_acceptance_recorded": False,
        "worksheet_status": _worksheet_status(rows),
        "decision_summary": dict(decision_review_pack["decision_summary"]),
        "worksheet_groups": _worksheet_groups(rows),
        "decision_rows": rows,
        "manual_transfer_template": _manual_transfer_template(decision_review_pack, rows, created_at),
        "next_action": "copy_fill_decisions_then_run_loulan_context_bundle",
        "claim_boundaries": _claim_boundaries(),
    }
    reject_unsafe_output(worksheet)
    return worksheet


def write_loulan_decision_worksheet(worksheet: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "loulan_decision_worksheet.json", worksheet)
    report_path = output_root / "loulan_decision_worksheet.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_loulan_decision_worksheet_report(worksheet), encoding="utf-8")
    return [json_path, report_path]


def render_loulan_decision_worksheet_report(worksheet: dict[str, Any]) -> str:
    lines = [
        "# Loulan Decision Worksheet",
        "",
        f"- Decision review pack: `{worksheet['decision_review_pack_id']}`",
        f"- Status: `{worksheet['worksheet_status']}`",
        f"- Rows: {len(worksheet['decision_rows'])}",
        "- Human acceptance: not recorded",
        "- Provider calls: not started",
        "- Durable Memory runtime: not implemented",
        "",
        "## Manual Fill Rows",
        "",
    ]
    for row in worksheet["decision_rows"]:
        allowed = ", ".join(row["allowed_decisions"])
        lines.append(f"- `{row['target_ref']}`: `{row['status']}`; fill one of: {allowed}")
    lines.append("")
    return "\n".join(lines)


def _validate_decision_review_pack(decision_review_pack: dict[str, Any]) -> None:
    if decision_review_pack.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Loulan decision worksheet requires decision review pack schema_version 0.1.0")
    if decision_review_pack.get("artifact_type") != DECISION_REVIEW_PACK_TYPE:
        raise ValueError(
            f"Loulan decision worksheet requires artifact_type {DECISION_REVIEW_PACK_TYPE}"
        )
    if decision_review_pack.get("provider_calls_started") is not False:
        raise ValueError("decision review pack must not have provider calls started")
    if decision_review_pack.get("writes_long_term_memory") is not False:
        raise ValueError("decision review pack must not write long-term memory")
    if decision_review_pack.get("human_acceptance_recorded") is not False:
        raise ValueError("decision review pack must not record human acceptance")
    if not decision_review_pack.get("decision_review_pack_id"):
        raise ValueError("decision review pack missing decision_review_pack_id")
    if not decision_review_pack.get("review_pack_id"):
        raise ValueError("decision review pack missing review_pack_id")


def _decision_row(card: dict[str, Any]) -> dict[str, Any]:
    suggested = list(card.get("suggested_evidence_refs") or [])
    allowed = list(card.get("allowed_decisions") or [])
    decision_id = str(card.get("decision_id") or _fallback_decision_id(card))
    return {
        "decision_id": decision_id,
        "target_ref": str(card.get("target_ref") or ""),
        "target_type": str(card.get("target_type") or "unknown"),
        "status": str(card.get("status") or ""),
        "current_decision": str(card.get("current_decision") or ""),
        "allowed_decisions": allowed,
        "suggested_evidence_refs": suggested,
        "required_fields": list(card.get("required_fields") or []),
        "manual_fill_required": card.get("status") != "ready_for_context_projection",
        "decision_to_fill": "",
        "decided_by_to_fill": "",
        "evidence_refs_to_fill": [],
        "review_note_to_fill": "",
        "copy_target_json": {
            "decision_id": decision_id,
            "target_ref": str(card.get("target_ref") or ""),
            "decision": "",
            "allowed_decisions": allowed,
            "decided_by": "",
            "evidence_refs": [],
            "suggested_evidence_refs": suggested,
            "review_note": "",
        },
    }


def _fallback_decision_id(card: dict[str, Any]) -> str:
    return str(card.get("target_ref") or "unknown_target").replace(":", "_").lower() + "_decision"


def _worksheet_status(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "blocked_no_decisions"
    blocking_statuses = {"needs_human_input", "missing_decision_slot", "invalid_decision"}
    if any(row["status"] in blocking_statuses for row in rows):
        return "awaiting_manual_decisions"
    return "ready_for_manual_transfer"


def _worksheet_groups(rows: list[dict[str, Any]]) -> list[dict[str, int | str]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["target_type"], []).append(row)
    return [
        {
            "target_type": target_type,
            "count": len(items),
            "pending_count": _count_status(items, "needs_human_input"),
            "missing_count": _count_status(items, "missing_decision_slot"),
            "invalid_count": _count_status(items, "invalid_decision"),
            "ready_count": _count_status(items, "ready_for_context_projection"),
        }
        for target_type, items in sorted(grouped.items())
    ]


def _count_status(rows: list[dict[str, Any]], status: str) -> int:
    return sum(1 for row in rows if row["status"] == status)


def _manual_transfer_template(
    decision_review_pack: dict[str, Any],
    rows: list[dict[str, Any]],
    created_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": DECISIONS_TYPE,
        "review_pack_id": decision_review_pack["review_pack_id"],
        "created_at": created_at,
        "template_status": "pending_human_input",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "human_acceptance_recorded": False,
        "instructions": "Copy rows, then fill decision, decided_by=human, evidence_refs, and review_note.",
        "decisions": [dict(row["copy_target_json"]) for row in rows],
    }


def _claim_boundaries() -> dict[str, str]:
    return {
        "structure_verification": "decision_worksheet_only",
        "runtime_verification": "not_run",
        "provider_smoke": "not_run",
        "human_acceptance": "not_recorded",
        "business_validation": "not_validated",
        "durable_memory_runtime": "not_implemented",
    }
