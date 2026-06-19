from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest, load_provider_registry
from apps.api.runtime_llm_enhancement_constants import PROMPT_OPTIMIZER_PROVIDER
from apps.api.runtime_llm_enhancement_dispatch import dispatch_llm_with_fallback
from apps.api.runtime_llm_enhancement_fallback import deterministic_chinese_fallback_prompt, salvage_prompt_from_llm_article
from apps.api.runtime_llm_enhancement_gate import (
    llm_provider_gate,
    prompt_optimization_mode,
    provider_name,
    provider_text_requested,
)
from apps.api.runtime_llm_enhancement_instructions import enhancement_instruction, strict_format_retry_instruction
from apps.api.runtime_llm_enhancement_safety import (
    safe_reason,
    sanitize_enhanced_prompt,
    sections_from_canonical,
    validate_enhanced_prompt_specificity,
)
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_prompt_text import plain_prompt_from_sections, strip_user_prompt_section_headers


def maybe_enhance_prompt_with_llm(
    request: PromptOptimizationRequest,
    assembly: dict[str, Any],
) -> dict[str, Any]:
    requested = provider_text_requested(request)
    optimization_mode = prompt_optimization_mode(request)
    base = {
        "requested": requested,
        "provider": provider_name(request) if requested else "not_requested",
        "model": "provider_configured" if requested else "not_requested",
        "optimization_mode": optimization_mode,
        "status": "not_requested",
        "provider_calls_started": False,
        "discard_reason": None,
    }
    if not requested:
        return base
    if llm_provider_gate()["status"] == "blocked":
        return {**base, "status": "blocked", "discard_reason": "remote_llm_gate_closed"}

    try:
        registry = load_provider_registry()
        dispatch_request = ProviderDispatchRequest(
            prompt=enhancement_instruction(request, assembly),
            output_dir=Path("."),
            task_type="prompt_enhancement",
        )
        result = dispatch_llm_with_fallback(registry, request, dispatch_request)
        enhanced = str(result.get("text") or "")
    except ModelGatewayError as exc:
        return {**base, "status": "discarded", "discard_reason": safe_reason(str(exc))}

    retry_count = 0
    try:
        prompt = sanitize_enhanced_prompt(enhanced)
    except ValueError as exc:
        if str(exc) == "enhancement missing required sections":
            retry_result = _retry_or_salvage_enhancement(base, registry, request, assembly, enhanced)
            if retry_result.get("status") in {"applied", "continue"}:
                prompt = str(retry_result["prompt"])
                retry_count = int(retry_result.get("format_retry_count") or 1)
                base["format_salvage_used"] = bool(retry_result.get("format_salvage_used"))
            else:
                return retry_result
        else:
            return _discard_with_fallback(base, request, assembly, str(exc), retry_count=retry_count)
    try:
        validate_enhanced_prompt_specificity(prompt, request)
    except ValueError as exc:
        fallback = deterministic_chinese_fallback_prompt(request, assembly)
        return {
            **base,
            "status": "applied",
            "provider_calls_started": True,
            "discard_reason": safe_reason(str(exc)),
            "guardrail_fallback_used": True,
            **_prompt_payload(fallback),
        }

    return {
        **base,
        "status": "applied",
        "provider_calls_started": True,
        "format_retry_count": retry_count,
        "format_salvage_used": bool(base.get("format_salvage_used")),
        **_prompt_payload(prompt),
    }


def _retry_or_salvage_enhancement(
    base: dict[str, Any],
    registry: Any,
    request: PromptOptimizationRequest,
    assembly: dict[str, Any],
    enhanced: str,
) -> dict[str, Any]:
    try:
        retry_request = ProviderDispatchRequest(
            prompt=strict_format_retry_instruction(request),
            output_dir=Path("."),
            task_type="prompt_enhancement_retry",
        )
        result = dispatch_llm_with_fallback(registry, request, retry_request)
        retried = str(result.get("text") or "")
        return {"status": "continue", "prompt": sanitize_enhanced_prompt(retried), "format_retry_count": 1}
    except (ModelGatewayError, ValueError) as retry_exc:
        try:
            prompt = salvage_prompt_from_llm_article(enhanced, request)
            return {
                "status": "continue",
                "prompt": prompt,
                "format_retry_count": 1,
                "format_salvage_used": True,
            }
        except ValueError:
            return _discard_with_fallback(
                base,
                request,
                assembly,
                str(retry_exc),
                retry_count=1,
                salvage_used=False,
            )


def _discard_with_fallback(
    base: dict[str, Any],
    request: PromptOptimizationRequest,
    assembly: dict[str, Any],
    reason: str,
    *,
    retry_count: int,
    salvage_used: bool | None = None,
) -> dict[str, Any]:
    fallback = deterministic_chinese_fallback_prompt(request, assembly)
    result = {
        **base,
        "status": "discarded",
        "provider_calls_started": True,
        "discard_reason": safe_reason(reason),
        "format_retry_count": retry_count,
        **_prompt_payload(fallback),
    }
    if salvage_used is not None:
        result["format_salvage_used"] = salvage_used
    return result


def _prompt_payload(prompt: str) -> dict[str, Any]:
    sections = sections_from_canonical(prompt)
    return {
        "optimized_prompt": prompt,
        "user_prompt": prompt,
        "user_prompt_plain": plain_prompt_from_sections(sections) or strip_user_prompt_section_headers(prompt),
        "user_prompt_sections": sections,
    }


_enhancement_instruction = enhancement_instruction
_strict_format_retry_instruction = strict_format_retry_instruction
_dispatch_llm_with_fallback = dispatch_llm_with_fallback
_safe_reason = safe_reason
_salvage_prompt_from_llm_article = salvage_prompt_from_llm_article
_sections_from_canonical = sections_from_canonical


__all__ = (
    "PROMPT_OPTIMIZER_PROVIDER",
    "deterministic_chinese_fallback_prompt",
    "llm_provider_gate",
    "maybe_enhance_prompt_with_llm",
    "provider_text_requested",
    "sanitize_enhanced_prompt",
)
