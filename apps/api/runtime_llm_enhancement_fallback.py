from __future__ import annotations

import re
from typing import Any

from agentflow.algorithms.creative_intent_control import deterministic_video_fallback_prompt as algorithm_video_fallback_prompt
from apps.api.runtime_llm_enhancement_constants import BANNED_GENERIC_PHRASES
from apps.api.runtime_llm_enhancement_gate import prompt_optimization_mode
from apps.api.runtime_llm_enhancement_safety import (
    compact,
    contains_cjk,
    reference_hint_terms,
    slot,
    visual_reference_hint,
)
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_store import reject_unsafe_text


def deterministic_chinese_fallback_prompt(
    request: PromptOptimizationRequest,
    assembly: dict[str, Any],
) -> str:
    mode = prompt_optimization_mode(request)
    if mode == "i2i":
        return deterministic_i2i_fallback_prompt(request)
    if mode in {"i2v", "t2v"}:
        return deterministic_video_fallback_prompt(request, assembly)
    slots = assembly.get("selected_slots") if isinstance(assembly, dict) else {}
    params = request.node_parameters or {}
    subject = slot(slots, "subject") or compact(request.prompt_text)
    scene = slot(slots, "scene") or compact(request.prompt_text)
    action = slot(slots, "action") or slot(slots, "emotion") or "保留当前提示词中的核心动作和情绪转折。"
    lighting = slot(slots, "lighting") or "灯光服务叙事情绪，避免无来源强光和过度风格化。"
    style = request.style or slot(slots, "style") or "cinematic"
    aspect = str(params.get("aspect_ratio") or params.get("spec") or "").strip()
    camera = str(params.get("camera") or "").strip()
    framing_bits = [bit for bit in (camera, f"画幅/规格：{aspect}" if aspect else "") if bit]
    framing = "；".join(framing_bits) or "明确主体位置、景别和背景信息层次。"
    prompt = "\n".join(
        [
            f"意图：围绕“{compact(request.prompt_text)}”生成本轮节点可直接使用的创作提示词，先保证意图清晰和可控，再强化画面表现。",
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


def deterministic_i2i_fallback_prompt(request: PromptOptimizationRequest) -> str:
    prompt_text = compact(request.prompt_text)
    reference_hint = visual_reference_hint(request)
    reference_subject = reference_hint or "参考图中的同一人物"
    wardrobe_guard = "保持参考图中的服装、体型比例、姿态、背景和整体风格"
    if "校服" in reference_hint:
        wardrobe_guard = "保持校服款式、蓝白运动校服配色、体型比例、姿态、背景和整体风格"
    hair_guard = "只将头发长度改为短发；除非用户明确要求，不改变发色、脸型、五官、年龄感和人物身份"
    if "短发" in prompt_text and not any(color in prompt_text for color in ("金发", "棕发", "红发", "白发", "银发")):
        hair_guard = "只将头发长度改为短发，保持原参考图发色和发质方向；不要染浅、不要变成金发或棕发"
    prompt = "\n".join(
        [
            f"意图：对{reference_subject}执行“{prompt_text}”，本次只做这一项图生图编辑。",
            f"人物/主体：{reference_subject}；保持参考图脸部辨识度、五官比例、眼神、年龄感和人物身份；{hair_guard}。",
            f"场景/美术：保持参考图原有场景、道具、背景层次和画面氛围；{wardrobe_guard}。",
            f"动作/情节：人物保持参考图原有静态姿态和身体朝向，只呈现“{prompt_text}”带来的外观变化。",
            "镜头/构图：保持参考图主体大小、三视图或半身/全身布局、主体位置和构图关系稳定，不重新设计画面。",
            "灯光：保持参考图主要光源方向、明暗关系和曝光，不新增无来源强光。",
            "运动/时间推进：单帧图像编辑，不制造多阶段动作或剧情。",
            "连续性：保持身份、脸部、服装、体型、姿态、背景和画风连续；只改变用户明确点名的头发长度。",
            "负面约束：不要身份漂移、不要换脸、不要换服装、不要改变校服配色、不要染发变浅、不要新增人物、不要水印、不要文字乱码、不要五官畸形。",
        ]
    )
    reject_unsafe_text(prompt)
    return prompt


def deterministic_video_fallback_prompt(request: PromptOptimizationRequest, assembly: dict[str, Any]) -> str:
    slots = assembly.get("selected_slots") if isinstance(assembly, dict) else {}
    prompt = algorithm_video_fallback_prompt(
        prompt_text=request.prompt_text,
        node_parameters=request.node_parameters or {},
        slots=slots,
    )
    reject_unsafe_text(prompt)
    return prompt


def salvage_prompt_from_llm_article(value: str, request: PromptOptimizationRequest) -> str:
    candidate = extract_article_prompt_candidate(value)
    if not candidate:
        raise ValueError("enhancement missing required sections")
    negative = extract_article_negative_prompt(value)
    prompt = "\n".join(
        [
            f"意图：围绕“{compact(request.prompt_text, 160)}”生成可直接用于本节点的画面提示词。",
            f"人物/主体：{compact(candidate, 260)}",
            f"场景/美术：{compact(candidate, 260)}",
            f"动作/情节：{compact(request.prompt_text, 180)}",
            f"镜头/构图：{compact(candidate, 220)}",
            f"灯光：{compact(candidate, 220)}",
            "运动/时间推进：以当前节点目标为准，关键帧保持单帧可读；视频节点再强调短时间动作方向。",
            "连续性：保持上文主体、场景、服装、身份和项目风格一致，不漂移到无关题材。",
            f"负面约束：{negative or '不要水印、文字乱码、畸形肢体、身份漂移、无关人物或不合理背景元素。'}",
        ]
    )
    reject_unsafe_text(prompt)
    return prompt


def extract_article_prompt_candidate(value: str) -> str:
    lines = str(value or "").splitlines()
    candidates: list[tuple[int, str]] = []
    prefer_chinese = False
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if "中文" in line and "Prompt" in line:
            prefer_chinese = True
            continue
        cleaned = line.lstrip(">").strip().strip("*` ")
        if len(cleaned) < 40:
            continue
        lowered = cleaned.lower()
        if any(phrase in lowered for phrase in BANNED_GENERIC_PHRASES):
            continue
        if "negative prompt" in lowered or lowered.startswith(("low quality", "使用技巧", "要素 |")):
            continue
        if "|" in cleaned and cleaned.count("|") >= 2:
            continue
        score = len(cleaned)
        if prefer_chinese or contains_cjk(cleaned):
            score += 500
        if "prompt" in lowered:
            score -= 80
        candidates.append((score, cleaned))
    if not candidates:
        return ""
    return max(candidates, key=lambda item: item[0])[1]


def extract_article_negative_prompt(value: str) -> str:
    lowered = str(value or "").lower()
    if "negative prompt" not in lowered and "负向提示" not in str(value) and "负面" not in str(value):
        return ""
    fenced = re.findall(r"```(?:[a-zA-Z0-9_-]+)?\s*(.*?)```", str(value), flags=re.DOTALL)
    for block in fenced:
        text = " ".join(block.split())
        if len(text) >= 20:
            return compact(text, 220)
    return ""


__all__ = (
    "deterministic_chinese_fallback_prompt",
    "deterministic_i2i_fallback_prompt",
    "deterministic_video_fallback_prompt",
    "salvage_prompt_from_llm_article",
)
