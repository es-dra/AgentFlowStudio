from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import (
    ProviderDispatchRequest,
    load_provider_registry,
)
from apps.api.runtime_image_assets import resolve_reference_images
from apps.api.runtime_context_resolver import provider_prompt_from_bundle, resolve_context_bundle
from apps.api.runtime_models import KeyframeGenerationRequest, PromptOptimizationRequest
from apps.api.runtime_keyframe_payloads import (
    keyframe_candidate_summary,
    keyframe_request_plan,
    keyframe_safe_manifest,
)
from apps.api.runtime_prompt_memory_engine import assemble_prompt_context
from apps.api.runtime_prompt_memory_state import load_creative_memory_state
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload


REMOTE_IMAGE_ENV = "AFS_ALLOW_REMOTE_IMAGE"
REMOTE_TRUE_VALUES = {"1", "true", "yes", "on"}
DEFAULT_IMAGE_PROMPT_LIMIT = 1500
DEFAULT_REFERENCE_IMAGE_SLOTS = 1
KEYFRAME_NON_CLAIMS = [
    "runtime verification only",
    "not human acceptance",
    "not business validation",
    "not video provider smoke",
    "not durable memory",
]


def build_keyframe_generation(
    store: RuntimeStore,
    project_id: str,
    request: KeyframeGenerationRequest,
    output_dir: Path,
    *,
    include_fixed_assets: bool = True,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_request = _prompt_request(request)
    state = load_creative_memory_state(store, project_id)
    assembly_state = _resolver_safe_state(state) if request.context_subgraph else state
    assembly = assemble_prompt_context(prompt_request, assembly_state)
    registry = None
    descriptor = _default_descriptor()
    if os.environ.get(REMOTE_IMAGE_ENV, "").strip().lower() in REMOTE_TRUE_VALUES:
        try:
            registry = load_provider_registry()
            descriptor = registry.descriptor(request.provider_service_id)
        except ModelGatewayError:
            registry = None
    context_bundle = _context_bundle(
        store,
        project_id,
        request,
        include_fixed_assets=include_fixed_assets,
        prompt_char_limit=int(getattr(descriptor, "prompt_char_limit", DEFAULT_IMAGE_PROMPT_LIMIT)),
        reference_image_slots=int(getattr(descriptor, "reference_image_slots", DEFAULT_REFERENCE_IMAGE_SLOTS)),
    )
    reference_images = _reference_images(
        store,
        project_id,
        request,
        context_bundle,
        limit=int(getattr(descriptor, "reference_image_slots", DEFAULT_REFERENCE_IMAGE_SLOTS)),
    )
    if context_bundle:
        provider_prompt = minimax_keyframe_prompt(
            provider_prompt_from_bundle(context_bundle),
            limit=int(getattr(descriptor, "prompt_char_limit", DEFAULT_IMAGE_PROMPT_LIMIT)),
        )
    else:
        provider_prompt = minimax_keyframe_prompt(
            request.optimized_prompt or assembly["creative_agent"]["provider_translation"]["prompt"],
            limit=int(getattr(descriptor, "prompt_char_limit", DEFAULT_IMAGE_PROMPT_LIMIT)),
        )
    if reference_images and not context_bundle:
        provider_prompt = minimax_keyframe_prompt(
            f"{provider_prompt}\n{_reference_prompt_instruction(request, len(reference_images))}",
            limit=int(getattr(descriptor, "prompt_char_limit", DEFAULT_IMAGE_PROMPT_LIMIT)),
        )
    required_gate = str(getattr(descriptor, "required_gate", REMOTE_IMAGE_ENV) or REMOTE_IMAGE_ENV)
    provider_gate = image_provider_gate(required_gate)

    provider_outputs: list[dict[str, Any]] = []
    status = "blocked"
    blocks = []
    provider_calls_started = False
    if provider_gate["status"] == "blocked":
        blocks.append(_gate_closed_block(required_gate))
    else:
        try:
            if registry is None:
                registry = load_provider_registry()
                descriptor = registry.descriptor(request.provider_service_id)
            provider_calls_started = True
            manifest = registry.dispatch(
                "image",
                request.provider_service_id,
                ProviderDispatchRequest(
                    prompt=provider_prompt,
                    output_dir=output_dir,
                    aspect_ratio=request.aspect_ratio,
                    candidate_count=request.candidate_count,
                    seed=request.seed,
                    reference_image_paths=tuple(item["path"] for item in reference_images),
                    subject_reference_image_path=reference_images[0]["path"] if reference_images else None,
                ),
            )
            status = "succeeded"
            provider_outputs = _provider_outputs(manifest)
        except ModelGatewayError as exc:
            status = "blocked"
            blocks.append(
                {
                    "block_id": "remote_image_provider_not_ready",
                    "reason": _safe_error(str(exc)),
                    "required_gate": required_gate,
                }
            )

    request_plan = keyframe_request_plan(
        request,
        provider_prompt,
        provider_gate,
        assembly,
        status,
        reference_images,
        context_bundle,
        KEYFRAME_NON_CLAIMS,
    )
    candidates = keyframe_candidate_summary(request, provider_prompt, provider_outputs, KEYFRAME_NON_CLAIMS)
    safe_manifest = keyframe_safe_manifest(
        project_id,
        request,
        status=status,
        provider_gate=provider_gate,
        blocks=blocks,
        provider_calls_started=provider_calls_started,
        output_count=len(provider_outputs),
        reference_image_count=len(reference_images),
        context_bundle=context_bundle,
        non_claims=KEYFRAME_NON_CLAIMS,
    )
    for payload in (request_plan, candidates, safe_manifest):
        reject_unsafe_payload(payload)
    write_json(output_dir / "keyframe_request_plan.json", request_plan)
    write_json(output_dir / "keyframe_candidates_summary.json", candidates)
    write_json(output_dir / "keyframe_generation_safe_manifest.json", safe_manifest)
    return {
        "status": status,
        "provider_gate": provider_gate,
        "provider_calls_started": provider_calls_started,
        "provider_outputs": provider_outputs,
        "safe_manifest": safe_manifest,
        "context_bundle": context_bundle,
        "tool_gate_state": {
            "remote_llm": "not_requested",
            "remote_asr": "blocked_by_default",
            "remote_image": provider_gate["status"],
            "remote_video": "blocked_by_default",
        },
    }


def _context_bundle(
    store: RuntimeStore,
    project_id: str,
    request: KeyframeGenerationRequest,
    *,
    include_fixed_assets: bool,
    prompt_char_limit: int,
    reference_image_slots: int,
) -> dict[str, Any] | None:
    if not request.context_subgraph:
        return None
    visible_prompt = request.optimized_prompt or request.prompt_text
    return resolve_context_bundle(
        store,
        project_id,
        mode="generate",
        visible_prompt=visible_prompt,
        context_subgraph=request.context_subgraph,
        temporary_lock_overrides=request.temporary_lock_overrides,
        include_fixed_assets=include_fixed_assets,
        style_preference=request.style,
        prompt_char_limit=prompt_char_limit,
        reference_image_slots=reference_image_slots,
    )


def _reference_images(
    store: RuntimeStore,
    project_id: str,
    request: KeyframeGenerationRequest,
    context_bundle: dict[str, Any] | None,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    if not context_bundle:
        return resolve_reference_images(store, project_id, request.asset_refs, limit=limit)
    refs = [
        str(item.get("asset_id") or "")
        for item in context_bundle.get("reference_image_channel", [])
        if isinstance(item, dict)
    ]
    return resolve_reference_images(store, project_id, refs, limit=limit)


def _resolver_safe_state(state: dict[str, Any]) -> dict[str, Any]:
    safe_state = dict(state)
    for field in ("characters", "scenes", "style_preferences", "user_preferences"):
        safe_state[field] = []
    return safe_state


def image_provider_gate(required_gate: str = REMOTE_IMAGE_ENV) -> dict[str, str]:
    status = "ready_not_run" if os.environ.get(required_gate, "").strip().lower() in REMOTE_TRUE_VALUES else "blocked"
    return {"capability": "image", "env": required_gate, "status": status}


def _prompt_request(request: KeyframeGenerationRequest) -> PromptOptimizationRequest:
    params = dict(request.node_parameters or {})
    params.setdefault("aspect_ratio", request.aspect_ratio)
    return PromptOptimizationRequest(
        node_id=request.node_id,
        node_type="image",
        prompt_text=request.prompt_text,
        generation_target="keyframe",
        target_platform=request.target_platform,
        style=request.style,
        asset_refs=list(request.asset_refs),
        director_setup=request.director_setup,
        node_parameters=params,
        context_subgraph=request.context_subgraph,
        generated_at=request.generated_at,
    )


def _provider_outputs(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    outputs = []
    for item in manifest.get("outputs", []):
        if not isinstance(item, dict):
            continue
        outputs.append(
            {
                "candidate_id": item.get("candidate_id"),
                "image_ref": item.get("image_path"),
                "byte_count": item.get("byte_count"),
                "sha256": item.get("sha256"),
                "width": item.get("width"),
                "height": item.get("height"),
                "aspect_ratio": item.get("aspect_ratio"),
                "provider_url_persisted": False,
            }
        )
    return outputs


def _reference_prompt_instruction(request: KeyframeGenerationRequest, reference_count: int) -> str:
    lines = [
        (
            f"Connected reference images: {reference_count}. Preserve the reference identity, hairstyle, "
            "wardrobe, silhouette, body proportions, and key visual traits."
        )
    ]
    params = request.node_parameters or {}
    for item in list(params.get("connected_reference_nodes") or [])[:4]:
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("prompt") or "").strip()
        title = str(item.get("title") or "reference").strip()
        if prompt:
            lines.append(f"Reference note {title}: {prompt}")
    return "\n".join(lines)


def _gate_closed_block(required_gate: str = REMOTE_IMAGE_ENV) -> dict[str, str]:
    return {
        "block_id": "remote_image_gate_closed",
        "reason": f"Set {required_gate}=true only for an explicit image/keyframe provider smoke.",
        "required_gate": required_gate,
    }


def _safe_error(value: str) -> str:
    lowered = value.lower()
    if "status_code 2049" in lowered and "invalid api key" in lowered:
        return "MiniMax image response status_code 2049: invalid API Key"
    if "api" in lowered or "key" in lowered or "secret" in lowered:
        return "Image provider configuration is not ready."
    return value[:160]


def minimax_keyframe_prompt(value: str, *, limit: int = DEFAULT_IMAGE_PROMPT_LIMIT) -> str:
    lines = []
    for raw_line in str(value or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if any(term in lowered for term in _internal_prompt_terms()):
            continue
        lines.append(line)
    prompt = " ".join(lines)
    prompt = " ".join(prompt.split())
    if len(prompt) <= limit:
        return prompt
    return prompt[:limit].rsplit(" ", 1)[0].strip()


class _DefaultImageDescriptor:
    prompt_char_limit = DEFAULT_IMAGE_PROMPT_LIMIT
    reference_image_slots = DEFAULT_REFERENCE_IMAGE_SLOTS
    required_gate = REMOTE_IMAGE_ENV


def _default_descriptor() -> _DefaultImageDescriptor:
    return _DefaultImageDescriptor()


def _internal_prompt_terms() -> tuple[str, ...]:
    return (
        "provider calls remain off",
        "do not claim provider execution",
        "provider gate",
        "authorization",
        "secret",
        "signed url",
        "media bytes",
        "raw provider",
        "api key",
        "agent rationale:",
        "claim_boundary",
    )


__all__ = (
    "KEYFRAME_NON_CLAIMS",
    "DEFAULT_IMAGE_PROMPT_LIMIT",
    "REMOTE_IMAGE_ENV",
    "build_keyframe_generation",
    "image_provider_gate",
    "minimax_keyframe_prompt",
)
