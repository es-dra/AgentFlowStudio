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


REVIEW_PACK_TYPE = "agentflow_loulan_human_review_pack"
DECISION_REVIEW_PACK_TYPE = "agentflow_loulan_decision_review_pack"
REQUIRED_FIELDS = ["decision", "decided_by", "evidence_refs", "review_note"]


def build_loulan_decision_review_pack(
    review_pack: dict[str, Any],
    decisions: dict[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    """Build a no-call operator review pack for Loulan human decisions."""
    _validate_review_pack(review_pack)
    _validate_decisions(decisions, review_pack)
    cards = _decision_cards(review_pack, decisions)
    summary = _decision_summary(review_pack, decisions, cards)
    pack = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": DECISION_REVIEW_PACK_TYPE,
        "review_pack_id": review_pack["review_pack_id"],
        "decision_review_pack_id": f"{review_pack['review_pack_id']}_decision_review_pack_v0",
        "created_at": created_at,
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "human_acceptance_recorded": False,
        "review_status": _review_status(summary),
        "decision_summary": summary,
        "decision_groups": _decision_groups(cards),
        "decision_cards": cards,
        "next_action": "fill_decisions_manually_then_run_loulan_context_bundle",
        "claim_boundaries": _claim_boundaries(),
    }
    reject_unsafe_output(pack)
    return pack


def write_loulan_decision_review_pack(pack: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "loulan_decision_review_pack.json", pack)
    report_path = output_root / "loulan_decision_review_pack.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_loulan_decision_review_pack_report(pack), encoding="utf-8")
    return [json_path, report_path]


def render_loulan_decision_review_pack_report(pack: dict[str, Any]) -> str:
    summary = pack["decision_summary"]
    lines = [
        "# Loulan Decision Review Pack",
        "",
        f"- Review pack: `{pack['review_pack_id']}`",
        f"- Status: `{pack['review_status']}`",
        f"- Required decisions: {summary['required_decisions']}",
        f"- Pending: {summary['pending_count']}",
        f"- Missing slots: {summary['missing_slot_count']}",
        f"- Ready for context projection: {summary['ready_count']}",
        "- Human acceptance: not recorded",
        "- Provider calls: not started",
        "- Durable Memory runtime: not implemented",
        "",
        "## Decision Slots",
        "",
    ]
    for card in pack["decision_cards"]:
        lines.append(f"- `{card['target_ref']}`: `{card['status']}`; allowed={', '.join(card['allowed_decisions'])}")
    lines.append("")
    return "\n".join(lines)


def _validate_review_pack(review_pack: dict[str, Any]) -> None:
    if review_pack.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Loulan decision review pack requires review pack schema_version 0.1.0")
    if review_pack.get("artifact_type") != REVIEW_PACK_TYPE:
        raise ValueError(f"Loulan decision review pack requires review pack artifact_type {REVIEW_PACK_TYPE}")
    if review_pack.get("provider_calls_started") is not False:
        raise ValueError("review pack must not have provider calls started")
    if review_pack.get("writes_long_term_memory") is not False:
        raise ValueError("review pack must not write long-term memory")
    if review_pack.get("human_acceptance_recorded") is not False:
        raise ValueError("review pack must not record human acceptance")


def _validate_decisions(decisions: dict[str, Any], review_pack: dict[str, Any]) -> None:
    if decisions.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Loulan decision review pack requires decisions schema_version 0.1.0")
    if decisions.get("artifact_type") != DECISIONS_TYPE:
        raise ValueError(f"Loulan decision review pack requires decisions artifact_type {DECISIONS_TYPE}")
    if decisions.get("review_pack_id") != review_pack.get("review_pack_id"):
        raise ValueError("Loulan decisions review_pack_id must match review pack")
    if decisions.get("provider_calls_started") is True:
        raise ValueError("Loulan decisions must not have provider calls started")
    if decisions.get("writes_long_term_memory") is not False:
        raise ValueError("Loulan decisions must not write long-term memory")
    if decisions.get("human_acceptance_recorded") is True:
        raise ValueError("Loulan decisions must not record human acceptance")


def _decision_cards(review_pack: dict[str, Any], decisions: dict[str, Any]) -> list[dict[str, Any]]:
    by_ref = {str(item.get("target_ref")): item for item in decisions.get("decisions") or []}
    cards = []
    for target_ref in review_pack.get("next_pass_readiness", {}).get("required_decisions") or []:
        item = by_ref.get(str(target_ref))
        cards.append(_decision_card(str(target_ref), item, review_pack))
    return cards


def _decision_card(target_ref: str, item: dict[str, Any] | None, review_pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_ref": target_ref,
        "target_type": _target_type(target_ref),
        "decision_id": str((item or {}).get("decision_id") or ""),
        "status": _card_status(target_ref, item),
        "current_decision": str((item or {}).get("decision") or ""),
        "allowed_decisions": _allowed_decisions(target_ref, item, review_pack),
        "decided_by": str((item or {}).get("decided_by") or ""),
        "evidence_refs": list((item or {}).get("evidence_refs") or []),
        "suggested_evidence_refs": _suggested_evidence_refs(target_ref, item, review_pack),
        "required_fields": REQUIRED_FIELDS,
        "review_note_present": bool((item or {}).get("review_note")),
    }


def _card_status(target_ref: str, item: dict[str, Any] | None) -> str:
    if item is None:
        return "missing_decision_slot"
    decision = str(item.get("decision") or "")
    if decision == "pending_human_review" or not decision:
        return "needs_human_input"
    if _invalid_reason(target_ref, item):
        return "invalid_decision"
    return "ready_for_context_projection"


def _invalid_reason(target_ref: str, item: dict[str, Any]) -> str:
    decision = str(item.get("decision") or "")
    if item.get("decided_by") != "human":
        return "decision_not_human"
    if not item.get("evidence_refs"):
        return "missing_evidence_refs"
    if target_ref.startswith("shot:") and decision not in SHOT_REUSE_DECISIONS | SHOT_BLOCK_DECISIONS:
        return "invalid_shot_decision"
    if _is_asset_target(target_ref) and decision not in ASSET_REUSE_DECISIONS | ASSET_BLOCK_DECISIONS:
        return "invalid_asset_decision"
    return ""


def _decision_summary(
    review_pack: dict[str, Any],
    decisions: dict[str, Any],
    cards: list[dict[str, Any]],
) -> dict[str, int]:
    return {
        "required_decisions": len(review_pack.get("next_pass_readiness", {}).get("required_decisions") or []),
        "decision_slots": len(decisions.get("decisions") or []),
        "pending_count": sum(1 for card in cards if card["status"] == "needs_human_input"),
        "missing_slot_count": sum(1 for card in cards if card["status"] == "missing_decision_slot"),
        "invalid_count": sum(1 for card in cards if card["status"] == "invalid_decision"),
        "ready_count": sum(1 for card in cards if card["status"] == "ready_for_context_projection"),
    }


def _review_status(summary: dict[str, int]) -> str:
    if summary["missing_slot_count"]:
        return "blocked_missing_decisions"
    if summary["invalid_count"]:
        return "blocked_invalid_decisions"
    if summary["pending_count"]:
        return "blocked_pending_human_input"
    return "ready_for_context_projection" if summary["ready_count"] else "blocked_no_decisions"


def _decision_groups(cards: list[dict[str, Any]]) -> list[dict[str, int | str]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for card in cards:
        groups.setdefault(card["target_type"], []).append(card)
    return [
        {
            "target_type": target_type,
            "count": len(items),
            "pending_count": sum(1 for item in items if item["status"] == "needs_human_input"),
        }
        for target_type, items in sorted(groups.items())
    ]


def _target_type(target_ref: str) -> str:
    return target_ref.split(":", 1)[0] if ":" in target_ref else "unknown"


def _allowed_decisions(target_ref: str, item: dict[str, Any] | None, review_pack: dict[str, Any]) -> list[str]:
    if item and item.get("allowed_decisions"):
        return list(item["allowed_decisions"])
    if target_ref.startswith("shot:"):
        return ["approve_anchor", "reject", "request_repair"]
    if _is_asset_target(target_ref):
        return ["promoted", "merged", "rejected", "expired"]
    return []


def _suggested_evidence_refs(
    target_ref: str,
    item: dict[str, Any] | None,
    review_pack: dict[str, Any],
) -> list[str]:
    if item and item.get("suggested_evidence_refs"):
        return list(item["suggested_evidence_refs"])
    if item and item.get("evidence_refs"):
        return list(item["evidence_refs"])
    if target_ref.startswith("shot:"):
        shot_id = target_ref.split(":", 1)[1]
        for card in review_pack.get("shot_review_cards") or []:
            if card.get("shot_id") == shot_id:
                return [card["candidate_id"], *card.get("evidence_refs", []), *card.get("rejected_evidence_refs", [])]
    if _is_asset_target(target_ref):
        for card in review_pack.get("asset_review", {}).get("cards") or []:
            if card.get("memory_ref") == target_ref:
                return [card["memory_ref"], card.get("asset_id", "")]
    return []


def _is_asset_target(target_ref: str) -> bool:
    return target_ref.startswith(("character:", "asset:"))


def _claim_boundaries() -> dict[str, str]:
    return {
        "structure_verification": "decision_review_pack_only",
        "runtime_verification": "not_run",
        "provider_smoke": "not_run",
        "human_acceptance": "not_recorded",
        "business_validation": "not_validated",
        "durable_memory_runtime": "not_implemented",
    }
