from __future__ import annotations

import re
from typing import Any

from apps.api.runtime_llm_enhancement_constants import (
    BANNED_GENERIC_PHRASES,
    REQUIRED_SECTION_LABELS,
    SECTION_LABEL_ALIASES,
)
from apps.api.runtime_llm_enhancement_gate import prompt_optimization_mode
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_store import reject_unsafe_text


def sanitize_enhanced_prompt(value: str) -> str:
    text = strip_code_fence(value).strip()
    if not text:
        raise ValueError("empty enhancement")
    text = normalize_enhancement_sections(text)
    lowered = text.lower()
    if "<think" in lowered or "reasoning_content" in lowered or "\nthinking:" in lowered:
        raise ValueError("reasoning content is not allowed")
    if len(text) > 5000:
        raise ValueError("enhancement too long")
    missing = [label for label in REQUIRED_SECTION_LABELS if not has_section(text, label)]
    if missing:
        raise ValueError("enhancement missing required sections")
    if any(phrase in lowered for phrase in BANNED_GENERIC_PHRASES):
        raise ValueError("enhancement includes generic placeholder")
    reject_unsafe_text(text)
    return text


def validate_enhanced_prompt_specificity(prompt: str, request: PromptOptimizationRequest) -> None:
    if prompt_optimization_mode(request) != "i2i":
        return
    terms = reference_hint_terms(request)
    require_reference_terms = should_require_reference_hint_terms(request)
    if terms and require_reference_terms and not any(term in prompt for term in terms):
        raise ValueError("i2i enhancement did not use reference image hints")
    prompt_text = request.prompt_text
    if require_reference_terms and "短发" in prompt_text and not any(term in prompt for term in ("不要染发", "不改变发色", "保持原参考图发色", "保持发色")):
        raise ValueError("i2i short-hair enhancement missed hair color lock")
    if require_reference_terms and any("校服" in term for term in terms) and not any(term in prompt for term in ("保持校服", "不改变校服", "校服款式", "校服配色")):
        raise ValueError("i2i school-uniform enhancement missed wardrobe lock")


def sections_from_canonical(prompt: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in prompt.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parsed = parse_section_line(line)
        if parsed:
            matched, text = parsed
            current = {"title": matched, "text": text.strip()}
            sections.append(current)
            continue
        if current:
            current["text"] = f"{current['text']} {line}".strip()
    return sections


def section_label(line: str) -> str:
    parsed = parse_section_line(line)
    return parsed[0] if parsed else ""


def has_section(text: str, label: str) -> bool:
    return any(section_label(line.strip()) == label for line in text.splitlines())


def normalize_enhancement_sections(text: str) -> str:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parsed = parse_section_line(line)
        if parsed:
            label, content = parsed
            lines.append(f"{label}：{content}".strip())
        else:
            lines.append(line)
    return "\n".join(lines).strip()


def parse_section_line(line: str) -> tuple[str, str] | None:
    cleaned = re.sub(r"^\s*(?:#{1,6}\s*)?(?:[-*•]\s*)?(?:\d+[\.、)]\s*)?", "", line).strip()
    if not cleaned:
        return None

    bracket = re.match(r"^[\[【](?P<label>[^\]】]+)[\]】]\s*(?P<rest>.*)$", cleaned)
    if bracket:
        raw_label = bracket.group("label")
        rest = bracket.group("rest").lstrip("：: -—").strip()
    else:
        match = re.match(r"^(?P<label>[^：:\-—]{1,24})\s*[：:\-—]\s*(?P<rest>.*)$", cleaned)
        if not match:
            return None
        raw_label = match.group("label")
        rest = match.group("rest").strip()

    label = canonical_section_label(raw_label)
    return (label, rest) if label else None


def canonical_section_label(value: str) -> str:
    normalized = str(value or "").strip().strip("*_ `[]【】")
    normalized = re.sub(r"\s+", "", normalized)
    for canonical, aliases in SECTION_LABEL_ALIASES.items():
        if normalized in aliases:
            return canonical
    return ""


def visual_reference_hint(request: PromptOptimizationRequest) -> str:
    terms = reference_hint_terms(request)
    if terms:
        return "、".join(terms[:6])
    return ""


def reference_role(request: PromptOptimizationRequest) -> str:
    terms = reference_hint_terms(request)
    if not terms:
        return "none"
    prompt = str(request.prompt_text or "")
    if has_explicit_subject_reference(prompt):
        return "subject"
    if has_explicit_new_subject(prompt):
        return "style"
    return "subject"


def should_require_reference_hint_terms(request: PromptOptimizationRequest) -> bool:
    return reference_role(request) == "subject"


def has_explicit_new_subject(prompt: str) -> bool:
    text = str(prompt or "").strip()
    if not text:
        return False
    if re.search(r"(生成|创建|画|绘制|输出|制作|做)(一只|一个|一位|一名|一张|新的|全新)", text):
        return True
    if re.search(r"\b(generate|create|draw|render|make)\s+(a|an|one|new)\b", text, re.IGNORECASE):
        return True
    return False


def has_explicit_subject_reference(prompt: str) -> bool:
    text = str(prompt or "")
    subject_terms = (
        "这个人物",
        "这个角色",
        "这个主体",
        "该人物",
        "该角色",
        "该主体",
        "同一人物",
        "同一个人物",
        "同一角色",
        "同一主体",
        "参考图中的人物",
        "参考图中的角色",
        "参考图中的主体",
        "参考图主体",
        "原图主体",
        "当前图片",
        "这张图",
        "原图",
        "保留参考图",
        "保持参考图",
        "基于参考图编辑",
        "基于当前图",
        "上游节点的",
        "参考上游节点",
        "根据上游节点",
        "上游参考图",
    )
    if any(term in text for term in subject_terms):
        return True
    animal_reference_terms = (
        "这只猫",
        "该猫",
        "同一只猫",
        "同一个猫",
        "同一动物",
        "参考图中的猫",
        "参考图里的猫",
        "原图中的猫",
        "上游节点的猫",
        "上游节点的狸花猫",
        "参考上游节点的猫",
    )
    if any(term in text for term in animal_reference_terms):
        return True
    return bool(re.search(r"\b(same|current|reference)\s+(person|character|subject|image)\b", text, re.IGNORECASE))


def reference_hint_terms(request: PromptOptimizationRequest) -> list[str]:
    params = request.node_parameters or {}
    terms: list[str] = []
    for item in params.get("uploaded_images") or []:
        if not isinstance(item, dict):
            continue
        for value in (item.get("filename"), item.get("label")):
            term = filename_hint(value)
            if term:
                terms.append(term)
    for item in params.get("connected_reference_nodes") or []:
        if not isinstance(item, dict):
            continue
        for value in (item.get("title"), item.get("prompt")):
            term = compact(str(value or ""), 40)
            if term and not term.startswith(("图片节点", "文本节点")):
                terms.append(term)
    result: list[str] = []
    for term in terms:
        if term and term not in result:
            result.append(term)
    return result[:8]


def filename_hint(value: Any) -> str:
    text = str(value or "").replace("\\", "/").split("/")[-1].strip()
    if "." in text:
        text = ".".join(text.split(".")[:-1]) or text
    text = text.replace("_", " ").replace("-", " ").strip()
    text = re.sub(r"\bv\d+\b", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\s+", " ", text)
    if not text or text.lower() in {"reference", "image", "candidate", "upload"}:
        return ""
    return compact(text, 60)


def slot(slots: Any, key: str) -> str:
    if not isinstance(slots, dict):
        return ""
    value = slots.get(key)
    return compact(str(value)) if value is not None else ""


def compact(value: str, limit: int = 120) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def contains_cjk(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value)


def strip_code_fence(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def safe_reason(value: str) -> str:
    lowered = value.lower()
    if "key" in lowered or "token" in lowered or "authorization" in lowered:
        return "provider_configuration_not_ready"
    return value[:120]


__all__ = (
    "compact",
    "contains_cjk",
    "reference_role",
    "safe_reason",
    "sanitize_enhanced_prompt",
    "sections_from_canonical",
    "should_require_reference_hint_terms",
    "slot",
    "validate_enhanced_prompt_specificity",
    "visual_reference_hint",
)
