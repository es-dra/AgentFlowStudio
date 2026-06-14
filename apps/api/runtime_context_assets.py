from __future__ import annotations

import hashlib
import json
from typing import Any

from apps.api.runtime_context_budget import duplicate_labels
from apps.api.runtime_context_subgraph import RELATION_PRIORITY
from apps.api.runtime_visual_assets import public_visual_asset


MAX_OPTIMIZE_SIGNATURES = 4
MAX_GENERATE_FULL_CHARACTER_ASSETS = 3
MAX_GENERATE_FULL_SCENE_ASSETS = 1


def optimize_asset_ids(assets: dict[str, dict[str, Any]], connected_ids: list[str], prompt: str) -> list[str]:
    selected: list[str] = []
    for asset_id in connected_ids:
        if asset_id not in selected:
            selected.append(asset_id)
    prompt_fold = prompt.casefold()
    for asset_id, asset in sorted(assets.items()):
        label = str(asset.get("label") or "").casefold()
        if label and label in prompt_fold and asset_id not in selected:
            selected.append(asset_id)
    return selected[:MAX_OPTIMIZE_SIGNATURES]


def apply_label_arbitration(
    assets: dict[str, dict[str, Any]],
    candidate_ids: list[str],
) -> tuple[list[str], list[dict[str, Any]]]:
    groups: dict[tuple[str, str], list[str]] = {}
    for asset_id in candidate_ids:
        asset = assets.get(asset_id)
        if not asset:
            continue
        key = (str(asset.get("asset_type") or ""), str(asset.get("label") or "").casefold())
        groups.setdefault(key, []).append(asset_id)

    selected_by_group: dict[tuple[str, str], str] = {}
    exclusions: list[dict[str, Any]] = []
    for key, ids in groups.items():
        unique_ids = [item for index, item in enumerate(ids) if item and item not in ids[:index]]
        if len(unique_ids) == 1:
            selected_by_group[key] = unique_ids[0]
            continue
        selected = _terminal_asset_id(assets, unique_ids)
        selected_by_group[key] = selected
        for asset_id in unique_ids:
            if asset_id == selected:
                continue
            asset = assets[asset_id]
            exclusions.append(
                {
                    "asset_id": asset_id,
                    "label": asset.get("label"),
                    "asset_type": asset.get("asset_type"),
                    "reason": "superseded_by_newer_label_version",
                    "selected_asset_id": selected,
                }
            )

    selected_ids: list[str] = []
    for asset_id in candidate_ids:
        asset = assets.get(asset_id)
        if not asset:
            continue
        key = (str(asset.get("asset_type") or ""), str(asset.get("label") or "").casefold())
        selected = selected_by_group.get(key, asset_id)
        if selected == asset_id and selected not in selected_ids:
            selected_ids.append(selected)
    return selected_ids, exclusions


def asset_detail_levels(assets: dict[str, dict[str, Any]], included_ids: list[str], mode: str) -> dict[str, str]:
    if mode != "generate":
        return {asset_id: "signature_only" for asset_id in included_ids}
    counts = {"character": 0, "scene": 0}
    limits = {"character": MAX_GENERATE_FULL_CHARACTER_ASSETS, "scene": MAX_GENERATE_FULL_SCENE_ASSETS}
    detail: dict[str, str] = {}
    for asset_id in included_ids:
        asset_type = str(assets.get(asset_id, {}).get("asset_type") or "character")
        if counts.get(asset_type, 0) < limits.get(asset_type, 0):
            detail[asset_id] = "full_card"
            counts[asset_type] = counts.get(asset_type, 0) + 1
        else:
            detail[asset_id] = "signature_only"
    return detail


def degraded_asset_exclusions(
    assets: dict[str, dict[str, Any]],
    included_ids: list[str],
    detail_levels: dict[str, str],
) -> list[dict[str, Any]]:
    degraded: list[dict[str, Any]] = []
    for asset_id in included_ids:
        if detail_levels.get(asset_id) != "signature_only":
            continue
        asset = assets.get(asset_id)
        if not asset:
            continue
        degraded.append(
            {
                "asset_id": asset_id,
                "label": asset.get("label"),
                "asset_type": asset.get("asset_type"),
                "reason": "degraded_to_signature_over_limit",
                "degraded_channel": "signature_text",
            }
        )
    return degraded


def included_asset(asset: dict[str, Any], ref: dict[str, Any] | None, mode: str, detail_level: str) -> dict[str, Any]:
    public = public_visual_asset(asset)
    public.update(
        {
            "channel": "signature_text" if mode == "optimize" else "companion_text",
            "detail_level": detail_level,
            "feature_card_hash": hash_payload(asset.get("feature_card") if isinstance(asset.get("feature_card"), dict) else {}),
            "hop": (ref or {}).get("hop"),
            "relation_type": (ref or {}).get("relation_type"),
            "connected": ref is not None,
        }
    )
    return public


def excluded_assets(
    assets: dict[str, dict[str, Any]],
    included_ids: list[str],
    refs: dict[str, dict[str, Any]],
    mode: str,
    include_fixed_assets: bool,
    extra_exclusions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    excluded: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    explicitly_excluded_asset_ids: set[str] = set()
    for item in extra_exclusions or []:
        asset_id = str(item.get("asset_id") or "")
        reason = str(item.get("reason") or "")
        if not asset_id or not reason:
            continue
        seen.add((asset_id, reason))
        explicitly_excluded_asset_ids.add(asset_id)
        excluded.append(item)
    for asset_id in sorted(refs):
        if asset_id in assets or asset_id in included_ids:
            continue
        reason = "retired_or_missing_visual_asset"
        if (asset_id, reason) in seen:
            continue
        seen.add((asset_id, reason))
        excluded.append({"asset_id": asset_id, "label": None, "asset_type": None, "reason": reason})
    for asset_id, asset in sorted(assets.items()):
        if asset_id in included_ids or asset_id in explicitly_excluded_asset_ids:
            continue
        reason = "not_selected_for_optimize" if mode == "optimize" else "not_connected_to_target"
        if mode == "generate" and not include_fixed_assets and asset_id in refs:
            reason = "fixed_assets_excluded_by_comparison_arm"
        if (asset_id, reason) in seen:
            continue
        excluded.append({"asset_id": asset_id, "label": asset.get("label"), "asset_type": asset.get("asset_type"), "reason": reason})
    return excluded


def temporary_asset_exclusion_records(
    assets: dict[str, dict[str, Any]],
    asset_ids: set[str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for asset_id in sorted(asset_ids):
        asset = assets.get(asset_id)
        records.append(
            {
                "asset_id": asset_id,
                "label": asset.get("label") if asset else None,
                "asset_type": asset.get("asset_type") if asset else None,
                "reason": "temporary_asset_excluded_by_user",
            }
        )
    return records


def available_assets(
    assets: dict[str, dict[str, Any]],
    included_ids: list[str],
    refs: dict[str, dict[str, Any]],
    prompt: str,
) -> list[dict[str, Any]]:
    prompt_fold = prompt.casefold()
    items = []
    for asset_id, asset in sorted(assets.items()):
        label = str(asset.get("label") or "")
        public = public_visual_asset(asset)
        public["connected"] = asset_id in refs
        public["injected"] = asset_id in included_ids
        public["label_matched"] = bool(label and label.casefold() in prompt_fold)
        items.append(public)
    return items


def subject_reference_asset(assets: list[dict[str, Any]], refs: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    characters = [asset for asset in assets if asset.get("asset_type") == "character" and asset.get("image_asset_refs")]
    if not characters:
        return None
    return sorted(
        characters,
        key=lambda asset: (
            refs.get(str(asset.get("asset_id")), {}).get("hop", 99),
            RELATION_PRIORITY.get(refs.get(str(asset.get("asset_id")), {}).get("relation_type", "generation"), 9),
            str(asset.get("asset_id")),
        ),
    )[0]


def reference_image_channel(
    assets: list[dict[str, Any]],
    refs: dict[str, dict[str, Any]],
    reference_image_slots: int,
) -> list[dict[str, str]]:
    if reference_image_slots <= 0:
        return []
    characters = [asset for asset in assets if asset.get("asset_type") == "character" and asset.get("image_asset_refs")]
    sorted_characters = sorted(
        characters,
        key=lambda asset: (
            refs.get(str(asset.get("asset_id")), {}).get("hop", 99),
            RELATION_PRIORITY.get(refs.get(str(asset.get("asset_id")), {}).get("relation_type", "generation"), 9),
            str(asset.get("asset_id")),
        ),
    )
    channel: list[dict[str, str]] = []
    for asset in sorted_characters:
        image_refs = [str(item) for item in list(asset.get("image_asset_refs") or []) if str(item)]
        for image_ref in image_refs:
            channel.append({"asset_id": image_ref, "visual_asset_id": str(asset["asset_id"]), "role": "subject_reference"})
            if len(channel) >= reference_image_slots:
                return channel
    return channel


def duplicate_label_candidates(assets: dict[str, dict[str, Any]], included_ids: list[str]) -> list[dict[str, Any]]:
    return duplicate_labels([assets[item] for item in included_ids if item in assets])


def hash_payload(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:16]


def _terminal_asset_id(assets: dict[str, dict[str, Any]], ids: list[str]) -> str:
    superseded = {
        str(assets[asset_id].get("supersedes_asset_id") or "")
        for asset_id in ids
        if str(assets[asset_id].get("supersedes_asset_id") or "") in ids
    }
    terminals = [asset_id for asset_id in ids if asset_id not in superseded] or ids
    return sorted(terminals, key=lambda asset_id: (_asset_recorded_at(assets[asset_id]), asset_id))[-1]


def _asset_recorded_at(asset: dict[str, Any]) -> str:
    review = asset.get("promotion_review") if isinstance(asset.get("promotion_review"), dict) else {}
    return str(review.get("server_recorded_at") or asset.get("created_at") or "")


__all__ = (
    "MAX_GENERATE_FULL_CHARACTER_ASSETS",
    "MAX_GENERATE_FULL_SCENE_ASSETS",
    "MAX_OPTIMIZE_SIGNATURES",
    "apply_label_arbitration",
    "asset_detail_levels",
    "available_assets",
    "degraded_asset_exclusions",
    "duplicate_label_candidates",
    "excluded_assets",
    "hash_payload",
    "included_asset",
    "optimize_asset_ids",
    "reference_image_channel",
    "subject_reference_asset",
    "temporary_asset_exclusion_records",
)
