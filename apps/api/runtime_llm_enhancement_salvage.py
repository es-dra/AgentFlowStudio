from __future__ import annotations

import re

from apps.api.runtime_llm_enhancement_constants import BANNED_GENERIC_PHRASES
from apps.api.runtime_llm_enhancement_safety import compact, contains_cjk
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_store import reject_unsafe_text


def salvage_prompt_from_llm_article(value: str, request: PromptOptimizationRequest) -> str:
    candidate = extract_article_prompt_candidate(value)
    if not candidate:
        raise ValueError("enhancement missing required sections")
    negative = extract_article_negative_prompt(value)
    prompt = "\n".join(
        [
            f"意图：围绕“{compact(request.prompt_text, 160)}”生成可直接用于本节点的画面提示词。",
            f"角色/主体：{compact(candidate, 260)}",
            f"场景/美术：{compact(candidate, 260)}",
            f"动作/情节：{compact(request.prompt_text, 180)}",
            f"镜头/构图：{compact(candidate, 220)}",
            f"灯光：{compact(candidate, 220)}",
            "运动/时间推进：以当前节点目标为准，关键帧保持单帧可读；视频节点再强调短时间动作方向。",
            "连续性：保持上文主体、场景、服装、身份和项目风格一致，不漂移到无关题材。",
            f"负面约束：{negative or '不要水印、文字乱码、畸形肢体、身份漂移、无关角色或不合理背景元素。'}",
        ]
    )
    reject_unsafe_text(prompt)
    return prompt


def extract_article_prompt_candidate(value: str) -> str:
    candidates: list[tuple[int, str]] = []
    prefer_chinese = False
    for raw_line in str(value or "").splitlines():
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
    return max(candidates, key=lambda item: item[0])[1] if candidates else ""


def extract_article_negative_prompt(value: str) -> str:
    source = str(value or "")
    lowered = source.lower()
    if "negative prompt" not in lowered and "负向提示" not in source and "负面" not in source:
        return ""
    fenced = re.findall(r"```(?:[a-zA-Z0-9_-]+)?\s*(.*?)```", source, flags=re.DOTALL)
    for block in fenced:
        text = " ".join(block.split())
        if len(text) >= 20:
            return compact(text, 220)
    return ""


__all__ = ("extract_article_negative_prompt", "extract_article_prompt_candidate", "salvage_prompt_from_llm_article")
