from __future__ import annotations

from typing import Any

from agentflow_studio.memory_advantage_demo_011_content import (
    NEGATIVE_CONSTRAINTS,
    STYLE_LINE,
    accepted_character_asset,
    evaluation_rubric,
    visual_memory_asset_card,
)


MAX_T2I_PROMPT_CHARS = 1500
MODEL_NAME = "image-01"
ASPECT_RATIO = "9:16"
SCENE_SEEDS = {
    "desert_wind_walk": 120401,
    "neon_rain_turn": 120402,
    "combat_dodge_motion": 120403,
}


def demo_012_scenes() -> list[dict[str, Any]]:
    return [
        {
            "scene_id": "desert_wind_walk",
            "source_script_summary": (
                "Yiqi walks through a Taklamakan desert wind field, sand sweeping from left to right, "
                "the full casual outfit remains visible through the dust."
            ),
            "stressor": "wind and wide-environment transfer",
            "physics_targets": [
                "ponytail and loose strands follow one wind direction",
                "T-shirt and jeans remain readable through sand",
                "body leans naturally against wind",
            ],
            "duration_sec": 5,
        },
        {
            "scene_id": "neon_rain_turn",
            "source_script_summary": (
                "Yiqi turns back under neon rain on a wet city street, face partially side-lit, "
                "raindrops and reflections changing the material appearance without changing the outfit."
            ),
            "stressor": "wet lighting and three-quarter face transfer",
            "physics_targets": [
                "wet hair strands still match the high ponytail silhouette",
                "T-shirt fabric reacts to rain without becoming a new costume",
                "face family stays stable under colored light",
            ],
            "duration_sec": 5,
        },
        {
            "scene_id": "combat_dodge_motion",
            "source_script_summary": (
                "Yiqi dodges sideways in a close action keyframe, one sneaker planted, torso twisting, "
                "camera slightly low while the same casual outfit and body proportions remain intact."
            ),
            "stressor": "fast pose and motion-physics transfer",
            "physics_targets": [
                "hair inertia follows the dodge direction",
                "sneaker traction and body balance are plausible",
                "limbs keep natural 3D anime proportions",
            ],
            "duration_sec": 5,
        },
    ]


def demo_012_image_requests(
    scenes: list[dict[str, Any]],
    card: dict[str, Any],
    provider_plan_builder,
) -> list[dict[str, Any]]:
    baseline = [_request("baseline", scene, card, provider_plan_builder) for scene in scenes]
    memory = [_request("memory_assisted", scene, card, provider_plan_builder) for scene in scenes]
    return baseline + memory


def demo_012_experiment_card() -> dict[str, Any]:
    return {
        "question": "Does structured visual memory improve a fixed character asset's cross-scene I2I consistency?",
        "hypothesis": (
            "With the same MiniMax I2I model, same subject reference, same seed per scene, and same script, "
            "the memory-assisted lane should retain more named identity, hair, wardrobe, and physics anchors."
        ),
        "baseline": "same reference image plus normal professional character-consistency prompt",
        "change": "same reference image plus Visual Memory Asset Card Yiqi v1 and explicit invariant/mutable fields",
        "metric_or_qa_signal": "side-by-side human anchor-retention review across six keyframes",
        "failure_signal": "face drift, ponytail drift, outfit drift, body-proportion drift, or implausible motion",
    }


def demo_012_image_budget() -> dict[str, Any]:
    return {
        "total_keyframes": 6,
        "scene_count": 3,
        "lanes": ["baseline", "memory_assisted"],
        "candidate_count_per_request": 1,
        "retakes_allowed_before_review": 0,
    }


def demo_012_evaluation_rubric() -> dict[str, Any]:
    rubric = evaluation_rubric()
    rubric["criteria"] = [
        *rubric["criteria"],
        {
            "id": "same_provider_and_seed_fairness",
            "question": "Did baseline and memory-assisted use the same provider, model, reference image, and seed per scene?",
        },
        {
            "id": "i2v_readiness",
            "question": "Are the keyframes strong enough to spend Kling I2V calls?",
        },
    ]
    return rubric


def build_asset_and_card() -> tuple[dict[str, Any], dict[str, Any]]:
    asset = accepted_character_asset()
    return asset, visual_memory_asset_card(asset)


def _request(
    lane: str,
    scene: dict[str, Any],
    card: dict[str, Any],
    provider_plan_builder,
) -> dict[str, Any]:
    scene_id = str(scene["scene_id"])
    prompt = _baseline_prompt(scene) if lane == "baseline" else _memory_prompt(scene, card)
    provider_plan = provider_plan_builder(prompt=prompt, seed=SCENE_SEEDS[scene_id])
    return {
        "request_id": f"{lane}_{scene_id}",
        "lane": lane,
        "scene_id": scene_id,
        "model": MODEL_NAME,
        "aspect_ratio": ASPECT_RATIO,
        "seed": SCENE_SEEDS[scene_id],
        "candidate_count": 1,
        "subject_reference_role": "same_fixed_character_reference_image",
        "method_note": (
            "normal professional character-consistency prompt"
            if lane == "baseline"
            else "structured visual memory card prompt"
        ),
        "image_prompt": prompt,
        "continuity_anchors": [] if lane == "baseline" else _memory_anchors(card),
        "provider_plan": provider_plan,
    }


def _baseline_prompt(scene: dict[str, Any]) -> str:
    return (
        f"Use the provided character reference image as the fixed subject. Vertical 9:16 cinematic keyframe. "
        f"Scene: {scene['source_script_summary']} Character should remain the same young East Asian woman from "
        "the reference image, with long high ponytail, white fitted short-sleeve T-shirt, blue skinny jeans, "
        f"white sneakers, slim athletic body. Style: {STYLE_LINE}. Keep character consistency, natural 3D anime "
        "proportions, readable outfit, coherent lighting and motion. Avoid: "
        f"{'; '.join(NEGATIVE_CONSTRAINTS)}."
    )


def _memory_prompt(scene: dict[str, Any], card: dict[str, Any]) -> str:
    physics_line = "; ".join(str(item) for item in scene["physics_targets"])
    return (
        "Use reference image as fixed subject plus Visual Memory Asset Card Yiqi v1. "
        f"3D anime cinematic keyframe, 9:16. Scene: {scene['source_script_summary']} "
        f"identity lock: {card['identity_lock']}. "
        "hair lock: long high ponytail, loose face-framing strands, same dark hair. "
        "body lock: slim athletic build. wardrobe lock: full-length white fitted short-sleeve T-shirt; "
        "T-shirt hem covers the waist; T-shirt tucked into blue skinny jeans; white sneakers. "
        "Mutable only: pose, expression, lighting, weather, camera, background, motion. "
        f"Physics: {physics_line}. "
        "Avoid: different woman; generic anime face; hair color/short hair; body type drift; "
        "no crop top; exposed midriff; no hair accessories; dress/armor; live action; text/logo."
    )


def _memory_anchors(card: dict[str, Any]) -> list[str]:
    return [
        card["identity_lock"],
        card["hair_lock"],
        card["body_lock"],
        card["wardrobe_lock"],
    ]
