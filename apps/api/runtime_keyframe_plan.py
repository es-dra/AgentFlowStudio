from __future__ import annotations

import re
from typing import Any

from agentflow.knowledge.professional_reference import professional_reference_from_text
from apps.api.runtime_models import KeyframeGenerationRequest


def build_keyframe_plan(
    request: KeyframeGenerationRequest,
    *,
    provider_prompt: str,
    reference_images: list[dict[str, Any]],
    context_bundle: dict[str, Any] | None,
) -> dict[str, Any]:
    source = _plan_source(request, provider_prompt, context_bundle)
    refs = [item.get("public") or {} for item in reference_images]
    ref_ids = [str(item.get("asset_id")) for item in refs if item.get("asset_id")]
    return {
        "artifact_type": "agentflow_keyframe_plan",
        "schema_version": "0.1.0",
        "node_id": request.node_id,
        "frame_role": "story_continuity_keyframe",
        "composition": _composition_plan(source, request.aspect_ratio),
        "subject_pose": _subject_pose_plan(source),
        "asset_locks": _asset_locks(source, refs, context_bundle),
        "scene_locks": _scene_locks(source, context_bundle),
        "lighting_plan": _lighting_plan(source),
        "camera_plan": _camera_plan(source),
        "professional_reference": professional_reference_from_text(source, node_type="image", generation_target="keyframe"),
        "reference_asset_ids": ref_ids,
        "candidate_assets_are_editable": True,
        "forbidden_changes": _forbidden_changes(source),
    }


def _plan_source(
    request: KeyframeGenerationRequest,
    provider_prompt: str,
    context_bundle: dict[str, Any] | None,
) -> str:
    parts = [request.prompt_text, request.optimized_prompt or "", provider_prompt]
    text_channel = context_bundle.get("text_channel") if isinstance(context_bundle, dict) else None
    if isinstance(text_channel, dict):
        parts.extend(str(text_channel.get(key) or "") for key in sorted(text_channel))
    return "\n".join(part for part in parts if str(part or "").strip())


def _composition_plan(source: str, aspect_ratio: str) -> dict[str, str]:
    return {
        "aspect_ratio": aspect_ratio,
        "shot_size": "medium" if not _wide_scene(source) else "wide_or_medium_wide",
        "subject_placement": "clear primary subject with stable readable environment",
        "background_policy": "use only scripted or referenced scene geometry",
    }


def _subject_pose_plan(source: str) -> str:
    if "sitting" in source.lower() or "\u5750" in source:
        return "sitting only because source explicitly requests it"
    if "standing" in source.lower() or "\u7ad9" in source:
        return "standing or lightly leaning, matching source action"
    return "neutral readable pose; do not add chair, stool, or extra furniture to justify the pose"


def _asset_locks(source: str, refs: list[dict[str, Any]], context_bundle: dict[str, Any] | None) -> list[dict[str, Any]]:
    locks: list[dict[str, Any]] = []
    for ref in refs:
        locks.append(
            {
                "asset_id": str(ref.get("asset_id") or ""),
                "role": str(ref.get("role") or ref.get("asset_type") or "reference"),
                "lock_fields": ["identity", "silhouette", "proportions", "materials"],
            }
        )
    for asset in _included_assets(context_bundle):
        asset_id = str(asset.get("asset_id") or "")
        if asset_id and not any(item.get("asset_id") == asset_id for item in locks):
            locks.append(
                {
                    "asset_id": asset_id,
                    "role": str(asset.get("asset_type") or "asset"),
                    "lock_fields": ["identity", "approved signature", "relationship to scene"],
                }
            )
    if _has_robot(source) and not locks:
        locks.append({"asset_id": "candidate:future_robot", "role": "character", "lock_fields": ["robot head shell", "body proportions", "material finish"]})
    return locks[:16]


def _scene_locks(source: str, context_bundle: dict[str, Any] | None) -> list[str]:
    locks = ["scene layout", "main spatial relationship", "lighting direction"]
    if _has_rooftop(source):
        locks.extend(["rooftop platform geometry", "sky/background relationship"])
    if _included_assets(context_bundle):
        locks.append("approved context bundle scene assets")
    return locks


def _lighting_plan(source: str) -> str:
    if "night" in source.lower() or "\u591c" in source or _has_stars(source):
        return "night ambient light with readable subject edges and stable color temperature"
    return "motivated natural light matching upstream scene"


def _camera_plan(source: str) -> str:
    if "close" in source.lower() or "\u7279\u5199" in source:
        return "close composition while preserving identity and environment anchors"
    if _wide_scene(source):
        return "medium-wide composition with clear subject and environment"
    return "medium composition, stable lens, no abrupt reframing"


def _forbidden_changes(source: str) -> list[str]:
    changes = ["text", "watermark", "UI", "borders", "new characters", "identity drift", "unrequested props"]
    if _has_rooftop(source):
        changes.extend(["unrequested eaves", "unrequested chair", "unrequested stool"])
    if _has_robot(source):
        changes.extend(["humanizing the robot beyond approved design", "changing robot head shell"])
    return changes


def _included_assets(context_bundle: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(context_bundle, dict):
        return []
    assets = context_bundle.get("included_assets")
    return assets if isinstance(assets, list) else []


def _wide_scene(source: str) -> bool:
    return any(token in source.lower() for token in ("wide", "establishing", "landscape")) or any(
        token in source for token in ("\u5168\u666f", "\u8fdc\u666f", "\u73af\u5883")
    )


def _has_robot(source: str) -> bool:
    return "robot" in source.lower() or "\u673a\u5668\u4eba" in source


def _has_rooftop(source: str) -> bool:
    return "rooftop" in source.lower() or "\u5c4b\u9876" in source or "\u5929\u53f0" in source


def _has_stars(source: str) -> bool:
    return "star" in source.lower() or "\u661f" in source


__all__ = ("build_keyframe_plan",)
