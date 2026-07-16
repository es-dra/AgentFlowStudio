from __future__ import annotations

from typing import Any


def attach_fixed_visual_asset_refs(
    shots: list[dict[str, Any]],
    fixed_visual_assets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fixed_assets = [
        asset
        for asset in fixed_visual_assets
        if isinstance(asset, dict)
        and str(asset.get("status") or "") == "fixed"
        and str(asset.get("asset_type") or "") in {"character", "scene", "prop"}
        and str(asset.get("label") or "").strip()
        and str(asset.get("asset_id") or "").strip()
    ]
    if not fixed_assets:
        return shots
    result: list[dict[str, Any]] = []
    for shot in shots if isinstance(shots, list) else []:
        if not isinstance(shot, dict):
            result.append(shot)
            continue
        source = _shot_source_text(shot)
        refs = [ref for ref in shot.get("asset_refs", []) if isinstance(ref, dict)]
        replaced = False
        for asset in fixed_assets:
            label = str(asset.get("label") or "").strip()
            asset_type = str(asset.get("asset_type") or "").strip()
            if not _fixed_asset_label_in_text(label, source):
                continue
            fixed_ref = _fixed_asset_ref(asset, source)
            found_index = next(
                (
                    index
                    for index, ref in enumerate(refs)
                    if str(ref.get("asset_type") or "") == asset_type
                    and str(ref.get("label") or ref.get("display_name") or "") == label
                ),
                None,
            )
            if found_index is None:
                refs.append(fixed_ref)
                replaced = True
            else:
                refs[found_index] = {**refs[found_index], **fixed_ref}
                replaced = True
        result.append({**shot, "asset_refs": refs} if replaced else shot)
    return result


def _fixed_asset_ref(asset: dict[str, Any], source: str) -> dict[str, Any]:
    label = str(asset.get("label") or "").strip()
    asset_type = str(asset.get("asset_type") or "").strip()
    return {
        "label": label,
        "display_name": label,
        "asset_id": str(asset.get("asset_id") or "").strip(),
        "asset_type": asset_type,
        "status": "fixed",
        "source": "fixed_visual_asset_reuse",
        "scope": "project",
        "confidence": 0.9,
        "evidence_text": source[:240],
        "descriptive_signature": str(asset.get("signature") or label)[:240],
        "evidence_modality": "visual",
        "visual_evidence_span": source[:240],
        "name_source": "fixed_visual_asset",
        "provisional_name": False,
    }


def _shot_source_text(shot: dict[str, Any]) -> str:
    span = shot.get("source_span") if isinstance(shot.get("source_span"), dict) else {}
    return " ".join(
        str(value or "").strip()
        for value in (
            span.get("text"),
            shot.get("source_text"),
            shot.get("description"),
        )
        if str(value or "").strip()
    )


def _fixed_asset_label_in_text(label: str, text: str) -> bool:
    if not label or not text:
        return False
    return label in text


__all__ = ("attach_fixed_visual_asset_refs",)
