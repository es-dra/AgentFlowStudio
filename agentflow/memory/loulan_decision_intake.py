from __future__ import annotations

from pathlib import Path
from typing import Any

from narratocut.utils import write_json

from agentflow.memory.loulan_context_bundle import (
    ASSET_BLOCK_DECISIONS,
    ASSET_REUSE_DECISIONS,
    DECISIONS_TYPE,
    SHOT_BLOCK_DECISIONS,
    SHOT_REUSE_DECISIONS,
)
from agentflow.memory.loulan_human_review_support import SCHEMA_VERSION, reject_unsafe_output
from agentflow.memory.loulan_decision_worksheet import DECISION_WORKSHEET_TYPE


DECISION_INTAKE_REPORT_TYPE = "agentflow_loulan_decision_intake_report"


def build_loulan_decision_intake_report(
    worksheet: dict[str, Any],
    decisions: dict[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    """Validate manually filled Loulan decisions before context projection."""
    _validate_worksheet(worksheet)
    _validate_decisions(decisions, worksheet)
    rows = _decision_rows(worksheet, decisions)
    summary = _summary(rows, decisions, worksheet)
    status = _intake_status(summary)
    report = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": DECISION_INTAKE_REPORT_TYPE,
        "intake_report_id": f"{worksheet['worksheet_id']}_intake_report_v0",
        "worksheet_id": worksheet["worksheet_id"],
        "decision_review_pack_id": worksheet["decision_review_pack_id"],
        "review_pack_id": worksheet["review_pack_id"],
        "created_at": created_at,
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "human_acceptance_recorded": False,
        "intake_status": status,
        "context_bundle_command_ready": status == "ready_for_context_bundle",
        "intake_summary": summary,
        "unexpected_decision_refs": _unexpected_refs(worksheet, decisions),
        "decision_rows": rows,
        "next_action": _next_action(status),
        "claim_boundaries": _claim_boundaries(),
    }
    reject_unsafe_output(report)
    return report


def write_loulan_decision_intake_report(report: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "loulan_decision_intake_report.json", report)
    report_path = output_root / "loulan_decision_intake_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_loulan_decision_intake_report(report), encoding="utf-8")
    return [json_path, report_path]


def render_loulan_decision_intake_report(report: dict[str, Any]) -> str:
    summary = report["intake_summary"]
    lines = [
        "# Loulan Decision Intake Report",
        "",
        f"- Worksheet: `{report['worksheet_id']}`",
        f"- Status: `{report['intake_status']}`",
        f"- Ready: {summary['ready_count']}",
        f"- Pending: {summary['pending_count']}",
        f"- Missing: {summary['missing_count']}",
        f"- Invalid: {summary['invalid_count']}",
        f"- Unexpected: {summary['unexpected_count']}",
        "- Human acceptance: not recorded",
        "- Provider calls: not started",
        "- Durable Memory runtime: not implemented",
        "",
        "## Decision Rows",
        "",
    ]
    for row in report["decision_rows"]:
        lines.append(f"- `{row['target_ref']}`: `{row['intake_status']}`; reason={row['reason']}")
    lines.append("")
    return "\n".join(lines)


def _validate_worksheet(worksheet: dict[str, Any]) -> None:
    if worksheet.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Loulan decision intake requires worksheet schema_version 0.1.0")
    if worksheet.get("artifact_type") != DECISION_WORKSHEET_TYPE:
        raise ValueError(f"Loulan decision intake requires worksheet artifact_type {DECISION_WORKSHEET_TYPE}")
    if worksheet.get("provider_calls_started") is not False:
        raise ValueError("decision worksheet must not have provider calls started")
    if worksheet.get("writes_long_term_memory") is not False:
        raise ValueError("decision worksheet must not write long-term memory")
    if worksheet.get("human_acceptance_recorded") is not False:
        raise ValueError("decision worksheet must not record human acceptance")
    if not worksheet.get("worksheet_id"):
        raise ValueError("decision worksheet missing worksheet_id")
    if not worksheet.get("review_pack_id"):
        raise ValueError("decision worksheet missing review_pack_id")


def _validate_decisions(decisions: dict[str, Any], worksheet: dict[str, Any]) -> None:
    if decisions.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Loulan decision intake requires decisions schema_version 0.1.0")
    if decisions.get("artifact_type") != DECISIONS_TYPE:
        raise ValueError(f"Loulan decision intake requires decisions artifact_type {DECISIONS_TYPE}")
    if decisions.get("review_pack_id") != worksheet.get("review_pack_id"):
        raise ValueError("Loulan decisions review_pack_id must match worksheet")
    if decisions.get("provider_calls_started") is True:
        raise ValueError("Loulan decisions must not have provider calls started")
    if decisions.get("writes_long_term_memory") is not False:
        raise ValueError("Loulan decisions must not write long-term memory")
    if decisions.get("human_acceptance_recorded") is True:
        raise ValueError("Loulan decisions must not record human acceptance")


def _decision_rows(worksheet: dict[str, Any], decisions: dict[str, Any]) -> list[dict[str, Any]]:
    by_ref = {str(item.get("target_ref")): item for item in decisions.get("decisions") or []}
    return [_decision_row(row, by_ref.get(str(row.get("target_ref")))) for row in worksheet.get("decision_rows") or []]


def _decision_row(worksheet_row: dict[str, Any], decision: dict[str, Any] | None) -> dict[str, Any]:
    target_ref = str(worksheet_row.get("target_ref") or "")
    allowed = list(worksheet_row.get("allowed_decisions") or [])
    reason = _invalid_reason(target_ref, allowed, decision)
    status = "ready_for_context_bundle" if not reason else _row_status(reason)
    value = str((decision or {}).get("decision") or "")
    return {
        "decision_id": str((decision or {}).get("decision_id") or worksheet_row.get("decision_id") or ""),
        "target_ref": target_ref,
        "target_type": str(worksheet_row.get("target_type") or "unknown"),
        "decision": value,
        "allowed_decisions": allowed,
        "decided_by": str((decision or {}).get("decided_by") or ""),
        "evidence_refs": list((decision or {}).get("evidence_refs") or []),
        "review_note_present": bool((decision or {}).get("review_note")),
        "intake_status": status,
        "reason": reason or "ready",
        "reusable_for_context": _is_reusable(target_ref, value) if not reason else False,
        "blocked_for_context": _is_blocked(target_ref, value) if not reason else False,
    }


def _invalid_reason(target_ref: str, allowed: list[str], decision: dict[str, Any] | None) -> str:
    if decision is None:
        return "missing_decision"
    value = str(decision.get("decision") or "")
    if value in {"", "pending_human_review"}:
        return "pending_manual_decision"
    if value not in allowed:
        return "invalid_decision_value"
    if decision.get("decided_by") != "human":
        return "decision_not_human"
    if not decision.get("evidence_refs"):
        return "missing_evidence_refs"
    if not decision.get("review_note"):
        return "missing_review_note"
    if target_ref.startswith("shot:") and value not in SHOT_REUSE_DECISIONS | SHOT_BLOCK_DECISIONS:
        return "invalid_shot_decision"
    if _is_asset_target(target_ref) and value not in ASSET_REUSE_DECISIONS | ASSET_BLOCK_DECISIONS:
        return "invalid_asset_decision"
    return ""


def _row_status(reason: str) -> str:
    if reason in {"missing_decision", "pending_manual_decision"}:
        return "pending_manual_decision"
    return "invalid_decision"


def _summary(rows: list[dict[str, Any]], decisions: dict[str, Any], worksheet: dict[str, Any]) -> dict[str, int]:
    return {
        "required_decisions": len(worksheet.get("decision_rows") or []),
        "submitted_decisions": len(decisions.get("decisions") or []),
        "ready_count": _count_status(rows, "ready_for_context_bundle"),
        "pending_count": _count_status(rows, "pending_manual_decision"),
        "missing_count": sum(1 for row in rows if row["reason"] == "missing_decision"),
        "invalid_count": _count_status(rows, "invalid_decision"),
        "unexpected_count": len(_unexpected_refs(worksheet, decisions)),
        "reusable_count": sum(1 for row in rows if row["reusable_for_context"]),
        "blocked_count": sum(1 for row in rows if row["blocked_for_context"]),
    }


def _intake_status(summary: dict[str, int]) -> str:
    if summary["missing_count"]:
        return "blocked_missing_decisions"
    if summary["invalid_count"] or summary["unexpected_count"]:
        return "blocked_invalid_decisions"
    if summary["pending_count"]:
        return "blocked_pending_manual_decisions"
    return "ready_for_context_bundle" if summary["ready_count"] else "blocked_no_decisions"


def _count_status(rows: list[dict[str, Any]], status: str) -> int:
    return sum(1 for row in rows if row["intake_status"] == status)


def _unexpected_refs(worksheet: dict[str, Any], decisions: dict[str, Any]) -> list[str]:
    expected = {str(row.get("target_ref")) for row in worksheet.get("decision_rows") or []}
    submitted = {str(item.get("target_ref")) for item in decisions.get("decisions") or []}
    return sorted(ref for ref in submitted - expected if ref)


def _next_action(status: str) -> str:
    if status == "ready_for_context_bundle":
        return "run_loulan_context_bundle_with_validated_decisions"
    return "fix_manual_decisions_before_context_bundle"


def _is_reusable(target_ref: str, decision: str) -> bool:
    return (target_ref.startswith("shot:") and decision in SHOT_REUSE_DECISIONS) or (
        _is_asset_target(target_ref) and decision in ASSET_REUSE_DECISIONS
    )


def _is_blocked(target_ref: str, decision: str) -> bool:
    return (target_ref.startswith("shot:") and decision in SHOT_BLOCK_DECISIONS) or (
        _is_asset_target(target_ref) and decision in ASSET_BLOCK_DECISIONS
    )


def _is_asset_target(target_ref: str) -> bool:
    return target_ref.startswith(("character:", "asset:"))


def _claim_boundaries() -> dict[str, str]:
    return {
        "structure_verification": "decision_intake_report_only",
        "runtime_verification": "not_run",
        "provider_smoke": "not_run",
        "human_acceptance": "decision_file_validated_not_product_acceptance",
        "business_validation": "not_validated",
        "durable_memory_runtime": "not_implemented",
    }
