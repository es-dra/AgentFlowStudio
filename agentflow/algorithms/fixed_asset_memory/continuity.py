from __future__ import annotations

from typing import Any


ALGORITHM_ID = "afs.fixed_asset_memory.v0.1"


def asset_continuity_context(
    assets: dict[str, dict[str, Any]],
    *,
    locked_asset_ids: list[str] | None = None,
    excluded_asset_ids: list[str] | None = None,
) -> dict[str, Any]:
    fixed = {
        str(asset_id): asset
        for asset_id, asset in assets.items()
        if asset.get("status") == "fixed"
    }
    locked = _dedupe([str(item or "").strip() for item in (locked_asset_ids or []) if str(item or "").strip()])
    excluded = _dedupe([str(item or "").strip() for item in (excluded_asset_ids or []) if str(item or "").strip()])
    eligible = [asset_id for asset_id in fixed if asset_id not in set(excluded)]
    locked_fixed = [asset_id for asset_id in locked if asset_id in fixed and asset_id not in set(excluded)]
    blocked_locks = [asset_id for asset_id in locked if asset_id not in locked_fixed]
    return {
        "schema_version": "afs_asset_continuity_context.v0.1",
        "algorithm_id": ALGORITHM_ID,
        "context_eligible_asset_ids": eligible,
        "locked_fixed_asset_ids": locked_fixed,
        "blocked_lock_asset_ids": blocked_locks,
        "excluded_asset_ids": excluded,
        "asset_state_counts": {
            "fixed": len([asset for asset in assets.values() if asset.get("status") == "fixed"]),
            "draft": len([asset for asset in assets.values() if asset.get("status") == "draft"]),
            "rejected": len([asset for asset in assets.values() if asset.get("status") == "rejected"]),
            "retired": len([asset for asset in assets.values() if asset.get("status") == "retired"]),
        },
        "continuity_policy": {
            "draft_assets_enter_context": False,
            "rejected_assets_enter_context": False,
            "retired_assets_enter_context": False,
            "fixed_assets_require_human_confirmation": True,
        },
        "claim_boundary": "asset_continuity_context_not_durable_memory_promotion",
    }


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


__all__ = ("asset_continuity_context",)
