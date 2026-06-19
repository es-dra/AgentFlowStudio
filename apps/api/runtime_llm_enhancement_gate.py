from __future__ import annotations

import os
from typing import Any

from agentflow.algorithms.creative_intent_control import (
    has_visual_reference as algorithm_has_visual_reference,
    prompt_optimization_mode as algorithm_prompt_optimization_mode,
)
from apps.api.runtime_llm_enhancement_constants import (
    PROMPT_OPTIMIZER_MODEL_IDS,
    PROMPT_OPTIMIZER_PROVIDER,
    REMOTE_TRUE_VALUES,
)
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_provider_script import REMOTE_LLM_ENV


def provider_text_requested(request: PromptOptimizationRequest) -> bool:
    params = request.node_parameters or {}
    values = [
        params.get("llm_provider"),
        params.get("llm_model"),
    ]
    for value in values:
        normalized = str(value or "").strip().lower().replace(" ", "-")
        if normalized in PROMPT_OPTIMIZER_MODEL_IDS:
            return True
    return False


def llm_provider_gate() -> dict[str, str]:
    status = "ready_not_run" if os.environ.get(REMOTE_LLM_ENV, "").strip().lower() in REMOTE_TRUE_VALUES else "blocked"
    return {"capability": "llm", "env": REMOTE_LLM_ENV, "status": status}


def prompt_optimization_mode(request: PromptOptimizationRequest) -> str:
    return algorithm_prompt_optimization_mode(
        node_type=request.node_type,
        generation_target=request.generation_target,
        has_visual_reference=has_visual_reference(request),
    )


def has_visual_reference(request: PromptOptimizationRequest) -> bool:
    return algorithm_has_visual_reference(
        asset_refs=list(request.asset_refs),
        node_parameters=request.node_parameters or {},
        context_subgraph=request.context_subgraph,
        node_id=request.node_id,
    )


def provider_name(request: PromptOptimizationRequest) -> str:
    params = request.node_parameters or {}
    value = str(params.get("llm_provider") or "").strip()
    return value or PROMPT_OPTIMIZER_PROVIDER


def provider_candidates(request: PromptOptimizationRequest, registry: Any) -> list[str]:
    params = request.node_parameters or {}
    explicit = str(params.get("llm_provider") or "").strip()
    descriptors = getattr(registry, "_descriptors", {})
    descriptor_ids = sorted(descriptors) if isinstance(descriptors, dict) else []
    candidates: list[str] = []

    def add(value: str) -> None:
        if value and value not in candidates:
            candidates.append(value)

    if explicit:
        add(explicit)
        if explicit == PROMPT_OPTIMIZER_PROVIDER:
            for service_id in descriptor_ids:
                descriptor = descriptors[service_id]
                if getattr(descriptor, "modality", None) == "llm":
                    add(service_id)
    else:
        if PROMPT_OPTIMIZER_PROVIDER in descriptor_ids:
            add(PROMPT_OPTIMIZER_PROVIDER)

    if isinstance(descriptors, dict):
        for service_id in descriptor_ids:
            descriptor = descriptors[service_id]
            if getattr(descriptor, "modality", None) == "llm":
                add(service_id)
    return candidates


__all__ = (
    "has_visual_reference",
    "llm_provider_gate",
    "prompt_optimization_mode",
    "provider_candidates",
    "provider_name",
    "provider_text_requested",
)
