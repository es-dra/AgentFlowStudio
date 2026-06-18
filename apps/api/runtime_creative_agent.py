from __future__ import annotations

from typing import Any

from apps.api.runtime_models import PromptOptimizationRequest


AGENT_NAME = "creative_intent_control_agent_v1"
HARD_PARAMETER_KEYS = (
    "aspect_ratio",
    "panorama",
    "shot_scale",
    "camera",
    "motion",
    "lighting",
    "seed",
)
SCORE_KEYS = (
    "semantic_coverage",
    "visual_controllability",
    "character_consistency",
    "scene_continuity",
    "professional_alignment",
    "provider_fit",
    "negative_constraint_safety",
    "preference_fit",
)


def build_creative_agent_decision(
    request: PromptOptimizationRequest,
    *,
    sections: list[dict[str, str]],
    rules: list[dict[str, Any]],
    slots: dict[str, str],
    background: list[dict[str, Any]],
    suppressed_context: list[dict[str, str]],
) -> dict[str, Any]:
    constraint_layers = _constraint_layers(request, rules, slots, background, suppressed_context)
    section_prompt = _sections_to_prompt(sections)
    candidates = _candidates(request, section_prompt, constraint_layers, rules)
    selected = _select_candidate(request, candidates)
    return {
        "agent_name": AGENT_NAME,
        "schema_version": "0.1.0",
        "agent_mode": "layered_single_agent",
        "optimization_objective": "keyframe_controllability",
        "candidate_count": len(candidates),
        "constraint_layers": constraint_layers,
        "internal_lenses": [
            "director_intent",
            "cinematography",
            "lighting",
            "production_design",
            "continuity",
            "provider_translation",
            "safety_negative_constraints",
        ],
        "candidates": candidates,
        "selected_candidate": selected,
        "selection_policy": {
            "method": "deterministic_pareto_frontier",
            "primary_axes": [
                "visual_controllability",
                "character_consistency",
                "scene_continuity",
                "provider_fit",
            ],
            "tie_breaker": "professional_alignment",
        },
        "provider_translation": _provider_translation(request, selected, constraint_layers),
        "feedback_policy": {
            "post_generation_feedback": "candidate_evidence_only",
            "durable_memory_promotion": "requires_human_confirmation",
        },
    }


def _constraint_layers(
    request: PromptOptimizationRequest,
    rules: list[dict[str, Any]],
    slots: dict[str, str],
    background: list[dict[str, Any]],
    suppressed_context: list[dict[str, str]],
) -> dict[str, Any]:
    params = request.node_parameters or {}
    hard = [
        {"source": "node_type", "key": "node_type", "value": request.node_type},
        {"source": "generation_target", "key": "generation_target", "value": request.generation_target},
        {"source": "provider_gate", "key": "remote_provider_default", "value": "blocked"},
    ]
    for key in HARD_PARAMETER_KEYS:
        if key in params and params[key] not in (None, ""):
            hard.append({"source": "node_parameters", "key": key, "value": str(params[key])})
    if request.director_setup:
        hard.append({"source": "director_setup", "key": "view", "value": request.director_setup.view})

    strong = [
        {
            "source": "professional_knowledge_base",
            "key": str(rule.get("rule_id")),
            "domain": str(rule.get("domain")),
            "weight": rule.get("weight"),
        }
        for rule in rules[:12]
    ]
    if slots.get("subject") and slots["subject"] != "Primary character":
        strong.append({"source": "selected_slots", "key": "subject", "value": slots["subject"]})
    if slots.get("scene") and slots["scene"] != "Primary scene":
        strong.append({"source": "selected_slots", "key": "scene", "value": slots["scene"]})

    soft = []
    if slots.get("preference"):
        soft.append({"source": "user_preferences", "key": "style_preference", "value": slots["preference"]})
    if request.style:
        soft.append({"source": "request_style", "key": "style", "value": request.style})

    return {
        "hard_constraints": hard,
        "strong_constraints": strong,
        "soft_constraints": soft,
        "background_context_count": len(background),
        "suppressed_context": suppressed_context,
        "precedence": [
            "current_node_goal",
            "node_parameters",
            "professional_knowledge_base",
            "script_character_scene_assets",
            "user_preferences",
        ],
    }


def _candidates(
    request: PromptOptimizationRequest,
    section_prompt: str,
    constraints: dict[str, Any],
    rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    controls = _hard_control_sentence(constraints)
    return [
        _candidate(
            "continuity_safe",
            "Continuity-safe version",
            section_prompt,
            controls,
            "Prioritize stable character identity, scene geography, and lighting continuity.",
            _score("continuity_safe", request, rules, constraints),
        ),
        _candidate(
            "expressive_cinematic",
            "Expressive cinematic version",
            section_prompt,
            controls,
            "Increase cinematic specificity only where it does not conflict with hard controls.",
            _score("expressive_cinematic", request, rules, constraints),
        ),
        _candidate(
            "provider_safe_keyframe",
            "Provider-safe keyframe version",
            section_prompt,
            controls,
            "Compress the brief into image/keyframe-ready visual instructions for provider translation.",
            _score("provider_safe_keyframe", request, rules, constraints),
        ),
    ]


def _candidate(
    candidate_id: str,
    label: str,
    section_prompt: str,
    controls: str,
    rationale: str,
    score: dict[str, float],
) -> dict[str, Any]:
    prompt = section_prompt
    if controls:
        prompt = f"{prompt}\nHard Controls: {controls}"
    prompt = f"{prompt}\nAgent Rationale: {rationale}"
    return {
        "candidate_id": candidate_id,
        "label": label,
        "canonical_prompt": prompt,
        "score": score,
        "rationale": rationale,
    }


def _score(
    candidate_id: str,
    request: PromptOptimizationRequest,
    rules: list[dict[str, Any]],
    constraints: dict[str, Any],
) -> dict[str, float]:
    hard_count = len(constraints["hard_constraints"])
    rule_count = len(rules)
    image_like = request.generation_target in {"image", "keyframe"}
    base = {
        "semantic_coverage": 0.78 + min(rule_count, 8) * 0.01,
        "visual_controllability": 0.74 + min(hard_count, 6) * 0.02,
        "character_consistency": 0.76,
        "scene_continuity": 0.75 + min(constraints["background_context_count"], 4) * 0.03,
        "professional_alignment": 0.80 + min(rule_count, 10) * 0.01,
        "provider_fit": 0.74,
        "negative_constraint_safety": 0.84,
        "preference_fit": 0.52,
    }
    if candidate_id == "continuity_safe":
        base["character_consistency"] += 0.08
        base["scene_continuity"] += 0.08
        base["preference_fit"] += 0.03
    elif candidate_id == "expressive_cinematic":
        base["semantic_coverage"] += 0.04
        base["professional_alignment"] += 0.04
        base["preference_fit"] += 0.12
        base["visual_controllability"] -= 0.02
    elif candidate_id == "provider_safe_keyframe":
        base["visual_controllability"] += 0.08
        base["provider_fit"] += 0.12 if image_like else 0.04
        base["negative_constraint_safety"] += 0.04
        base["preference_fit"] -= 0.02
    return {key: round(max(0.0, min(0.99, base[key])), 2) for key in SCORE_KEYS}


def _select_candidate(request: PromptOptimizationRequest, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    preferred = "provider_safe_keyframe" if request.generation_target in {"image", "keyframe"} else "continuity_safe"
    for candidate in candidates:
        if candidate["candidate_id"] == preferred:
            return candidate
    return candidates[0]


def _provider_translation(
    request: PromptOptimizationRequest,
    selected: dict[str, Any],
    constraints: dict[str, Any],
) -> dict[str, Any]:
    prompt = selected["canonical_prompt"]
    if request.generation_target in {"image", "keyframe"}:
        capability = "image_keyframe"
        provider = "codex_image"
    elif request.generation_target == "video":
        capability = "video"
        provider = "not_enabled"
    else:
        capability = request.generation_target
        provider = "local_runtime"
    return {
        "capability": capability,
        "provider": provider,
        "prompt": prompt,
        "negative_prompt_policy": "use_negative_constraints_section",
        "hard_controls_applied": [
            {"key": item["key"], "value": item["value"]}
            for item in constraints["hard_constraints"]
            if item.get("source") == "node_parameters"
        ],
        "provider_calls_started": False,
    }


def _hard_control_sentence(constraints: dict[str, Any]) -> str:
    parts = []
    for item in constraints["hard_constraints"]:
        if item.get("source") != "node_parameters":
            continue
        key = str(item["key"]).replace("_", " ")
        parts.append(f"{key} {item['value']}")
    return "; ".join(parts)


def _sections_to_prompt(sections: list[dict[str, str]]) -> str:
    return "\n".join(f"{section['title']}: {section['text']}" for section in sections)


__all__ = ("AGENT_NAME", "build_creative_agent_decision")
