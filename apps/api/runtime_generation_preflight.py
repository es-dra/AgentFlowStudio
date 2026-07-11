from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import load_provider_registry
from apps.api.runtime_context_resolver import resolve_context_bundle
from apps.api.generation_path_contract import generation_path_preflight
from apps.api.runtime_models import KeyframeGenerationRequest, VideoGenerationRequest
from apps.api.runtime_prompt_text import strip_user_prompt_section_headers
from apps.api.runtime_video_contract import (
    video_duration_contract,
    video_generation_path_contract,
    video_input_mode,
    video_input_source_contract,
)
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
        **_provider_capability_fields(kind, request),
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
    path_contract = video_generation_path_contract(request)
    return {
        "generation_path": path_contract["path_id"],
        "generation_path_contract": path_contract,
        "input_source": video_input_source_contract(request),
        "input_mode": video_input_mode(request),
        "duration_contract": video_duration_contract(request.duration_sec),
    }


def _provider_capability_fields(kind: str, request: KeyframeGenerationRequest | VideoGenerationRequest) -> dict[str, Any]:
    if kind != "video" or not isinstance(request, VideoGenerationRequest):
        return {}
    path_preflight = generation_path_preflight(request)
    limits = _video_provider_capability_limits(request)
    blocks = [*path_preflight["blocks"], *_video_unsupported_combination_blocks(limits)]
    return {
        "provider_capability_limits": limits,
        "generation_path_preflight": path_preflight,
        "preflight_blocked": bool(blocks),
        "blocked_unsupported_combinations": blocks,
    }


def _video_provider_capability_limits(request: VideoGenerationRequest) -> dict[str, Any]:
    descriptor = _descriptor_or_none(request.provider_service_id)
    source = "provider_descriptor" if descriptor is not None else "provider_descriptor_unavailable"
    durations = _int_list(getattr(descriptor, "supported_durations_sec", []) if descriptor is not None else [])
    input_modes = _str_list(getattr(descriptor, "frame_modes", []) if descriptor is not None else [])
    resolutions = _str_list(getattr(descriptor, "supported_resolutions", []) if descriptor is not None else [])
    aspect_ratios = _str_list(getattr(descriptor, "supported_aspect_ratios", []) if descriptor is not None else [])
    input_mode = video_input_mode(request)
    return {
        "provider_service_id": request.provider_service_id,
        "source": source,
        "provider_calls_started": False,
        "required_gate": _provider_required_gate("video", request),
        "generation_path_contract": video_generation_path_contract(request),
        "duration_seconds": {
            "requested": request.duration_sec,
            "allowed": durations,
            "supported": not durations or request.duration_sec in durations,
            "request_contract": video_duration_contract(request.duration_sec),
        },
        "input_modes": {
            "requested": input_mode,
            "allowed": input_modes,
            "supported": not input_modes or input_mode in input_modes,
        },
        "resolutions": {
            "requested": request.resolution,
            "allowed": resolutions,
            "supported": not resolutions or request.resolution.lower() in {item.lower() for item in resolutions},
        },
        "aspect_ratios": {
            "requested": request.aspect_ratio,
            "allowed": aspect_ratios,
            "supported": not aspect_ratios or request.aspect_ratio in aspect_ratios,
        },
    }


def _video_unsupported_combination_blocks(limits: dict[str, Any]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    checks = [
        ("unsupported_duration", "duration_sec", "duration_seconds"),
        ("unsupported_input_mode", "input_mode", "input_modes"),
        ("unsupported_resolution", "resolution", "resolutions"),
        ("unsupported_aspect_ratio", "aspect_ratio", "aspect_ratios"),
    ]
    for error, field, key in checks:
        section = limits.get(key) if isinstance(limits.get(key), dict) else {}
        if section.get("supported") is not False:
            continue
        blocks.append(
            {
                "error": error,
                "field": field,
                "stage": "provider_capability_check",
                "provider_calls_started": False,
                "details": {
                    "requested": section.get("requested"),
                    "allowed": list(section.get("allowed") or []),
                    "provider_service_id": limits.get("provider_service_id"),
                    "provider_calls_started": False,
                },
            }
        )
    return blocks


def _preflight_token(kind: str, request: KeyframeGenerationRequest | VideoGenerationRequest, bundle: dict[str, Any] | None) -> str:
    request_payload = request.model_dump(mode="json", by_alias=True)
    request_payload.pop("generated_at", None)
    request_payload.pop("preflight_token", None)
    digest = {
        "kind": kind,
        "request": request_payload,
        "provider_submit_preflight": provider_submit_preflight_requirement(kind, request),
        "generation_path_contract": video_generation_path_contract(request) if isinstance(request, VideoGenerationRequest) else None,
        "provider_capability_limits": _provider_capability_fields(kind, request).get("provider_capability_limits"),
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
    descriptor = _descriptor_or_none(service_id)
    if descriptor is None:
        return prompt_default, reference_default
    return (
        int(getattr(descriptor, "prompt_char_limit", prompt_default) or prompt_default),
        int(getattr(descriptor, "reference_image_slots", reference_default) or reference_default),
    )


def _provider_required_gate(kind: str, request: KeyframeGenerationRequest | VideoGenerationRequest) -> str:
    default_gate = REMOTE_VIDEO_ENV if kind == "video" else REMOTE_IMAGE_ENV
    descriptor = _descriptor_or_none(request.provider_service_id)
    if descriptor is None:
        return default_gate
    return str(getattr(descriptor, "required_gate", default_gate) or default_gate)


def _descriptor_or_none(service_id: str) -> Any | None:
    try:
        return load_provider_registry().descriptor(service_id)
    except (ModelGatewayError, ValueError, OSError):
        return None


def _int_list(values: Any) -> list[int]:
    result: list[int] = []
    seen: set[int] = set()
    for item in values if isinstance(values, (list, tuple, set)) else []:
        try:
            value = int(item)
        except (TypeError, ValueError):
            continue
        if value <= 0 or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return sorted(result)


def _str_list(values: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in values if isinstance(values, (list, tuple, set)) else []:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


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
