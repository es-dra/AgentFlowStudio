from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.api.runtime_director_compiler import compile_director_setup
from apps.api.runtime_models import DirectorSetup2D


SECTION_ORDER = ["主体调度", "机位景别", "光线", "空间道具", "运动连续", "负面约束"]


class DirectorSceneExportsV1(BaseModel):
    screenshot_artifact_id: str | None = None
    thumbnail_artifact_id: str | None = None


class DirectorSceneBlockingV1(BaseModel):
    version: Literal["director_scene_blocking_v1"] = "director_scene_blocking_v1"
    units: str = "normalized_stage"
    camera: dict[str, Any] | None = None
    subjects: list[dict[str, Any]] = Field(default_factory=list)
    props: list[dict[str, Any]] = Field(default_factory=list)
    lights: list[dict[str, Any]] = Field(default_factory=list)
    stage: dict[str, Any] = Field(default_factory=dict)
    exports: DirectorSceneExportsV1 = Field(default_factory=DirectorSceneExportsV1)
    warnings: list[str] = Field(default_factory=list)


def compile_director_scene_blocking(
    blocking: DirectorSceneBlockingV1 | dict[str, Any] | None,
    *,
    fallback_setup: DirectorSetup2D | dict[str, Any] | None = None,
    visual_asset_signatures: dict[str, str] | None = None,
) -> dict[str, Any]:
    if blocking is None and fallback_setup is not None:
        result = compile_director_setup(fallback_setup, visual_asset_signatures=visual_asset_signatures)
        result["trace_summary"] = {**result.get("trace_summary", {}), "fallback_source": "director_setup_2d"}
        return result

    data = _blocking_model(blocking)
    asset_signatures = visual_asset_signatures or {}
    camera = data.camera if isinstance(data.camera, dict) else None
    subjects = _list(data.subjects)
    props = [item for item in _list(data.props) if item.get("visible", True)]
    lights = _list(data.lights)
    subject_labels, asset_refs_used = _subject_labels(subjects, asset_signatures)
    sections = [
        {"title": "主体调度", "text": _subject_text(subject_labels, subjects)},
        {"title": "机位景别", "text": _camera_text(camera)},
        {"title": "光线", "text": _light_text(lights)},
        {"title": "空间道具", "text": _prop_text(props, subjects[0] if subjects else None)},
        {"title": "运动连续", "text": _motion_text(camera, subjects)},
        {"title": "负面约束", "text": _negative_text(bool(camera or subjects or props or lights))},
    ]
    return {
        "schema_version": "director_scene_blocking_compile_result.v1",
        "sections": sections,
        "warnings": [{"warning_id": item} for item in data.warnings],
        "active_camera_id": _clean(camera.get("id")) if camera and camera.get("id") else None,
        "active_subject_ids": [_clean(item.get("id")) for item in subjects if item.get("id")],
        "prop_ids": [_clean(item.get("id")) for item in props if item.get("id")],
        "asset_refs_used": asset_refs_used,
        "safe_exports": data.exports.model_dump(mode="json", exclude_none=True),
        "trace_summary": {
            "compiler": "director_scene_blocking_compiler_v1_deterministic",
            "units": data.units,
            "subject_count": len(subjects),
            "prop_count": len(props),
            "asset_signature_source": "runtime_visual_asset_store_by_id",
        },
    }


def _blocking_model(blocking: DirectorSceneBlockingV1 | dict[str, Any] | None) -> DirectorSceneBlockingV1:
    if isinstance(blocking, DirectorSceneBlockingV1):
        return blocking
    if isinstance(blocking, dict):
        return DirectorSceneBlockingV1.model_validate(blocking)
    return DirectorSceneBlockingV1()


def _subject_labels(subjects: list[dict[str, Any]], asset_signatures: dict[str, str]) -> tuple[list[str], list[str]]:
    labels: list[str] = []
    asset_refs: list[str] = []
    for subject in subjects:
        asset_id = _clean(subject.get("visual_asset_id") or subject.get("visualAssetId"))
        if asset_id and asset_id in asset_signatures:
            labels.append(asset_signatures[asset_id])
            asset_refs.append(asset_id)
            continue
        labels.append(_clean(subject.get("label") or subject.get("name") or subject.get("id") or "主体"))
    return labels, asset_refs


def _subject_text(labels: list[str], subjects: list[dict[str, Any]]) -> str:
    if not subjects:
        return "没有指定 V2 blocking 主体；按原始提示词中的主体安排调度。"
    parts = []
    anchor = subjects[0]
    for label, subject in zip(labels, subjects):
        phrases = [label, _stage_position_text(subject.get("position")), _subject_relation(subject, anchor)]
        pose = _clean(subject.get("pose"))
        action = _clean(subject.get("action"))
        rotation = _rotation_text(subject.get("rotation"))
        if pose:
            phrases.append(pose)
        if action:
            phrases.append(action)
        if rotation:
            phrases.append(rotation)
        parts.append("，".join(item for item in phrases if item))
    return "；".join(parts) + "。保持主体身份、朝向、姿态和相互距离连续。"


def _camera_text(camera: dict[str, Any] | None) -> str:
    if not camera:
        return "没有指定 V2 生效机位；按原始提示词选择服务动作的清晰机位。"
    parts = [
        _clean(camera.get("label") or camera.get("name") or "生效机位"),
        _clean(camera.get("shot_size") or camera.get("shotSize")),
        _clean(camera.get("angle")),
        _focal_length_text(camera.get("focal_length") or camera.get("focalLength")),
        _clean(camera.get("movement")),
    ]
    return "，".join(item for item in parts if item) + "；以该机位解释主体站位和景别，不直接朗读空间坐标。"


def _light_text(lights: list[dict[str, Any]]) -> str:
    if not lights:
        return "未指定 V2 灯光；使用有明确动机的主光，保持方向、色温和反差统一。"
    parts = []
    for light in lights[:4]:
        label = _clean(light.get("label") or light.get("name") or light.get("type") or "光源")
        phrases = [label, _color_text(light.get("color")), _intensity_text(light.get("intensity")), _direction_text(light.get("direction"))]
        parts.append("，".join(item for item in phrases if item))
    return "；".join(parts) + "。"


def _prop_text(props: list[dict[str, Any]], anchor_subject: dict[str, Any] | None) -> str:
    if not props:
        return "未指定道具；仅保留原始提示词中的空间信息，不自动添加模板元素。"
    parts = []
    for prop in props[:6]:
        label = _clean(prop.get("label") or prop.get("name") or prop.get("id") or "道具")
        parts.append("，".join(item for item in [label, _relative_position(prop, anchor_subject)] if item))
    return "；".join(parts) + "。"


def _motion_text(camera: dict[str, Any] | None, subjects: list[dict[str, Any]]) -> str:
    actions = [_clean(item.get("action")) for item in subjects if _clean(item.get("action"))]
    movement = _clean(camera.get("movement")) if camera else ""
    if actions and movement:
        return f"主体动作以{'、'.join(actions[:3])}为核心；镜头运动采用{movement}，保持轴线和速度连续。"
    if actions:
        return f"主体动作以{'、'.join(actions[:3])}为核心；用姿态和视线暗示运动连续。"
    if movement:
        return f"镜头运动采用{movement}；避免空间跳变和主体漂移。"
    return "按原始提示词安排动作节奏，避免空间跳变和主体漂移。"


def _negative_text(has_blocking: bool) -> str:
    text = "避免角色畸形、五官扭曲、多余肢体、文字乱码、水印、身份漂移。"
    if has_blocking:
        text += "避免机位、景别、光源、主体站位和道具方位互相矛盾。"
    return text


def _stage_position_text(position: Any) -> str:
    if not isinstance(position, dict):
        return ""
    x = _number(position.get("x"), None)
    z = _number(position.get("z"), None)
    horizontal = "舞台左侧" if x is not None and x < 0.38 else "舞台右侧" if x is not None and x > 0.62 else "舞台中线附近"
    depth = "前景" if z is not None and z < 0.38 else "后景" if z is not None and z > 0.62 else "中景层"
    return f"位于{horizontal}{depth}"


def _subject_relation(subject: dict[str, Any], anchor: dict[str, Any]) -> str:
    if subject is anchor:
        return ""
    subject_pos = subject.get("position")
    anchor_pos = anchor.get("position")
    if not isinstance(subject_pos, dict) or not isinstance(anchor_pos, dict):
        return ""
    dx = _number(subject_pos.get("x")) - _number(anchor_pos.get("x"))
    dz = _number(subject_pos.get("z")) - _number(anchor_pos.get("z"))
    horizontal = "右侧" if dx > 0.08 else "左侧" if dx < -0.08 else "同轴"
    depth = "后方" if dz > 0.08 else "前方" if dz < -0.08 else "同一景深"
    return f"相对第一主体在{horizontal}{depth}"


def _relative_position(item: dict[str, Any], anchor_subject: dict[str, Any] | None) -> str:
    if not anchor_subject:
        return ""
    item_pos = item.get("position")
    anchor_pos = anchor_subject.get("position")
    if not isinstance(item_pos, dict) or not isinstance(anchor_pos, dict):
        return ""
    dx = _number(item_pos.get("x")) - _number(anchor_pos.get("x"))
    dz = _number(item_pos.get("z")) - _number(anchor_pos.get("z"))
    horizontal = "主体右侧" if dx > 0.08 else "主体左侧" if dx < -0.08 else "主体中线附近"
    depth = "后景" if dz > 0.08 else "前景" if dz < -0.08 else "同一景深层"
    return f"位于{horizontal}{depth}"


def _rotation_text(rotation: Any) -> str:
    if not isinstance(rotation, dict):
        return ""
    yaw = _number(rotation.get("y"), None)
    if yaw is None:
        return ""
    if -20 <= yaw <= 20:
        return "正向调度"
    if yaw > 0:
        return "向画面右侧转身"
    return "向画面左侧转身"


def _focal_length_text(value: Any) -> str:
    focal_length = _number(value, None)
    if focal_length is None:
        return ""
    if focal_length <= 28:
        return "广角空间感"
    if focal_length >= 70:
        return "长焦压缩空间"
    return "标准焦段"


def _color_text(value: Any) -> str:
    color = _clean(value).lower()
    if not color:
        return ""
    if "cold" in color or "blue" in color or "cyan" in color:
        return "冷蓝色调"
    if "warm" in color or "amber" in color or "orange" in color:
        return "暖色调"
    return _clean(value)


def _intensity_text(value: Any) -> str:
    intensity = _number(value, None)
    if intensity is None:
        return ""
    if intensity >= 0.72:
        return "强主导光"
    if intensity <= 0.32:
        return "低强度补光"
    return "中等强度"


def _direction_text(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    x = _number(value.get("x"))
    z = _number(value.get("z"))
    horizontal = "从画面右侧" if x > 0.05 else "从画面左侧" if x < -0.05 else "从中轴"
    depth = "向前打光" if z < -0.05 else "向后打光" if z > 0.05 else "平向打光"
    return horizontal + depth


def _list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value or [] if isinstance(item, dict)]


def _number(value: Any, default: float | None = 0) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clean(value: Any) -> str:
    return str(value or "").strip()


__all__ = ("DirectorSceneBlockingV1", "SECTION_ORDER", "compile_director_scene_blocking")
