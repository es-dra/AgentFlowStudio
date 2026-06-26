from __future__ import annotations

import re
from typing import Any

from apps.api.runtime_models import PromptOptimizationRequest


SCRIPT_CONTRACT = "formal_script_before_storyboard_breakdown"


def should_build_script_plan(request: PromptOptimizationRequest) -> bool:
    params = request.node_parameters or {}
    return (
        request.node_type == "script"
        or request.generation_target == "script"
        or str(params.get("script_expansion_contract") or "") == SCRIPT_CONTRACT
    )


def build_script_plan(request: PromptOptimizationRequest) -> dict[str, Any] | None:
    if not should_build_script_plan(request):
        return None
    params = request.node_parameters or {}
    source_idea = _clean(str(params.get("source_idea") or request.prompt_text or ""))
    prompt_text = _clean(request.prompt_text)
    source = source_idea or prompt_text
    subject_hints = _subject_hints(source)
    scene_hints = _scene_hints(source)
    return {
        "artifact_type": "agentflow_script_plan",
        "schema_version": "0.1.0",
        "node_id": request.node_id,
        "script_type": "formal_short_video_script",
        "source_idea": source_idea[:600],
        "story_title_seed": _title_seed(source),
        "detected_subject_hints": subject_hints,
        "detected_scene_hints": scene_hints,
        "narrative_sections": [
            {
                "section_id": "setup",
                "function": "establish protagonist, location, desire, and emotional baseline",
                "output_mode": "continuous prose",
                "must_include": ["who is present", "where the story begins", "why this moment matters"],
            },
            {
                "section_id": "development",
                "function": "advance behavior, emotion, and environment instead of listing camera shots",
                "output_mode": "continuous prose",
                "must_include": ["observable action", "sensory detail", "emotional movement"],
            },
            {
                "section_id": "turn",
                "function": "create a clear visual or dramatic change that later supports storyboard splitting",
                "output_mode": "continuous prose",
                "must_include": ["change trigger", "reaction", "visual emphasis"],
            },
            {
                "section_id": "ending",
                "function": "close the moment while preserving enough information for keyframes",
                "output_mode": "continuous prose",
                "must_include": ["resulting state", "remaining visual anchors", "next-shot continuity"],
            },
        ],
        "asset_seed_policy": {
            "character_candidates": subject_hints,
            "scene_candidates": scene_hints,
            "candidate_assets_are_editable": True,
            "fixed_assets_required": False,
            "do_not_promote_to_memory": True,
        },
        "next_stage_contract": {
            "storyboard_input": "formal script prose, not placeholder shot labels",
            "storyboard_should_extract": ["beats", "shot functions", "asset candidates", "keyframe requirements"],
            "keyframe_should_lock": ["approved asset identity", "scene geometry", "camera composition"],
        },
        "forbidden_outputs": [
            "storyboard_placeholder_outline",
            "shot list as the final script",
            "generic lines such as advance subject, show change, or close result",
            "provider execution claims",
        ],
    }


def _subject_hints(text: str) -> list[str]:
    source = text.lower()
    hints: list[str] = []
    if "robot" in source or "\u673a\u5668\u4eba" in text:
        hints.append("future robot" if "future" in source or "\u672a\u6765" in text else "robot")
    if "cat" in source or "\u732b" in text:
        hints.append("cat")
    if "founder" in source:
        hints.append("founder")
    if not hints:
        hints.append("primary subject")
    return hints[:4]


def _scene_hints(text: str) -> list[str]:
    source = text.lower()
    hints: list[str] = []
    if "rooftop" in source or "\u5c4b\u9876" in text or "\u5929\u53f0" in text:
        hints.append("rooftop platform")
    if "rural" in source or "\u519c\u6751" in text or "\u4e61\u6751" in text:
        hints.append("rural environment")
    if "star" in source or "\u661f" in text:
        hints.append("starry night sky")
    if not hints:
        hints.append("primary scene")
    return hints[:4]


def _title_seed(text: str) -> str:
    compact = re.sub(r"[\s,.;:!?]+", "", str(text or ""))
    return (compact or "short_video_script")[:32]


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


__all__ = ("SCRIPT_CONTRACT", "build_script_plan", "should_build_script_plan")
