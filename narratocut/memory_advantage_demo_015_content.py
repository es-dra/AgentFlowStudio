from __future__ import annotations

from typing import Any

from narratocut.memory_advantage_demo_011_content import (
    NEGATIVE_CONSTRAINTS,
    STYLE_LINE,
    accepted_character_asset,
    visual_memory_asset_card,
)


SCENE_ID = "desert_occlusion_recovery"
DEFAULT_DURATION = "15"
DEFAULT_MODE = "pro"
MAX_KLING_PROMPT_CHARS = 2500

USER_TASK = (
    "Create a 15 second 3D anime video. The character moves through a sandstorm "
    "in front of a ruined Loulan Buddhist tower in the Taklamakan desert. The "
    "sandstorm partially occludes the character, she keeps walking forward, and "
    "the final shot returns to a readable front three-quarter view."
)


def build_memory_inputs() -> dict[str, Any]:
    asset = accepted_character_asset()
    character_card = visual_memory_asset_card(asset)
    return {
        "character_memory_card": character_card,
        "scene_memory_card": scene_memory_card(),
        "feedback_memory_patch": feedback_memory_patch(),
    }

def scene_memory_card() -> dict[str, Any]:
    return {
        "card_id": "scene_memory_card_loulan_desert_storm_v1",
        "scene_id": SCENE_ID,
        "setting_lock": "Taklamakan desert with a ruined Loulan Buddhist tower",
        "weather_lock": "large black sandstorm wall and wind-driven sand",
        "wind_lock": "sand and loose hair move from left to right",
        "lighting_lock": "warm dusty desert light remains coherent",
        "mutable_fields": ["camera distance", "camera push", "partial occlusion", "walking pace"],
        "forbidden_scene_drift": [
            "generic empty desert without the tower",
            "modern city background",
            "snow, rain, ocean, or forest weather",
            "inconsistent wind direction",
        ],
    }


def feedback_memory_patch() -> dict[str, Any]:
    return {
        "patch_id": "feedback_memory_patch_desert_recovery_v1",
        "source_evidence": [
            {
                "source_demo_id": "AFS-MEMORY-ADVANTAGE-DEMO-012",
                "issue_id": "shirt_anchor_drift",
                "finding": "Some prior keyframes shortened the white T-shirt and exposed the waist.",
                "reuse_rule": "Keep the white T-shirt full-length and tucked; do not expose midriff.",
            },
            {
                "source_demo_id": "AFS-MEMORY-ADVANTAGE-DEMO-012",
                "issue_id": "new_hair_accessory",
                "finding": "A prior action keyframe introduced an unwanted hair accessory.",
                "reuse_rule": "Do not introduce new hair accessories.",
            },
            {
                "source_demo_id": "AFS-MEMORY-ADVANTAGE-DEMO-014",
                "issue_id": "final_recovery_needs_same_person_check",
                "finding": "The final frame can look acceptable but still weak as an identity proof.",
                "reuse_rule": "End with a readable front three-quarter same-person recovery check.",
            },
            {
                "source_demo_id": "AFS-MEMORY-ADVANTAGE-DEMO-014",
                "issue_id": "scene_anchor_needs_tower",
                "finding": "The desert can become generic if the tower anchor is not carried through.",
                "reuse_rule": "Keep the Loulan tower or its ruins readable through the shot.",
            },
        ],
        "writes_long_term_memory": False,
        "promotion_status": "candidate_patch_for_demo_reuse",
    }


def generation_projections(memory_inputs: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    inputs = memory_inputs or build_memory_inputs()
    return [
        {
            "lane": "baseline",
            "production_mode": "stateless_generation",
            "user_task": USER_TASK,
            "memory_sources_loaded": [],
            "projection_note": "Normal one-off production from current user task and current keyframe only.",
            "video_prompt": baseline_video_prompt(),
        },
        {
            "lane": "memory_backed",
            "production_mode": "memory_backed_production",
            "user_task": USER_TASK,
            "memory_sources_loaded": [
                "character_memory_card",
                "scene_memory_card",
                "feedback_memory_patch",
            ],
            "projection_note": (
                "The provider prompt is a runtime projection of asset memory, scene memory, "
                "and feedback memory. The user task stays the same as baseline."
            ),
            "video_prompt": memory_backed_video_prompt(inputs),
        },
    ]


def baseline_video_prompt() -> str:
    return (
        "Animate the source keyframe as a 15 second vertical 3D anime cinematic shot. "
        f"Task: {USER_TASK} "
        "Use a slow camera push, natural walking motion, coherent sand, clothing and hair motion, "
        "and keep the character and desert tower scene consistent."
    )


def memory_backed_video_prompt(memory_inputs: dict[str, Any]) -> str:
    character = memory_inputs["character_memory_card"]
    scene = memory_inputs["scene_memory_card"]
    patch = memory_inputs["feedback_memory_patch"]
    feedback_rules = "; ".join(str(item["reuse_rule"]) for item in patch["source_evidence"])
    return (
        "Animate the source keyframe as a 15 second vertical 3D anime cinematic shot. "
        f"Task: {USER_TASK} "
        f"Style: {STYLE_LINE}. "
        f"Character memory: {character['identity_lock']}; {character['hair_lock']}; "
        f"{character['body_lock']}; {character['wardrobe_lock']}. "
        f"Scene memory: {scene['setting_lock']}; {scene['weather_lock']}; "
        f"{scene['wind_lock']}; {scene['lighting_lock']}. "
        f"Feedback memory patch: {feedback_rules}. "
        "Motion checkpoints: 0-3s readable front three-quarter view with outfit and tower visible; "
        "3-7s sand gust crosses left to right and partially occludes face and upper body; "
        "7-11s she walks forward and turns slightly, ponytail and shirt move with the same wind; "
        "11-15s sand clears and camera returns to readable front three-quarter same-person view. "
        f"Avoid: {'; '.join(NEGATIVE_CONSTRAINTS)}."
    )


def scorecard_rubric() -> dict[str, Any]:
    return {
        "status": "not_reviewed",
        "scale": "0=fail, 1=partial, 2=stable",
        "criteria": [
            {"id": "face_identity", "question": "Does the final face still read as the same person?"},
            {"id": "hair_silhouette", "question": "Does the high ponytail silhouette survive motion and wind?"},
            {"id": "wardrobe_consistency", "question": "Do white T-shirt, blue jeans, and white sneakers remain stable?"},
            {"id": "scene_anchor", "question": "Does the Loulan tower / desert storm scene remain identifiable?"},
            {"id": "motion_physics", "question": "Do wind, walking, foot contact, hair, and cloth move coherently?"},
            {"id": "occlusion_recovery", "question": "After sand occlusion, does the shot recover the same character and scene?"},
        ],
        "penalties": [
            {"id": "new_hair_accessory", "points": -1},
            {"id": "exposed_midriff_or_crop_top", "points": -1},
            {"id": "costume_replacement", "points": -1},
            {"id": "tower_disappears", "points": -1},
            {"id": "final_same_person_failure", "points": -2},
        ],
        "decision_rule": (
            "Do not claim product validation from provider success. Claim only a bounded video-stage "
            "memory-reuse signal when the memory-backed lane retains more named anchors under the same user task."
        ),
    }


def protocol_card() -> dict[str, Any]:
    return {
        "protocol_id": "memory_backed_production_protocol_v1",
        "demo_id": "AFS-MEMORY-ADVANTAGE-DEMO-015",
        "question": (
            "With the same user task and same source keyframe, does memory-backed production "
            "reuse asset, scene, and feedback memory to improve I2V continuity?"
        ),
        "baseline": "stateless generation from current task and source keyframe only",
        "change": "same user task plus automatic character, scene, and feedback memory reuse",
        "not_a_prompt_length_test": True,
        "human_acceptance_required": True,
        "writes_long_term_memory": False,
    }
