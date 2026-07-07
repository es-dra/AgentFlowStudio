from __future__ import annotations

import re
from typing import Any


IMAGE_EDIT_REPLACEMENTS = {
    "本次只做这一项图生图编辑": "本次生成连续视频段落",
    "单帧图像编辑，不制造多阶段动作或剧情": "连续视频运动，动作自然推进",
    "单帧关键画面，不制造多阶段动作": "连续视频运动，动作自然推进",
    "人物保持参考图原有静态姿态和身体朝向": "人物从首帧姿态自然开始运动，保持身体比例和身份一致",
    "只呈现": "以连续运动呈现",
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
    reference_transform_mode: str | None = None,
    limit: int = 4000,
) -> str:
    base = strip_image_edit_language(optimized_prompt or prompt_text)
    text_channel = context_bundle.get("text_channel") if isinstance(context_bundle, dict) else None
    params = context_bundle.get("request_parameters") if isinstance(context_bundle, dict) else None
    reference_mode = str(reference_transform_mode or "").strip().lower()
    if isinstance(params, dict):
        reference_mode = reference_mode or str(params.get("reference_transform_mode") or "").strip().lower()
    if not reference_mode and ("原创重生" in base or "降 IP" in base or "降低 IP" in base):
        reference_mode = "originalize_ip_safe"
    originalize = reference_mode in {"originalize", "originalize_ip_safe", "ip_safe_rebirth", "ip_risk_reduction"} or "降低可识别 IP" in base
    parts = [
        base,
        f"Video task: generate a continuous {duration_sec}s image-to-video clip from the first frame.",
        (
            "Use the first frame as inspiration only for broad mood, material direction, and motion feasibility; redesign identity, costume, silhouette, scene composition, and recognizable IP cues."
            if originalize
            else "Use the first frame as a strict visual anchor for identity, clothing, hairstyle silhouette, body proportions, scene layout, lighting, color palette, and composition."
        ),
    ]
    if motion:
        parts.append(f"Motion: {strip_image_edit_language(motion)}")
    if last_frame_image_asset_id:
        parts.append("Use the last frame as the ending visual anchor; interpolate motion smoothly between first and last frame.")
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
        "Avoid copying recognizable IP, exact iconic costume, logo, pose, weapon, scene composition, static single-frame language, text, watermark, distorted limbs, or abrupt transitions."
        if originalize
        else "Avoid static single-frame language, image-edit wording, identity drift, face changes, wardrobe changes, sudden scene changes, text, watermark, distorted limbs, or abrupt transitions."
    )
    return "\n".join(part for part in parts if part.strip())[:limit]


__all__ = ("IMAGE_EDIT_REPLACEMENTS", "strip_image_edit_language", "video_provider_prompt")
