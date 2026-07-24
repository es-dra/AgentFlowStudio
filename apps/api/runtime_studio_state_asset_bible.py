from __future__ import annotations

from typing import Any, Callable

from apps.api.runtime_store import safe_id


TextSanitizer = Callable[[Any, str, int], str]
NumberSanitizer = Callable[[Any, float], float]

ASSET_TYPES = {"character", "scene", "prop", "wardrobe", "continuity_object"}
ASSET_STATES = {"candidate", "approved", "rejected", "split", "merged"}
BIBLE_STATES = {"empty", "candidate_review", "locked"}


def sanitize_asset_bible(
    value: Any,
    *,
    text: TextSanitizer,
    number: NumberSanitizer,
    reject_forbidden: Callable[[Any], None],
) -> dict[str, Any]:
    data = value if isinstance(value, dict) else {}
    if not data:
        return {}
    if data.get("schema_version") != "afs.asset_bible.v0.1":
        raise ValueError("asset Bible schema is invalid")
    reject_forbidden(data)
    assets = [_asset(item, text=text, number=number) for item in _list(data.get("assets"))[:96]]
    assets = [item for item in assets if item]
    revisions = [_revision(item, text=text, number=number) for item in _list(data.get("revisions"))[-24:]]
    revisions = [item for item in revisions if item]
    candidate_set = data.get("candidate_set") if isinstance(data.get("candidate_set"), dict) else {}
    status = text(data.get("status"), "empty", 40)
    if status not in BIBLE_STATES:
        status = "empty"
    authority_mode = text(data.get("authority_mode"), "legacy_studio_adapter", 48)
    if authority_mode not in {"legacy_studio_adapter", "canonical_production_graph"}:
        authority_mode = "legacy_studio_adapter"
    result = {
        "schema_version": "afs.asset_bible.v0.1",
        "authority_mode": authority_mode,
        "status": status,
        "version": max(0, int(number(data.get("version"), 0))),
        "candidate_set": {
            "candidate_set_id": _id(candidate_set.get("candidate_set_id")),
            "version": max(0, int(number(candidate_set.get("version"), 0))),
            "source_node_id": _id(candidate_set.get("source_node_id")),
            "script_revision_id": _id(candidate_set.get("script_revision_id")),
            "shot_candidate_id": _id(candidate_set.get("shot_candidate_id")),
            "scene_count": max(0, int(number(candidate_set.get("scene_count"), 0))),
            "shot_count": max(0, int(number(candidate_set.get("shot_count"), 0))),
            "source_digest": _digest(candidate_set.get("source_digest")),
            "created_at": text(candidate_set.get("created_at"), "", 80),
        },
        "assets": assets,
        "revisions": revisions,
        "current_revision_id": _id(data.get("current_revision_id")),
        "locked_revision_id": _id(data.get("locked_revision_id")),
        "locked_at": text(data.get("locked_at"), "", 80),
        "last_receipt": _receipt(data.get("last_receipt"), text=text, number=number),
        "idempotency_keys": [_id(item) for item in _list(data.get("idempotency_keys"))[-40:] if _id(item)],
        "provider_dispatch_count": 0,
        "external_cost_usd": 0,
    }
    return result


def _asset(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    data = value if isinstance(value, dict) else {}
    stable_id = _id(data.get("stable_id"))
    asset_type = text(data.get("asset_type"), "", 40)
    if not stable_id or asset_type not in ASSET_TYPES:
        return {}
    review_state = text(data.get("review_state"), "candidate", 32)
    if review_state not in ASSET_STATES:
        review_state = "candidate"
    occurrences = data.get("occurrences") if isinstance(data.get("occurrences"), dict) else {}
    return {
        "stable_id": stable_id,
        "asset_type": asset_type,
        "display_name": text(data.get("display_name"), "待确认资产", 120),
        "aliases": _texts(data.get("aliases"), text=text, limit=20, length=120),
        "review_state": review_state,
        "confidence": max(0.0, min(1.0, number(data.get("confidence"), 0))),
        "needs_confirmation": data.get("needs_confirmation") is not False,
        "occurrences": {
            "scene_ids": _ids(occurrences.get("scene_ids"), 80),
            "shot_ids": _ids(occurrences.get("shot_ids"), 160),
        },
        "continuity_states": [
            {
                "state_id": _id(item.get("state_id")),
                "label": text(item.get("label"), "连续性待确认", 120),
                "status": text(item.get("status"), "pending_confirmation", 40),
                "scene_ids": _ids(item.get("scene_ids"), 80),
                "shot_ids": _ids(item.get("shot_ids"), 160),
            }
            for item in _list(data.get("continuity_states"))[:16]
            if isinstance(item, dict) and _id(item.get("state_id"))
        ],
        "positive_traits": _texts(data.get("positive_traits"), text=text, limit=24, length=160),
        "negative_locks": _texts(data.get("negative_locks"), text=text, limit=24, length=160),
        "pending_fields": _texts(data.get("pending_fields"), text=text, limit=24, length=80),
        "source_evidence": [
            {
                "source_type": text(item.get("source_type"), "script", 40),
                "source_id": _id(item.get("source_id")),
                "excerpt": text(item.get("excerpt"), "", 240),
            }
            for item in _list(data.get("source_evidence"))[:12]
            if isinstance(item, dict)
        ],
        "lineage": {
            "parent_ids": _ids(data.get("lineage", {}).get("parent_ids") if isinstance(data.get("lineage"), dict) else [], 16),
            "merged_from_ids": _ids(data.get("lineage", {}).get("merged_from_ids") if isinstance(data.get("lineage"), dict) else [], 16),
        },
    }


def _revision(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    data = value if isinstance(value, dict) else {}
    revision_id = _id(data.get("revision_id"))
    if not revision_id:
        return {}
    return {
        "revision_id": revision_id,
        "version": max(0, int(number(data.get("version"), 0))),
        "status": text(data.get("status"), "candidate_review", 40),
        "created_at": text(data.get("created_at"), "", 80),
        "command_type": text(data.get("command_type"), "", 40),
        "asset_snapshot": [
            {
                "stable_id": _id(item.get("stable_id")),
                "display_name": text(item.get("display_name"), "", 120),
                "asset_type": text(item.get("asset_type"), "", 40),
                "review_state": text(item.get("review_state"), "candidate", 32),
            }
            for item in _list(data.get("asset_snapshot"))[:96]
            if isinstance(item, dict) and _id(item.get("stable_id"))
        ],
    }


def _receipt(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    data = value if isinstance(value, dict) else {}
    if not data:
        return {}
    return {
        "receipt_id": _id(data.get("receipt_id")),
        "command_type": text(data.get("command_type"), "", 40),
        "status": text(data.get("status"), "confirmed", 32),
        "summary": text(data.get("summary"), "", 360),
        "confirmed_at": text(data.get("confirmed_at"), "", 80),
        "version": max(0, int(number(data.get("version"), 0))),
        "impact_scene_count": max(0, int(number(data.get("impact_scene_count"), 0))),
        "impact_shot_count": max(0, int(number(data.get("impact_shot_count"), 0))),
        "provider_dispatch_count": 0,
        "external_cost_usd": 0,
    }


def _id(value: Any) -> str:
    raw = str(value or "").strip()
    return safe_id(raw) if raw else ""


def _digest(value: Any) -> str:
    raw = str(value or "").strip().lower()
    return raw if len(raw) == 64 and all(ch in "0123456789abcdef" for ch in raw) else ""


def _ids(value: Any, limit: int) -> list[str]:
    return [item for item in (_id(raw) for raw in _list(value)[:limit]) if item]


def _texts(value: Any, *, text: TextSanitizer, limit: int, length: int) -> list[str]:
    return [item for item in (text(raw, "", length).strip() for raw in _list(value)[:limit]) if item]


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = ("sanitize_asset_bible",)
