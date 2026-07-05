from __future__ import annotations

import re
from typing import Any, Callable

from apps.api.runtime_store import safe_id


TextSanitizer = Callable[[Any, str, int], str]
NumberSanitizer = Callable[[Any, float], float]

KEYFRAME_CONSTRAINT_SCHEMA_VERSION = "afs_keyframe_constraints.v0.1"
KEYFRAME_CONSTRAINT_SECTIONS = {
    "character", "scene", "object", "camera", "lighting", "motion", "negative", "fixed_asset", "local_reference"
}
KEYFRAME_PROVIDER_SECTIONS = {"character", "scene", "object", "camera", "lighting", "motion", "negative"}
UNSAFE_CONSTRAINT_TEXT_RE = re.compile(
    r"(?:"
    r"\bdata:[^\s\"'<>]+|"
    r"https?://[^\s\"'<>]+|"
    r"\b[A-Za-z]:\\[^\s\"'<>]+|"
    r"\b[A-Za-z]:[^\s\"'<>]+|"
    r"/(?:home|Users|mnt|var|tmp|opt)/[^\s\"'<>]+|"
    r"\b(?:raw[_ -]?provider[_ -]?response|provider[_ -]?raw[_ -]?response|"
    r"signed[_ -]?url|data[_ -]?base64|media[_ -]?bytes|token|secret|api[_ -]?key|cookie)\b|"
    r"\b(?:iVBORw0KGgo|/9j/|R0lGOD|UklGR|AAAAGGZ0eXB|JVBERi0)[A-Za-z0-9+/=]{8,}\b|"
    r"\b[A-Za-z0-9+/]{96,}={0,2}\b"
    r")",
    re.IGNORECASE,
)


def keyframe_constraints(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(value.get("rows") if isinstance(value.get("rows"), list) else []):
        if not isinstance(item, dict):
            continue
        row = _keyframe_constraint_row(item, index=index, text=text, number=number)
        if row:
            rows.append(row)
        if len(rows) >= 80:
            break
    if not rows:
        return {}
    return {
        "schema_version": KEYFRAME_CONSTRAINT_SCHEMA_VERSION,
        "updated_at": _safe_constraint_text(value.get("updated_at"), text=text, limit=80),
        "rows": rows,
    }


def _keyframe_constraint_row(
    item: dict[str, Any],
    *,
    index: int,
    text: TextSanitizer,
    number: NumberSanitizer,
) -> dict[str, Any]:
    section = _keyframe_constraint_section(item.get("section"))
    projection = _keyframe_constraint_projection(item.get("projection"), section=section)
    row_text = _safe_constraint_text(item.get("text"), text=text, limit=700)
    asset_id = _safe_constraint_id(item.get("asset_id") or item.get("assetId"), text=text, limit=120)
    label = _safe_constraint_text(item.get("label"), text=text, limit=120)
    note = _safe_constraint_text(item.get("note"), text=text, limit=240)
    if not any([row_text, asset_id, label, note]):
        return {}
    row: dict[str, Any] = {
        "id": _safe_constraint_id(item.get("id"), text=text, limit=80) or f"kc_{index + 1}",
        "section": section,
        "text": row_text,
        "enabled": item.get("enabled") is not False,
        "order": int(max(0, min(9999, number(item.get("order"), index)))),
        "projection": projection,
    }
    if asset_id:
        row["asset_id"] = asset_id
    if label:
        row["label"] = label
    if note:
        row["note"] = note
    return {key: value for key, value in row.items() if value not in ("", [], {}, None)}


def _keyframe_constraint_section(value: Any) -> str:
    section = str(value or "").strip()
    return section if section in KEYFRAME_CONSTRAINT_SECTIONS else "local_reference"


def _keyframe_constraint_projection(value: Any, *, section: str) -> str:
    if section not in KEYFRAME_PROVIDER_SECTIONS:
        return "audit_only"
    return "audit_only" if str(value or "").strip() == "audit_only" else "provider"


def _safe_constraint_id(value: Any, *, text: TextSanitizer, limit: int) -> str:
    raw = str(value or "").strip()
    if not raw or UNSAFE_CONSTRAINT_TEXT_RE.search(raw):
        return ""
    return safe_id(text(raw, "", limit))


def _safe_constraint_text(value: Any, *, text: TextSanitizer, limit: int) -> str:
    raw = str(value or "").strip()
    if not raw or UNSAFE_CONSTRAINT_TEXT_RE.search(raw):
        return ""
    return text(raw, "", limit)


__all__ = ("keyframe_constraints",)
