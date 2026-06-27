from __future__ import annotations

import re
from typing import Any

from agentflow.knowledge.director_scenarios import (
    director_scenario_from_text,
    format_director_scenario_reference,
)
from agentflow.knowledge.professional_reference import format_professional_reference, professional_reference_from_text


IMAGE_EDIT_REPLACEMENTS = {
    "\u672c\u6b21\u53ea\u505a\u8fd9\u4e00\u9879\u56fe\u751f\u56fe\u7f16\u8f91": "\u672c\u6b21\u751f\u6210\u8fde\u7eed\u89c6\u9891\u6bb5\u843d",
    "\u5355\u5e27\u56fe\u50cf\u7f16\u8f91\uff0c\u4e0d\u5236\u9020\u591a\u9636\u6bb5\u52a8\u4f5c\u6216\u5267\u60c5": "\u8fde\u7eed\u89c6\u9891\u8fd0\u52a8\uff0c\u52a8\u4f5c\u81ea\u7136\u63a8\u8fdb",
    "\u5355\u5e27\u5173\u952e\u753b\u9762\uff0c\u4e0d\u5236\u9020\u591a\u9636\u6bb5\u52a8\u4f5c": "\u8fde\u7eed\u89c6\u9891\u8fd0\u52a8\uff0c\u52a8\u4f5c\u81ea\u7136\u63a8\u8fdb",
    "\u4eba\u7269\u4fdd\u6301\u53c2\u8003\u56fe\u539f\u6709\u9759\u6001\u59ff\u6001\u548c\u8eab\u4f53\u671d\u5411": "\u4eba\u7269\u4ece\u9996\u5e27\u59ff\u6001\u81ea\u7136\u5f00\u59cb\u8fd0\u52a8\uff0c\u4fdd\u6301\u8eab\u4f53\u6bd4\u4f8b\u548c\u8eab\u4efd\u4e00\u81f4",
    "\u53ea\u5448\u73b0": "\u4ee5\u8fde\u7eed\u8fd0\u52a8\u5448\u73b0",
}


def strip_image_edit_language(value: str) -> str:
    text = str(value or "")
    for before, after in IMAGE_EDIT_REPLACEMENTS.items():
        text = text.replace(before, after)
    return re.sub(r"\s+", " ", text).strip()


def video_provider_prompt(
    *,
    prompt_text: str,
    optimized_prompt: str | None,
    duration_sec: int | float | str,
    motion: str | None,
    last_frame_image_asset_id: str | None,
    context_bundle: dict[str, Any] | None,
    limit: int = 4000,
) -> str:
    base = strip_image_edit_language(optimized_prompt or prompt_text)
    plan = video_generation_plan(
        prompt_text=prompt_text,
        optimized_prompt=optimized_prompt,
        duration_sec=duration_sec,
        motion=motion,
        last_frame_image_asset_id=last_frame_image_asset_id,
        context_bundle=context_bundle,
    )
    parts = [
        base,
        f"Video task: generate a continuous {duration_sec}s image-to-video clip from the first frame.",
        "Use the first frame as a strict visual anchor for identity, clothing, hairstyle silhouette, body proportions, scene layout, lighting, color palette, and composition.",
        _format_motion_plan_for_prompt(plan["motion_plan"]),
        _format_professional_reference_for_video(plan.get("professional_reference", {})),
        _format_director_scenario_for_video(plan.get("director_scenario", {})),
    ]
    if motion:
        parts.append(f"Motion: {strip_image_edit_language(motion)}")
    if last_frame_image_asset_id:
        parts.append("Use the last frame as the ending visual anchor; interpolate motion smoothly between first and last frame.")
    text_channel = context_bundle.get("text_channel") if isinstance(context_bundle, dict) else None
    if isinstance(text_channel, dict):
        for label, key in (
            ("Asset identity", "asset_identity_segment"),
            ("Asset signatures", "asset_signature_segment"),
            ("Director setup", "scene_director_segment"),
            ("Style", "preference_segment"),
        ):
            value = strip_image_edit_language(str(text_channel.get(key) or "").strip())
            if value:
                parts.append(f"{label}: {value}")
    parts.append(
        "Avoid static single-frame language, image-edit wording, identity drift, face changes, wardrobe changes, sudden scene changes, text, watermark, distorted limbs, or abrupt transitions."
    )
    return "\n".join(part for part in parts if part.strip())[:limit]


def video_generation_plan(
    *,
    prompt_text: str,
    optimized_prompt: str | None,
    duration_sec: int | float | str,
    motion: str | None,
    last_frame_image_asset_id: str | None,
    context_bundle: dict[str, Any] | None,
) -> dict[str, Any]:
    source = _combined_source(prompt_text, optimized_prompt, motion, context_bundle)
    motion_plan = video_motion_plan(
        duration_sec=duration_sec,
        motion=motion,
        last_frame_image_asset_id=last_frame_image_asset_id,
        source_text=source,
    )
    return {
        "artifact_type": "agentflow_video_generation_plan",
        "schema_version": "0.1.0",
        "motion_plan": motion_plan,
        "editing_plan": video_editing_plan(source_text=source, last_frame_image_asset_id=last_frame_image_asset_id),
        "professional_reference": professional_reference_from_text(source, node_type="video", generation_target="video"),
        "director_scenario": director_scenario_from_text(source, node_type="video", generation_target="video"),
        "prompt_contract": {
            "first_frame_is_strict_anchor": True,
            "time_beats_are_required": True,
            "candidate_assets_are_editable": True,
            "director_scenario_selected": True,
            "provider_prompt_uses_image_edit_language": False,
        },
    }


def video_motion_plan(
    *,
    duration_sec: int | float | str,
    motion: str | None,
    last_frame_image_asset_id: str | None,
    source_text: str,
) -> dict[str, Any]:
    duration = _duration_float(duration_sec)
    t1 = max(0.8, round(duration * 0.2, 1))
    t2 = max(t1 + 0.8, round(duration * 0.7, 1))
    final = round(duration, 1)
    action = strip_image_edit_language(motion or "continue the current pose with subtle cinematic motion")
    beats = [
        {"time": f"0.0s-{t1:.1f}s", "intent": "hold first-frame identity, layout, lighting, and pose as the visual anchor"},
        {"time": f"{t1:.1f}s-{t2:.1f}s", "intent": action},
        {"time": f"{t2:.1f}s-{final:.1f}s", "intent": "settle into a readable end state without new scene or identity changes"},
    ]
    if last_frame_image_asset_id:
        beats[-1]["intent"] = "arrive at the last-frame visual anchor with smooth interpolation"
    if _has_stars(source_text):
        beats[1]["intent"] = f"{beats[1]['intent']}; add tiny star shimmer and restrained breathing motion"
    return {
        "duration_sec": final,
        "motion_style": "image_to_video_continuity",
        "time_beats": beats,
        "camera_policy": _camera_policy(source_text),
        "subject_motion_policy": "one readable action only; no rewritten plot or new subject identity",
    }


def video_editing_plan(*, source_text: str, last_frame_image_asset_id: str | None) -> dict[str, Any]:
    return {
        "clip_role": "single_continuity_clip",
        "transition_in": "start_from_first_frame",
        "transition_out": "match_last_frame_anchor" if last_frame_image_asset_id else "hold_readable_end_state",
        "pacing": "slow_observational" if _has_stars(source_text) else "medium_continuous",
        "continuity_locks": _continuity_locks(source_text),
        "forbidden_changes": _forbidden_video_changes(source_text),
    }


def _format_professional_reference_for_video(context: dict[str, Any]) -> str:
    sections = [
        format_professional_reference(context, "Scene/Production Design"),
        format_professional_reference(context, "Camera/Framing"),
        format_professional_reference(context, "Lighting"),
        format_professional_reference(context, "Motion/Temporal Progression"),
    ]
    text = " ".join(section for section in sections if section)
    return f"Professional video reference: {text}" if text else ""


def _format_director_scenario_for_video(context: dict[str, Any]) -> str:
    sections = [
        format_director_scenario_reference(context, "Intent"),
        format_director_scenario_reference(context, "Camera/Framing"),
        format_director_scenario_reference(context, "Lighting"),
        format_director_scenario_reference(context, "Motion/Temporal Progression"),
        format_director_scenario_reference(context, "Continuity"),
    ]
    text = " ".join(section for section in sections if section)
    return f"Director scenario video guidance: {text}" if text else ""


def _format_motion_plan_for_prompt(motion_plan: dict[str, Any]) -> str:
    beats = motion_plan.get("time_beats") if isinstance(motion_plan, dict) else []
    if not isinstance(beats, list):
        beats = []
    lines = ["Temporal plan:"]
    for beat in beats:
        if isinstance(beat, dict):
            lines.append(f"- {beat.get('time')}: {beat.get('intent')}")
    return "\n".join(lines)


def _combined_source(
    prompt_text: str,
    optimized_prompt: str | None,
    motion: str | None,
    context_bundle: dict[str, Any] | None,
) -> str:
    parts = [prompt_text, optimized_prompt or "", motion or ""]
    text_channel = context_bundle.get("text_channel") if isinstance(context_bundle, dict) else None
    if isinstance(text_channel, dict):
        parts.extend(str(text_channel.get(key) or "") for key in sorted(text_channel))
    return "\n".join(part for part in parts if str(part or "").strip())


def _duration_float(value: int | float | str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = 5.0
    return max(1.0, parsed)


def _camera_policy(source_text: str) -> str:
    source = source_text.lower()
    if "push" in source or "\u63a8\u8fdb" in source_text:
        return "slow push-in, preserve subject scale and composition"
    if "follow" in source or "\u8ddf" in source_text:
        return "light follow motion, no abrupt reframing"
    return "locked-off or subtle breathing camera"


def _continuity_locks(source_text: str) -> list[str]:
    locks = ["identity", "wardrobe/material", "scene layout", "lighting direction", "camera composition"]
    if _has_robot(source_text):
        locks.append("robot shell and mechanical proportions")
    if _has_rooftop(source_text):
        locks.append("rooftop platform and sky relationship")
    return locks


def _forbidden_video_changes(source_text: str) -> list[str]:
    changes = ["new characters", "new props", "text", "watermark", "UI", "borders", "identity drift", "abrupt scene transition"]
    if _has_rooftop(source_text):
        changes.extend(["unrequested eaves", "unrequested chair", "unrequested stool"])
    return changes


def _has_robot(source_text: str) -> bool:
    return "robot" in source_text.lower() or "\u673a\u5668\u4eba" in source_text


def _has_rooftop(source_text: str) -> bool:
    return "rooftop" in source_text.lower() or "\u5c4b\u9876" in source_text or "\u5929\u53f0" in source_text


def _has_stars(source_text: str) -> bool:
    return "star" in source_text.lower() or "\u661f" in source_text


__all__ = (
    "IMAGE_EDIT_REPLACEMENTS",
    "strip_image_edit_language",
    "video_editing_plan",
    "video_generation_plan",
    "video_motion_plan",
    "video_provider_prompt",
)
