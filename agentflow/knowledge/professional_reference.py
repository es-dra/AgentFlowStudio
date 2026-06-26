from __future__ import annotations

import re
from typing import Any


SECTION_MAP = {
    "camera": "Camera/Framing",
    "depth_of_field": "Camera/Framing",
    "lighting": "Lighting",
    "pacing": "Motion/Temporal Progression",
    "scene_continuity": "Scene/Production Design",
}


def professional_reference_context(
    *,
    slots: dict[str, str],
    node_type: str,
    generation_target: str,
) -> dict[str, Any]:
    text = _combined_text(slots)
    tags = _tags(text, node_type=node_type, generation_target=generation_target)
    return {
        "artifact_type": "agentflow_professional_reference_context",
        "schema_version": "0.1.0",
        "node_type": node_type,
        "generation_target": generation_target,
        "tags": tags,
        "camera": _camera_reference(tags),
        "lighting": _lighting_reference(tags),
        "depth_of_field": _depth_reference(tags),
        "pacing": _pacing_reference(tags, generation_target),
        "scene_continuity": _scene_continuity_reference(tags),
        "selection_reasons": _selection_reasons(tags),
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def professional_reference_from_text(
    text: str,
    *,
    node_type: str,
    generation_target: str,
) -> dict[str, Any]:
    return professional_reference_context(
        slots={
            "subject": text,
            "scene": text,
            "action": text,
            "lighting": text,
            "camera": text,
            "motion": text,
            "style": text,
        },
        node_type=node_type,
        generation_target=generation_target,
    )


def format_professional_reference(context: dict[str, Any], output_section: str) -> str:
    chunks: list[str] = []
    for key, section in SECTION_MAP.items():
        if section != output_section:
            continue
        ref = context.get(key)
        if isinstance(ref, dict):
            chunks.append(_format_ref(key, ref))
    if not chunks:
        return ""
    return "Professional reference: " + " ".join(chunks)


def _format_ref(name: str, ref: dict[str, Any]) -> str:
    decision = str(ref.get("decision") or "").strip()
    must = "; ".join(str(item) for item in (ref.get("must_include") or [])[:3])
    avoid = "; ".join(str(item) for item in (ref.get("avoid") or [])[:2])
    parts = [f"{name}={decision}"]
    if must:
        parts.append(f"include {must}")
    if avoid:
        parts.append(f"avoid {avoid}")
    return "(" + "; ".join(parts) + ")."


def _combined_text(slots: dict[str, str]) -> str:
    return "\n".join(str(value or "") for value in slots.values())


def _tags(text: str, *, node_type: str, generation_target: str) -> list[str]:
    source = str(text or "").lower()
    tags: list[str] = []
    for tag, patterns in {
        "night": ("night", "star", "moon", "\u591c", "\u661f", "\u6708"),
        "rooftop": ("rooftop", "roof", "\u5c4b\u9876", "\u5929\u53f0"),
        "rural": ("rural", "village", "\u519c\u6751", "\u4e61\u6751"),
        "interior": ("interior", "room", "office", "\u5ba4\u5185", "\u623f\u95f4", "\u529e\u516c\u5ba4"),
        "low_key": ("low key", "dark", "\u4f4e\u7167\u5ea6", "\u660f\u6697"),
        "action": ("fight", "battle", "chase", "\u6218", "\u51b2\u7a81", "\u8ffd"),
        "observational": ("watch", "observe", "look", "\u770b", "\u89c2\u5bdf", "\u51dd\u89c6"),
        "product": ("product", "packshot", "\u4ea7\u54c1", "\u5546\u54c1"),
        "portrait": ("face", "portrait", "emotion", "\u8138", "\u8868\u60c5", "\u60c5\u7eea"),
        "robot": ("robot", "android", "\u673a\u5668\u4eba"),
    }.items():
        if any(pattern in source or pattern in text for pattern in patterns):
            tags.append(tag)
    if generation_target == "video" or node_type == "video":
        tags.append("video")
    if generation_target in {"image", "keyframe"} or node_type == "image":
        tags.append("single_frame")
    return sorted(set(tags))


def _camera_reference(tags: list[str]) -> dict[str, Any]:
    if "action" in tags:
        return {
            "decision": "medium-wide or medium shot with one dominant camera direction",
            "must_include": ["subject relationship", "action vector", "readable screen direction"],
            "avoid": ["stacked camera moves", "decorative dutch tilt"],
            "quality_checks": ["camera move supports action", "subject scale stays readable"],
        }
    if "rooftop" in tags and "night" in tags:
        return {
            "decision": "medium-wide or rear three-quarter medium shot to hold subject-sky relationship",
            "must_include": ["subject placement", "sky/environment share", "stable horizon or rooftop boundary"],
            "avoid": ["tight close-up that loses the stars", "unmotivated drone angle"],
            "quality_checks": ["sky remains narratively visible", "camera height supports solitude or wonder"],
        }
    if "product" in tags:
        return {
            "decision": "locked medium or close product framing with controlled perspective",
            "must_include": ["product silhouette", "use context", "clean background hierarchy"],
            "avoid": ["wide framing that loses product detail", "fast handheld movement"],
            "quality_checks": ["product is readable", "perspective does not deform geometry"],
        }
    return {
        "decision": "shot scale chosen from narrative priority: place, relationship, action, or face",
        "must_include": ["shot scale", "camera height", "frame intent"],
        "avoid": ["generic cinematic camera language", "conflicting angles in one shot"],
        "quality_checks": ["camera purpose is explicit", "composition supports the beat"],
    }


def _lighting_reference(tags: list[str]) -> dict[str, Any]:
    if "night" in tags and "rooftop" in tags:
        return {
            "decision": "motivated night exterior light from moon/stars plus distant practical spill and subtle rim separation",
            "must_include": ["source direction", "low contrast fill level", "subject edge readability"],
            "avoid": ["unmotivated spotlight", "daylight-bright exposure"],
            "quality_checks": ["light source can exist in scene", "robot/material edges remain readable"],
        }
    if "low_key" in tags or "interior" in tags:
        return {
            "decision": "motivated low-key key/fill/back separation tied to window, lamp, screen, or doorway",
            "must_include": ["key direction", "fill ratio", "shadow detail", "color temperature"],
            "avoid": ["flat bright fill", "random neon color without source"],
            "quality_checks": ["mood remains dark but readable", "source motivates highlights"],
        }
    return {
        "decision": "motivated source, direction, contrast, color temperature, and atmosphere",
        "must_include": ["visible or implied light source", "contrast level", "color temperature"],
        "avoid": ["lighting adjectives without source", "palette that overrides readability"],
        "quality_checks": ["lighting supports emotion", "continuity can carry to adjacent nodes"],
    }


def _depth_reference(tags: list[str]) -> dict[str, Any]:
    if "night" in tags and "rooftop" in tags:
        return {
            "decision": "moderate-to-deep depth cues so subject and starry environment both remain legible",
            "must_include": ["clear subject silhouette", "layered distant sky", "controlled background detail"],
            "avoid": ["excessive shallow bokeh that erases sky", "flat infinite focus without subject separation"],
            "quality_checks": ["subject is primary", "environment context survives"],
        }
    if "portrait" in tags and "product" not in tags:
        return {
            "decision": "shallow-to-moderate depth only when facial emotion is the priority",
            "must_include": ["sharp eyes or face", "soft but identifiable environment", "no identity blur"],
            "avoid": ["blurred defining features", "macro depth on full-body shots"],
            "quality_checks": ["emotion is readable", "identity remains stable"],
        }
    return {
        "decision": "depth of field chosen from subject-environment hierarchy",
        "must_include": ["subject plane", "background readability level", "separation method"],
        "avoid": ["default shallow depth for every cinematic prompt", "lens jargon without visual purpose"],
        "quality_checks": ["depth supports story priority", "scene context is not accidentally lost"],
    }


def _pacing_reference(tags: list[str], generation_target: str) -> dict[str, Any]:
    if generation_target == "video" or "video" in tags:
        if "observational" in tags and "night" in tags:
            decision = "5s slow observational beat: anchor, micro action, settle"
            must = ["0-1s hold identity/composition", "1-3.5s subtle gaze/breath/light motion", "3.5-5s readable end state"]
            avoid = ["new plot event", "large composition jump"]
        elif "action" in tags:
            decision = "short action beat with one clean acceleration and one readable impact/reaction"
            must = ["clear start pose", "single action vector", "held impact or reaction"],
            avoid = ["multiple fight beats in one 5s clip", "motion blur hiding identity"]
            must = list(must[0])
        else:
            decision = "single continuity clip with one primary motion idea"
            must = ["start anchor", "one motion direction", "settled end state"]
            avoid = ["rewritten story", "conflicting motion directions"]
    else:
        decision = "single frame or script beat should preserve later video continuity"
        must = ["clear beat priority", "next-stage continuity", "no overloaded action list"]
        avoid = ["multi-stage video action inside one keyframe", "placeholder beat labels"]
    return {
        "decision": decision,
        "must_include": must,
        "avoid": avoid,
        "quality_checks": ["timing is readable", "motion density fits the duration"],
    }


def _scene_continuity_reference(tags: list[str]) -> dict[str, Any]:
    avoid = ["unrequested furniture", "new scene geometry", "text/watermark/UI"]
    if "rooftop" in tags:
        avoid.extend(["unapproved eaves", "unapproved chair or stool"])
    return {
        "decision": "scene geometry and set dressing should be treated as controlled continuity assets",
        "must_include": ["location type", "layout boundary", "approved set dressing"],
        "avoid": avoid,
        "quality_checks": ["scene matches approved asset card", "new props are justified by script or user edit"],
    }


def _selection_reasons(tags: list[str]) -> list[str]:
    if not tags:
        return ["fallback professional reference for under-specified prompt"]
    return [f"detected_{tag}" for tag in tags]


__all__ = (
    "format_professional_reference",
    "professional_reference_context",
    "professional_reference_from_text",
)
