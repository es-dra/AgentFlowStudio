from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest, load_provider_registry
from apps.api.runtime_llm_enhancement_constants import PROMPT_OPTIMIZER_PROVIDER
from apps.api.runtime_llm_enhancement_dispatch import dispatch_llm_with_fallback
from apps.api.runtime_llm_enhancement_fallback import deterministic_chinese_fallback_prompt
from apps.api.runtime_llm_enhancement_salvage import salvage_prompt_from_llm_article
from apps.api.runtime_llm_enhancement_gate import (
    llm_provider_gate,
    prompt_optimization_mode,
    provider_name,
    provider_text_requested,
)
from apps.api.runtime_llm_enhancement_instructions import (
    enhancement_instruction,
    is_script_expansion_request,
    strict_format_retry_instruction,
)
from apps.api.runtime_llm_enhancement_safety import (
    contains_tool_failure_text,
    safe_reason,
    sanitize_enhanced_prompt,
    sections_from_canonical,
    validate_enhanced_prompt_specificity,
)
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_prompt_text import plain_prompt_from_sections, strip_user_prompt_section_headers
from apps.api.runtime_store import reject_unsafe_text


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
    if is_script_expansion_request(request):
        return _script_expansion_result(base, enhanced, request, assembly)
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
        elif str(exc) == "enhancement contains tool failure text":
            fallback = deterministic_chinese_fallback_prompt(request, assembly)
            return {
                **base,
                "status": "applied",
                "provider_calls_started": True,
                "discard_reason": "provider_output_tool_failure_text",
                "guardrail_fallback_used": True,
                "format_retry_count": retry_count,
                **_prompt_payload(fallback),
            }
        else:
            return _discard_with_fallback(base, request, assembly, str(exc), retry_count=retry_count)
    if contains_tool_failure_text(prompt):
        fallback = deterministic_chinese_fallback_prompt(request, assembly)
        return {
            **base,
            "status": "applied",
            "provider_calls_started": True,
            "discard_reason": "provider_output_tool_failure_text",
            "guardrail_fallback_used": True,
            "format_retry_count": retry_count,
            "format_salvage_used": bool(base.get("format_salvage_used")),
            **_prompt_payload(fallback),
        }
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


def _script_expansion_result(
    base: dict[str, Any],
    enhanced: str,
    request: PromptOptimizationRequest,
    assembly: dict[str, Any],
) -> dict[str, Any]:
    try:
        prompt = sanitize_script_expansion(enhanced, request)
    except ValueError as exc:
        prompt = deterministic_script_expansion_fallback(request)
        return {
            **base,
            "status": "applied",
            "provider_calls_started": True,
            "discard_reason": safe_reason(str(exc)),
            "guardrail_fallback_used": True,
            "format_retry_count": 0,
            "optimized_prompt": prompt,
            "user_prompt": prompt,
            "user_prompt_plain": prompt,
            "user_prompt_sections": [],
        }
    return {
        **base,
        "status": "applied",
        "provider_calls_started": True,
        "format_retry_count": 0,
        "optimized_prompt": prompt,
        "user_prompt": prompt,
        "user_prompt_plain": prompt,
        "user_prompt_sections": [],
    }


def sanitize_script_expansion(value: str, request: PromptOptimizationRequest) -> str:
    prompt = str(value or "").strip()
    if not prompt:
        raise ValueError("empty script expansion")
    if contains_tool_failure_text(prompt):
        raise ValueError("script expansion contains tool failure text")
    lower = prompt.lower()
    if "<think" in lower or "reasoning_content" in lower or "\nthinking:" in lower:
        raise ValueError("reasoning content is not allowed")
    forbidden = (
        "请把下面的一句话扩写",
        "输出要求",
        "原始想法：",
        "意图：",
        "角色/主体：",
        "场景/美术：",
        "镜头/构图：",
        "负面约束：",
        "分镜 01",
        "推进主体",
        "展示变化",
        "收束结果",
    )
    if any(item in prompt for item in forbidden):
        raise ValueError("script expansion copied instructions or placeholder sections")
    if "片名" not in prompt and "《" not in prompt:
        raise ValueError("script expansion missing title")
    if len(prompt) < 80:
        raise ValueError("script expansion too short")
    reject_unsafe_text(prompt)
    return prompt[:5000]


def deterministic_script_expansion_fallback(request: PromptOptimizationRequest) -> str:
    params = request.node_parameters or {}
    source = str(params.get("source_idea") or request.prompt_text).strip()
    compact_source = " ".join(source.split()) or "一个新的短视频故事"
    title = "".join(ch for ch in compact_source if ch not in "，。！？；、,.!?;:： ")[:12] or "短片"
    prompt = "\n".join(
        [
            f"片名：《{title}》",
            "",
            f"{compact_source}。故事从这个异常而具体的瞬间开始：熟悉的人物被放进陌生的现代环境，第一反应不是立刻解释一切，而是通过观察、迟疑和行动让观众理解处境。",
            "",
            "随后，角色开始和周围世界发生碰撞。现代空间里的声音、光线、人群和物件不断提醒她已经离开原本的童话秩序，她必须在惊讶和不安中做出一个小选择，让故事从设定推进成行动。",
            "",
            "结尾停在一个清晰的决定上：她没有完全弄懂这个时代，却主动向前迈出一步，抓住能帮助自己继续寻找答案的线索。这个结尾留下继续拆分分镜的空间，也保留人物身份、场景变化和情绪转折。",
        ]
    )
    reject_unsafe_text(prompt)
    return prompt


_enhancement_instruction = enhancement_instruction
_strict_format_retry_instruction = strict_format_retry_instruction
_dispatch_llm_with_fallback = dispatch_llm_with_fallback
_safe_reason = safe_reason
_salvage_prompt_from_llm_article = salvage_prompt_from_llm_article
_sections_from_canonical = sections_from_canonical


__all__ = (
    "PROMPT_OPTIMIZER_PROVIDER",
    "deterministic_chinese_fallback_prompt",
    "deterministic_script_expansion_fallback",
    "llm_provider_gate",
    "maybe_enhance_prompt_with_llm",
    "provider_text_requested",
    "sanitize_enhanced_prompt",
)
