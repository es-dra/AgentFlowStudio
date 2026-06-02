from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from agentflow.memory.production_asset_profile_promotion_contract import (
    candidate_patch_ops,
    profile_by_id,
    validate_asset_profile_update_candidate,
    validate_asset_profiles,
)
from agentflow.memory.production_asset_profile_promotion_render import (
    render_asset_profile_promotion_decision_markdown,
    render_asset_profile_version_markdown,
)
from agentflow.memory.production_asset_profile_promotion_utils import (
    list_value,
    next_profile_id,
    next_version_label,
    profile_promotion_claim_boundaries,
    profile_promotion_non_claims,
    reject_unsafe_asset_profile_promotion,
    remove_stale_profile_version_outputs,
    safe_id,
    version_change_summary,
)
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow_studio.utils import write_json

ASSET_PROFILE_PROMOTION_DECISION_KIND = "agentflow_production_memory_asset_profile_promotion_decision"
ASSET_PROFILE_VERSION_KIND = "agentflow_production_memory_asset_profile_version"
ASSET_PROFILE_PROMOTION_DECISIONS = frozenset({"promoted", "merged", "rejected", "expired", "blocked"})
VERSION_APPLY_DECISIONS = frozenset({"promoted", "merged"})
SUPPORTED_ADD_UNIQUE_PATHS = {
    "/negative_constraints/-": "negative_constraints",
    "/allowed_variations/-": "allowed_variations",
    "/evidence_refs/-": "evidence_refs",
}


def load_asset_profiles(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("asset profiles must be a JSON object")
    validate_asset_profiles(payload)
    return payload


def load_asset_profile_update_candidate(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("asset profile update candidate must be a JSON object")
    validate_asset_profile_update_candidate(payload)
    return payload


def build_asset_profile_promotion_review(
    *,
    asset_profiles: dict[str, Any],
    update_candidate: dict[str, Any],
    decision: str,
    rationale: str,
    reviewer_role: str,
    decided_at: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Review a profile update candidate and optionally apply a local profile version."""
    validate_asset_profiles(asset_profiles)
    validate_asset_profile_update_candidate(update_candidate)
    _validate_inputs(decision, rationale, reviewer_role, decided_at)
    source_profile = profile_by_id(asset_profiles, str(update_candidate["profile_id"]))
    if source_profile.get("profile_kind") != update_candidate.get("profile_kind"):
        raise ValueError("asset profile update candidate profile_kind does not match source profile")

    applies_version = decision in VERSION_APPLY_DECISIONS
    patch_ops = candidate_patch_ops(update_candidate)
    if applies_version and update_candidate.get("candidate_generation_status") != "candidate_only":
        raise ValueError("asset profile promotion requires candidate_only update candidate")
    if applies_version and not patch_ops:
        raise ValueError("asset profile promotion requires patch_ops before versioning")

    promotion_decision = _build_decision(
        update_candidate=update_candidate,
        decision=decision,
        rationale=rationale,
        reviewer_role=reviewer_role,
        decided_at=decided_at,
        creates_profile_version=applies_version,
    )
    version = (
        _build_profile_version(source_profile, update_candidate, promotion_decision, patch_ops, decided_at)
        if applies_version
        else None
    )
    reject_unsafe_asset_profile_promotion(promotion_decision)
    if version is not None:
        reject_unsafe_asset_profile_promotion(version)
    return promotion_decision, version


def write_asset_profile_promotion_review(
    decision: dict[str, Any],
    version: dict[str, Any] | None,
    output_dir: str | Path,
) -> list[Path]:
    output_root = Path(output_dir)
    written = [write_json(output_root / "asset_profile_promotion_decision.json", decision)]
    decision_md = output_root / "asset_profile_promotion_decision.md"
    decision_md.parent.mkdir(parents=True, exist_ok=True)
    decision_md.write_text(render_asset_profile_promotion_decision_markdown(decision), encoding="utf-8")
    written.append(decision_md)
    if version is not None:
        written.append(write_json(output_root / "asset_profile_version.json", version))
        version_md = output_root / "asset_profile_version.md"
        version_md.write_text(render_asset_profile_version_markdown(version), encoding="utf-8")
        written.append(version_md)
    else:
        remove_stale_profile_version_outputs(output_root)
    return written


def _build_decision(
    *,
    update_candidate: dict[str, Any],
    decision: str,
    rationale: str,
    reviewer_role: str,
    decided_at: str,
    creates_profile_version: bool,
) -> dict[str, Any]:
    candidate_id = str(update_candidate["candidate_id"])
    return {
        "kind": ASSET_PROFILE_PROMOTION_DECISION_KIND,
        "artifact_type": ASSET_PROFILE_PROMOTION_DECISION_KIND,
        "schema_version": update_candidate.get("schema_version", SCHEMA_VERSION),
        "decision_id": safe_id("promotion:asset-profile-update", candidate_id, decided_at),
        "candidate_id": candidate_id,
        "source_candidate_id": candidate_id,
        "source_candidate_status": update_candidate.get("candidate_generation_status", "unknown"),
        "source_feedback_event_id": update_candidate.get("source_feedback_event_id", "unknown"),
        "project_id": update_candidate.get("project_id", "unknown"),
        "profile_id": update_candidate.get("profile_id"),
        "profile_kind": update_candidate.get("profile_kind"),
        "decision": decision,
        "decision_effect": _decision_effect(decision),
        "review_mode": "explicit_operator_decision",
        "reviewer_role": reviewer_role,
        "rationale": rationale,
        "decided_at": decided_at,
        "template_only": False,
        "profile_version_allowed": decision in VERSION_APPLY_DECISIONS,
        "creates_profile_version": creates_profile_version,
        "next_context_eligibility": (
            "eligible_by_explicit_profile_version"
            if creates_profile_version
            else "blocked_by_explicit_operator_decision"
        ),
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "decision_is_durable_memory_write": False,
        "decision_writes_company_kb": False,
        "claim_boundaries": profile_promotion_claim_boundaries(),
        "non_claims": profile_promotion_non_claims(),
    }


def _build_profile_version(
    source_profile: dict[str, Any],
    candidate: dict[str, Any],
    decision: dict[str, Any],
    patch_ops: list[dict[str, Any]],
    decided_at: str,
) -> dict[str, Any]:
    profile = _apply_patch_ops(source_profile, patch_ops)
    source_profile_id = str(source_profile["profile_id"])
    next_label = next_version_label(str(source_profile.get("profile_version", "v1")))
    profile["profile_id"] = next_profile_id(source_profile_id, next_label)
    profile["profile_version"] = next_label
    profile["supersedes_profile_id"] = source_profile_id
    profile["profile_status"] = "promoted"
    _append_unique(profile, "promotion_decision_refs", str(decision["decision_id"]))
    _append_unique(profile, "profile_version_decision_refs", str(decision["decision_id"]))
    profile["usable_for_next_context"] = (
        profile.get("profile_status") == "promoted"
        and profile.get("context_eligibility") == "included"
        and not list_value(profile.get("blockers"))
    )
    return {
        "kind": ASSET_PROFILE_VERSION_KIND,
        "artifact_type": ASSET_PROFILE_VERSION_KIND,
        "schema_version": candidate.get("schema_version", SCHEMA_VERSION),
        "version_id": safe_id("asset-profile-version", str(profile["profile_id"]), decided_at),
        "generated_at": decided_at,
        "project_id": candidate.get("project_id", "unknown"),
        "source_profile_id": source_profile_id,
        "profile_id": profile["profile_id"],
        "profile_kind": profile.get("profile_kind"),
        "profile_version": next_label,
        "source_candidate_id": candidate["candidate_id"],
        "source_decision_id": decision["decision_id"],
        "source_patch_ops_count": len(patch_ops),
        "version_change_summary": version_change_summary(
            source_profile_id=source_profile_id,
            target_profile_id=str(profile["profile_id"]),
            candidate=candidate,
            decision=decision,
            patch_ops=patch_ops,
        ),
        "profile_version_applied": True,
        "usable_for_next_context": profile["usable_for_next_context"],
        "profile": profile,
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "claim_boundaries": profile_promotion_claim_boundaries(),
        "non_claims": profile_promotion_non_claims(),
    }


def _apply_patch_ops(profile: dict[str, Any], patch_ops: list[dict[str, Any]]) -> dict[str, Any]:
    updated = deepcopy(profile)
    for field in SUPPORTED_ADD_UNIQUE_PATHS.values():
        _dedupe_in_place(updated, field)
    for op in patch_ops:
        if op.get("op") != "add_unique":
            raise ValueError("unsupported asset profile patch op")
        target = SUPPORTED_ADD_UNIQUE_PATHS.get(str(op.get("path")))
        if target is None:
            raise ValueError("unsupported asset profile patch op path")
        value = op.get("value")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("asset profile patch op value must be text")
        _append_unique(updated, target, value)
    return updated


def _append_unique(payload: dict[str, Any], field: str, value: str) -> None:
    items = payload.get(field)
    if not isinstance(items, list):
        items = []
        payload[field] = items
    if value not in items:
        items.append(value)


def _dedupe_in_place(payload: dict[str, Any], field: str) -> None:
    items = payload.get(field)
    if not isinstance(items, list):
        return
    seen: set[str] = set()
    deduped: list[Any] = []
    for item in items:
        key = str(item)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    payload[field] = deduped


def _validate_inputs(decision: str, rationale: str, reviewer_role: str, decided_at: str) -> None:
    for label, value in {"rationale": rationale, "reviewer_role": reviewer_role, "decided_at": decided_at}.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is required")
    if decision not in ASSET_PROFILE_PROMOTION_DECISIONS:
        raise ValueError(f"unsupported asset profile promotion decision: {decision}")
    reject_unsafe_asset_profile_promotion({"decision": decision, "rationale": rationale, "reviewer_role": reviewer_role})


def _decision_effect(decision: str) -> str:
    if decision in VERSION_APPLY_DECISIONS:
        return "profile_version_applied"
    return {
        "rejected": "blocked_by_operator_rejection",
        "expired": "blocked_by_expiration",
        "blocked": "blocked_by_operator_block",
    }[decision]


__all__ = (
    "ASSET_PROFILE_PROMOTION_DECISION_KIND",
    "ASSET_PROFILE_PROMOTION_DECISIONS",
    "ASSET_PROFILE_VERSION_KIND",
    "build_asset_profile_promotion_review",
    "load_asset_profile_update_candidate",
    "load_asset_profiles",
    "render_asset_profile_promotion_decision_markdown",
    "render_asset_profile_version_markdown",
    "write_asset_profile_promotion_review",
)
