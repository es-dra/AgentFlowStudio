from __future__ import annotations

from typing import Any


TOTAL_PROMPT_BUDGET = 1500


def context_budget(visible_prompt: str, text: dict[str, str]) -> dict[str, Any]:
    allocations = {
        "visible_prompt": 550,
        "lock_identity": 400,
        "scene_director": 250,
        "upstream_summary": 150,
        "preference": 100,
    }
    values = {
        "visible_prompt": visible_prompt,
        "lock_identity": text.get("asset_identity_segment", ""),
        "scene_director": text.get("scene_director_segment", ""),
        "upstream_summary": text.get("upstream_summary_segment", ""),
        "preference": text.get("preference_segment", ""),
    }
    return {
        "unit": "characters",
        "total_limit": TOTAL_PROMPT_BUDGET,
        "segments": {
            name: {"allocated": allocations[name], "used": len(value), "truncated": len(value) > allocations[name]}
            for name, value in values.items()
        },
        "visible_prompt_floor": 550,
        "lock_identity_never_truncate": True,
        "truncation_order": ["preference", "upstream_summary", "scene_director", "visible_prompt_above_floor", "lock_identity_never"],
    }


def context_warnings(
    assets: dict[str, dict[str, Any]],
    refs: dict[str, dict[str, Any]],
    prompt: str,
    overrides: set[tuple[str, str]],
) -> list[dict[str, str]]:
    prompt_fold = prompt.casefold()
    warnings: list[dict[str, str]] = []
    for asset_id, asset in sorted(assets.items()):
        label = str(asset.get("label") or "")
        if label and label.casefold() in prompt_fold and asset_id not in refs:
            warnings.append({"warning_id": "named_asset_not_connected", "asset_id": asset_id, "label": label})
        for lock in asset.get("negative_locks", []):
            if (asset_id, str(lock)) in overrides:
                continue
            if "black short hair" in str(lock).casefold() and "red long hair" in prompt_fold:
                warnings.append({"warning_id": "best_effort_lock_conflict", "asset_id": asset_id, "lock_text": str(lock)})
    return warnings


def duplicate_labels(assets: list[dict[str, Any]]) -> list[dict[str, str]]:
    seen: dict[tuple[str, str], str] = {}
    duplicates: list[dict[str, str]] = []
    for asset in assets:
        key = (str(asset.get("asset_type")), str(asset.get("label")).casefold())
        if key in seen:
            duplicates.append(
                {
                    "asset_type": key[0],
                    "label": str(asset.get("label")),
                    "first_asset_id": seen[key],
                    "asset_id": str(asset.get("asset_id")),
                }
            )
        else:
            seen[key] = str(asset.get("asset_id"))
    return duplicates


__all__ = ("context_budget", "context_warnings", "duplicate_labels")
