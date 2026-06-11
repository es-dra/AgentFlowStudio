from __future__ import annotations

from typing import Any

from agentflow.knowledge.creative_prompt_rules import (
    REPO_KNOWLEDGE_ROOT,
    load_creative_prompt_rules,
    load_registry,
    normalized_knowledgebase_hash,
    select_creative_prompt_rules,
)
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_prompt_memory_slots import extract_prompt_slots


SECTION_ORDER = [
    "Intent",
    "Subject/Character",
    "Scene/Production Design",
    "Action/Beat",
    "Camera/Framing",
    "Lighting",
    "Motion/Temporal Progression",
    "Continuity",
    "Negative Constraints",
]


def assemble_prompt_context(request: PromptOptimizationRequest, state: dict[str, Any]) -> dict[str, Any]:
    slots = extract_prompt_slots(request)
    registry = load_registry(REPO_KNOWLEDGE_ROOT)
    all_rules = load_creative_prompt_rules(REPO_KNOWLEDGE_ROOT)
    selected_rules = select_creative_prompt_rules(
        all_rules,
        node_type=request.node_type,
        generation_target=request.generation_target,
        target_platform=request.target_platform,
        slots=slots,
    )
    background = _background_context(state)
    suppressed = _suppressed_preferences(slots, selected_rules)
    sections = _prompt_sections(request, slots, selected_rules, background, suppressed)
    return {
        "optimized_prompt": "\n".join(f"{section['title']}: {section['text']}" for section in sections),
        "prompt_sections": sections,
        "knowledge_rules": selected_rules,
        "selected_slots": slots,
        "background_context": background,
        "suppressed_context": suppressed,
        "conflict_resolution": {
            "policy": "professional_knowledge_over_user_preference",
            "professional_rules_applied": len(selected_rules),
            "suppressed_count": len(suppressed),
        },
        "knowledgebase_version": str(registry["version"]),
        "knowledgebase_registry_hash": normalized_knowledgebase_hash(REPO_KNOWLEDGE_ROOT),
        "knowledgebase_rules_count": len(all_rules),
    }


def _prompt_sections(
    request: PromptOptimizationRequest,
    slots: dict[str, str],
    rules: list[dict[str, Any]],
    background: list[dict[str, Any]],
    suppressed: list[dict[str, str]],
) -> list[dict[str, str]]:
    rule_guidance = _guidance_by_section(rules)
    background_text = _background_text(background)
    text_by_section = {
        "Intent": (
            f"Optimize this {request.node_type} node for {request.generation_target} on {request.target_platform}. "
            f"Original request: {request.prompt_text}. {rule_guidance.get('Intent', '')}"
        ),
        "Subject/Character": (
            f"{slots['subject']}; keep identity separate from one-off action. "
            f"{_character_background(background)} {rule_guidance.get('Subject/Character', '')}"
        ),
        "Scene/Production Design": (
            f"{slots['scene']}; preserve reusable scene geography, props, and atmosphere. "
            f"{_scene_background(background)} {rule_guidance.get('Scene/Production Design', '')}"
        ),
        "Action/Beat": f"{slots['action']}; visible emotional cue: {slots['emotion']}. {rule_guidance.get('Action/Beat', '')}",
        "Camera/Framing": f"{slots['camera']}; choose shot scale and angle for the beat. {rule_guidance.get('Camera/Framing', '')}",
        "Lighting": f"{slots['lighting']}; specify motivated source, direction, contrast, color temperature, and atmosphere. {rule_guidance.get('Lighting', '')}",
        "Motion/Temporal Progression": f"{slots['motion']}; describe temporal change, direction, speed, and camera relation. {rule_guidance.get('Motion/Temporal Progression', '')}",
        "Continuity": (
            f"Reuse safe background context only: {background_text}. Asset refs: {_asset_refs(request)}. "
            f"Durable memory remains false. {rule_guidance.get('Continuity', '')}"
        ),
        "Negative Constraints": (
            "Provider calls remain off; do not claim generation, upload, download, or provider execution. "
            "No private paths, signed URLs, tokens, provider raw payloads, media bytes, identity drift, unwanted text, or continuity breaks. "
            f"{_suppressed_text(suppressed)} {rule_guidance.get('Negative Constraints', '')}"
        ),
    }
    return [{"title": section, "text": text_by_section[section].strip()} for section in SECTION_ORDER]


def _guidance_by_section(rules: list[dict[str, Any]]) -> dict[str, str]:
    guidance: dict[str, list[str]] = {}
    for rule in rules:
        transform = rule.get("prompt_transform", {})
        section = str(transform.get("output_section") or "")
        if section not in SECTION_ORDER:
            continue
        guidance.setdefault(section, []).append(f"[{rule['rule_id']}] {transform.get('guidance')}")
    return {section: " ".join(items[:3]) for section, items in guidance.items()}


def _background_context(state: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for field in ("characters", "scenes", "style_preferences", "user_preferences"):
        for item in _list(state.get(field)):
            if isinstance(item, dict):
                items.append(item)
    return items


def _suppressed_preferences(slots: dict[str, str], rules: list[dict[str, Any]]) -> list[dict[str, str]]:
    preference = slots.get("preference", "")
    if not preference:
        return []
    risky_terms = ("高饱和", "夸张炫光", "快速甩镜", "whip", "oversaturated", "flashy")
    if any(term.lower() in preference.lower() for term in risky_terms):
        return [
            {
                "source": "user_preferences",
                "value": preference,
                "reason": "Professional lighting, continuity, and motion rules have higher priority than style preference.",
            }
        ]
    if any(rule["domain"] == "negative_constraints" for rule in rules):
        return []
    return []


def _background_text(background: list[dict[str, Any]]) -> str:
    if not background:
        return "none yet"
    return "; ".join(f"{item.get('memory_type')}: {item.get('label')}" for item in background[:6])


def _character_background(background: list[dict[str, Any]]) -> str:
    labels = [str(item.get("label")) for item in background if item.get("memory_type") == "character"]
    return "Background characters: " + ", ".join(labels[:3]) + "." if labels else ""


def _scene_background(background: list[dict[str, Any]]) -> str:
    labels = [str(item.get("label")) for item in background if item.get("memory_type") == "scene"]
    return "Background scenes: " + ", ".join(labels[:3]) + "." if labels else ""


def _asset_refs(request: PromptOptimizationRequest) -> str:
    return ", ".join(request.asset_refs) if request.asset_refs else "none"


def _suppressed_text(suppressed: list[dict[str, str]]) -> str:
    if not suppressed:
        return ""
    return "Suppressed lower-priority preference: " + "; ".join(item["value"] for item in suppressed)


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = ("assemble_prompt_context",)
