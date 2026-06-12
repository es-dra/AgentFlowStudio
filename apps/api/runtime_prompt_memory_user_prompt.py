from __future__ import annotations

from typing import Any

from apps.api.runtime_director_compiler import compile_director_setup
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_prompt_text import plain_prompt_from_sections


USER_SECTION_ORDER = ["人物", "场景", "镜头", "灯光", "运动", "负面约束"]

_EN_FALLBACKS = {
    "Primary character",
    "Primary scene",
    "emotion implied by the prompt",
    "motivated cinematic light",
    "camera movement aligned with the beat",
    "subtle subject and camera motion",
    "visible action from the node prompt",
}


def build_user_prompt(request: PromptOptimizationRequest, slots: dict[str, str]) -> dict[str, Any]:
    params = request.node_parameters or {}
    director = request.director_setup.model_dump(mode="json") if request.director_setup else {}
    if request.director_setup:
        return _compiled_director_user_prompt(request)
    sections = {
        "人物": _character_section(slots, director),
        "场景": _scene_section(request, slots, director),
        "镜头": _camera_section(request, slots, params, director),
        "灯光": _lighting_section(slots, director),
        "运动": _motion_section(request, slots, params, director),
        "负面约束": _negative_section(request, director),
    }
    user_sections = [{"title": title, "text": sections[title]} for title in USER_SECTION_ORDER]
    user_prompt = "\n".join(f"{item['title']}：{item['text']}" for item in user_sections)
    return {
        "user_prompt": user_prompt,
        "user_prompt_plain": plain_prompt_from_sections(user_sections),
        "user_prompt_sections": user_sections,
    }


def _compiled_director_user_prompt(request: PromptOptimizationRequest) -> dict[str, Any]:
    compiled = compile_director_setup(request.director_setup)
    compiled_by_title = {section["title"]: section["text"] for section in compiled["sections"]}
    sections = {
        "人物": compiled_by_title.get("主体调度", ""),
        "场景": compiled_by_title.get("空间道具", ""),
        "镜头": compiled_by_title.get("机位景别", ""),
        "灯光": compiled_by_title.get("光线", ""),
        "运动": compiled_by_title.get("运动连续", ""),
        "负面约束": compiled_by_title.get("负面约束", ""),
    }
    user_sections = [{"title": title, "text": sections[title]} for title in USER_SECTION_ORDER]
    user_prompt = "\n".join(f"{item['title']}：{item['text']}" for item in user_sections)
    return {
        "user_prompt": user_prompt,
        "user_prompt_plain": plain_prompt_from_sections(user_sections),
        "user_prompt_sections": user_sections,
        "director_compile_result": compiled,
    }


def _character_section(slots: dict[str, str], director: dict[str, Any]) -> str:
    subject = _first(director.get("subjects")) or _first(director.get("characters")) or {}
    slot_subject = _zh(slots.get("subject"))
    name = _clean(subject.get("name") or subject.get("label") or slot_subject)
    parts = []
    if name:
        parts.append(f"主体为{name}")
    if subject:
        parts.append(_join_existing([
            f"站位 {subject.get('x')}/{subject.get('y')}" if subject.get("x") is not None else "",
            f"朝向 {subject.get('angle')}°" if subject.get("angle") is not None else "",
            f"动作 {subject.get('action')}" if subject.get("action") else "",
            f"情绪 {subject.get('emotion')}" if subject.get("emotion") else "",
        ]))
    emotion = _zh(slots.get("emotion"))
    if emotion and not subject.get("emotion"):
        parts.append(f"情绪基调为{emotion}")
    if not parts:
        parts.append("以原始描述中的主体为核心")
    parts.append("保持人物身份、服装与神态在多镜头间一致，避免一次性动作改变人物设定。")
    return "，".join(filter(None, parts))


def _scene_section(request: PromptOptimizationRequest, slots: dict[str, str], director: dict[str, Any]) -> str:
    scene = _zh(slots.get("scene"))
    style = _zh(slots.get("style")) or _zh(request.style)
    props = [
        f"{_clean(item.get('name') or item.get('kind'))}（{_clean(item.get('narrative')) or '可见'}）"
        for item in _list(director.get("props"))
        if item.get("visible", True)
    ]
    modifiers = [_clean(item.get("name") or item.get("kind")) for item in _list(director.get("modifiers"))]
    parts = []
    if scene:
        parts.append(f"场景设定在{scene}")
    else:
        parts.append("依据原始描述补全场景：交代地点、时间与氛围")
    if style and style.lower() != "cinematic":
        parts.append(f"整体风格为{style}")
    if props:
        parts.append("关键道具包括" + "、".join(props))
    if modifiers:
        parts.append("辅助器材包括" + "、".join(modifiers))
    if director.get("composition"):
        parts.append(f"空间构图意图：{director['composition']}")
    if director.get("notes"):
        parts.append(f"导演备注：{director['notes']}")
    parts.append("保留可复用的空间结构、关键道具与氛围元素，环境服务于主体而不喧宾夺主。")
    return "，".join(parts)


def _camera_section(
    request: PromptOptimizationRequest,
    slots: dict[str, str],
    params: dict[str, Any],
    director: dict[str, Any],
) -> str:
    camera = _first(director.get("cameras")) or {}
    parts: list[str] = []
    if camera:
        parts.extend([
            f"机位 {camera.get('name')}" if camera.get("name") else "",
            f"{camera.get('shot')}" if camera.get("shot") else "",
            f"{camera.get('height')}" if camera.get("height") else "",
            f"FOV {camera.get('fov')}" if camera.get("fov") is not None else "",
            f"焦段 {camera.get('focalLength')}mm" if camera.get("focalLength") is not None else "",
            f"构图 {camera.get('composition')}" if camera.get("composition") else "",
            f"注视 {camera.get('lookAt')}" if camera.get("lookAt") else "",
        ])
    camera_kw = _zh(slots.get("camera"))
    if camera_kw:
        parts.append(camera_kw)
    if params.get("camera"):
        parts.append(f"摄影参数：{params['camera']}")
    if params.get("spec"):
        parts.append(f"画面规格：{params['spec']}")
    if params.get("panorama"):
        parts.append("720° 全景画面，画幅 2:1")
    if not _join_existing(parts):
        parts.append("根据画面优先级选择景别与角度：先交代环境再聚焦主体" if request.generation_target in ("video", "keyframe") else "中景为主，主体置于视觉优先位")
    return _join_existing(parts) + "，构图清晰，单一镜头只表达一个主要意图。"


def _lighting_section(slots: dict[str, str], director: dict[str, Any]) -> str:
    lights = _list(director.get("lights"))
    if lights:
        parts = []
        for light in lights:
            parts.append(_join_existing([
                _clean(light.get("name") or light.get("kind")),
                f"强度 {light.get('intensity')}%" if light.get("intensity") is not None else "",
                f"色温 {light.get('colorTemp')}K" if light.get("colorTemp") is not None else "",
                f"柔硬 {light.get('softness')}" if light.get("softness") is not None else "",
                "动机光" if light.get("motivated") else "",
            ]))
        return "；".join(filter(None, parts)) + "。光源方向、强弱和色温必须互相一致，服务情绪与空间层次。"
    lighting = _zh(slots.get("lighting"))
    if lighting:
        return f"以{lighting}为主光，光源有明确动机，明暗对比与色温服务情绪，保留环境氛围层次。"
    return "光源有明确动机：主光方向清晰，明暗对比柔和，色温与情绪一致，避免无来源的平光。"


def _motion_section(
    request: PromptOptimizationRequest,
    slots: dict[str, str],
    params: dict[str, Any],
    director: dict[str, Any],
) -> str:
    subject = _first(director.get("subjects")) or _first(director.get("characters")) or {}
    camera = _first(director.get("cameras")) or {}
    if request.generation_target in ("image", "keyframe"):
        base = "静态画面：通过姿态、视线与景深暗示动势，强调材质与细节质感。"
    else:
        parts = []
        if params.get("motion"):
            parts.append(f"运镜采用“{params['motion']}”")
        elif camera.get("angle") is not None:
            parts.append(f"镜头运动方向参考机位朝向 {camera.get('angle')}°")
        else:
            parts.append("一个主导镜头运动贯穿始终，速度与情绪节奏一致")
        if subject.get("action"):
            parts.append(f"主体动作保持为{subject['action']}")
        base = "，".join(parts) + "。"
    return base + "关键帧之间保持光线、空间、服装和主体方向连续。"


def _negative_section(request: PromptOptimizationRequest, director: dict[str, Any]) -> str:
    base = "避免人物畸形、五官扭曲、多余肢体、文字乱码与水印；避免镜头语言互相冲突；避免画面元素与上述设定矛盾。"
    if director:
        base += "避免光源冲突、机位冲突、空间关系错乱、人物站位漂移和道具位置跳变。"
    if request.generation_target == "video":
        base += "避免画面闪烁、场景跳变与身份漂移。"
    return base


def _zh(value: str | None) -> str:
    text = (value or "").strip()
    if not text or text in _EN_FALLBACKS:
        return ""
    return text


def _list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value or [] if isinstance(item, dict)]


def _first(value: Any) -> dict[str, Any] | None:
    items = _list(value)
    return items[0] if items else None


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _join_existing(parts: list[str]) -> str:
    return "，".join(part for part in parts if part)


__all__ = ("USER_SECTION_ORDER", "build_user_prompt")
