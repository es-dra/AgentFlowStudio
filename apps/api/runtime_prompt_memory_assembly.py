from __future__ import annotations

from typing import Any

from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_prompt_memory_engine import assemble_prompt_context
from apps.api.runtime_prompt_memory_slots import extract_prompt_slots
from apps.api.runtime_prompt_memory_state import background_memory_record
from apps.api.runtime_llm_enhancement import llm_provider_gate


CONTEXT_PRIORITY = [
    "professional_knowledge_base",
    "script_character_scene_assets",
    "user_preferences",
]


def knowledge_rules(request: PromptOptimizationRequest) -> list[dict[str, str]]:
    return assemble_prompt_context(request, {})["knowledge_rules"]


def optimized_prompt(request: PromptOptimizationRequest, rules: list[dict[str, str]], state: dict[str, Any]) -> str:
    return assemble_prompt_context(request, state)["optimized_prompt"]


def extract_background_context(
    project_id: str,
    request: PromptOptimizationRequest,
    slots: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    selected_slots = slots or extract_prompt_slots(request)
    records: list[dict[str, Any]] = []
    character = _usable_slot(selected_slots.get("subject"), "Primary character")
    scene = _usable_slot(selected_slots.get("scene"), "Primary scene")
    style = _usable_slot(selected_slots.get("style"), "Project style")
    if character:
        records.append(
            background_memory_record(
                project_id,
                "character",
                character,
                f"Recurring subject extracted from node prompt: {character}",
                request.generated_at,
                source_node_id=request.node_id,
                confidence=0.55,
            )
        )
    if scene:
        records.append(
            background_memory_record(
                project_id,
                "scene",
                scene,
                f"Reusable scene abstraction extracted from node prompt: {scene}",
                request.generated_at,
                source_node_id=request.node_id,
                confidence=0.55,
            )
        )
    if style:
        records.append(
            background_memory_record(
                project_id,
                "style_preference",
                style,
                f"Style preference extracted from request: {style}",
                request.generated_at,
                source_node_id=request.node_id,
                confidence=0.45,
            )
        )
    return records[:12]


def _usable_slot(value: str | None, fallback: str) -> str:
    text = str(value or "").strip()
    if not text or text.casefold() == fallback.casefold():
        return ""
    return text


def provider_gate() -> dict[str, str]:
    return llm_provider_gate()


__all__ = (
    "CONTEXT_PRIORITY",
    "extract_background_context",
    "knowledge_rules",
    "optimized_prompt",
    "provider_gate",
)
