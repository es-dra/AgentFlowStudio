from __future__ import annotations

from pathlib import Path
from typing import Any

from narratocut.utils import write_json

from agentflow.memory.loulan_context_bundle import DECISIONS_TYPE
from agentflow.memory.loulan_human_review_support import SCHEMA_VERSION, reject_unsafe_output


REVIEW_PACK_TYPE = "agentflow_loulan_human_review_pack"


def build_loulan_decision_template(review_pack: dict[str, Any], *, created_at: str) -> dict[str, Any]:
    """Build a fillable human-decision template that cannot approve by default."""
    _validate_review_pack(review_pack)
    decisions = [_decision_slot(ref, review_pack) for ref in review_pack["next_pass_readiness"]["required_decisions"]]
    template = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": DECISIONS_TYPE,
        "review_pack_id": review_pack["review_pack_id"],
        "created_at": created_at,
        "template_status": "pending_human_input",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "human_acceptance_recorded": False,
        "instructions": "Fill decision, decided_by=human, evidence_refs, and review_note before context projection.",
        "decisions": decisions,
    }
    reject_unsafe_output(template)
    return template


def write_loulan_decision_template(template: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "loulan_decisions.template.json", template)
    report_path = output_root / "loulan_decisions.template.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_loulan_decision_template_report(template), encoding="utf-8")
    return [json_path, report_path]


def render_loulan_decision_template_report(template: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Loulan Decision Template",
            "",
            f"- Review pack: `{template['review_pack_id']}`",
            f"- Status: `{template['template_status']}`",
            f"- Decision slots: {len(template['decisions'])}",
            "- Human acceptance: not recorded",
            "- Provider calls: not started",
            "- Durable Memory runtime: not implemented",
            "",
        ]
    )


def _validate_review_pack(review_pack: dict[str, Any]) -> None:
    if review_pack.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Loulan decision template requires review pack schema_version 0.1.0")
    if review_pack.get("artifact_type") != REVIEW_PACK_TYPE:
        raise ValueError(f"Loulan decision template requires review pack artifact_type {REVIEW_PACK_TYPE}")
    if review_pack.get("provider_calls_started") is not False:
        raise ValueError("review pack must not have provider calls started")
    if review_pack.get("writes_long_term_memory") is not False:
        raise ValueError("review pack must not write long-term memory")
    if review_pack.get("human_acceptance_recorded") is not False:
        raise ValueError("review pack must not record human acceptance")


def _decision_slot(target_ref: str, review_pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision_id": _decision_id(review_pack, target_ref),
        "target_ref": target_ref,
        "decision": "pending_human_review",
        "allowed_decisions": _allowed_decisions(target_ref, review_pack),
        "decided_by": "",
        "evidence_refs": [],
        "suggested_evidence_refs": _suggested_evidence_refs(target_ref, review_pack),
        "review_note": "",
    }


def _decision_id(review_pack: dict[str, Any], target_ref: str) -> str:
    safe_target = target_ref.replace(":", "_").replace("-", "_").lower()
    return f"{review_pack['review_pack_id']}_{safe_target}_decision"


def _allowed_decisions(target_ref: str, review_pack: dict[str, Any]) -> list[str]:
    if target_ref.startswith("shot:"):
        shot_id = target_ref.split(":", 1)[1]
        for card in review_pack.get("shot_review_cards") or []:
            if card.get("shot_id") == shot_id:
                return list(card.get("allowed_decisions") or ["approve_anchor", "reject", "request_repair"])
        return ["approve_anchor", "reject", "request_repair"]
    if _is_asset_target(target_ref):
        for card in review_pack.get("asset_review", {}).get("cards") or []:
            if card.get("memory_ref") == target_ref:
                return list(card.get("allowed_decisions") or ["promoted", "merged", "rejected", "expired"])
        return ["promoted", "merged", "rejected", "expired"]
    return []


def _suggested_evidence_refs(target_ref: str, review_pack: dict[str, Any]) -> list[str]:
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
