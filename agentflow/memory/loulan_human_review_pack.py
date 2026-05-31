from __future__ import annotations

from pathlib import Path
from typing import Any

from narratocut.utils import write_json

from agentflow.memory.loulan_human_review_support import (
    FEEDBACK_EVENT_TYPE,
    PACK_TYPE,
    SCHEMA_VERSION,
    read_json,
    reject_unsafe_output,
    safe_ref,
    validate_api_plan,
    validate_package,
)


REVIEWABLE_ASSET_STATUSES = frozenset({"candidate", "candidate_pending_human_review", "needs_repair"})
REUSABLE_ASSET_STATUSES = frozenset({"approved", "promoted", "merged"})


def build_loulan_human_review_pack(
    package: dict[str, Any],
    api_plan: dict[str, Any],
    *,
    project_root: str | Path,
    block_id: str,
    created_at: str,
) -> dict[str, Any]:
    """Prepare a no-call human review pack without approving Loulan memory."""
    validate_package(package)
    validate_api_plan(api_plan, package)
    root = Path(project_root)
    shots = read_json(root / "manifests" / "shot_list.json").get("shots") or []
    image_qa = read_json(root / "reviews" / f"{block_id}-horizontal-pack" / "image_qa.json").get("shots") or []
    cards = _shot_review_cards(root, block_id, shots, image_qa)
    asset_review = _asset_review(package)
    promotion_drafts = _promotion_decision_drafts(package, asset_review, created_at)
    pack = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": PACK_TYPE,
        "review_pack_id": f"{package['package_id']}_{block_id.lower()}_human_review_pack_v0",
        "created_at": created_at,
        "package_id": package["package_id"],
        "project_id": package.get("project", {}).get("project_id"),
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "human_acceptance_recorded": False,
        "review_scope": _review_scope(block_id, cards),
        "shot_review_cards": cards,
        "asset_review": asset_review,
        "api_workbench_status": _api_workbench_status(api_plan),
        "promotion_decision_drafts": promotion_drafts,
        "feedback_event_draft": _feedback_event_draft(package, block_id, cards, created_at),
        "next_pass_readiness": _next_pass_readiness(cards, asset_review, api_plan),
        "claim_boundaries": _claim_boundaries(),
    }
    reject_unsafe_output(pack)
    return pack


def write_loulan_human_review_pack(pack: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    paths = [
        write_json(output_root / "loulan_human_review_pack.json", pack),
        write_json(output_root / "shot_review_cards.json", {"cards": pack["shot_review_cards"]}),
        write_json(output_root / "promotion_decision_drafts.json", {"drafts": pack["promotion_decision_drafts"]}),
        write_json(output_root / "feedback_event_draft.json", pack["feedback_event_draft"]),
    ]
    report_path = output_root / "loulan_human_review_pack.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_loulan_human_review_pack_report(pack), encoding="utf-8")
    paths.append(report_path)
    return paths


def render_loulan_human_review_pack_report(pack: dict[str, Any]) -> str:
    readiness = pack["next_pass_readiness"]
    return "\n".join(
        [
            "# Loulan Human Review Pack",
            "",
            f"- Review pack: `{pack['review_pack_id']}`",
            f"- Block: `{pack['review_scope']['block_id']}`",
            f"- Shots queued: {pack['review_scope']['shot_count']}",
            f"- Evidence status: `{pack['review_scope']['evidence_status']}`",
            "- Human acceptance: not recorded",
            "- Provider calls: not started",
            "- Durable Memory runtime: not implemented",
            f"- Next pass readiness: `{readiness['status']}`",
            f"- Required decisions: {len(readiness['required_decisions'])}",
            "",
        ]
    )


def _shot_review_cards(
    root: Path,
    block_id: str,
    shots: list[dict[str, Any]],
    image_qa: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    qa_by_candidate = {str(row.get("shot") or ""): row for row in image_qa}
    cards = []
    for shot in shots:
        shot_id = str(shot.get("shot_id") or "")
        if not shot_id.startswith(f"{block_id}-"):
            continue
        candidate_id = _candidate_id(shot)
        qa = qa_by_candidate.get(candidate_id, {})
        evidence_refs = _evidence_refs(root, shot)
        blocking = _blocking_reasons(qa, evidence_refs, shot)
        cards.append(
            {
                "shot_id": shot_id,
                "candidate_id": candidate_id,
                "status": str(shot.get("quality_status") or "planned"),
                "review_status": "pending_human_review",
                "image_size": str(qa.get("size") or shot.get("expected_image_size") or ""),
                "image_sha256": str(qa.get("sha256") or ""),
                "evidence_refs": evidence_refs,
                "evidence_status": "blocked" if blocking else "ready_for_human_review",
                "blocking_reasons": blocking,
                "rejected_evidence_refs": _rejected_refs(shot),
                "allowed_decisions": ["approve_anchor", "reject", "request_repair"],
                "auto_promotes_memory": False,
            }
        )
    return cards


def _candidate_id(shot: dict[str, Any]) -> str:
    versioned = str(shot.get("versioned_image_path") or "")
    if versioned:
        return Path(versioned).stem
    return f"{shot.get('shot_id', 'unknown')}-candidate"


def _evidence_refs(root: Path, shot: dict[str, Any]) -> list[str]:
    refs = []
    for key in ("director_art_card", "feedback_asset", "motion_intent", "vfx_asset"):
        ref = safe_ref(shot.get(key))
        if ref and _evidence_exists(root, ref):
            refs.append(ref)
    return refs


def _evidence_exists(root: Path, ref: str) -> bool:
    try:
        return (root / ref).is_file()
    except OSError:
        return False


def _blocking_reasons(qa: dict[str, Any], evidence_refs: list[str], shot: dict[str, Any]) -> list[str]:
    reasons = []
    if not qa.get("sha256"):
        reasons.append("missing_image_sha256")
    if not evidence_refs:
        reasons.append("missing_review_evidence")
    if shot.get("rejected_previous_asset"):
        reasons.append("has_rejected_previous_asset")
    return reasons


def _rejected_refs(shot: dict[str, Any]) -> list[str]:
    rejected = safe_ref(shot.get("rejected_previous_asset"))
    return [rejected] if rejected else []


def _asset_review(package: dict[str, Any]) -> dict[str, Any]:
    candidate_refs = []
    reusable_refs = []
    cards = []
    for asset in package.get("asset_summary", {}).get("assets") or []:
        memory_ref = str(asset.get("memory_ref") or "")
        status = str(asset.get("status") or "")
        if status in REVIEWABLE_ASSET_STATUSES:
            candidate_refs.append(memory_ref)
        if status in REUSABLE_ASSET_STATUSES:
            reusable_refs.append(memory_ref)
        cards.append(
            {
                "memory_ref": memory_ref,
                "asset_id": str(asset.get("asset_id") or ""),
                "status": status,
                "sha256_present": bool(asset.get("sha256")),
                "review_status": "pending_human_review" if status in REVIEWABLE_ASSET_STATUSES else "already_reusable",
                "allowed_decisions": ["promoted", "merged", "rejected", "expired"],
            }
        )
    return {
        "status": "pending_human_review" if candidate_refs else "no_candidate_assets",
        "candidate_memory_refs": candidate_refs,
        "approved_or_promoted_memory_refs": reusable_refs,
        "rejected_memory_refs": package.get("asset_summary", {}).get("rejected_asset_refs") or [],
        "cards": cards,
    }


def _promotion_decision_drafts(
    package: dict[str, Any],
    asset_review: dict[str, Any],
    created_at: str,
) -> list[dict[str, Any]]:
    drafts = []
    for memory_ref in asset_review["candidate_memory_refs"]:
        drafts.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "agentflow_memory_promotion_decision",
                "decision_id": f"{package['package_id']}_{memory_ref.replace(':', '_')}_decision_draft",
                "source_memory_ref": memory_ref,
                "draft_status": "pending_human_review",
                "allowed_decisions": ["promoted", "merged", "rejected", "expired"],
                "writes_long_term_memory": False,
                "created_at": created_at,
            }
        )
    return drafts


def _feedback_event_draft(
    package: dict[str, Any],
    block_id: str,
    cards: list[dict[str, Any]],
    created_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": FEEDBACK_EVENT_TYPE,
        "feedback_id": f"{package['package_id']}_{block_id.lower()}_review_feedback_draft",
        "source": "human_review_pending_draft",
        "target_type": "package",
        "target_id": package["package_id"],
        "decision": "note",
        "reason_tags": sorted({"pending_human_review", *[reason for card in cards for reason in card["blocking_reasons"]]}),
        "user_note": "Draft only: review B01 keyframe sequence and character anchors before next-pass reuse.",
        "created_at": created_at,
        "draft_status": "draft_not_persisted",
        "writes_long_term_memory": False,
    }


def _review_scope(block_id: str, cards: list[dict[str, Any]]) -> dict[str, Any]:
    blocked = [card["shot_id"] for card in cards if card["evidence_status"] == "blocked"]
    return {
        "block_id": block_id,
        "status": "pending_human_review",
        "shot_count": len(cards),
        "evidence_status": "blocked" if blocked else "ready_for_human_review",
        "blocked_shot_ids": blocked,
        "auto_accepts_assets": False,
    }


def _api_workbench_status(api_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": api_plan["artifact_type"],
        "reference_pack_status": api_plan.get("reference_pack", {}).get("status"),
        "request_manifest_status": api_plan.get("request_manifest", {}).get("status"),
        "provider_calls_started": False,
        "blocking_reasons": api_plan.get("blocking_reasons") or [],
    }


def _next_pass_readiness(
    cards: list[dict[str, Any]],
    asset_review: dict[str, Any],
    api_plan: dict[str, Any],
) -> dict[str, Any]:
    blocked_refs = [f"shot:{card['shot_id']}" for card in cards if card["evidence_status"] == "blocked"]
    blocked_refs.extend(asset_review["candidate_memory_refs"])
    status = "blocked_until_human_review" if blocked_refs or api_plan.get("request_manifest", {}).get("status") != "ready" else "review_required"
    return {
        "status": status,
        "required_decisions": [f"shot:{card['shot_id']}" for card in cards] + asset_review["candidate_memory_refs"],
        "blocked_refs": blocked_refs,
        "ready_memory_refs": asset_review["approved_or_promoted_memory_refs"],
        "writes_long_term_memory": False,
    }


def _claim_boundaries() -> dict[str, str]:
    return {
        "structure_verification": "human_review_pack_contract_only",
        "runtime_verification": "not_run",
        "provider_smoke": "not_run",
        "human_acceptance": "not_recorded",
        "business_validation": "not_validated",
        "durable_memory_runtime": "not_implemented",
    }
