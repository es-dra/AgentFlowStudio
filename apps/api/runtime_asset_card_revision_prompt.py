from __future__ import annotations

from typing import Any

from apps.api.runtime_models import KeyframeGenerationRequest


def asset_card_revision_reference_instruction(request: KeyframeGenerationRequest) -> str:
    params = request.node_parameters if isinstance(request.node_parameters, dict) else {}
    revision = params.get("asset_card_revision") if isinstance(params.get("asset_card_revision"), dict) else {}
    if not revision:
        return ""
    changes = _changed_field_lines(revision)
    locks = [str(item).strip() for item in list(revision.get("preserve_locks") or [])[:8] if str(item).strip()]
    lines = [
        "Asset-card revision mode: reference image #1 is the primary visual source of truth, not optional style inspiration.",
        "The changed fields are the only editable delta; treat this as localized image editing, not text-to-image redesign.",
        "Apply only the changed asset-card details; preserve original identity, sheet layout, proportions, head shape, limbs, camera distance, neutral background, and non-edited details.",
        "Revision strength: conservative low-change pass; output should look like the same previous reference sheet after one art-director edit, not a fresh redesign.",
        "Do not turn the subject into a toy, chibi, mascot, cute round-head robot, unrelated character, or different body type unless explicitly requested.",
    ]
    if changes:
        lines.append(f"Changed fields: {'; '.join(changes)}.")
    lines.extend(_edit_policy_lines(revision))
    if locks:
        lines.append(f"Preserve locks: {'; '.join(locks)}.")
    return " ".join(lines)


def _changed_field_lines(revision: dict[str, Any]) -> list[str]:
    changes: list[str] = []
    for item in list(revision.get("changed_fields") or [])[:8]:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("field") or "field").strip()
        target = str(item.get("to") or "").strip()
        if label and target:
            changes.append(f"{label}: {target}")
    return changes


def _edit_policy_lines(revision: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for item in list(revision.get("changed_fields") or [])[:8]:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field") or "").strip()
        target = str(item.get("to") or "").casefold()
        if field == "wardrobe":
            lines.append("Wardrobe edit scope: add clothing as an outer garment layer only; do not redesign head, face screen, eyes, ear side modules, neck, chest core, mechanical limbs, hands, feet, body scale, or reference-sheet layout.")
            lines.append("Keep the robot body visible at uncovered neck, chest, hands, or legs unless explicitly hidden; clothing must not convert the robot into a human, child, monk, mascot, or different character archetype.")
        if field == "appearance":
            lines.append("Appearance edit scope: change only the named surface or recognizable detail; preserve identity, adult/humanoid scale, head-to-body ratio, joint layout, limb length, camera distance, and sheet composition.")
            if any(term in target for term in ("plush", "fur", "furry", "fabric", "毛绒", "绒", "布料", "织物")):
                lines.append("Plush/fabric material must read as a surface covering on the same existing robot frame, not as a cute toy, chibi body, stuffed doll, or new rounded robot design.")
        if field == "palette":
            lines.append("Palette edit scope: change colors only; preserve form, materials, proportions, clothing cut, lighting direction, and reference sheet layout.")
        if field == "demeanor":
            lines.append("Demeanor edit scope: change expression or mood only; preserve geometry, outfit, material, palette, and view layout.")
    return _dedupe(lines)[:8]


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


__all__ = ("asset_card_revision_reference_instruction",)
