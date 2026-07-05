from __future__ import annotations

from typing import Any, Callable

from apps.api.runtime_store import safe_id


TextSanitizer = Callable[[Any, str, int], str]
NumberSanitizer = Callable[[Any, float], float]


def sanitize_keyframe_local_edit_draft(
    value: Any,
    *,
    text: TextSanitizer,
    number: NumberSanitizer,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result = {
        "schema_version": text(value.get("schema_version"), "afs_keyframe_local_edit_draft.v0.1", 80),
        "request": _request(value.get("request"), text=text, number=number),
        "preflight": _preflight(value.get("preflight"), text=text),
        "availability": sanitize_local_edit_availability(value.get("availability"), text=text),
    }
    return {key: item for key, item in result.items() if item not in ({}, [], "")}


def sanitize_local_edit_availability(value: Any, *, text: TextSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result = {
        "status": text(value.get("status"), "", 80),
        "required_capability": text(value.get("required_capability"), "", 120),
        "reason": text(value.get("reason"), "", 120),
        "user_message": text(value.get("user_message"), "", 500),
    }
    return {key: item for key, item in result.items() if item not in ({}, [], "")}


def _request(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result = {
        "schema_version": text(value.get("schema_version"), "afs_keyframe_local_edit_request.v0.1", 80),
        "request_id": safe_id(text(value.get("request_id"), "", 160)),
        "target_node_id": safe_id(text(value.get("target_node_id"), "", 160)),
        "parent_lineage": _parent_lineage(value.get("parent_lineage"), text=text),
        "edit_intent": text(value.get("edit_intent"), "", 500),
        "edit_scope": _edit_scope(value.get("edit_scope"), text=text, number=number),
        "preserve_locks": _text_list(value.get("preserve_locks"), text=text, max_items=12, max_length=120),
        "negative_locks": _text_list(value.get("negative_locks"), text=text, max_items=12, max_length=120),
        "fallback_policy": _fallback_policy(value.get("fallback_policy"), text=text),
        "provider_capability_mode": _provider_mode(value.get("provider_capability_mode"), text=text),
        "created_at": text(value.get("created_at"), "", 80),
        "updated_at": text(value.get("updated_at"), "", 80),
    }
    return {key: item for key, item in result.items() if item not in ({}, [], "")}


def _preflight(value: Any, *, text: TextSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result = {
        "schema_version": text(value.get("schema_version"), "afs_keyframe_local_edit_preflight.v0.1", 80),
        "request_id": safe_id(text(value.get("request_id"), "", 160)),
        "contract_status": text(value.get("contract_status"), "", 120),
        "execution_status": text(value.get("execution_status"), "", 120),
        "provider_calls_started": bool(value.get("provider_calls_started")),
        "local_transformation_started": bool(value.get("local_transformation_started")),
        "generated_media_created": bool(value.get("generated_media_created")),
        "fallback_full_frame_edit": bool(value.get("fallback_full_frame_edit")),
        "local_edit_truth_label": text(value.get("local_edit_truth_label"), "", 120),
        "blocking_capability": text(value.get("blocking_capability"), "", 120),
        "blockers": _blockers(value.get("blockers"), text=text),
        "allowed_next_actions": _text_list(value.get("allowed_next_actions"), text=text, max_items=8, max_length=120),
        "non_claims": _text_list(value.get("non_claims"), text=text, max_items=12, max_length=120),
    }
    return {key: item for key, item in result.items() if item not in ({}, [], "")}


def _parent_lineage(value: Any, *, text: TextSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "immutable_parent": bool(value.get("immutable_parent", True)),
        "parent_node_id": safe_id(text(value.get("parent_node_id"), "", 160)),
        "parent_keyframe_job_id": safe_id(text(value.get("parent_keyframe_job_id"), "", 160)),
        "parent_image_asset_id": safe_id(text(value.get("parent_image_asset_id"), "", 160)),
        "parent_candidate_id": safe_id(text(value.get("parent_candidate_id"), "", 160)),
        "parent_preview_url_present": bool(value.get("parent_preview_url_present")),
    }


def _edit_scope(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    kind = text(value.get("kind"), "semantic_region", 80)
    if kind not in {"mask_asset", "bbox", "polygon", "semantic_region"}:
        kind = "semantic_region"
    result = {
        "kind": kind,
        "target_description": text(value.get("target_description"), "", 240),
        "mask_asset_id": safe_id(text(value.get("mask_asset_id"), "", 120)),
        "bbox": _bbox(value.get("bbox"), number=number),
        "polygon": _polygon(value.get("polygon"), number=number),
    }
    return {key: item for key, item in result.items() if item not in ({}, [], "", None)}


def _bbox(value: Any, *, number: NumberSanitizer) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    result = {key: max(0, min(1, number(value.get(key), 0))) for key in ("x", "y", "width", "height")}
    return result if any(result.values()) else None


def _polygon(value: Any, *, number: NumberSanitizer) -> list[dict[str, float]]:
    points = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        points.append({"x": max(0, min(1, number(item.get("x"), 0))), "y": max(0, min(1, number(item.get("y"), 0)))})
        if len(points) >= 16:
            break
    return points


def _fallback_policy(value: Any, *, text: TextSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "allow_full_frame_fallback": bool(value.get("allow_full_frame_fallback")),
        "fallback_truth_label": text(value.get("fallback_truth_label"), "not_allowed_in_first_slice", 120),
        "user_confirmation_required": bool(value.get("user_confirmation_required", True)),
    }


def _blockers(value: Any, *, text: TextSanitizer) -> list[dict[str, Any]]:
    blockers = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        blockers.append(
            {
                "code": safe_id(text(item.get("code"), "", 120)),
                "reason": text(item.get("reason"), "", 500),
                "provider_calls_started": bool(item.get("provider_calls_started")),
                "local_transformation_started": bool(item.get("local_transformation_started")),
                "generated_media_created": bool(item.get("generated_media_created")),
            }
        )
        if len(blockers) >= 8:
            break
    return [item for item in blockers if item["code"] or item["reason"]]


def _text_list(value: Any, *, text: TextSanitizer, max_items: int, max_length: int) -> list[str]:
    result = []
    for item in value if isinstance(value, list) else []:
        clean = text(item, "", max_length)
        if clean:
            result.append(clean)
        if len(result) >= max_items:
            break
    return result


def _provider_mode(value: Any, *, text: TextSanitizer) -> str:
    clean = text(value, "no_provider_execution", 80)
    return clean if clean == "no_provider_execution" else "no_provider_execution"


__all__ = ("sanitize_keyframe_local_edit_draft", "sanitize_local_edit_availability")
