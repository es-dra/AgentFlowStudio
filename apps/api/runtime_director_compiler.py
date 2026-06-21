from __future__ import annotations

import math
from typing import Any

from apps.api.runtime_models import DirectorSetup2D


SECTION_ORDER = ["主体调度", "机位景别", "光线", "空间道具", "运动连续", "负面约束"]


def compile_director_setup(
    setup: DirectorSetup2D | dict[str, Any] | None,
    *,
    visual_asset_signatures: dict[str, str] | None = None,
) -> dict[str, Any]:
    data = _setup_dict(setup)
    asset_signatures = visual_asset_signatures or {}
    warnings: list[dict[str, Any]] = []
    cameras = _list(data.get("cameras"))
    subjects = _list(data.get("subjects") or data.get("characters"))
    lights = _list(data.get("lights"))
    props = [item for item in _list(data.get("props")) if item.get("visible", True)]

    camera, inactive_camera_ids = _active_camera(data, cameras, warnings)
    active_subjects = _active_subjects(data, subjects)
    if subjects and not active_subjects:
        active_subjects = subjects

    subject_labels, asset_refs_used = _subject_labels(active_subjects, asset_signatures)
    inferred_shot = _infer_shot(camera, active_subjects[0] if active_subjects else None)
    camera_text = _camera_text(camera, active_subjects, inferred_shot, warnings)

    sections = [
        {"title": "主体调度", "text": _subject_text(subject_labels, active_subjects, camera)},
        {"title": "机位景别", "text": camera_text},
        {"title": "光线", "text": _light_text(lights, camera, active_subjects[0] if active_subjects else None)},
        {"title": "空间道具", "text": _prop_text(props, active_subjects[0] if active_subjects else None, data)},
        {"title": "运动连续", "text": _motion_text(active_subjects, camera)},
        {"title": "负面约束", "text": _negative_text(bool(camera or active_subjects or lights or props))},
    ]

    return {
        "schema_version": "director_compile_result.v1",
        "sections": sections,
        "warnings": warnings,
        "active_camera_id": str(camera.get("id")) if camera and camera.get("id") else None,
        "active_subject_ids": [str(item.get("id")) for item in active_subjects if item.get("id")],
        "asset_refs_used": asset_refs_used,
        "trace_summary": {
            "compiler": "director_compiler_v1_deterministic",
            "inactive_camera_ids": inactive_camera_ids,
            "active_subject_count": len(active_subjects),
            "asset_signature_source": "runtime_visual_asset_store_by_id",
        },
    }


def _setup_dict(setup: DirectorSetup2D | dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(setup, DirectorSetup2D):
        return setup.model_dump(mode="json")
    return setup if isinstance(setup, dict) else {}


def _active_camera(data: dict[str, Any], cameras: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, list[str]]:
    if not cameras:
        return None, []
    active_id = str(data.get("activeCameraId") or "").strip()
    selected = None
    if active_id:
        selected = next((item for item in cameras if str(item.get("id")) == active_id), None)
        if selected is None:
            warnings.append({"warning_id": "active_camera_missing", "active_camera_id": active_id})
    if selected is None:
        selected = cameras[0]
        if len(cameras) > 1:
            warnings.append({"warning_id": "active_camera_defaulted", "active_camera_id": str(selected.get("id") or "")})
    inactive = [str(item.get("id")) for item in cameras if item is not selected and item.get("id")]
    return selected, inactive


def _active_subjects(data: dict[str, Any], subjects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    active_ids = [str(item) for item in data.get("activeSubjectIds") or [] if str(item)]
    if active_ids:
        wanted = set(active_ids)
        return [item for item in subjects if str(item.get("id")) in wanted]
    return subjects


def _subject_labels(subjects: list[dict[str, Any]], asset_signatures: dict[str, str]) -> tuple[list[str], list[str]]:
    labels: list[str] = []
    asset_refs: list[str] = []
    for subject in subjects:
        asset_id = str(subject.get("visual_asset_id") or subject.get("visualAssetId") or "").strip()
        if asset_id and asset_id in asset_signatures:
            labels.append(asset_signatures[asset_id])
            asset_refs.append(asset_id)
            continue
        labels.append(_clean(subject.get("name") or subject.get("label") or subject.get("id") or "主体"))
    return labels, asset_refs


def _subject_text(labels: list[str], subjects: list[dict[str, Any]], camera: dict[str, Any] | None) -> str:
    if not subjects:
        return "没有指定生效主体；按原始提示词中的主体安排调度。"
    parts = []
    for label, subject in zip(labels, subjects):
        relation = _facing_relation(camera, subject)
        action = _clean(subject.get("action"))
        emotion = _clean(subject.get("emotion"))
        phrases = [label, relation]
        if action:
            phrases.append(action)
        if emotion:
            phrases.append(emotion)
        parts.append("，".join(item for item in phrases if item))
    return "；".join(parts) + "。保持主体在镜头内的身份、姿态方向和情绪连续。"


def _camera_text(
    camera: dict[str, Any] | None,
    subjects: list[dict[str, Any]],
    inferred_shot: str,
    warnings: list[dict[str, Any]],
) -> str:
    if not camera:
        return "没有指定生效机位；按原始提示词选择服务动作的清晰机位。"
    manual_shot = _clean(camera.get("shot"))
    if manual_shot and inferred_shot and not _shot_compatible(manual_shot, inferred_shot):
        warnings.append({"warning_id": "shot_geometry_conflict", "manual_shot": manual_shot, "inferred_shot": inferred_shot})
    height = _clean(camera.get("height")) or "平视"
    composition = _clean(camera.get("composition"))
    subject = subjects[0] if subjects else None
    angle = _camera_subject_angle(camera, subject)
    angle_text = _shooting_angle_text(angle)
    shot = manual_shot or inferred_shot or "中景"
    parts = [_clean(camera.get("name")) or "生效机位", height, shot, angle_text]
    if composition:
        parts.append(composition)
    return "，".join(item for item in parts if item) + "；用摄影语言表达空间关系，避免机械读数。"


def _light_text(lights: list[dict[str, Any]], camera: dict[str, Any] | None, subject: dict[str, Any] | None) -> str:
    if not lights:
        return "未指定灯光；使用有明确动机的主光，保持方向、色温和反差统一。"
    lines = []
    for light in lights[:4]:
        name = _clean(light.get("name") or light.get("kind") or "光源")
        position = _light_position(light, camera, subject)
        temp = _color_temperature_text(light.get("colorTemp"))
        softness = _softness_text(light.get("softness"))
        intensity = _intensity_text(light.get("intensity"))
        motive = "有动机光来源" if light.get("motivated") else ""
        lines.append("，".join(item for item in [name, position, temp, softness, intensity, motive] if item))
    return "；".join(lines) + "。"


def _prop_text(props: list[dict[str, Any]], subject: dict[str, Any] | None, data: dict[str, Any]) -> str:
    parts = []
    for prop in props[:6]:
        name = _clean(prop.get("name") or prop.get("kind") or "道具")
        relation = _relative_position(prop, subject)
        narrative = _clean(prop.get("narrative"))
        parts.append("，".join(item for item in [name, relation, narrative] if item))
    if data.get("composition"):
        parts.append(f"构图意图：{_clean(data.get('composition'))}")
    if data.get("notes"):
        parts.append(f"导演备注：{_clean(data.get('notes'))}")
    return "；".join(parts) if parts else "未指定道具；仅保留原始提示词中的空间信息，不自动添加模板元素。"


def _motion_text(subjects: list[dict[str, Any]], camera: dict[str, Any] | None) -> str:
    actions = [_clean(item.get("action")) for item in subjects if _clean(item.get("action"))]
    if actions:
        return f"主体动作以{'、'.join(actions[:3])}为核心；镜头只表达一个主要意图，保持角色方向、光线和空间连续。"
    if camera:
        return "静态关键帧通过姿态、视线和景深暗示动势；镜头之间保持空间轴线连续。"
    return "按原始提示词安排动作节奏，避免空间跳变和主体漂移。"


def _negative_text(has_setup: bool) -> str:
    base = "避免角色畸形、五官扭曲、多余肢体、文字乱码、水印、身份漂移。"
    if has_setup:
        base += "避免机位冲突、景别冲突；避免光源冲突、主体站位和道具方位互相矛盾。"
    return base


def _infer_shot(camera: dict[str, Any] | None, subject: dict[str, Any] | None) -> str:
    if not camera or not subject:
        return ""
    distance = _distance(camera, subject)
    fov = _number(camera.get("fov"), 50)
    if distance <= 22 and fov <= 55:
        return "近景"
    if distance <= 42 and fov <= 70:
        return "中景"
    return "远景"


def _shot_compatible(manual: str, inferred: str) -> bool:
    if manual == inferred:
        return True
    groups = [{"特写", "近景", "中近景"}, {"中景", "中近景"}, {"全景", "远景"}]
    return any(manual in group and inferred in group for group in groups)


def _camera_subject_angle(camera: dict[str, Any], subject: dict[str, Any] | None) -> float | None:
    if not subject:
        return None
    return math.degrees(math.atan2(_number(subject.get("y")) - _number(camera.get("y")), _number(subject.get("x")) - _number(camera.get("x"))))


def _shooting_angle_text(angle: float | None) -> str:
    if angle is None:
        return "面向主体动作线"
    normalized = (angle + 360) % 360
    if 45 <= normalized < 135:
        return "从下方空间向主体拍摄"
    if 135 <= normalized < 225:
        return "从画面右侧形成侧向观察"
    if 225 <= normalized < 315:
        return "从上方空间压向主体"
    return "从画面左侧形成侧向观察"


def _facing_relation(camera: dict[str, Any] | None, subject: dict[str, Any]) -> str:
    if not camera or subject.get("angle") is None:
        return ""
    to_camera = math.degrees(math.atan2(_number(camera.get("y")) - _number(subject.get("y")), _number(camera.get("x")) - _number(subject.get("x"))))
    diff = abs(((to_camera - _number(subject.get("angle")) + 180) % 360) - 180)
    if diff <= 40:
        return "正面朝向镜头"
    if diff >= 140:
        return "背对镜头"
    return "四分之三侧身"


def _light_position(light: dict[str, Any], camera: dict[str, Any] | None, subject: dict[str, Any] | None) -> str:
    if not camera or not subject:
        return "作为主导环境光"
    light_angle = math.degrees(math.atan2(_number(light.get("y")) - _number(subject.get("y")), _number(light.get("x")) - _number(subject.get("x"))))
    camera_angle = math.degrees(math.atan2(_number(camera.get("y")) - _number(subject.get("y")), _number(camera.get("x")) - _number(subject.get("x"))))
    diff = abs(((light_angle - camera_angle + 180) % 360) - 180)
    if diff <= 35:
        return "顺光"
    if diff <= 110:
        return "侧光"
    if diff <= 155:
        return "侧逆光"
    return "逆光或轮廓光"


def _color_temperature_text(value: Any) -> str:
    temp = _number(value, None)
    if temp is None:
        return ""
    if temp < 4000:
        return "偏暖色温"
    if temp > 5200:
        return "偏冷色温"
    return "中性偏暖色温"


def _softness_text(value: Any) -> str:
    softness = _number(value, None)
    if softness is None:
        return ""
    if softness >= 70:
        return "柔光"
    if softness <= 35:
        return "硬光"
    return "柔硬适中"


def _intensity_text(value: Any) -> str:
    intensity = _number(value, None)
    if intensity is None:
        return ""
    if intensity >= 75:
        return "强主导光"
    if intensity <= 35:
        return "低强度补光"
    return "中等强度"


def _relative_position(item: dict[str, Any], subject: dict[str, Any] | None) -> str:
    if not subject:
        return ""
    dx = _number(item.get("x")) - _number(subject.get("x"))
    dy = _number(item.get("y")) - _number(subject.get("y"))
    horizontal = "右侧" if dx > 6 else "左侧" if dx < -6 else "中线附近"
    depth = "前景" if dy > 8 else "背景" if dy < -8 else "同一景深层"
    return f"位于主体{horizontal}{depth}"


def _distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    return math.hypot(_number(a.get("x")) - _number(b.get("x")), _number(a.get("y")) - _number(b.get("y")))


def _list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value or [] if isinstance(item, dict)]


def _number(value: Any, default: float = 0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clean(value: Any) -> str:
    return str(value or "").strip()


__all__ = ("SECTION_ORDER", "compile_director_setup")
