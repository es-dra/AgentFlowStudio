from __future__ import annotations

from typing import Any


MAX_T2I_PROMPT_CHARS = 1500
STYLE_LINE = (
    "premium 3D anime cinematic character, clean commercial image quality, physically grounded human proportions, "
    "not live action, not flat 2D anime, no fashion runway exaggeration"
)

IDENTITY_ANCHORS = [
    "Yiqi",
    "young adult East Asian woman",
    "same face family across every scene",
    "almond-shaped brown eyes",
    "straight nose bridge",
    "soft but defined jawline",
    "natural lips",
    "long high ponytail",
    "loose face-framing hair strands",
]

BODY_ANCHORS = [
    "slim athletic build",
    "natural realistic proportions",
    "narrow waist",
    "long legs",
    "relaxed but ready posture",
]

WARDROBE_ANCHORS = [
    "white fitted short-sleeve T-shirt",
    "same full-length white fitted short-sleeve T-shirt",
    "T-shirt hem covers the waist",
    "T-shirt is tucked into the jeans",
    "blue skinny jeans",
    "white sneakers",
    "simple modern casual outfit",
]

NON_NEGOTIABLE_ANCHORS = [
    "same face family across every scene",
    "same high ponytail silhouette",
    "same full-length white fitted short-sleeve T-shirt",
    "T-shirt hem covers the waist",
    "T-shirt is tucked into the jeans",
    "same blue skinny jeans",
    "same white sneakers",
    "same slim athletic build",
]

NEGATIVE_CONSTRAINTS = [
    "do not change into another woman",
    "do not turn the face into a generic anime face",
    "no hair color change",
    "no short hair",
    "no heavy makeup transformation",
    "no different body type",
    "no crop top",
    "no exposed midriff",
    "no hair accessories",
    "no dress or armor unless explicitly requested as overlay",
    "no live-action realism drift",
    "no unreadable text or logo",
]

SCENE_STRESS_BRIEFS = {
    "desert_wind_walk": (
        "Yiqi walks through a desert wind field, casual outfit still visible, ponytail and loose strands "
        "pulled by the same wind direction."
    ),
    "neon_rain_turn": (
        "Yiqi turns under neon rain on a city street, wet hair strands and T-shirt material reacting to rain."
    ),
    "firelight_closeup": (
        "Close-up by warm firelight, the same eyes, nose bridge, lips, jawline, and ponytail roots remain readable."
    ),
    "combat_dodge_motion": (
        "Yiqi dodges sideways in a fast action shot, keeping natural balance, ponytail inertia, and sneaker traction."
    ),
}


def accepted_character_asset() -> dict[str, Any]:
    return {
        "asset_id": "yiqi_user_accepted_multiview_v1",
        "source_type": "user_attached_reference_image",
        "store_image_in_git": False,
        "source_image_policy": (
            "Use the attached image in this thread as human-provided visual reference. Do not commit the image file, "
            "provider URLs, or local copies into the repository."
        ),
        "views": ["front_full_body", "side_full_body", "back_full_body", "face_closeup"],
        "identity_anchors": IDENTITY_ANCHORS,
        "body_anchors": BODY_ANCHORS,
        "wardrobe_anchors": WARDROBE_ANCHORS,
        "non_negotiable_anchors": NON_NEGOTIABLE_ANCHORS,
        "mutable_fields": [
            "pose",
            "expression intensity",
            "lighting",
            "weather",
            "camera distance",
            "background scene",
            "action dynamics",
        ],
    }


def visual_memory_asset_card(asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "card_id": "visual_memory_asset_card_yiqi_v1",
        "asset_id": asset["asset_id"],
        "evidence_summary": "front side back and close-up reference views are all available",
        "identity_lock": "face shape, eye spacing, nose bridge, lip shape, and jawline stay stable",
        "hair_lock": "long high ponytail with loose face-framing strands stays stable",
        "body_lock": "slim athletic build and natural realistic proportions stay stable",
        "wardrobe_lock": (
            "same full-length white fitted short-sleeve T-shirt with hem covering the waist, "
            "T-shirt tucked into the blue skinny jeans, and white sneakers stay stable"
        ),
        "mutable_fields": [
            "scene costume overlay is allowed only after identity is preserved",
            "lighting and weather may change",
            "pose and motion may change",
            "background may change",
        ],
        "negative_constraints": NEGATIVE_CONSTRAINTS,
    }


def scene_stress_tests() -> list[dict[str, Any]]:
    return [
        _scene("desert_wind_walk", "wind and scene transfer", ["ponytail follows wind", "T-shirt remains readable"]),
        _scene("neon_rain_turn", "wet lighting transfer", ["same face under neon rain", "wet material remains plausible"]),
        _scene("firelight_closeup", "close-up identity", ["same eyes nose lips jawline", "hair roots and strands remain stable"]),
        _scene("combat_dodge_motion", "motion physics", ["hair inertia follows body motion", "sneaker traction remains plausible"]),
    ]


def baseline_prompts(scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_baseline_prompt(scene) for scene in scenes]


def memory_prompts(scenes: list[dict[str, Any]], card: dict[str, Any]) -> list[dict[str, Any]]:
    return [_memory_prompt(scene, card) for scene in scenes]


def evaluation_rubric() -> dict[str, Any]:
    return {
        "status": "not_reviewed",
        "criteria": [
            {"id": "asset_reference_traceability", "question": "Is the accepted user-provided multiview asset referenced without committing the image?"},
            {"id": "identity_retention", "question": "Do face, eyes, nose, lips, jawline, and ponytail stay stable?"},
            {"id": "wardrobe_retention", "question": "Do white T-shirt, blue jeans, and white sneakers stay readable?"},
            {"id": "view_transfer", "question": "Does the model preserve front, side, back, and close-up evidence?"},
            {"id": "scene_transfer", "question": "Does identity survive desert, rain, firelight, and action scenes?"},
            {"id": "motion_physics", "question": "Do hair inertia, cloth, wetness, wind, and foot traction remain plausible?"},
            {"id": "baseline_vs_memory_explainability", "question": "Can reviewers explain the memory advantage from named anchors?"},
        ],
        "decision_rule": (
            "Do not claim memory advantage from provider success alone. Claim only after human side-by-side review "
            "shows the memory-assisted lane retains more named asset anchors than baseline."
        ),
    }


def experiment_card() -> dict[str, Any]:
    return {
        "question": "Does an accepted multiview character asset improve cross-scene consistency?",
        "hypothesis": "Memory-assisted prompts using the accepted asset card should reduce identity and wardrobe drift.",
        "baseline": "normal prompt technique with a concise character description",
        "change": "same scenes plus accepted Visual Memory Asset Card Yiqi v1",
        "metric_or_qa_signal": "human anchor-retention review across keyframes and I2V clips",
        "failure_signal": "face drift, ponytail drift, outfit drift, scene overfitting, or implausible motion",
    }


def _scene(scene_id: str, stressor: str, physics_targets: list[str]) -> dict[str, Any]:
    return {
        "scene_id": scene_id,
        "source_script_summary": SCENE_STRESS_BRIEFS[scene_id],
        "stressor": stressor,
        "physics_targets": physics_targets,
        "duration_sec": 5,
    }


def _baseline_prompt(scene: dict[str, Any]) -> dict[str, Any]:
    image_prompt = (
        f"Vertical 9:16 cinematic keyframe. Scene: {scene['source_script_summary']} "
        "Character: Yiqi, young East Asian woman with high ponytail, "
        "white T-shirt, same full-length white fitted short-sleeve T-shirt, T-shirt hem covers the waist, "
        "T-shirt is tucked into the jeans, blue jeans, white sneakers. "
        f"Style: {STYLE_LINE}. Natural lighting, stable anatomy, no crop top, no exposed midriff, "
        "no hair accessories, no readable text, no logo."
    )
    video_prompt = (
        f"Animate this keyframe as a 5 second vertical cinematic shot. Scene: {scene['source_script_summary']} "
        "Use natural camera motion and stable geometry."
    )
    return {
        "lane": "baseline",
        "scene_id": scene["scene_id"],
        "memory_asset_applied": False,
        "image_prompt": image_prompt,
        "video_prompt": video_prompt,
        "continuity_anchors": [],
    }


def _memory_prompt(scene: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    physics_line = "; ".join(scene["physics_targets"])
    image_prompt = (
        f"Vertical 9:16 keyframe using Visual Memory Asset Card Yiqi v1. Scene: {scene['source_script_summary']} "
        "Preserve same face family, long high ponytail, same full-length white fitted short-sleeve T-shirt, "
        "T-shirt hem covers the waist, T-shirt is tucked into the jeans, blue skinny jeans, white sneakers, slim athletic build, "
        "front, side, back, and close-up evidence. "
        f"Physics targets: {physics_line}. Style: {STYLE_LINE}. no crop top, no exposed midriff, "
        "no hair accessories, no readable text, no logo."
    )
    video_prompt = (
        f"Animate this keyframe as a 5 second vertical cinematic shot using Visual Memory Asset Card Yiqi v1. "
        f"Scene: {scene['source_script_summary']} Preserve identity and wardrobe anchors. "
        f"Maintain plausible motion: hair inertia follows body motion; {physics_line}."
    )
    return {
        "lane": "memory_assisted",
        "scene_id": scene["scene_id"],
        "memory_asset_applied": True,
        "image_prompt": image_prompt,
        "video_prompt": video_prompt,
        "continuity_anchors": [
            card["identity_lock"],
            card["hair_lock"],
            card["body_lock"],
            card["wardrobe_lock"],
        ],
    }
