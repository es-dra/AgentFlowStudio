from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest, load_provider_registry
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_provider_script import REMOTE_LLM_ENV
from apps.api.runtime_prompt_text import plain_prompt_from_sections, strip_user_prompt_section_headers
from apps.api.runtime_store import reject_unsafe_text


REMOTE_TRUE_VALUES = {"1", "true", "yes", "on"}
MINIMAX_TEXT_PROVIDER = "minimax_m3"
MINIMAX_TEXT_MODEL = "MiniMax-M2.7-highspeed"
MINIMAX_MODEL_IDS = {
    "minimax-m3",
    "minimax_m3",
    "minimax-m3-enhance",
    "minimax_m3_enhance",
    "minimax-m3-prompt",
    "minimax_m3_prompt",
    "minimax-image-01",
}
REQUIRED_SECTION_LABELS = (
    "意图",
    "人物/主体",
    "场景/美术",
    "镜头/构图",
    "灯光",
    "负面约束",
)
SECTION_ORDER = (
    "意图",
    "人物/主体",
    "场景/美术",
    "动作/情节",
    "镜头/构图",
    "灯光",
    "运动/时间推进",
    "连续性",
    "负面约束",
)
BANNED_GENERIC_PHRASES = (
    "primary character",
    "primary scene",
    "stable identity",
    "user original prompt unclear",
    "用户原始提示词含义仍不明确",
    "主体角色",
    "主要场景",
)


def maybe_enhance_prompt_with_llm(
    request: PromptOptimizationRequest,
    assembly: dict[str, Any],
) -> dict[str, Any]:
    requested = minimax_text_requested(request)
    base = {
        "requested": requested,
        "provider": MINIMAX_TEXT_PROVIDER if requested else "not_requested",
        "model": MINIMAX_TEXT_MODEL if requested else "not_requested",
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
            prompt=_enhancement_instruction(request, assembly),
            output_dir=Path("."),
            task_type="prompt_enhancement",
        )
        result = _dispatch_llm_with_fallback(registry, request, dispatch_request)
        enhanced = str(result.get("text") or "")
    except ModelGatewayError as exc:
        return {**base, "status": "discarded", "discard_reason": _safe_reason(str(exc))}

    try:
        prompt = sanitize_enhanced_prompt(enhanced)
    except ValueError as exc:
        fallback = deterministic_chinese_fallback_prompt(request, assembly)
        return {
            **base,
            "status": "discarded",
            "provider_calls_started": True,
            "discard_reason": _safe_reason(str(exc)),
            "optimized_prompt": fallback,
            "user_prompt": fallback,
            "user_prompt_plain": strip_user_prompt_section_headers(fallback),
            "user_prompt_sections": _sections_from_canonical(fallback),
        }

    sections = _sections_from_canonical(prompt)
    return {
        **base,
        "status": "applied",
        "provider_calls_started": True,
        "optimized_prompt": prompt,
        "user_prompt": prompt,
        "user_prompt_plain": plain_prompt_from_sections(sections) or strip_user_prompt_section_headers(prompt),
        "user_prompt_sections": sections,
    }


def minimax_text_requested(request: PromptOptimizationRequest) -> bool:
    params = request.node_parameters or {}
    value = str(params.get("model") or params.get("llm_model") or "").strip().lower()
    normalized = value.replace(" ", "-")
    return normalized in MINIMAX_MODEL_IDS


def llm_provider_gate() -> dict[str, str]:
    status = "ready_not_run" if os.environ.get(REMOTE_LLM_ENV, "").strip().lower() in REMOTE_TRUE_VALUES else "blocked"
    return {"capability": "llm", "env": REMOTE_LLM_ENV, "status": status}


def sanitize_enhanced_prompt(value: str) -> str:
    text = _strip_code_fence(value).strip()
    if not text:
        raise ValueError("empty enhancement")
    lowered = text.lower()
    if "<think" in lowered or "reasoning_content" in lowered or "\nthinking:" in lowered:
        raise ValueError("reasoning content is not allowed")
    if len(text) > 5000:
        raise ValueError("enhancement too long")
    missing = [label for label in REQUIRED_SECTION_LABELS if not _has_section(text, label)]
    if missing:
        raise ValueError("enhancement missing required sections")
    if any(phrase in lowered for phrase in BANNED_GENERIC_PHRASES):
        raise ValueError("enhancement includes generic placeholder")
    reject_unsafe_text(text)
    return text


def deterministic_chinese_fallback_prompt(
    request: PromptOptimizationRequest,
    assembly: dict[str, Any],
) -> str:
    slots = assembly.get("selected_slots") if isinstance(assembly, dict) else {}
    params = request.node_parameters or {}
    subject = _slot(slots, "subject") or _compact(request.prompt_text)
    scene = _slot(slots, "scene") or _compact(request.prompt_text)
    action = _slot(slots, "action") or _slot(slots, "emotion") or "保留当前提示词中的核心动作和情绪转折。"
    lighting = _slot(slots, "lighting") or "灯光服务叙事情绪，避免无来源强光和过度风格化。"
    style = request.style or _slot(slots, "style") or "cinematic"
    aspect = str(params.get("aspect_ratio") or params.get("spec") or "").strip()
    camera = str(params.get("camera") or "").strip()
    framing_bits = [bit for bit in (camera, f"画幅/规格：{aspect}" if aspect else "") if bit]
    framing = "；".join(framing_bits) or "明确主体位置、景别和背景信息层次。"
    prompt = "\n".join(
        [
            f"意图：围绕“{_compact(request.prompt_text)}”生成本轮节点可直接使用的创作提示词，先保证意图清晰和可控，再强化画面表现。",
            f"人物/主体：{subject}。保持身份、服装、姿态和情绪连续，不新增原始提示词没有的人物数量或身份。",
            f"场景/美术：{scene}。空间、道具和环境细节服务当前画面，不让背景抢走主体。",
            f"动作/情节：{action}",
            f"镜头/构图：{framing}",
            f"灯光：{lighting}",
            f"运动/时间推进：当前目标是 {request.generation_target}；关键帧优先保持单帧可读，视频节点再强调运动方向和节奏。",
            f"连续性：保留本轮提示词中的具体细节，并与项目人物、场景和风格资产保持一致；用户偏好只作为低权重风格倾向。当前风格：{style}。",
            "负面约束：不要水印、文字乱码、过度磨皮、五官或手部畸形、身份漂移、镜头语言互相冲突。",
        ]
    )
    reject_unsafe_text(prompt)
    return prompt


def _enhancement_instruction(request: PromptOptimizationRequest, assembly: dict[str, Any]) -> str:
    if request.node_type in {"text", "script"}:
        return _text_enhancement_instruction(request)
    return _visual_enhancement_instruction(request)


def _visual_enhancement_instruction(request: PromptOptimizationRequest) -> str:
    parts = [
        f"意图：围绕“{request.prompt_text}”完成本次生成。",
        "人物/主体：保留原始提示词中的主体；若写到“这个人物”，必须理解为参考图中的同一个人物。",
        "场景/美术：保持参考图或原提示中的场景信息；未指定时不要新增具体地点。",
        f"动作/情节：只执行“{request.prompt_text}”这一项变化，不扩写新剧情。",
        "镜头/构图：关键帧清晰呈现主体变化，构图稳定，主体可辨识。",
        "灯光：保持自然可读的光线，不改变参考图的主要光感。",
        "运动/时间推进：单帧关键画面，不制造多阶段动作。",
        "连续性：保持参考图人物身份、脸部辨识度、服装、体型比例和整体风格；只改变用户明确要求改变的部分。",
        "负面约束：不要水印、文字乱码、五官畸形、身份漂移、服装漂移、背景大幅变化。",
    ]
    return "\n".join(
        [
            f"原始提示词：{request.prompt_text}",
            "硬性要求：只优化提示词，不解释、不输出思考过程、不添加标题；保留用户明确要求，尤其是图生图时只改用户点名的部分。",
            "输出必须只有以下九行，标签不可改名：意图、人物/主体、场景/美术、动作/情节、镜头/构图、灯光、运动/时间推进、连续性、负面约束。",
            " ".join(parts),
        ]
    )


def _text_enhancement_instruction(request: PromptOptimizationRequest) -> str:
    parts = [
        f"意图：围绕“{request.prompt_text}”形成清晰、可继续扩写的创作方向。",
        f"人物/主体：以“{request.prompt_text}”中的主体为核心，不新增无关主角。",
        "场景/美术：保留原始提示词中的场景信息；未指定时只补充服务主题的环境氛围。",
        f"动作/情节：围绕“{request.prompt_text}”展开一个单一、明确的情境，不扩写成完整长故事。",
        "镜头/构图：用画面化语言说明主体位置、视角和信息层次。",
        "灯光：根据情绪选择自然、可读的光线描述。",
        "运动/时间推进：保持节奏克制，说明当前瞬间或短段落的时间感。",
        "连续性：保留原始提示词的主题、主体和情绪，不漂移到无关题材。",
        "负面约束：不要模板化空话、不要新增无关角色、不要过度解释、不要水印或乱码。",
    ]
    return "\n".join(
        [
            f"原始提示词：{request.prompt_text}",
            "硬性要求：只优化提示词，不解释、不输出思考过程、不添加标题；保持主题清楚、可生成、可继续扩写。",
            "输出必须只有以下九行，标签不可改名：意图、人物/主体、场景/美术、动作/情节、镜头/构图、灯光、运动/时间推进、连续性、负面约束。",
            " ".join(parts),
        ]
    )


def _sections_from_canonical(prompt: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in prompt.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        matched = _section_label(line)
        if matched:
            text = line[len(matched):].lstrip("：: ").strip()
            current = {"title": matched, "text": text}
            sections.append(current)
            continue
        if current:
            current["text"] = f"{current['text']} {line}".strip()
    return sections


def _section_label(line: str) -> str:
    for label in SECTION_ORDER:
        if line.startswith(f"{label}：") or line.startswith(f"{label}:"):
            return label
    return ""


def _has_section(text: str, label: str) -> bool:
    return any(line.strip().startswith(f"{label}：") or line.strip().startswith(f"{label}:") for line in text.splitlines())


def _slot(slots: Any, key: str) -> str:
    if not isinstance(slots, dict):
        return ""
    value = slots.get(key)
    return _compact(str(value)) if value is not None else ""


def _compact(value: str, limit: int = 120) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _provider_name(request: PromptOptimizationRequest) -> str:
    params = request.node_parameters or {}
    value = str(params.get("llm_provider") or "").strip()
    return value or MINIMAX_TEXT_PROVIDER


def _provider_candidates(request: PromptOptimizationRequest, registry: Any) -> list[str]:
    params = request.node_parameters or {}
    explicit = str(params.get("llm_provider") or "").strip()
    candidates: list[str] = []
    for value in (explicit, MINIMAX_TEXT_PROVIDER, "minimax_llm"):
        if value and value not in candidates:
            candidates.append(value)
    descriptors = getattr(registry, "_descriptors", {})
    if isinstance(descriptors, dict):
        for service_id, descriptor in sorted(descriptors.items()):
            if getattr(descriptor, "modality", None) == "llm" and service_id not in candidates:
                candidates.append(service_id)
    return candidates


def _dispatch_llm_with_fallback(
    registry: Any,
    request: PromptOptimizationRequest,
    dispatch_request: ProviderDispatchRequest,
) -> dict[str, Any]:
    missing: list[str] = []
    for service_id in _provider_candidates(request, registry):
        try:
            return registry.dispatch("llm", service_id, dispatch_request)
        except ModelGatewayError as exc:
            message = str(exc)
            if "Provider service not found" in message or "OpenAI-compatible HTTP error 404" in message:
                missing.append(service_id)
                continue
            raise
    missing_text = ", ".join(missing) if missing else _provider_name(request)
    raise ModelGatewayError(f"Provider service not found: {missing_text}")


def _strip_code_fence(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _safe_reason(value: str) -> str:
    lowered = value.lower()
    if "key" in lowered or "token" in lowered or "authorization" in lowered:
        return "provider_configuration_not_ready"
    return value[:120]


__all__ = (
    "MINIMAX_TEXT_MODEL",
    "MINIMAX_TEXT_PROVIDER",
    "llm_provider_gate",
    "maybe_enhance_prompt_with_llm",
    "minimax_text_requested",
    "sanitize_enhanced_prompt",
    "deterministic_chinese_fallback_prompt",
)
