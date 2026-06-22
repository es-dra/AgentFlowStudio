from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentflow.algorithms.context_resolver import merged_reference_image_refs
from agentflow.algorithms.request_projection import build_request_plan
from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import (
    ProviderDispatchRequest,
    load_provider_registry,
)
from apps.api.runtime_image_assets import resolve_reference_images
from apps.api.runtime_context_resolver import provider_prompt_from_bundle, resolve_context_bundle
from apps.api.runtime_model_call_context import keyframe_model_call_context
from apps.api.runtime_models import KeyframeGenerationRequest, PromptOptimizationRequest
from apps.api.runtime_media_validation import reference_image_size_blocks
from apps.api.runtime_asset_card_revision_prompt import asset_card_revision_reference_instruction
from apps.api.runtime_provider_dispatch import dispatch_provider_with_retry
from apps.api.runtime_keyframe_payloads import (
    keyframe_candidate_summary,
    keyframe_request_plan,
    keyframe_safe_manifest,
)
from apps.api.runtime_prompt_memory_engine import assemble_prompt_context
from apps.api.runtime_prompt_memory_state import load_creative_memory_state
from apps.api.runtime_prompt_text import strip_user_prompt_section_headers
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
    try:
        registry = load_provider_registry()
        descriptor = registry.descriptor(request.provider_service_id)
    except (ModelGatewayError, OSError, ValueError):
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
    is_asset_card_revision = _has_asset_card_revision(request)
    if context_bundle:
        provider_prompt = _guarded_provider_keyframe_prompt(
            provider_prompt_from_bundle(context_bundle),
            reference_count=len(reference_images),
            asset_card_revision=is_asset_card_revision,
            limit=int(getattr(descriptor, "prompt_char_limit", DEFAULT_IMAGE_PROMPT_LIMIT)),
        )
    else:
        provider_prompt = _guarded_provider_keyframe_prompt(
            request.optimized_prompt or assembly["creative_agent"]["provider_translation"]["prompt"],
            reference_count=len(reference_images),
            asset_card_revision=is_asset_card_revision,
            limit=int(getattr(descriptor, "prompt_char_limit", DEFAULT_IMAGE_PROMPT_LIMIT)),
        )
    if reference_images:
        reference_instruction = _reference_prompt_instruction(request, len(reference_images))
        prompt_with_references = (
            f"{reference_instruction}\n{provider_prompt}"
            if is_asset_card_revision
            else f"{provider_prompt}\n{reference_instruction}"
        )
        provider_prompt = _guarded_provider_keyframe_prompt(
            prompt_with_references,
            reference_count=len(reference_images),
            asset_card_revision=is_asset_card_revision,
            limit=int(getattr(descriptor, "prompt_char_limit", DEFAULT_IMAGE_PROMPT_LIMIT)),
        )
    required_gate = str(getattr(descriptor, "required_gate", REMOTE_IMAGE_ENV) or REMOTE_IMAGE_ENV)
    provider_gate = image_provider_gate(required_gate)
    min_reference_edge = int(getattr(descriptor, "min_reference_image_edge_px", 0) or 0)
    model_call_context = keyframe_model_call_context(
        project_id=project_id,
        request=request,
        context_bundle=context_bundle,
        provider_constraints={
            "capability": "image",
            "provider_service_id": request.provider_service_id,
            "required_gate": required_gate,
            "prompt_char_limit": int(getattr(descriptor, "prompt_char_limit", DEFAULT_IMAGE_PROMPT_LIMIT)),
            "reference_image_slots": int(getattr(descriptor, "reference_image_slots", DEFAULT_REFERENCE_IMAGE_SLOTS)),
        },
    )
    model_request_plan = build_request_plan(
        model_call_context=model_call_context,
        canonical_brief={"canonical_prompt": provider_prompt},
        provider_service_id=request.provider_service_id,
    )

    provider_outputs: list[dict[str, Any]] = []
    status = "blocked"
    blocks = []
    provider_calls_started = False
    retry_count = 0
    if provider_gate["status"] == "blocked":
        blocks.append(_gate_closed_block(required_gate))
    elif size_blocks := reference_image_size_blocks(
        reference_images,
        min_edge_px=min_reference_edge,
        capability="image",
        required_gate=required_gate,
    ):
        blocks.extend(size_blocks)
    else:
        try:
            if registry is None:
                registry = load_provider_registry()
                descriptor = registry.descriptor(request.provider_service_id)
            provider_calls_started = True
            dispatch_request = ProviderDispatchRequest(
                prompt=provider_prompt,
                output_dir=output_dir,
                aspect_ratio=request.aspect_ratio,
                candidate_count=request.candidate_count,
                seed=request.seed,
                reference_image_paths=tuple(item["path"] for item in reference_images),
                subject_reference_image_path=reference_images[0]["path"] if reference_images else None,
            )
            if str(getattr(descriptor, "execution_mode", "sync") or "sync") == "async":
                provider_task = registry.submit("image", request.provider_service_id, dispatch_request)
                status = str((provider_task.get("task") or {}).get("status") or "submitted")
                _write_task_state(
                    output_dir,
                    _task_state(
                        request=request,
                        provider_task=provider_task,
                        status=status,
                        provider_prompt=provider_prompt,
                        provider_gate=provider_gate,
                        reference_image_count=len(reference_images),
                        context_bundle=context_bundle,
                    ),
                )
            else:
                manifest, retry_count = dispatch_provider_with_retry(
                    registry,
                    "image",
                    request.provider_service_id,
                    dispatch_request,
                )
                status = "succeeded"
                provider_outputs = _provider_outputs(manifest)
        except ModelGatewayError as exc:
            retry_count = max(retry_count, int(getattr(exc, "retry_count", 0) or 0))
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
    request_plan["model_call_context_id"] = model_call_context["context_id"]
    request_plan["model_request_plan_ref"] = "model_request_plan.json"
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
        retry_count=retry_count,
        context_bundle=context_bundle,
        non_claims=KEYFRAME_NON_CLAIMS,
    )
    for payload in (model_call_context, model_request_plan, request_plan, candidates, safe_manifest):
        reject_unsafe_payload(payload)
    write_json(output_dir / "model_call_context.json", model_call_context)
    write_json(output_dir / "model_request_plan.json", model_request_plan)
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
        "model_call_context": model_call_context,
        "model_request_plan": model_request_plan,
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
    visible_prompt = strip_user_prompt_section_headers(request.optimized_prompt or request.prompt_text)
    return resolve_context_bundle(
        store,
        project_id,
        mode="generate",
        visible_prompt=visible_prompt,
        context_subgraph=request.context_subgraph,
        temporary_lock_overrides=request.temporary_lock_overrides,
        temporary_asset_exclusions=request.temporary_asset_exclusions,
        include_fixed_assets=include_fixed_assets,
        style_preference=request.style,
        prompt_char_limit=prompt_char_limit,
        reference_image_slots=reference_image_slots,
        director_setup=request.director_setup,
    )


def _reference_images(
    store: RuntimeStore,
    project_id: str,
    request: KeyframeGenerationRequest,
    context_bundle: dict[str, Any] | None,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    refs = merged_reference_image_refs(
        request_asset_refs=request.asset_refs,
        context_bundle=context_bundle,
    )
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


def _task_state(
    *,
    request: KeyframeGenerationRequest,
    provider_task: dict[str, Any],
    status: str,
    provider_prompt: str,
    provider_gate: dict[str, str],
    reference_image_count: int,
    context_bundle: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "schema_version": "afs_keyframe_generation_task_state.v0.1",
        "status": status,
        "provider_service_id": request.provider_service_id,
        "capability": "image",
        "task": _provider_task_for_state(provider_task),
        "request": request.model_dump(mode="json"),
        "provider_prompt": provider_prompt,
        "provider_gate": provider_gate,
        "reference_image_count": reference_image_count,
        "context_bundle": context_bundle,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provider_raw_persisted": False,
    }


def _provider_task_for_state(provider_task: dict[str, Any]) -> dict[str, Any]:
    task = dict(provider_task)
    inner = task.get("task")
    if isinstance(inner, dict):
        safe_inner = dict(inner)
        safe_inner.pop("output_dir", None)
        task["task"] = safe_inner
    task.pop("output_dir", None)
    return task


def _write_task_state(output_dir: Path, state: dict[str, Any]) -> None:
    _write_json_checked(output_dir / "keyframe_task_state.json", state)


def _write_json_checked(path: Path, payload: dict[str, Any]) -> None:
    reject_unsafe_payload(payload)
    write_json(path, payload)


def _reference_prompt_instruction(request: KeyframeGenerationRequest, reference_count: int) -> str:
    animal_reference = _looks_like_animal_reference_request(request)
    revision = asset_card_revision_reference_instruction(request)
    lines = []
    if revision:
        lines.append(revision)
    if revision:
        lines.append(
            (
                f"Connected reference images: {reference_count}. For this asset-card revision, reference image #1 is the primary visual source of truth; "
                "other reference images are detail support only. Preserve original identity, sheet composition, proportions, camera distance, view layout, and all non-edited details."
            )
        )
    else:
        lines.append(
            (
                f"Connected reference images: {reference_count}. 参考图只作为本次显式连线的视觉参考。"
                "只保留与用户目标不冲突的相关主体特征、轮廓比例、颜色材质、镜头关系和关键视觉线索。"
                "不要把无关背景、服装、图表、界面文字或旧失败风格带入结果。"
            )
        )
    if animal_reference:
        lines.append(
            "Animal subject reference: 如果参考主体是猫或动物，只保留同一动物主体的毛色、斑纹、眼睛、耳朵、尾巴和体型比例；"
            "未明确要求时不要添加人类头发、服装或拟人身份；不要把参考图当作脸部贴图素材，必须重绘为统一完整的动物主体。"
        )
    params = request.node_parameters or {}
    for item in list(params.get("connected_reference_nodes") or [])[:4]:
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("prompt") or "").strip()
        title = str(item.get("title") or "reference").strip()
        if prompt:
            lines.append(f"Reference note {title}: {prompt}")
    return "\n".join(lines)


def _has_asset_card_revision(request: KeyframeGenerationRequest) -> bool:
    params = request.node_parameters if isinstance(request.node_parameters, dict) else {}
    return isinstance(params.get("asset_card_revision"), dict)


def _looks_like_animal_reference_request(request: KeyframeGenerationRequest) -> bool:
    params = request.node_parameters or {}
    parts = [request.prompt_text, request.optimized_prompt]
    for item in list(params.get("connected_reference_nodes") or [])[:4]:
        if isinstance(item, dict):
            parts.extend([str(item.get("title") or ""), str(item.get("prompt") or "")])
    text = " ".join(str(part or "") for part in parts).casefold()
    animal_terms = ("猫", "狸花猫", "黑猫", "白猫", "橘猫", "狗", "犬", "宠物", "动物", "cat", "tabby", "kitten", "feline", "dog", "puppy", "animal", "pet")
    return any(term.casefold() in text for term in animal_terms)


def _gate_closed_block(required_gate: str = REMOTE_IMAGE_ENV) -> dict[str, str]:
    return {
        "block_id": "remote_image_gate_closed",
        "reason": f"Set {required_gate}=true only for an explicit image/keyframe provider smoke.",
        "required_gate": required_gate,
    }


def _safe_error(value: str) -> str:
    lowered = value.lower()
    if "status_code 2049" in lowered and "invalid api key" in lowered:
        return "Image provider rejected the configured credential."
    if "api" in lowered or "key" in lowered or "secret" in lowered:
        return "Image provider configuration is not ready."
    return value[:160]


def provider_keyframe_prompt(value: str, *, limit: int = DEFAULT_IMAGE_PROMPT_LIMIT) -> str:
    lines = []
    for raw_line in strip_user_prompt_section_headers(str(value or "")).splitlines():
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


def _guarded_provider_keyframe_prompt(
    value: str,
    *,
    reference_count: int = 0,
    asset_card_revision: bool = False,
    limit: int = DEFAULT_IMAGE_PROMPT_LIMIT,
) -> str:
    guard = _image_generation_guard(reference_count=reference_count, asset_card_revision=asset_card_revision)
    reserve = len(guard) + 1
    base_limit = max(240, limit - reserve)
    prompt = provider_keyframe_prompt(value, limit=base_limit)
    if not prompt:
        return provider_keyframe_prompt(guard, limit=limit)
    if "保真约束" in prompt:
        return provider_keyframe_prompt(prompt, limit=limit)
    return provider_keyframe_prompt(f"{prompt} {guard}", limit=limit)


def _image_generation_guard(*, reference_count: int = 0, asset_card_revision: bool = False) -> str:
    base = (
        "保真约束：按用户提示直接生成清晰自然的主体，主体身份、物种、材质和关键特征必须可读；"
        "不要改成图标、标志、吉祥物、矢量插画、抽象符号或无关场景，除非用户明确要求这种风格。"
    )
    if reference_count <= 0:
        return base
    if asset_card_revision:
        return (
            f"{base} 资产卡局部修订约束：本次携带 {reference_count} 张参考图；"
            "reference image #1 is primary visual source of truth；changed fields are only editable delta；不要重设计身份、比例、版式或未编辑细节。"
        )
    return (
        f"{base} 参考图约束：本次携带 {reference_count} 张参考图；"
        "参考图只补充相关视觉线索，不能覆盖用户本次明确的新目标。"
    )


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
    "provider_keyframe_prompt",
)
