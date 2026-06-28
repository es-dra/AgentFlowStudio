from __future__ import annotations

import re
from typing import Any

from agentflow.knowledge.director_scenarios import director_scenario_context
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
    director_scenario = director_scenario_context(
        text=source,
        node_type=request.node_type,
        generation_target="script",
        target_platform=request.target_platform,
        style=request.style,
        node_parameters=params,
    )
    return {
        "artifact_type": "agentflow_script_plan",
        "schema_version": "0.1.0",
        "node_id": request.node_id,
        "script_type": "formal_short_video_script",
        "source_idea": source_idea[:600],
        "story_title_seed": _title_seed(source),
        "director_scenario": director_scenario,
        "detected_subject_hints": subject_hints,
        "detected_scene_hints": scene_hints,
        "script_expansion_strategy": _script_expansion_strategy(source),
        "narrative_sections": _narrative_sections(source),
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


def _script_expansion_strategy(text: str) -> dict[str, Any]:
    density = _idea_density(text)
    return {
        "agent_role": "professional_script_expansion_director",
        "section_count_policy": "llm_decides_from_idea_density",
        "storyboard_split_deferred": True,
        "input_density": density,
        "script_output_mode": "formal_continuous_script_prose",
        "must_not_output": ["shot_labels_as_script", "fixed_four_part_outline", "generic_placeholder_sections"],
        "grounding_policy": "expand only from user idea, explicit assets, and selected professional references",
    }


def _narrative_sections(text: str) -> list[dict[str, Any]]:
    density = _idea_density(text)
    sections = [
        {
            "section_id": "premise",
            "function": "turn the idea into a concrete dramatic situation, not a storyboard label",
            "output_mode": "continuous prose",
            "must_include": ["who is present", "where the moment happens", "what emotional question starts the scene"],
        },
        {
            "section_id": "progression",
            "function": "advance observable behavior, sensory detail, and inner change in prose",
            "output_mode": "continuous prose",
            "must_include": ["visible action", "environment response", "emotional movement"],
        },
        {
            "section_id": "resolution_image",
            "function": "close on a readable story state that later enables storyboard splitting",
            "output_mode": "continuous prose",
            "must_include": ["resulting state", "continuity anchors", "what should remain visually stable"],
        },
    ]
    if density in {"multi_beat", "complex_script"}:
        sections.insert(
            2,
            {
                "section_id": "turn_or_reveal",
                "function": "surface the decisive change only if the source idea supports it",
                "output_mode": "continuous prose",
                "must_include": ["change trigger", "reaction", "visual consequence"],
            },
        )
    if density == "complex_script":
        sections.insert(
            1,
            {
                "section_id": "context_pressure",
                "function": "clarify stakes, constraints, or relationship pressure already implied by the source",
                "output_mode": "continuous prose",
                "must_include": ["stakes", "constraint", "why this moment matters now"],
            },
        )
    return sections


def _idea_density(text: str) -> str:
    source = _clean(text)
    if len(source) >= 260:
        return "complex_script"
    sentence_count = len([part for part in re.split(r"(?<=[。！？!?；;])\s*", source) if part.strip()])
    action_hits = len(re.findall(r"看|望|走|跑|冲|转身|发现|变化|战|打|递|拿|打开|关闭|升起|落下|等待", source))
    if sentence_count >= 4 or action_hits >= 4:
        return "multi_beat"
    return "simple_idea"


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
