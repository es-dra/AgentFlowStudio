from __future__ import annotations

from typing import Any, Callable

from apps.api.runtime_store import safe_id


TextSanitizer = Callable[[Any, str, int], str]
NumberSanitizer = Callable[[Any, float], float]

ASSET_TYPES = {"character", "scene", "prop", "wardrobe", "continuity_object"}
ASSET_STATES = {"candidate", "approved", "rejected", "superseded"}
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
    required_occurrences = [
        item
        for item in (
            _required_occurrence(value, text=text)
            for value in _list(data.get("required_occurrences"))[:512]
        )
        if item
    ]
    requirement_ids = {item["requirement_id"] for item in required_occurrences}
    occurrence_resolutions = [
        item
        for item in (
            _occurrence_resolution(value, text=text)
            for value in _list(data.get("occurrence_resolutions"))[:512]
        )
        if item and item["requirement_id"] in requirement_ids
    ]
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
            "scene_index": [
                {
                    "scene_id": _id(item.get("scene_id")),
                    "name": text(item.get("name"), "场景", 120),
                    "number": max(1, int(number(item.get("number"), index + 1))),
                }
                for index, item in enumerate(_list(candidate_set.get("scene_index"))[:80])
                if isinstance(item, dict) and _id(item.get("scene_id"))
            ],
            "shot_index": [
                {
                    "shot_id": _id(item.get("shot_id")),
                    "scene_id": _id(item.get("scene_id")),
                    "title": text(item.get("title"), "镜头", 120),
                    "number": max(1, int(number(item.get("number"), index + 1))),
                    "description": text(item.get("description"), "", 600),
                    "purpose": text(item.get("purpose"), "", 400),
                    "shot_size": text(item.get("shot_size"), "", 80),
                    "composition": text(item.get("composition"), "", 240),
                    "camera_angle": text(item.get("camera_angle"), "", 160),
                    "movement": text(item.get("movement"), "", 240),
                    "action": text(item.get("action"), "", 400),
                    "dialogue": text(item.get("dialogue"), "", 400),
                    "emotion": text(item.get("emotion"), "", 240),
                    "continuity_cues": _texts(
                        item.get("continuity_cues"),
                        text=text,
                        limit=16,
                        length=240,
                    ),
                }
                for index, item in enumerate(_list(candidate_set.get("shot_index"))[:240])
                if isinstance(item, dict) and _id(item.get("shot_id"))
            ],
            "required_asset_anchors": [
                {
                    "anchor_id": _id(item.get("anchor_id")),
                    "source_asset_id": _id(item.get("source_asset_id")),
                    "asset_type": text(item.get("asset_type"), "", 40),
                    "display_name": text(item.get("display_name"), "待确认资产", 120),
                    "aliases": _texts(item.get("aliases"), text=text, limit=20, length=120),
                    "scene_ids": _ids(item.get("scene_ids"), 80),
                    "shot_ids": _ids(item.get("shot_ids"), 160),
                    "ambiguity": text(item.get("ambiguity"), "", 64),
                }
                for item in _list(candidate_set.get("required_asset_anchors"))[:96]
                if isinstance(item, dict)
                and _id(item.get("anchor_id"))
                and text(item.get("asset_type"), "", 40) in ASSET_TYPES
            ],
            "recognition_ambiguities": [
                {
                    "code": text(item.get("code"), "recognition_ambiguity", 64),
                    "asset_type": text(item.get("asset_type"), "", 40),
                    "labels": _texts(item.get("labels"), text=text, limit=8, length=120),
                    "message": text(item.get("message"), "资产别名关系需要人工确认。", 240),
                }
                for item in _list(candidate_set.get("recognition_ambiguities"))[:32]
                if isinstance(item, dict)
            ],
            "source_digest": _digest(candidate_set.get("source_digest")),
            "created_at": text(candidate_set.get("created_at"), "", 80),
        },
        "assets": assets,
        "required_occurrences": required_occurrences,
        "occurrence_resolutions": occurrence_resolutions,
        "resolution_ledger": [
            item
            for item in (
                _ledger_item(value, text=text)
                for value in _list(data.get("resolution_ledger"))[:512]
            )
            if item and item["requirement_id"] in requirement_ids
        ],
        "coverage": _coverage(data.get("coverage"), number=number),
        "recognition_quality": _recognition_quality(
            data.get("recognition_quality"),
            text=text,
            number=number,
        ),
        "recognition_delta": {
            key: _ids(
                data.get("recognition_delta", {}).get(key)
                if isinstance(data.get("recognition_delta"), dict)
                else [],
                96,
            )
            for key in (
                "added_asset_ids",
                "merged_asset_ids",
                "retained_asset_ids",
                "history_asset_ids",
            )
        },
        "art_direction": _art_direction(data.get("art_direction"), text=text),
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
        "visual_identity": text(data.get("visual_identity"), "", 600),
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
                "scene_ids": _ids(item.get("scene_ids"), 80),
                "shot_ids": _ids(item.get("shot_ids"), 160),
            }
            for item in _list(data.get("source_evidence"))[:12]
            if isinstance(item, dict)
        ],
        "lineage": {
            "parent_ids": _ids(data.get("lineage", {}).get("parent_ids") if isinstance(data.get("lineage"), dict) else [], 16),
            "merged_from_ids": _ids(data.get("lineage", {}).get("merged_from_ids") if isinstance(data.get("lineage"), dict) else [], 16),
        },
        "superseded_by_ids": _ids(data.get("superseded_by_ids"), 16),
    }


def _art_direction(value: Any, *, text: TextSanitizer) -> dict[str, Any]:
    data = value if isinstance(value, dict) else {}
    fields = {
        "visual_style": text(data.get("visual_style"), "", 240),
        "medium": text(data.get("medium"), "", 240),
        "palette": text(data.get("palette"), "", 240),
        "lighting": text(data.get("lighting"), "", 240),
    }
    complete = all(fields.values())
    return {
        **fields,
        "status": "confirmed" if complete and data.get("status") == "confirmed" else "pending",
        "source": "human_review" if data.get("source") == "human_review" else "",
        "confirmed_at": text(data.get("confirmed_at"), "", 80) if complete else "",
    }


def _required_occurrence(value: Any, *, text: TextSanitizer) -> dict[str, Any]:
    data = value if isinstance(value, dict) else {}
    requirement_id = _id(data.get("requirement_id"))
    source_asset_id = _id(data.get("source_asset_id"))
    occurrence_kind = text(data.get("occurrence_kind"), "", 16)
    occurrence_id = _id(data.get("occurrence_id"))
    asset_type = text(data.get("asset_type"), "", 40)
    if (
        not requirement_id
        or not source_asset_id
        or occurrence_kind not in {"scene", "shot"}
        or not occurrence_id
        or asset_type not in ASSET_TYPES
    ):
        return {}
    return {
        "requirement_id": requirement_id,
        "source_asset_id": source_asset_id,
        "asset_type": asset_type,
        "occurrence_kind": occurrence_kind,
        "occurrence_id": occurrence_id,
    }


def _occurrence_resolution(value: Any, *, text: TextSanitizer) -> dict[str, Any]:
    data = value if isinstance(value, dict) else {}
    requirement_id = _id(data.get("requirement_id"))
    resolution = text(data.get("resolution"), "assigned", 24)
    if not requirement_id or resolution not in {"assigned", "not_needed"}:
        return {}
    return {
        "requirement_id": requirement_id,
        "resolution": resolution,
        "assigned_asset_id": _id(data.get("assigned_asset_id")),
        "reason": text(data.get("reason"), "", 240),
    }


def _ledger_item(value: Any, *, text: TextSanitizer) -> dict[str, Any]:
    base = _required_occurrence(value, text=text)
    if not base:
        return {}
    data = value if isinstance(value, dict) else {}
    status = text(data.get("status"), "pending", 24)
    if status not in {"approved", "pending", "rejected", "superseded", "orphaned", "not_needed"}:
        status = "pending"
    return {
        **base,
        "resolution": text(data.get("resolution"), "assigned", 24),
        "assigned_asset_id": _id(data.get("assigned_asset_id")),
        "reason": text(data.get("reason"), "", 240),
        "status": status,
        "resolved": data.get("resolved") is True,
    }


def _coverage(value: Any, *, number: NumberSanitizer) -> dict[str, Any]:
    data = value if isinstance(value, dict) else {}
    keys = (
        "scene_total",
        "scene_covered",
        "shot_total",
        "shot_covered",
        "asset_shot_covered",
        "missing_source_evidence_shot_count",
        "required_occurrence_total",
        "resolved_required",
        "unresolved_required",
        "unresolved_scene_count",
        "unresolved_shot_count",
        "alias_collision_count",
        "missing_anchor_count",
        "orphan_scene_coverage_count",
        "recognition_ambiguity_count",
        "quality_issue_count",
    )
    result = {key: max(0, int(number(data.get(key), 0))) for key in keys}
    result["unresolved_asset_ids"] = _ids(data.get("unresolved_asset_ids"), 96)
    result["coverage_pass"] = data.get("coverage_pass") is True
    result["quality_pass"] = data.get("quality_pass") is True
    return result


def _recognition_quality(
    value: Any,
    *,
    text: TextSanitizer,
    number: NumberSanitizer,
) -> dict[str, Any]:
    data = value if isinstance(value, dict) else {}
    status = text(data.get("status"), "blocked", 24)
    if status not in {"pass", "blocked"}:
        status = "blocked"
    return {
        "status": status,
        "issues": [
            {
                "code": text(item.get("code"), "recognition_quality_issue", 64),
                "asset_type": text(item.get("asset_type"), "", 40),
                "display_name": text(item.get("display_name"), "待确认资产", 120),
                "scene_count": max(0, int(number(item.get("scene_count"), 0))),
                "shot_count": max(0, int(number(item.get("shot_count"), 0))),
                "message": text(item.get("message"), "资产识别需要复核。", 240),
                "action": text(item.get("action"), "重新识别或人工修复", 160),
            }
            for item in _list(data.get("issues"))[:64]
            if isinstance(item, dict)
        ],
        "missing_anchor_count": max(0, int(number(data.get("missing_anchor_count"), 0))),
        "orphan_scene_coverage_count": max(
            0, int(number(data.get("orphan_scene_coverage_count"), 0))
        ),
        "alias_collision_count": max(0, int(number(data.get("alias_collision_count"), 0))),
        "recognition_ambiguity_count": max(
            0, int(number(data.get("recognition_ambiguity_count"), 0))
        ),
        "missing_source_evidence_shot_count": max(
            0, int(number(data.get("missing_source_evidence_shot_count"), 0))
        ),
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
