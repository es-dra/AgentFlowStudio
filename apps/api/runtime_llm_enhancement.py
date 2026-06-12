from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest, load_provider_registry
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_provider_script import REMOTE_LLM_ENV
from apps.api.runtime_store import reject_unsafe_text


REMOTE_TRUE_VALUES = {"1", "true", "yes", "on"}
MINIMAX_TEXT_PROVIDER = "minimax_m3"
MINIMAX_TEXT_MODEL = "MiniMax-M3"
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
BANNED_GENERIC_PHRASES = (
    "primary character",
    "primary scene",
    "stable identity",
    "user original prompt unclear",
    "原始提示词含义仍不明确",
    "用户原始提示词含义仍不明确",
)


def maybe_enhance_prompt_with_llm(
    request: PromptOptimizationRequest,
    assembly: dict[str, Any],
) -> dict[str, Any]:
    requested = minimax_text_requested(request)
    gate = llm_provider_gate()
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
    if gate["status"] == "blocked":
        return {**base, "status": "blocked", "discard_reason": "remote_llm_gate_closed"}

    try:
        registry = load_provider_registry()
        result = registry.dispatch(
            "llm",
            _provider_name(request),
            ProviderDispatchRequest(
                prompt=_enhancement_instruction(request, assembly),
                output_dir=Path("."),
                task_type="prompt_enhancement",
            ),
        )
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
            "user_prompt_sections": _sections_from_canonical(fallback),
        }

    sections = _sections_from_canonical(prompt)
    return {
        **base,
        "status": "applied",
        "provider_calls_started": True,
        "optimized_prompt": prompt,
        "user_prompt": prompt,
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
    if "<think" in text.lower() or "reasoning_content" in text.lower():
        raise ValueError("reasoning content is not allowed")
    if len(text) > 5000:
        raise ValueError("enhancement too long")
    missing = [label for label in REQUIRED_SECTION_LABELS if not _has_section(text, label)]
    if missing:
        raise ValueError("enhancement missing required sections")
    lowered = text.lower()
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
    lighting = _slot(slots, "lighting") or "灯光需要服务叙事情绪，避免无来源的强光和过度风格化。"
    style = request.style or _slot(slots, "style") or "cinematic"
    aspect = str(params.get("aspect_ratio") or params.get("spec") or "").strip()
    camera = str(params.get("camera") or "").strip()
    framing_bits = [bit for bit in (camera, f"画幅/规格：{aspect}" if aspect else "") if bit]
    framing = "；".join(framing_bits) or "镜头构图要明确主体位置、景别和背景信息层次。"
    prompt = "\n".join(
        [
            f"意图：围绕“{_compact(request.prompt_text)}”生成本轮节点可直接使用的创作提示词，先保证意图清晰和可控，再强化画面表现。",
            f"人物/主体：{subject}。保持身份、服装、姿态和情绪连续，不新增原始提示词没有的人物数量或身份。",
            f"场景/美术：{scene}。空间、道具和环境细节必须服务当前画面，不让背景抢走主体。",
            f"动作/情节：{action}",
            f"镜头/构图：{framing}",
            f"灯光：{lighting}",
            f"运动/时间推进：当前目标是 {request.generation_target}；关键帧优先保持单帧可读，视频节点再强调运动方向和节奏。",
            f"连续性：保留本轮提示词中的具体中文细节，并与项目人物、场景和风格资产保持一致；用户偏好只能作为低权重风格倾向。当前风格：{style}。",
            "负面约束：不要水印、文字乱码、过度磨皮、五官或手部畸形、身份漂移、镜头语言互相冲突；不要暴露 provider、路径、token 或内部工程信息。",
        ]
    )
    reject_unsafe_text(prompt)
    return prompt


def _slot(slots: Any, key: str) -> str:
    if not isinstance(slots, dict):
        return ""
    value = slots.get(key)
    if value is None:
        return ""
    return _compact(str(value))


def _compact(value: str, limit: int = 120) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _provider_name(request: PromptOptimizationRequest) -> str:
    params = request.node_parameters or {}
    value = str(params.get("llm_provider") or "").strip()
    return value or MINIMAX_TEXT_PROVIDER


def _enhancement_instruction(request: PromptOptimizationRequest, assembly: dict[str, Any]) -> str:
    return "\n".join(
        [
            "你是 AFS 创作意图控制智能体的中文提示词编辑器。",
            "请把 canonical brief 改写成适合节点输入框展示和继续生成的中文创作提示词。",
            "必须保留硬约束、人物身份、场景连续性、镜头意图、灯光意图和负面约束。",
            "必须保留用户原始提示词里的具体细节；不要替换成“主体角色”“主要场景”“稳定身份”等模板化占位词。",
            "当前节点原始提示词和 node parameters 是本轮最高优先级；如果 canonical brief 或历史上下文与原始提示词冲突，必须以原始提示词为准。",
            "禁止新增原始提示词没有的人物数量、职业、地点、道具和剧情事实。",
            "最终展示给用户的内容必须以中文为主；只有模型专用术语或镜头术语确实更清楚时才可夹少量英文。",
            "每个段落都要针对本次请求写具体内容，避免可复用模板腔。",
            "不要输出推理过程、chain-of-thought、工具日志、provider 元数据、路径、URL、token 或实现说明。",
            "只返回以下中文段落，顺序固定，标签也必须使用中文：",
            "意图：",
            "人物/主体：",
            "场景/美术：",
            "动作/情节：",
            "镜头/构图：",
            "灯光：",
            "运动/时间推进：",
            "连续性：",
            "负面约束：",
            "",
            f"Node type: {request.node_type}",
            f"Generation target: {request.generation_target}",
            f"Target platform: {request.target_platform}",
            f"Original user prompt: {request.prompt_text}",
            "",
            "Canonical brief:",
            str(assembly["optimized_prompt"]),
            "",
            "再次确认：请以 Original user prompt 为准，只输出上面列出的中文段落。",
        ]
    )


def _sections_from_canonical(prompt: str) -> list[dict[str, str]]:
    pattern = re.compile(r"^([^:\n：]{2,64})[:：]\s*(.*)$")
    sections: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in prompt.splitlines():
        match = pattern.match(line.strip())
        if match:
            current = {"title": match.group(1).strip(), "text": match.group(2).strip()}
            sections.append(current)
            continue
        if current and line.strip():
            current["text"] = f"{current['text']} {line.strip()}".strip()
    return sections


def _has_section(text: str, label: str) -> bool:
    return re.search(rf"^{re.escape(label)}\s*[:：]", text, flags=re.MULTILINE) is not None


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
