from __future__ import annotations
from typing import Any, Callable

from apps.api.runtime_studio_state_safe_text import has_media_filename_fragment
from apps.api.runtime_store import safe_id
from apps.api.runtime_studio_state_storyboard import production_graph_review, production_graph_snapshot, source_evidence_refs, visual_assets


TextSanitizer = Callable[[Any, str, int], str]
NumberSanitizer = Callable[[Any, float], float]
PreviewUrlSanitizer = Callable[..., str]


def structured_shot(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "shot_id": text(value.get("shot_id"), "shot_01", 80),
        "index": int(max(0, min(9999, number(value.get("index"), 0)))),
        "duration": text(value.get("duration"), "", 40),
        "description": text(value.get("description"), "", 3000),
        "shot_size": text(value.get("shot_size"), "", 120),
        "light_atmosphere": text(value.get("light_atmosphere"), "", 500),
        "camera_motion": text(value.get("camera_motion"), "", 500),
        "dialogue": text(value.get("dialogue"), "", 1000),
        "sound": text(value.get("sound"), "", 500),
        "asset_refs": asset_refs(value.get("asset_refs"), text=text),
        "source_text": text(value.get("source_text"), "", 3000),
    }


def asset_refs(value: Any, *, text: TextSanitizer) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        label = text(item.get("label"), "", 80)
        if not label:
            continue
        refs.append(
            {
                "label": label,
                "asset_id": safe_id(text(item.get("asset_id"), "", 160)),
                "asset_type": asset_type(item.get("asset_type")),
                "status": text(item.get("status"), "candidate", 40),
                "source": text(item.get("source"), "unknown", 40),
            }
        )
        if len(refs) >= 24:
            break
    return refs


def asset_card_draft(value: Any, *, text: TextSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "card_id": text(value.get("card_id"), "", 160),
        "asset_type": asset_type(value.get("asset_type")),
        "label": text(value.get("label"), "", 80),
        "status": text(value.get("status"), "draft", 40),
        "source": text(value.get("source"), "", 80),
        "source_script_node_id": text(value.get("source_script_node_id"), "", 120),
        "source_shot_id": text(value.get("source_shot_id"), "", 120),
        "source_asset_ref": asset_ref(value.get("source_asset_ref"), text=text),
        "role_in_shot": text(value.get("role_in_shot"), "", 500),
        "signature": text(value.get("signature"), "", 500),
        "feature_card": text_map(value.get("feature_card"), text=text, max_items=32, max_length=1000),
        "negative_locks": text_list(value.get("negative_locks"), text=text, max_items=32, max_length=500),
        "evidence_text": text(value.get("evidence_text"), "", 1000),
        "memory_policy": safe_object(value.get("memory_policy"), text=text, max_items=12),
        "created_at": text(value.get("created_at"), "", 80),
        "updated_at": text(value.get("updated_at"), "", 80),
        "user_edited_text": text(value.get("user_edited_text"), "", 5000),
        "updated_by_user": bool(value.get("updated_by_user")),
    }


def asset_card_revision(value: Any, *, text: TextSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    references: list[dict[str, Any]] = []
    source_refs = value.get("reference_assets") if isinstance(value.get("reference_assets"), list) else []
    for index, item in enumerate(source_refs):
        if not isinstance(item, dict):
            continue
        asset_id = safe_id(text(item.get("asset_id") or item.get("assetId"), "", 120))
        if not asset_id:
            continue
        role = text(item.get("role"), "identity_layout_anchor" if index == 0 else "secondary_identity_reference", 80)
        references.append({"asset_id": asset_id, "role": role, "priority": len(references) + 1, "source": text(item.get("source"), "", 80)})
        if len(references) >= 4:
            break
    changes: list[dict[str, str]] = []
    source_changes = value.get("changed_fields") if isinstance(value.get("changed_fields"), list) else []
    for item in source_changes:
        if not isinstance(item, dict):
            continue
        field = safe_id(text(item.get("field"), "", 80))
        target = text(item.get("to"), "", 240)
        if not field or not target:
            continue
        changes.append({"field": field, "label": text(item.get("label"), "", 80), "from": text(item.get("from"), "", 240), "to": target})
        if len(changes) >= 12:
            break
    return {
        "schema_version": "afs_asset_card_revision.v0.1",
        "mode": text(value.get("mode"), "text_only_revision", 80),
        "asset_type": asset_type(value.get("asset_type")),
        "asset_label": text(value.get("asset_label"), "", 80),
        "reference_assets": references,
        "changed_fields": changes,
        "preserve_locks": text_list(value.get("preserve_locks"), text=text, max_items=12, max_length=500),
        "created_at": text(value.get("created_at"), "", 80),
    }


def storyboard_breakdown(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    shots = [structured_shot(item, text=text, number=number) for item in list(value.get("shots") or [])[:80] if isinstance(item, dict)]
    result = {
        "job_id": text(value.get("job_id"), "", 120),
        "status": text(value.get("status"), "", 40),
        "mode": text(value.get("mode"), "", 80),
        "provider_calls_started": bool(value.get("provider_calls_started")),
        "shot_count": int(max(0, min(9999, number(value.get("shot_count") or len(shots), len(shots))))),
        "downstream_node_ids": text_list(value.get("downstream_node_ids"), text=text, max_items=80, max_length=120),
        "asset_node_ids": text_list(value.get("asset_node_ids"), text=text, max_items=80, max_length=120),
        "asset_nodes_created": bool(value.get("asset_nodes_created")),
        "created_at": text(value.get("created_at"), "", 80),
        "updated_at": text(value.get("updated_at"), "", 80),
        "shots": shots,
    }
    graph = production_graph_snapshot(value.get("productionGraph") or value.get("production_graph"), text=text, number=number)
    graph_artifact_id = text(
        value.get("productionGraphArtifactId") or value.get("production_graph_artifact_id"),
        "",
        180,
    )
    if graph:
        result["productionGraph"] = graph
    if graph_artifact_id:
        result["productionGraphArtifactId"] = graph_artifact_id
    return result


def keyframe_layer(value: Any, *, text: TextSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    refs = source_evidence_refs(value.get("fixed_asset_source_evidence_refs"), text=text)
    result = {
        "status": text(value.get("status"), "", 80),
        "source_script_node_id": text(value.get("source_script_node_id"), "", 120),
        "source_asset_card_node_ids": text_list(value.get("source_asset_card_node_ids"), text=text, max_items=24, max_length=120),
        "candidate_asset_card_node_ids": text_list(value.get("candidate_asset_card_node_ids"), text=text, max_items=24, max_length=120),
        "candidate_image_asset_refs": text_list(value.get("candidate_image_asset_refs"), text=text, max_items=8, max_length=120, safe=True),
        "fixed_visual_asset_ids": text_list(value.get("fixed_visual_asset_ids"), text=text, max_items=24, max_length=120, safe=True),
        "fixed_asset_source_evidence_count": int(max(0, min(99, len(refs)))),
        "fixed_asset_source_evidence_refs": refs,
        "production_graph_review": production_graph_review(value.get("production_graph_review"), text=text),
        "missing_asset_card_node_ids": text_list(value.get("missing_asset_card_node_ids"), text=text, max_items=24, max_length=120),
        "unfixed_candidate_asset_card_node_ids": text_list(value.get("unfixed_candidate_asset_card_node_ids"), text=text, max_items=24, max_length=120),
        "updated_at": text(value.get("updated_at"), "", 80),
    }
    return {key: item for key, item in result.items() if item not in ("", [], {}, None)}


def uploads(value: Any, *, project_id: str | None, preview_url: PreviewUrlSanitizer, text: TextSanitizer, number: NumberSanitizer) -> list[dict[str, Any]]:
    uploads_: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        asset_id = safe_id(text(item.get("asset_id") or item.get("assetId"), "", 120))
        filename = text(item.get("filename") or item.get("label"), "", 160)
        if has_media_filename_fragment(filename):
            filename = ""
        role = text(item.get("role"), "", 80)
        upload = {"asset_id": asset_id} if asset_id else {}
        if filename:
            upload["filename"] = filename
        if role:
            upload["role"] = role
        if item.get("preview_url"):
            upload["preview_url"] = preview_url(item.get("preview_url"), project_id=project_id)
        for key in ("width", "height"):
            size = int(max(0, min(20000, number(item.get(key), 0))))
            if size:
                upload[key] = size
        if upload["asset_id"] or upload["filename"]:
            uploads_.append(upload)
        if len(uploads_) >= 24:
            break
    return uploads_


def asset_exclusions(value: Any, *, text: TextSanitizer) -> list[dict[str, str]]:
    exclusions: list[dict[str, str]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        asset_id = safe_id(text(item.get("asset_id") or item.get("assetId"), "", 120))
        if not asset_id:
            continue
        exclusions.append({"asset_id": asset_id, "reason": text(item.get("reason"), "one_run_asset_exclusion", 120)})
        if len(exclusions) >= 24:
            break
    return exclusions


def warnings(value: Any, *, text: TextSanitizer) -> list[dict[str, str]]:
    warnings_: list[dict[str, str]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        warning = {key: text(item.get(key), "", 240) for key in ("warning_id", "asset_type", "label", "existing_asset_ids") if text(item.get(key), "", 240)}
        if warning:
            warnings_.append(warning)
        if len(warnings_) >= 12:
            break
    return warnings_


def safe_object(value: Any, *, text: TextSanitizer, number: NumberSanitizer | None = None, max_items: int = 24) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for key, item in list(value.items())[:max_items]:
        safe_key = safe_id(str(key))[:80]
        if not safe_key:
            continue
        if isinstance(item, bool) or item is None:
            result[safe_key] = item
        elif isinstance(item, (int, float)) and number:
            result[safe_key] = number(item, 0)
        elif isinstance(item, list):
            result[safe_key] = text_list(item, text=text, max_items=24, max_length=240)
        elif isinstance(item, dict):
            result[safe_key] = safe_object(item, text=text, number=number, max_items=12)
        else:
            result[safe_key] = text(item, "", 1000)
    return result


def asset_ref(value: Any, *, text: TextSanitizer) -> dict[str, Any]:
    refs = asset_refs([value] if isinstance(value, dict) else [], text=text)
    return refs[0] if refs else {}


def text_map(value: Any, *, text: TextSanitizer, max_items: int, max_length: int) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key, item in list(value.items())[:max_items]:
        safe_key = safe_id(str(key))[:80]
        safe_value = text(item, "", max_length)
        if safe_key and safe_value:
            result[safe_key] = safe_value
    return result


def text_list(value: Any, *, text: TextSanitizer, max_items: int, max_length: int, safe: bool = False) -> list[str]:
    source = value if isinstance(value, list) else []
    result: list[str] = []
    for item in source[:max_items]:
        clean = text(item, "", max_length)
        if clean:
            result.append(safe_id(clean) if safe else clean)
    return result


def asset_type(value: Any) -> str:
    clean = str(value or "").strip()
    return clean if clean in {"character", "scene", "prop", "video"} else "character"


__all__ = (
    "asset_card_revision",
    "asset_card_draft",
    "asset_exclusions",
    "asset_refs",
    "keyframe_layer",
    "safe_object",
    "storyboard_breakdown",
    "structured_shot",
    "text_list",
    "uploads",
    "visual_assets",
    "warnings",
)
