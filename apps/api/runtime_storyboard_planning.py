from __future__ import annotations

import re
from typing import Any

from agentflow.knowledge.director_scenarios import director_scenario_from_text
from agentflow.knowledge.professional_reference import professional_reference_from_text

SHOT_FUNCTIONS = ("establish", "develop", "reveal", "turn", "resolve")


def storyboard_plan_fields(source_text: str, index: int) -> dict[str, Any]:
    source = _clean(source_text)
    shot_function = _shot_function(source, index)
    return {
        "shot_function": shot_function,
        "professional_reference": professional_reference_from_text(source, node_type="script", generation_target="video"),
        "director_scenario": director_scenario_from_text(source, node_type="script", generation_target="video"),
        "editing_rhythm": _editing_rhythm(source, shot_function),
        "transition_in": "cut_in" if index <= 1 else "match_continuity_cut",
        "transition_out": "hold_for_next_keyframe" if shot_function == "resolve" else "continuity_cut",
        "keyframe_requirement": {
            "frame_role": f"{shot_function}_keyframe",
            "must_show": _must_show(source, shot_function),
            "composition_lock": "single clear keyframe, stable subject placement, no UI/text/borders",
            "asset_lock_policy": "use approved or candidate assets as editable cards; do not invent unrequested identity or scene geometry",
        },
        "video_motion_requirement": {
            "motion_role": f"{shot_function}_motion",
            "time_beats": _time_beats(source, shot_function),
            "camera_policy": _camera_policy(source),
            "forbidden_motion": [
                "large composition jump",
                "new character entrance unless scripted",
                "unrequested prop or furniture insertion",
                "identity drift",
            ],
        },
        "continuity_locks": _continuity_locks(source),
        "negative_scene_locks": _negative_scene_locks(source),
    }


def _shot_function(source: str, index: int) -> str:
    lower = source.lower()
    if index <= 1:
        return "establish"
    if any(token in lower for token in ("change", "reveal", "discover", "turn")) or any(
        token in source for token in ("\u53d8\u5316", "\u53d1\u73b0", "\u8f6c\u6298")
    ):
        return "reveal"
    if any(token in lower for token in ("conflict", "attack", "fight")) or any(
        token in source for token in ("\u51b2\u7a81", "\u6218", "\u6253")
    ):
        return "turn"
    if any(token in lower for token in ("end", "final", "leave")) or any(
        token in source for token in ("\u7ed3\u5c3e", "\u79bb\u5f00", "\u6536\u675f")
    ):
        return "resolve"
    return SHOT_FUNCTIONS[min(index - 1, len(SHOT_FUNCTIONS) - 1)]


def _editing_rhythm(source: str, shot_function: str) -> str:
    if shot_function in {"turn", "reveal"}:
        return "medium_fast_emphasis"
    if len(source) > 140:
        return "medium_continuous"
    return "slow_observational"


def _must_show(source: str, shot_function: str) -> list[str]:
    items = ["primary subject", "main environment", "story action"]
    if _has_robot(source):
        items[0] = "future robot identity and material details"
    if _has_rooftop(source):
        items[1] = "rooftop platform geometry and sky relationship"
    if shot_function == "establish":
        items.append("spatial relationship before action changes")
    return items


def _time_beats(source: str, shot_function: str) -> list[dict[str, str]]:
    beats = [
        {"time": "0.0s-1.0s", "intent": "start from keyframe pose and preserve composition"},
        {"time": "1.0s-3.5s", "intent": "advance one small action or environmental motion"},
        {"time": "3.5s-5.0s", "intent": "settle into a readable end state"},
    ]
    if shot_function in {"turn", "reveal"}:
        beats[1]["intent"] = "make the visual change readable without changing identity or layout"
    if _has_stars(source):
        beats[1]["intent"] = "add subtle breathing motion, tiny light shimmer, and restrained gaze movement"
    return beats


def _camera_policy(source: str) -> str:
    lower = source.lower()
    if "push" in lower or "\u63a8\u8fdb" in source:
        return "slow push-in only if it preserves first-frame composition"
    if "follow" in lower or "\u8ddf" in source:
        return "light follow motion with stable subject scale"
    return "locked-off or subtle breathing camera"


def _continuity_locks(source: str) -> list[str]:
    locks = ["identity", "wardrobe/material", "scene layout", "lighting direction", "camera composition"]
    if _has_robot(source):
        locks.append("robot head shell and mechanical body proportions")
    if _has_rooftop(source):
        locks.append("rooftop platform boundary and rural/sky background relationship")
    return locks


def _negative_scene_locks(source: str) -> list[str]:
    locks = ["no text", "no watermark", "no UI", "no borders"]
    if _has_rooftop(source):
        locks.extend(["no unrequested eaves", "no unrequested chair", "no unrequested stool"])
    return locks


def _has_robot(source: str) -> bool:
    return "robot" in source.lower() or "\u673a\u5668\u4eba" in source


def _has_rooftop(source: str) -> bool:
    return "rooftop" in source.lower() or "\u5c4b\u9876" in source or "\u5929\u53f0" in source


def _has_stars(source: str) -> bool:
    return "star" in source.lower() or "\u661f" in source


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


__all__ = ("storyboard_plan_fields",)
