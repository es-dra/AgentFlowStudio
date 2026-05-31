from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REGISTRY_REF = "manifests/asset_registry.json"
REGISTRY_TYPE = "loulan_unified_asset_registry"
CANONICAL_STATUSES = frozenset(
    {
        "source_reference",
        "candidate",
        "needs_repair",
        "approved_anchor",
        "promoted_reusable",
        "superseded",
        "rejected",
        "route_failed",
    }
)
REGISTRY_ELIGIBLE_STATUSES = frozenset({"approved_anchor", "promoted_reusable"})
REGISTRY_BLOCKED_STATUSES = frozenset(CANONICAL_STATUSES - REGISTRY_ELIGIBLE_STATUSES)
LEGACY_ELIGIBLE_STATUSES = frozenset({"approved", "promoted", "merged"})
LEGACY_BLOCKED_STATUSES = frozenset({"candidate", "candidate_pending_human_review", "needs_repair", "rejected", "expired"})


def registry_file(root: Path) -> Path:
    return root / REGISTRY_REF


def has_asset_registry(root: Path) -> bool:
    return registry_file(root).exists()


def registry_asset_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    entries = []
    for raw in payload.get("assets") or []:
        entries.append(_registry_entry(raw))
    return entries


def legacy_character_entries(character_assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_legacy_character_entry(asset) for asset in character_assets]


def asset_inventory(entries: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(entry["status"] for entry in entries)
    types = Counter(entry["asset_type"] for entry in entries)
    missing_sha = [entry["memory_ref"] for entry in entries if not entry["sha256_present"]]
    missing_refs = [
        {"memory_ref": entry["memory_ref"], "missing_refs": entry["missing_refs"]}
        for entry in entries
        if entry["missing_refs"]
    ]
    return {
        "source_registry_ref": REGISTRY_REF,
        "registry_type": REGISTRY_TYPE,
        "total_assets": len(entries),
        "type_counts": dict(sorted(types.items())),
        "status_counts": dict(sorted(statuses.items())),
        "missing_sha256_count": len(missing_sha),
        "missing_ref_count": sum(len(row["missing_refs"]) for row in missing_refs),
        "missing_sha256_refs": missing_sha[:24],
        "missing_refs": missing_refs[:24],
        "eligible_assets": [entry for entry in entries if entry["eligible_for_context"]][:24],
        "blocked_assets": [
            {
                "memory_ref": entry["memory_ref"],
                "asset_type": entry["asset_type"],
                "status": entry["status"],
                "reason": _registry_block_reason(entry),
            }
            for entry in entries
            if not entry["eligible_for_context"]
        ][:48],
        "assets": entries[:48],
    }


def legacy_asset_summary(entries: list[dict[str, Any]], rejected_refs: list[str]) -> dict[str, Any]:
    statuses = Counter(entry["status"] for entry in entries)
    return {
        "total_assets": len(entries),
        "status_counts": dict(sorted(statuses.items())),
        "missing_sha256_count": sum(1 for entry in entries if not entry["sha256_present"]),
        "rejected_asset_count": len(rejected_refs),
        "assets": entries[:16],
        "rejected_asset_refs": rejected_refs,
    }


def registry_asset_summary(entries: list[dict[str, Any]], rejected_refs: list[str]) -> dict[str, Any]:
    summary = legacy_asset_summary(entries, rejected_refs)
    summary["source_registry_ref"] = REGISTRY_REF
    summary["rejected_asset_count"] = len([entry for entry in entries if entry["status"] == "rejected"]) + len(rejected_refs)
    return summary


def promotion_gates(entries: list[dict[str, Any]], rejected_refs: list[str], *, registry_mode: bool) -> dict[str, Any]:
    blocking = []
    for entry in entries:
        reason = _registry_block_reason(entry) if registry_mode else _legacy_block_reason(entry)
        if reason:
            blocking.append({"memory_ref": entry["memory_ref"], "reason": reason})
    blocking.extend({"memory_ref": ref, "reason": "rejected_asset"} for ref in rejected_refs)
    payload = {
        "overall_status": "blocked" if blocking else "ready",
        "blocking_refs": blocking,
        "promotion_modes": ["promote", "merge", "reject", "expire"],
        "requires_human_review": True,
        "writes_long_term_memory": False,
    }
    if registry_mode:
        payload["eligible_statuses"] = sorted(REGISTRY_ELIGIBLE_STATUSES)
        payload["blocked_statuses"] = sorted(REGISTRY_BLOCKED_STATUSES)
    return payload


def next_context_bundle(entries: list[dict[str, Any]], rejected_refs: list[str], *, registry_mode: bool) -> dict[str, Any]:
    eligible = [entry["memory_ref"] for entry in entries if entry["eligible_for_context"]]
    blocked = [entry["memory_ref"] for entry in entries if not entry["eligible_for_context"]]
    blocked.extend(rejected_refs)
    payload = {
        "status": "promotion_decision_required",
        "eligible_memory_refs": eligible,
        "blocked_memory_refs": blocked,
        "projection_mode": "file_protocol_only",
        "writes_long_term_memory": False,
    }
    if registry_mode:
        by_reason: dict[str, list[str]] = defaultdict(list)
        for entry in entries:
            reason = _registry_block_reason(entry)
            if reason:
                by_reason[reason].append(entry["memory_ref"])
        payload["blocked_refs_by_reason"] = {reason: refs for reason, refs in sorted(by_reason.items())}
        payload["context_rule"] = "only approved_anchor or promoted_reusable assets may enter context"
    return payload


def _registry_entry(asset: dict[str, Any]) -> dict[str, Any]:
    status = _canonical_status(asset.get("status"))
    asset_id = str(asset.get("asset_id") or "unknown_asset")
    sha = str(asset.get("sha256") or "")
    refs = _refs_for_asset(asset)
    missing_refs = [ref for ref in refs if _is_missing_ref(ref)]
    current_ref = _safe_relative_text(asset.get("current_ref"))
    return {
        "memory_ref": f"asset:{asset_id}",
        "asset_id": asset_id,
        "asset_type": _asset_type(asset.get("asset_type")),
        "role": str(asset.get("role") or asset_id),
        "label": str(asset.get("role") or asset_id),
        "status": status,
        "current_ref": current_ref,
        "output_ref": current_ref,
        "source_refs": [_safe_relative_text(ref) for ref in asset.get("source_refs") or []],
        "evidence_refs": [_safe_relative_text(ref) for ref in asset.get("evidence_refs") or []],
        "review_refs": [_safe_relative_text(ref) for ref in asset.get("review_refs") or []],
        "asset_card_ref": _first_ref(asset.get("source_refs") or asset.get("evidence_refs") or []),
        "review_card_ref": _first_ref(asset.get("review_refs") or []),
        "sha256": sha,
        "sha256_present": bool(sha),
        "promotion_state": str(asset.get("promotion_state") or _promotion_state(status, bool(sha))),
        "reuse_policy": asset.get("reuse_policy") or {},
        "claim_boundary": asset.get("claim_boundary") or {},
        "missing_refs": missing_refs,
        "eligible_for_context": status in REGISTRY_ELIGIBLE_STATUSES and bool(sha),
    }


def _legacy_character_entry(asset: dict[str, Any]) -> dict[str, Any]:
    status = _normalize_status(asset.get("status"))
    sha = str(asset.get("sha256") or "")
    ref = f"character:{asset.get('asset_id') or 'unknown'}"
    return {
        "memory_ref": ref,
        "asset_id": str(asset.get("asset_id") or ""),
        "asset_type": "character",
        "label": _asset_label(asset),
        "character": str(asset.get("character") or ""),
        "phase": str(asset.get("phase") or ""),
        "status": status,
        "sha256": sha,
        "sha256_present": bool(sha),
        "output_ref": _safe_relative_text(asset.get("output_path")),
        "asset_card_ref": _safe_relative_text(asset.get("asset_card")),
        "review_card_ref": _safe_relative_text(asset.get("review_card")),
        "eligible_for_context": status in LEGACY_ELIGIBLE_STATUSES and bool(sha),
    }


def _refs_for_asset(asset: dict[str, Any]) -> list[str]:
    refs = [_safe_relative_text(asset.get("current_ref"))]
    for key in ("source_refs", "evidence_refs", "review_refs"):
        refs.extend(_safe_relative_text(ref) for ref in asset.get(key) or [])
    return [ref for ref in refs if ref]


def _registry_block_reason(entry: dict[str, Any]) -> str:
    if entry["status"] == "route_failed":
        return "route_failed"
    if entry["status"] in REGISTRY_BLOCKED_STATUSES:
        return entry["status"]
    if not entry["sha256_present"]:
        return "missing_sha256"
    if entry.get("missing_refs"):
        return "missing_ref"
    return ""


def _legacy_block_reason(entry: dict[str, Any]) -> str:
    if not entry["sha256_present"]:
        return "missing_sha256"
    if entry["status"] in LEGACY_BLOCKED_STATUSES:
        return entry["status"]
    return ""


def _canonical_status(value: Any) -> str:
    status = _normalize_status(value)
    if status in CANONICAL_STATUSES:
        return status
    if status in {"approved", "approved_character_memory", "merged", "promoted"}:
        return "approved_anchor"
    if "route_failure" in status or status.endswith("_failed") or "blocked_by_builtin_route" in status:
        return "route_failed"
    if "superseded" in status:
        return "superseded"
    if "repair" in status or "pending_repair" in status:
        return "needs_repair"
    if "rejected" in status:
        return "rejected"
    if "source_reference" in status:
        return "source_reference"
    return "candidate"


def _promotion_state(status: str, has_sha: bool) -> str:
    if status in REGISTRY_ELIGIBLE_STATUSES and has_sha:
        return "eligible_for_context"
    return "blocked"


def _asset_type(value: Any) -> str:
    asset_type = str(value or "run_evidence").strip().lower()
    return asset_type if asset_type in {"character", "scene", "prop", "vfx", "keyframe", "feedback", "run_evidence"} else "run_evidence"


def _asset_label(asset: dict[str, Any]) -> str:
    character = str(asset.get("character") or asset.get("asset_id") or "asset")
    phase = str(asset.get("phase") or "").replace("_", " ")
    return f"{character} {phase}".strip()


def _first_ref(values: list[Any]) -> str:
    for value in values:
        ref = _safe_relative_text(value)
        if ref:
            return ref
    return ""


def _safe_relative_text(value: Any) -> str:
    text = str(value or "")
    return "" if text.startswith(("D:\\", "C:\\", "file://")) else text.replace("\\", "/")


def _normalize_status(value: Any) -> str:
    status = str(value or "candidate").strip().lower()
    return status or "candidate"


def _is_missing_ref(ref: str) -> bool:
    return ref.startswith("missing:")
