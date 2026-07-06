from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from apps.api.runtime_errors import response_contains_unsafe_marker, safe_error_detail
from apps.api.runtime_logging import (
    client_request_id_from_request,
    log_business_event,
    request_id_from_request,
    studio_node_id_from_request,
    studio_node_type_from_request,
    user_action_from_request,
)
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload


KEYFRAME_LOCAL_EDIT_REQUEST_SCHEMA = "afs_keyframe_local_edit_request.v0.1"
KEYFRAME_LOCAL_EDIT_PREFLIGHT_SCHEMA = "afs_keyframe_local_edit_preflight.v0.1"
KEYFRAME_LOCAL_EDIT_NON_CLAIMS = [
    "no_provider_call",
    "no_generated_media",
    "no_pixel_transformation",
    "not_provider_or_human_acceptance",
    "not_full_frame_fallback",
]
KEYFRAME_LOCAL_EDIT_UNSAFE_REQUEST_MARKERS = (
    "data:",
    "base64",
    "data_base64",
    "raw_provider_response",
    "provider_response",
    "provider_raw",
)
KEYFRAME_LOCAL_EDIT_SCOPE_PLACEHOLDERS = {
    "please describe the local edit region.",
    "describe the local edit region.",
    "请描述要修改的局部区域。",
}


class KeyframeLocalEditParentLineage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    immutable_parent: bool = True
    parent_node_id: str = ""
    parent_keyframe_job_id: str = ""
    parent_image_asset_id: str = ""
    parent_candidate_id: str = ""
    parent_preview_url_present: bool = False


class KeyframeLocalEditBbox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(ge=0, le=1)
    height: float = Field(ge=0, le=1)


class KeyframeLocalEditScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["mask_asset", "bbox", "polygon", "semantic_region"] = "semantic_region"
    target_description: str = Field(default="", max_length=240)
    mask_asset_id: str = Field(default="", max_length=120)
    bbox: KeyframeLocalEditBbox | None = None
    polygon: list[dict[str, float]] = Field(default_factory=list, max_length=16)


class KeyframeLocalEditFallbackPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_full_frame_fallback: bool = False
    fallback_truth_label: str = Field(default="not_allowed_in_first_slice", max_length=120)
    user_confirmation_required: bool = True


class KeyframeLocalEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["afs_keyframe_local_edit_request.v0.1"] = KEYFRAME_LOCAL_EDIT_REQUEST_SCHEMA
    request_id: str = Field(default="", max_length=160)
    target_node_id: str = Field(default="", max_length=160)
    parent_lineage: KeyframeLocalEditParentLineage = Field(default_factory=KeyframeLocalEditParentLineage)
    edit_intent: str = Field(default="", max_length=500)
    edit_scope: KeyframeLocalEditScope = Field(default_factory=KeyframeLocalEditScope)
    preserve_locks: list[str] = Field(default_factory=list, max_length=12)
    negative_locks: list[str] = Field(default_factory=list, max_length=12)
    fallback_policy: KeyframeLocalEditFallbackPolicy = Field(default_factory=KeyframeLocalEditFallbackPolicy)
    provider_capability_mode: Literal["no_provider_execution"] = "no_provider_execution"
    created_at: str = Field(default="", max_length=80)
    updated_at: str = Field(default="", max_length=80)


def register_runtime_keyframe_local_edit_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/projects/{project_id}/keyframe-local-edits/preflight")
    def keyframe_local_edit_preflight_route(
        project_id: str,
        request: KeyframeLocalEditRequest,
        http_request: Request,
    ) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        node_id = request.target_node_id or studio_node_id_from_request(http_request)
        try:
            result = keyframe_local_edit_preflight(project_id, request)
        except ValueError as exc:
            detail = safe_error_detail(
                "invalid_keyframe_local_edit",
                request_id=request_id_from_request(http_request),
                client_request_id=client_request_id_from_request(http_request),
                project_id=project_id,
                node_id=node_id,
                action="keyframe_local_edit_preflight",
                stage="preflight",
                details={
                    "reason": str(exc),
                    "provider_calls_started": False,
                    "local_transformation_started": False,
                    "generated_media_created": False,
                },
            )
            _log_keyframe_local_edit_event("keyframe_local_edit_preflight_rejected", http_request, detail=detail)
            raise HTTPException(status_code=422, detail=detail) from exc
        _log_keyframe_local_edit_event(
            "keyframe_local_edit_preflight_completed",
            http_request,
            project_id=project_id,
            node_id=node_id,
            contract_status=result["contract_status"],
            execution_status=result["execution_status"],
            blocker_count=len(result["blockers"]),
        )
        return result


def keyframe_local_edit_preflight(project_id: str, request: KeyframeLocalEditRequest) -> dict[str, Any]:
    _reject_unsafe_request(request)
    blockers = _required_input_blockers(request)
    contract_ready = not blockers
    payload = {
        "schema_version": KEYFRAME_LOCAL_EDIT_PREFLIGHT_SCHEMA,
        "project_id": project_id,
        "request_id": request.request_id,
        "target_node_id": request.target_node_id,
        "contract_status": "ready_no_provider_execution" if contract_ready else "draft_needs_input",
        "execution_status": "blocked_no_local_transform" if contract_ready else "blocked_missing_required_input",
        "provider_calls_started": False,
        "local_transformation_started": False,
        "generated_media_created": False,
        "fallback_full_frame_edit": False,
        "local_edit_truth_label": "request_contract_only",
        "blocking_capability": "image_edit_or_masked_local_transform",
        "parent_lineage": request.parent_lineage.model_dump(mode="json"),
        "edit_scope": request.edit_scope.model_dump(mode="json"),
        "preserve_locks": _safe_string_list(request.preserve_locks),
        "negative_locks": _safe_string_list(request.negative_locks),
        "blockers": blockers or [_blocker("execution_not_implemented", "Local pixel transformation is not implemented in this no-provider preflight slice.")],
        "allowed_next_actions": (
            ["refine_edit_scope", "route_to_transform_or_provider_implementation_lane"]
            if contract_ready
            else ["add_parent_image_asset", "add_edit_intent", "refine_edit_scope"]
        ),
        "preflight_token": _preflight_token(project_id, request),
        "non_claims": list(KEYFRAME_LOCAL_EDIT_NON_CLAIMS),
    }
    reject_unsafe_payload(payload)
    return payload


def _reject_unsafe_request(request: KeyframeLocalEditRequest) -> None:
    payload = request.model_dump(mode="json")
    if response_contains_unsafe_marker(payload) or _contains_local_edit_unsafe_marker(payload):
        raise ValueError("unsafe_local_edit_request")
    reject_unsafe_payload(payload)
    policy = request.fallback_policy
    if policy.allow_full_frame_fallback:
        raise ValueError("full_frame_fallback_not_allowed")
    if policy.fallback_truth_label != "not_allowed_in_first_slice":
        raise ValueError("unsupported_fallback_truth_label")
    if not policy.user_confirmation_required:
        raise ValueError("fallback_confirmation_required")
    scope = request.edit_scope
    if scope.kind == "mask_asset" and not scope.mask_asset_id:
        raise ValueError("mask_asset_scope_requires_mask_asset_id")
    if scope.kind == "bbox" and scope.bbox is None:
        raise ValueError("bbox_scope_requires_bbox")
    if scope.kind == "polygon" and not scope.polygon:
        raise ValueError("polygon_scope_requires_points")


def _contains_local_edit_unsafe_marker(payload: dict[str, Any]) -> bool:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
    return any(marker in serialized for marker in KEYFRAME_LOCAL_EDIT_UNSAFE_REQUEST_MARKERS)


def _required_input_blockers(request: KeyframeLocalEditRequest) -> list[dict[str, Any]]:
    lineage = request.parent_lineage
    blockers = []
    if not request.target_node_id:
        blockers.append(_blocker("missing_target_node_id", "Missing target keyframe node id."))
    if not lineage.immutable_parent:
        blockers.append(_blocker("mutable_parent_lineage_not_supported", "Parent lineage must be immutable for local edit preflight."))
    if not lineage.parent_keyframe_job_id:
        blockers.append(_blocker("missing_parent_keyframe_job", "Missing parent keyframe job id."))
    if not lineage.parent_image_asset_id:
        blockers.append(_blocker("missing_parent_image_asset", "Missing parent image asset id."))
    if not request.edit_intent.strip():
        blockers.append(_blocker("missing_edit_intent", "Missing local edit intent."))
    if _is_missing_edit_scope_description(request.edit_scope.target_description):
        blockers.append(_blocker("missing_edit_scope", "Missing local edit target description."))
    return blockers


def _is_missing_edit_scope_description(value: str) -> bool:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return True
    normalized = text.casefold()
    if normalized in KEYFRAME_LOCAL_EDIT_SCOPE_PLACEHOLDERS:
        return True
    return normalized.startswith("璇锋弿杩")


def _blocker(code: str, reason: str) -> dict[str, Any]:
    return {
        "code": code,
        "reason": reason,
        "provider_calls_started": False,
        "local_transformation_started": False,
        "generated_media_created": False,
    }


def _safe_string_list(values: list[str]) -> list[str]:
    result = []
    for value in values[:12]:
        text = " ".join(str(value or "").split()).strip()[:120]
        if text:
            result.append(text)
    return result


def _preflight_token(project_id: str, request: KeyframeLocalEditRequest) -> str:
    request_payload = request.model_dump(mode="json")
    request_payload.pop("request_id", None)
    request_payload.pop("created_at", None)
    request_payload.pop("updated_at", None)
    digest = {
        "kind": "keyframe_local_edit",
        "schema_version": KEYFRAME_LOCAL_EDIT_PREFLIGHT_SCHEMA,
        "project_id": project_id,
        "request": request_payload,
    }
    data = json.dumps(digest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:32]


def _log_keyframe_local_edit_event(event_type: str, http_request: Request, **fields: Any) -> None:
    detail = fields.pop("detail", None)
    details = detail.get("details") if isinstance(detail, dict) and isinstance(detail.get("details"), dict) else {}
    project_id = str(fields.pop("project_id", "") or (detail or {}).get("project_id") or "")
    node_id = str(fields.pop("node_id", "") or (detail or {}).get("node_id") or studio_node_id_from_request(http_request))
    log_business_event(
        event_type,
        request_id=(detail or {}).get("request_id") or request_id_from_request(http_request),
        client_request_id=(detail or {}).get("client_request_id") or client_request_id_from_request(http_request),
        user_action=user_action_from_request(http_request),
        project_id=project_id,
        node_id=node_id,
        action="keyframe_local_edit_preflight",
        stage="preflight",
        studio_node_type=studio_node_type_from_request(http_request),
        **fields,
        **details,
        file_log_domain="keyframe_local_edit",
        file_log_event=event_type.removeprefix("keyframe_local_edit_"),
        file_log_level="WARNING" if event_type.endswith("_rejected") else "INFO",
    )


__all__ = (
    "KEYFRAME_LOCAL_EDIT_PREFLIGHT_SCHEMA",
    "KEYFRAME_LOCAL_EDIT_REQUEST_SCHEMA",
    "KeyframeLocalEditRequest",
    "keyframe_local_edit_preflight",
    "register_runtime_keyframe_local_edit_routes",
)
