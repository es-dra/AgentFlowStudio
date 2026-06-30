from __future__ import annotations

import hashlib
import json
from typing import Any

from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import load_provider_registry
from apps.api.runtime_context_resolver import resolve_context_bundle
from apps.api.runtime_models import KeyframeGenerationRequest, VideoGenerationRequest
from apps.api.runtime_prompt_text import strip_user_prompt_section_headers
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload


DEFAULT_IMAGE_PROMPT_LIMIT = 1500
DEFAULT_IMAGE_REFERENCE_SLOTS = 1
DEFAULT_VIDEO_PROMPT_LIMIT = 2000


def keyframe_generation_preflight(
    store: RuntimeStore,
    project_id: str,
    request: KeyframeGenerationRequest,
    *,
    include_fixed_assets: bool = True,
) -> dict[str, Any]:
    prompt_limit, reference_slots = _descriptor_limits(
        request.provider_service_id,
        prompt_default=DEFAULT_IMAGE_PROMPT_LIMIT,
        reference_default=DEFAULT_IMAGE_REFERENCE_SLOTS,
    )
    if reference_slots <= 0 and request.asset_refs:
        reference_slots = 1
    bundle = None
    if request.context_subgraph:
        bundle = resolve_context_bundle(
            store,
            project_id,
            mode="generate",
            visible_prompt=strip_user_prompt_section_headers(request.optimized_prompt or request.prompt_text),
            context_subgraph=request.context_subgraph,
            temporary_lock_overrides=request.temporary_lock_overrides,
            temporary_asset_exclusions=request.temporary_asset_exclusions,
            include_fixed_assets=include_fixed_assets,
            style_preference=request.style,
            prompt_char_limit=prompt_limit,
            reference_image_slots=reference_slots,
            director_setup=request.director_setup,
        )
    return _preflight_response("keyframe", request, bundle)


def video_generation_preflight(
    store: RuntimeStore,
    project_id: str,
    request: VideoGenerationRequest,
) -> dict[str, Any]:
    prompt_limit, _ = _descriptor_limits(
        request.provider_service_id,
        prompt_default=DEFAULT_VIDEO_PROMPT_LIMIT,
        reference_default=0,
    )
    bundle = None
    if request.context_subgraph:
        visible_prompt = " ".join(
            item.strip()
            for item in (request.optimized_prompt or request.prompt_text, request.motion)
            if item and item.strip()
        )
        bundle = resolve_context_bundle(
            store,
            project_id,
            mode="generate",
            visible_prompt=strip_user_prompt_section_headers(visible_prompt),
            context_subgraph=request.context_subgraph,
            temporary_lock_overrides=request.temporary_lock_overrides,
            temporary_asset_exclusions=request.temporary_asset_exclusions,
            include_fixed_assets=True,
            style_preference="video_i2v_v1",
            prompt_char_limit=prompt_limit,
            reference_image_slots=0,
        )
    return _preflight_response("video", request, bundle)


def preflight_token_matches(
    expected_preflight: dict[str, Any],
    provided_token: str | None,
) -> bool:
    return bool(provided_token) and provided_token == expected_preflight.get("preflight_token")


def _preflight_response(kind: str, request: KeyframeGenerationRequest | VideoGenerationRequest, bundle: dict[str, Any] | None) -> dict[str, Any]:
    payload = {
        "schema_version": "afs_generation_preflight.v0.1",
        "generation_kind": kind,
        "provider_calls_started": False,
        "requires_provider_gate": False,
        "context_bundle": bundle,
        "included_assets": list((bundle or {}).get("included_assets") or []),
        "excluded_assets": list((bundle or {}).get("excluded_assets") or []),
        "asset_conflicts": list((bundle or {}).get("asset_conflicts") or []),
        "reference_image_channel": list((bundle or {}).get("reference_image_channel") or []),
        "subject_reference_asset_id": (bundle or {}).get("subject_reference_asset_id"),
        "feedback_context_overlays": list((bundle or {}).get("feedback_context_overlays") or []),
        "preflight_token": _preflight_token(kind, request, bundle),
        "non_claims": [
            "preflight_only",
            "no_provider_submit",
            "not_human_acceptance",
            "not_business_validation",
        ],
    }
    reject_unsafe_payload(payload)
    return payload


def _preflight_token(kind: str, request: KeyframeGenerationRequest | VideoGenerationRequest, bundle: dict[str, Any] | None) -> str:
    request_payload = request.model_dump(mode="json", by_alias=True)
    request_payload.pop("generated_at", None)
    request_payload.pop("preflight_token", None)
    digest = {
        "kind": kind,
        "request": request_payload,
        "bundle": _bundle_digest(bundle),
    }
    data = json.dumps(digest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:32]


def _bundle_digest(bundle: dict[str, Any] | None) -> dict[str, Any] | None:
    if not bundle:
        return None
    return {
        "resolver_version": bundle.get("resolver_version"),
        "vocabulary_hash": bundle.get("vocabulary_hash"),
        "included_assets": [
            {
                "asset_id": item.get("asset_id"),
                "status": item.get("status"),
                "version": item.get("version"),
                "feature_card_hash": item.get("feature_card_hash"),
                "detail_level": item.get("detail_level"),
            }
            for item in bundle.get("included_assets", [])
            if isinstance(item, dict)
        ],
        "excluded_assets": [
            {"asset_id": item.get("asset_id"), "reason": item.get("reason")}
            for item in bundle.get("excluded_assets", [])
            if isinstance(item, dict)
        ],
        "asset_conflicts": list(bundle.get("asset_conflicts") or []),
        "reference_image_channel": list(bundle.get("reference_image_channel") or []),
        "subject_reference_asset_id": bundle.get("subject_reference_asset_id"),
        "feedback_context_overlays": [
            {
                "overlay_id": item.get("overlay_id"),
                "candidate_id": item.get("candidate_id"),
                "decision_effect": item.get("decision_effect"),
            }
            for item in bundle.get("feedback_context_overlays", [])
            if isinstance(item, dict)
        ],
        "temporary_lock_overrides": list(bundle.get("temporary_lock_overrides") or []),
        "temporary_asset_exclusions": list(bundle.get("temporary_asset_exclusions") or []),
    }


def _descriptor_limits(service_id: str, *, prompt_default: int, reference_default: int) -> tuple[int, int]:
    try:
        registry = load_provider_registry()
        descriptor = registry.descriptor(service_id)
    except (ModelGatewayError, ValueError, OSError):
        return prompt_default, reference_default
    return (
        int(getattr(descriptor, "prompt_char_limit", prompt_default) or prompt_default),
        int(getattr(descriptor, "reference_image_slots", reference_default) or reference_default),
    )


__all__ = (
    "keyframe_generation_preflight",
    "preflight_token_matches",
    "video_generation_preflight",
)
