from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


REFERENCE_CONDITIONED = "reference_conditioned"
FIRST_FRAME = "first_frame"
TEXT_TO_VIDEO = "text_to_video"
GENERATION_MODES = {
    REFERENCE_CONDITIONED,
    FIRST_FRAME,
    TEXT_TO_VIDEO,
}

TEMPORAL_STAGING_FIELDS = (
    "subject_action_arc",
    "spatial_displacement",
    "interaction_object",
    "camera_movement",
    "environment_dynamics",
    "pacing",
    "start_state",
    "end_state",
    "narrative_purpose",
)

TEMPORAL_STAGING_LABELS = {
    "subject_action_arc": "主体动作弧",
    "spatial_displacement": "空间位移",
    "interaction_object": "互动对象",
    "camera_movement": "镜头运动",
    "environment_dynamics": "环境动态",
    "pacing": "节奏",
    "start_state": "起始状态",
    "end_state": "结束状态",
    "narrative_purpose": "叙事目的",
}


def mode_options(capability: Mapping[str, Any]) -> list[dict[str, Any]]:
    options = [
        {
            "mode": REFERENCE_CONDITIONED,
            "label": "参考图约束视频",
            "supported": capability.get("reference_mode_supported") is True,
            "reason": "使用已批准角色、场景和道具图约束身份与连续性，不锁定首帧。",
        },
        {
            "mode": FIRST_FRAME,
            "label": "首帧图生视频",
            "supported": capability.get("first_frame_mode_supported") is True,
            "reason": "仅在镜头明确要求从已批准关键帧开始时使用。",
        },
        {
            "mode": TEXT_TO_VIDEO,
            "label": "文生视频（仅文字叙事）",
            "supported": capability.get("text_mode_supported") is True,
            "reason": "不发送图片；身份与画面连续性风险更高。",
        },
    ]
    return options


def default_mode(capability: Mapping[str, Any], reference_count: int) -> str:
    if reference_count > 0 and capability.get("reference_mode_supported") is True:
        return REFERENCE_CONDITIONED
    if capability.get("text_mode_supported") is True:
        return TEXT_TO_VIDEO
    return ""


def temporal_staging_template(shot: Mapping[str, Any]) -> dict[str, str]:
    return {
        "subject_action_arc": _text(shot.get("action")),
        "spatial_displacement": "",
        "interaction_object": "",
        "camera_movement": _text(shot.get("movement")),
        "environment_dynamics": "",
        "pacing": "",
        "start_state": "",
        "end_state": "",
        "narrative_purpose": _text(shot.get("narrative_purpose")),
    }


def validate_temporal_staging(value: Any) -> dict[str, str]:
    staging = dict(value) if isinstance(value, Mapping) else {}
    normalized = {
        field: _text(staging.get(field))
        for field in TEMPORAL_STAGING_FIELDS
    }
    missing = [
        TEMPORAL_STAGING_LABELS[field]
        for field, text in normalized.items()
        if not text
    ]
    if missing:
        raise ValueError(f"镜头叙事还需补充：{'、'.join(missing)}")
    oversized = [
        TEMPORAL_STAGING_LABELS[field]
        for field, text in normalized.items()
        if len(text) > 600
    ]
    if oversized:
        raise ValueError(f"镜头叙事字段过长：{'、'.join(oversized)}")
    return normalized


def validate_generation_mode(
    mode: Any,
    *,
    capability: Mapping[str, Any],
    source: Mapping[str, Any],
) -> dict[str, Any]:
    selected = _text(mode)
    if selected not in GENERATION_MODES:
        raise ValueError("请选择受支持的视频生成方式")
    option = next(
        item for item in mode_options(capability)
        if item["mode"] == selected
    )
    if option["supported"] is not True:
        raise ValueError(f"{option['label']}当前未由视频服务开放，不能静默替换")
    references = [
        item for item in source.get("references", [])
        if isinstance(item, Mapping)
    ]
    if selected == REFERENCE_CONDITIONED and not references:
        raise ValueError("参考图约束视频需要至少一张已批准资产参考图")
    if selected == FIRST_FRAME and not (source.get("keyframe") or {}).get("image_asset_id"):
        raise ValueError("首帧图生视频需要明确选择一张已批准关键帧")
    return deepcopy(option)


def build_temporal_prompt(
    *,
    mode: str,
    selection_reason: str,
    staging: Mapping[str, str],
    shot: Mapping[str, Any],
    canonical_entities: Mapping[str, list[str]],
) -> dict[str, Any]:
    mode_instruction = {
        REFERENCE_CONDITIONED: (
            "Create one continuous narrative video shot. Use the supplied reference images "
            "only for identity and continuity; do not treat any reference as a first or last frame."
        ),
        FIRST_FRAME: (
            "Create one continuous narrative video shot beginning exactly from the supplied first frame."
        ),
        TEXT_TO_VIDEO: (
            "Create one continuous narrative video shot from text only."
        ),
    }[mode]
    entity_lines = [
        f"Canonical characters: {', '.join(canonical_entities.get('characters', [])) or 'none'}.",
        f"Canonical scene: {', '.join(canonical_entities.get('scenes', [])) or 'none'}.",
        f"Canonical props: {', '.join(canonical_entities.get('props', [])) or 'none'}.",
    ]
    lines = [
        mode_instruction,
        *entity_lines,
        f"Subject action arc: {staging['subject_action_arc']}",
        f"Spatial displacement: {staging['spatial_displacement']}",
        f"Interaction object: {staging['interaction_object']}",
        f"Camera movement: {staging['camera_movement']}",
        f"Environment dynamics: {staging['environment_dynamics']}",
        f"Pacing: {staging['pacing']}",
        f"Start state: {staging['start_state']}",
        f"End state: {staging['end_state']}",
        f"Narrative purpose: {staging['narrative_purpose']}",
        f"Composition: {_text(shot.get('composition'))}",
        f"Camera angle: {_text(shot.get('camera_angle'))}",
        f"Emotion: {_text(shot.get('emotion'))}",
        (
            "Continuity: "
            + (
                "; ".join(
                    _text(item)
                    for item in shot.get("continuity_cues", [])
                    if _text(item)
                )
                or "preserve the approved canonical identities and art direction."
            )
        ),
        "Do not add unrequested characters, locations, props, text, logos, watermarks, or plot events.",
    ]
    return {
        "schema_version": "afs.video_prompt_contract.v0.2",
        "provider_prompt": "\n".join(lines),
        "generation_mode": mode,
        "selection_reason": _text(selection_reason),
        "temporal_staging": dict(staging),
        "canonical_entities": deepcopy(dict(canonical_entities)),
        "shot_action": staging["subject_action_arc"],
        "composition": _text(shot.get("composition")),
        "camera_angle": _text(shot.get("camera_angle")),
        "camera_movement": staging["camera_movement"],
        "motion": staging["camera_movement"],
        "emotion": _text(shot.get("emotion")),
        "continuity_cues": [
            _text(item)
            for item in shot.get("continuity_cues", [])
            if _text(item)
        ],
        "keyword_rewrite": False,
        "sample_fallback": False,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()
