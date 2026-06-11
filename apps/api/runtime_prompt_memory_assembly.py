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
    character = selected_slots.get("subject") or "Primary character"
    scene = selected_slots.get("scene") or "Primary scene"
    style = selected_slots.get("style") or "Project style"
    return [
        background_memory_record(
            project_id,
            "character",
            character,
            f"Recurring subject extracted from node prompt: {character}",
            request.generated_at,
        ),
        background_memory_record(
            project_id,
            "scene",
            scene,
            f"Reusable scene abstraction extracted from node prompt: {scene}",
            request.generated_at,
        ),
        background_memory_record(
            project_id,
            "style_preference",
            style,
            f"Style preference extracted from request: {style}",
            request.generated_at,
        ),
    ]


def provider_gate() -> dict[str, str]:
    return llm_provider_gate()


__all__ = (
    "CONTEXT_PRIORITY",
    "extract_background_context",
    "knowledge_rules",
    "optimized_prompt",
    "provider_gate",
)
