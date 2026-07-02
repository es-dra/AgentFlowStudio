from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import load_provider_registry
from apps.api.runtime_context_resolver import resolve_context_bundle
from apps.api.runtime_models import KeyframeGenerationRequest, VideoGenerationRequest
from apps.api.runtime_prompt_text import strip_user_prompt_section_headers
from apps.api.runtime_video_contract import video_duration_contract, video_input_mode, video_input_source_contract
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload


DEFAULT_IMAGE_PROMPT_LIMIT = 1500
DEFAULT_IMAGE_REFERENCE_SLOTS = 1
DEFAULT_VIDEO_PROMPT_LIMIT = 2000
REMOTE_IMAGE_ENV = "AFS_ALLOW_REMOTE_IMAGE"
REMOTE_VIDEO_ENV = "AFS_ALLOW_REMOTE_VIDEO"
REMOTE_TRUE_VALUES = {"1", "true", "yes", "on"}


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


def provider_submit_preflight_requirement(
    kind: str,
    request: KeyframeGenerationRequest | VideoGenerationRequest,
) -> dict[str, Any]:
    required_gate = _provider_required_gate(kind, request)
    return {
        "required": _env_gate_open(required_gate),
        "required_gate": required_gate,
        "provider_calls_started": False,
    }


def _preflight_response(kind: str, request: KeyframeGenerationRequest | VideoGenerationRequest, bundle: dict[str, Any] | None) -> dict[str, Any]:
    included_assets = list((bundle or {}).get("included_assets") or [])
    source_evidence_refs = _included_asset_source_evidence_refs(included_assets)
    payload = {
        "schema_version": "afs_generation_preflight.v0.1",
        "generation_kind": kind,
        "provider_calls_started": False,
        "requires_provider_gate": False,
        "provider_submit_preflight": provider_submit_preflight_requirement(kind, request),
        "context_bundle": bundle,
        "included_assets": included_assets,
        "included_asset_source_evidence_count": len(source_evidence_refs),
        "included_asset_source_evidence_refs": source_evidence_refs,
        "excluded_assets": list((bundle or {}).get("excluded_assets") or []),
        "asset_conflicts": list((bundle or {}).get("asset_conflicts") or []),
        "reference_image_channel": list((bundle or {}).get("reference_image_channel") or []),
        "subject_reference_asset_id": (bundle or {}).get("subject_reference_asset_id"),
        "feedback_context_overlays": list((bundle or {}).get("feedback_context_overlays") or []),
        **_video_contract_fields(kind, request),
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


def _video_contract_fields(kind: str, request: KeyframeGenerationRequest | VideoGenerationRequest) -> dict[str, Any]:
    if kind != "video" or not isinstance(request, VideoGenerationRequest):
        return {}
    return {
        "input_source": video_input_source_contract(request),
        "input_mode": video_input_mode(request),
        "duration_contract": video_duration_contract(request.duration_sec),
    }


def _preflight_token(kind: str, request: KeyframeGenerationRequest | VideoGenerationRequest, bundle: dict[str, Any] | None) -> str:
    request_payload = request.model_dump(mode="json", by_alias=True)
    request_payload.pop("generated_at", None)
    request_payload.pop("preflight_token", None)
    digest = {
        "kind": kind,
        "request": request_payload,
        "provider_submit_preflight": provider_submit_preflight_requirement(kind, request),
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
                "source_evidence": _source_evidence_digest(item.get("source_evidence")),
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


def _provider_required_gate(kind: str, request: KeyframeGenerationRequest | VideoGenerationRequest) -> str:
    default_gate = REMOTE_VIDEO_ENV if kind == "video" else REMOTE_IMAGE_ENV
    try:
        descriptor = load_provider_registry().descriptor(request.provider_service_id)
    except (ModelGatewayError, ValueError, OSError):
        return default_gate
    return str(getattr(descriptor, "required_gate", default_gate) or default_gate)


def _env_gate_open(required_gate: str) -> bool:
    return os.environ.get(required_gate, "").strip().lower() in REMOTE_TRUE_VALUES


def _included_asset_source_evidence_refs(included_assets: list[Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in included_assets:
        if not isinstance(item, dict):
            continue
        evidence = item.get("source_evidence")
        if not isinstance(evidence, dict):
            continue
        refs.append(
            {
                "asset_id": str(item.get("asset_id") or ""),
                "asset_type": str(item.get("asset_type") or ""),
                "label": str(item.get("label") or ""),
                "status": str(item.get("status") or ""),
                **_source_evidence_digest(evidence),
            }
        )
    return refs


def _source_evidence_digest(evidence: Any) -> dict[str, Any] | None:
    if not isinstance(evidence, dict):
        return None
    return {
        "source_contract": str(evidence.get("source_contract") or ""),
        "source_human_gate_id": str(evidence.get("source_human_gate_id") or ""),
        "source_asset_card_candidate_id": str(evidence.get("source_asset_card_candidate_id") or ""),
        "source_stage": str(evidence.get("source_stage") or ""),
        "result_asset_status": str(evidence.get("result_asset_status") or ""),
        "provider_calls_started": bool(evidence.get("provider_calls_started")),
        "generated_media_claimed": bool(evidence.get("generated_media_claimed")),
        "human_creative_acceptance_claimed": bool(evidence.get("human_creative_acceptance_claimed")),
        "business_validation_claimed": bool(evidence.get("business_validation_claimed")),
    }


__all__ = (
    "keyframe_generation_preflight",
    "preflight_token_matches",
    "provider_submit_preflight_requirement",
    "video_generation_preflight",
)
