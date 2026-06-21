from __future__ import annotations

import re
from typing import Any


VIDEO_MODES = {"i2v", "t2v"}


def prompt_optimization_mode(
    *,
    node_type: str | None,
    generation_target: str | None,
    has_visual_reference: bool,
) -> str:
    if node_type in {"video", "video_merge"} or generation_target == "video":
        return "i2v" if has_visual_reference else "t2v"
    if node_type in {"text", "script"}:
        return "text"
    return "i2i" if has_visual_reference else "t2i"


def has_visual_reference(
    *,
    asset_refs: list[str] | tuple[str, ...] | None,
    node_parameters: dict[str, Any] | None,
    context_subgraph: Any | None = None,
    node_id: str | None = None,
) -> bool:
    if asset_refs:
        return True
    params = node_parameters or {}
    for key in (
        "reference_image_count",
        "has_reference_image",
        "first_frame_image_asset_id",
        "last_frame_image_asset_id",
    ):
        if params.get(key):
            return True
    for key in ("connected_reference_nodes", "uploads", "uploaded_images", "image_asset_refs", "reference_images"):
        value = params.get(key)
        if isinstance(value, list) and value:
            return True
    graph = context_subgraph
    nodes = getattr(graph, "nodes", None)
    if graph and isinstance(nodes, list):
        target_id = str(getattr(graph, "target_node_id", "") or node_id or "")
        for node in nodes:
            if str(getattr(node, "id", "") or "") == target_id:
                continue
            if getattr(node, "image_asset_refs", None):
                return True
    return False


def deterministic_video_fallback_prompt(
    *,
    prompt_text: str,
    node_parameters: dict[str, Any] | None,
    slots: dict[str, Any] | None = None,
) -> str:
    params = node_parameters or {}
    slot_values = slots or {}
    clean_prompt = _compact(prompt_text)
    subject = _slot(slot_values, "subject") or video_reference_subject(params) or "首帧中的主体"
    scene = _slot(slot_values, "scene") or "延续首帧场景与空间关系"
    motion = str(params.get("motion") or "").strip() or _slot(slot_values, "motion") or clean_prompt
    duration = str(params.get("duration_sec") or params.get("duration") or "").strip()
    duration_text = f"时长约 {duration}，" if duration else ""
    return "\n".join(
        [
            f"意图：基于首帧生成视频，围绕“{clean_prompt}”设计连续运动，不改写为单帧图片编辑。",
            f"人物/主体：{subject}。保持首帧中的人物身份、脸部辨识度、服装、发型轮廓、体态比例和画风一致。",
            f"场景/美术：{scene}。延续首帧的空间、道具、色彩和光影气氛，只做视频运动需要的自然变化。",
            f"动作/情节：{motion}。动作从首帧自然开始，幅度克制、连贯，不突然换人、换装或换场景。",
            "镜头/构图：以首帧构图为起点，保持主体位置关系稳定，可做轻微推近、跟随或平移。",
            "灯光：保持首帧主要光源方向、曝光和色温，避免无来源强光和闪烁。",
            f"运动/时间推进：{duration_text}描述明确的时间推进、动作方向、速度和镜头关系，形成可执行的视频段落。",
            "连续性：首帧是强约束；保持身份、服装、体态、场景、镜头关系和资产签名一致。",
            "负面约束：不要静态图片编辑口吻、不要静止不动、不要身份漂移、换脸、换服装、肢体畸形、文字水印、突兀转场或背景跳变。",
        ]
    )


def video_enhancement_instruction(
    *,
    prompt_text: str,
    style: str | None,
    node_parameters: dict[str, Any] | None,
    mode: str,
) -> str:
    params = node_parameters or {}
    reference_hint = video_reference_subject(params)
    first_frame_line = (
        f"首帧/参考线索：{reference_hint}"
        if reference_hint
        else "首帧/参考线索：当前请求会携带首帧图片；必须把首帧作为主体、构图、服装和场景连续性的强约束。"
    )
    motion = str(params.get("motion") or "").strip()
    parts = [
        f"意图：基于首帧生成视频，围绕“{prompt_text}”组织连续运动，不写成图生图或单帧编辑。",
        "人物/主体：明确首帧中的主体；保持身份、脸部辨识度、服装、发型轮廓、体态比例和整体画风一致。",
        "场景/美术：延续首帧空间、道具、背景层次、色彩和氛围，只补足视频运动所需的环境连续性。",
        f"动作/情节：描述从首帧开始发生的动作和节奏；{('用户运动要求：' + motion) if motion else '若用户只说生成视频，则设计轻微、自然、克制的动作。'}",
        "镜头/构图：以首帧构图为起点，说明镜头推近、跟随、平移或保持稳定的方式，避免突然换景。",
        "灯光：保持首帧主要光源方向、曝光、明暗关系和色温，避免闪烁或无来源强光。",
        "运动/时间推进：写清楚时间推进、运动方向、速度、幅度和镜头关系；必须是视频段落，不是静态图。",
        "连续性：首帧是强约束；资产签名只转写成身份、服装、体态、场景和画风一致性约束。",
        "负面约束：不要图生图编辑口吻、不要单帧图像编辑、不要静止不动、不要身份漂移、换脸、换装、肢体畸形、文字水印、突兀转场或背景跳变。",
    ]
    return "\n".join(
        [
            f"原始视频节点提示词：{prompt_text}",
            first_frame_line,
            f"当前模式：{mode}；目标：video；风格：{style or 'cinematic'}。",
            "硬性要求：只输出可直接用于图生视频/首帧生视频的中文提示词；不要解释、不输出思考过程、不添加标题。",
            "禁止事项：不要写“本次只做图生图编辑”“单帧图像编辑”“不制造多阶段动作或剧情”；不要把上游节点标题或完整旧提示词当成人物名字。",
            "输出必须只有以下九行，标签不可改名：意图、人物/主体、场景/美术、动作/情节、镜头/构图、灯光、运动/时间推进、连续性、负面约束。",
            " ".join(parts),
        ]
    )


def video_strict_format_retry_instruction(
    *,
    prompt_text: str,
    style: str | None,
    mode: str,
    section_order: tuple[str, ...],
) -> str:
    labels = "、".join(section_order)
    return "\n".join(
        [
            "上一次输出没有按 AFS Studio 的视频提示词格式返回，已经被系统拒绝。",
            "现在必须重新输出。不要解释，不要标题，不要 Markdown，不要表格，不要英文教程。",
            f"原始视频节点提示词：{prompt_text}",
            f"当前模式：{mode}；目标：video；风格：{style or 'cinematic'}。",
            f"只允许输出以下九行，顺序和标签必须保持：{labels}。",
            "意图：写基于首帧生成视频的目标，不写图生图编辑。",
            "人物/主体：写首帧主体身份、外观、服装、体态和情绪连续性。",
            "场景/美术：写首帧场景延续与视频环境连续性。",
            "动作/情节：写从首帧开始发生的动作和节奏。",
            "镜头/构图：写视频镜头运动、景别和主体位置关系。",
            "灯光：写首帧光源延续、曝光和色温。",
            "运动/时间推进：写时间推进、动作方向、速度、幅度和镜头关系。",
            "连续性：写首帧、身份、服装、场景、画风和资产签名一致性。",
            "负面约束：写不要出现的视频错误，包括身份漂移、换装、突兀转场、背景跳变、水印和文字乱码。",
        ]
    )


def video_reference_subject(node_parameters: dict[str, Any] | None) -> str:
    params = node_parameters or {}
    terms: list[str] = []
    for item in params.get("uploaded_images") or []:
        if isinstance(item, dict):
            term = _filename_hint(item.get("filename") or item.get("label"))
            if term:
                terms.append(term)
    for item in params.get("connected_reference_nodes") or []:
        if not isinstance(item, dict):
            continue
        title = _compact(str(item.get("title") or ""), 40)
        if title and not title.startswith(("图片节点", "文本节点")):
            terms.append(title)
    for key in ("first_frame_image_asset_id", "last_frame_image_asset_id"):
        value = str(params.get(key) or "").strip()
        if value:
            terms.append("首帧参考图")
            break
    result: list[str] = []
    for term in terms:
        if term and term not in result:
            result.append(term)
    return "、".join(result[:4])


def _filename_hint(value: Any) -> str:
    text = str(value or "").replace("\\", "/").split("/")[-1].strip()
    if "." in text:
        text = ".".join(text.split(".")[:-1]) or text
    text = text.replace("_", " ").replace("-", " ").strip()
    text = re.sub(r"\bv\d+\b", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\s+", " ", text)
    if not text or text.lower() in {"reference", "image", "candidate", "upload"}:
        return ""
    return _compact(text, 60)


def _slot(slots: dict[str, Any], key: str) -> str:
    value = slots.get(key) if isinstance(slots, dict) else ""
    return _compact(str(value or ""))


def _compact(value: str, limit: int = 160) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())[:limit]


__all__ = (
    "VIDEO_MODES",
    "deterministic_video_fallback_prompt",
    "has_visual_reference",
    "prompt_optimization_mode",
    "video_enhancement_instruction",
    "video_reference_subject",
    "video_strict_format_retry_instruction",
)
