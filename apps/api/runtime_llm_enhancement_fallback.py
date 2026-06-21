from __future__ import annotations

import re
from typing import Any

from agentflow.algorithms.creative_intent_control import deterministic_video_fallback_prompt as algorithm_video_fallback_prompt
from apps.api.runtime_llm_enhancement_constants import BANNED_GENERIC_PHRASES
from apps.api.runtime_llm_enhancement_gate import prompt_optimization_mode
from apps.api.runtime_llm_enhancement_safety import (
    compact,
    contains_cjk,
    reference_role,
    reference_hint_terms,
    slot,
    visual_reference_hint,
)
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_store import reject_unsafe_text

ANIMAL_TERMS = (
    "狸花猫",
    "黑猫",
    "白猫",
    "橘猫",
    "猫",
    "小狗",
    "狗",
    "犬",
    "宠物",
    "动物",
    "tabby",
    "cat",
    "kitten",
    "feline",
    "dog",
    "puppy",
    "animal",
    "pet",
)

HUMAN_REFERENCE_TERMS = (
    "人物",
    "人像",
    "真人",
    "人类",
    "女孩",
    "男孩",
    "女人",
    "男人",
    "女性",
    "男性",
    "person",
    "human",
    "girl",
    "boy",
    "woman",
    "man",
)


def deterministic_chinese_fallback_prompt(
    request: PromptOptimizationRequest,
    assembly: dict[str, Any],
) -> str:
    mode = prompt_optimization_mode(request)
    if mode == "i2i":
        return deterministic_i2i_fallback_prompt(request)
    if mode in {"i2v", "t2v"}:
        return deterministic_video_fallback_prompt(request, assembly)
    slots = assembly.get("selected_slots") if isinstance(assembly, dict) else {}
    params = request.node_parameters or {}
    subject = slot(slots, "subject") or compact(request.prompt_text)
    scene = slot(slots, "scene") or compact(request.prompt_text)
    action = slot(slots, "action") or slot(slots, "emotion") or "保留当前提示词中的核心动作和情绪转折。"
    lighting = slot(slots, "lighting") or "灯光服务叙事情绪，避免无来源强光和过度风格化。"
    style = request.style or slot(slots, "style") or "cinematic"
    aspect = str(params.get("aspect_ratio") or params.get("spec") or "").strip()
    camera = str(params.get("camera") or "").strip()
    framing_bits = [bit for bit in (camera, f"画幅/规格：{aspect}" if aspect else "") if bit]
    framing = "；".join(framing_bits) or "明确主体位置、景别和背景信息层次。"
    prompt = "\n".join(
        [
            f"意图：围绕“{compact(request.prompt_text)}”生成本轮节点可直接使用的创作提示词，先保证意图清晰和可控，再强化画面表现。",
            f"角色/主体：{subject}。保持身份、服装、姿态和情绪连续，不新增原始提示词没有的角色数量或身份。",
            f"场景/美术：{scene}。空间、道具和环境细节服务当前画面，不让背景抢走主体。",
            f"动作/情节：{action}",
            f"镜头/构图：{framing}",
            f"灯光：{lighting}",
            f"运动/时间推进：当前目标是 {request.generation_target}；关键帧优先保持单帧可读，视频节点再强调运动方向和节奏。",
            f"连续性：保留本轮提示词中的具体细节，并与项目角色、场景和风格资产保持一致；用户偏好只作为低权重风格倾向。当前风格：{style}。",
            "负面约束：不要水印、文字乱码、过度磨皮、五官或手部畸形、身份漂移、镜头语言互相冲突。",
        ]
    )
    reject_unsafe_text(prompt)
    return prompt


def deterministic_i2i_fallback_prompt(request: PromptOptimizationRequest) -> str:
    prompt_text = compact(request.prompt_text)
    reference_hint = visual_reference_hint(request)
    if reference_role(request) == "style":
        prompt = "\n".join(
            [
                f"意图：围绕“{prompt_text}”生成本轮节点可直接使用的单帧画面；参考图只作为风格、质感或画面可读性的辅助线索，不替换用户指定的新主体。",
                f"角色/主体：以原始提示词为最高优先级，清晰呈现“{prompt_text}”中的主体；如果参考图主体与用户指定主体不一致，不继承参考图主体身份。",
                f"场景/美术：未指定具体地点时保持干净自然的画面背景；可参考“{reference_hint or '上传参考图'}”的整体风格、质感、色调和可读性，但不要复制其主体或剧情。",
                f"动作/情节：只执行原始提示词中的生成目标，不新增额外角色、身份、服装或复杂剧情。",
                "镜头/构图：主体位于画面核心位置，完整可辨识，关键特征清晰呈现；构图稳定，不让背景元素抢走主体。",
                "灯光：自然柔和、主体轮廓和关键特征清楚，不制造无来源强光或过度氛围化遮挡。",
                "运动/时间推进：单帧关键画面，不制造多阶段动作或时间变化。",
                "连续性：参考图仅提供视觉线索；主体、动作和生成目标以用户原始提示词为准，避免身份漂移和主体错配。",
                "负面约束：不要水印、文字乱码、五官畸形、身体比例异常、毛色错乱、身份漂移、服装漂移、背景大幅变化。",
            ]
        )
        reject_unsafe_text(prompt)
        return prompt
    if _is_animal_reference_request(prompt_text, reference_hint):
        prompt = _animal_i2i_fallback_prompt(prompt_text, reference_hint)
        reject_unsafe_text(prompt)
        return prompt
    reference_subject = reference_hint or "参考图中的同一角色"
    wardrobe_guard = "保持参考图中的服装、体型比例、姿态、背景和整体风格"
    if "校服" in reference_hint:
        wardrobe_guard = "保持校服款式、蓝白运动校服配色、体型比例、姿态、背景和整体风格"
    hair_guard = "只将头发长度改为短发；除非用户明确要求，不改变发色、脸型、五官、年龄感和角色身份"
    if "短发" in prompt_text and not any(color in prompt_text for color in ("金发", "棕发", "红发", "白发", "银发")):
        hair_guard = "只将头发长度改为短发，保持原参考图发色和发质方向；不要染浅、不要变成金发或棕发"
    prompt = "\n".join(
        [
            f"意图：对{reference_subject}执行“{prompt_text}”，本次只做这一项图生图编辑。",
            f"角色/主体：{reference_subject}；保持参考图脸部辨识度、五官比例、眼神、年龄感和角色身份；{hair_guard}。",
            f"场景/美术：保持参考图原有场景、道具、背景层次和画面氛围；{wardrobe_guard}。",
            f"动作/情节：角色保持参考图原有静态姿态和身体朝向，只呈现“{prompt_text}”带来的外观变化。",
            "镜头/构图：保持参考图主体大小、三视图或半身/全身布局、主体位置和构图关系稳定，不重新设计画面。",
            "灯光：保持参考图主要光源方向、明暗关系和曝光，不新增无来源强光。",
            "运动/时间推进：单帧图像编辑，不制造多阶段动作或剧情。",
            "连续性：保持身份、脸部、服装、体型、姿态、背景和画风连续；只改变用户明确点名的头发长度。",
            "负面约束：不要身份漂移、不要换脸、不要换服装、不要改变校服配色、不要染发变浅、不要新增角色、不要水印、不要文字乱码、不要五官畸形。",
        ]
    )
    reject_unsafe_text(prompt)
    return prompt


def _animal_i2i_fallback_prompt(prompt_text: str, reference_hint: str) -> str:
    subject = _animal_subject_name(f"{prompt_text} {reference_hint}")
    explicit_stylization = _explicit_animal_stylization(prompt_text)
    scene_line = "按用户当前要求组织场景；如果用户指定房间、舞蹈等新情境，以当前要求为准，不强行保留参考图的旧背景。"
    if "房间" not in prompt_text and "室内" not in prompt_text:
        scene_line = "场景按用户当前要求组织；未指定时使用干净自然、不会抢主体的背景，不强行复制参考图旧背景。"
    form_guard = (
        "按用户明确要求处理拟人化、服装、饰品或卡通化；即使风格变化，也要保持参考图中同一只动物的可识别特征。"
        if explicit_stylization
        else "默认保持自然动物形态；不要添加人类头发、服装或拟人身份，除非用户明确要求。"
    )
    return "\n".join(
        [
            f"意图：参考图中的{subject}只作为同一主体参考，执行“{prompt_text}”，生成单帧关键画面。",
            f"角色/主体：主体是{subject}；保持参考图中同一只动物的毛色、斑纹、脸部花纹、眼睛、耳朵、尾巴和体型比例；{form_guard}",
            f"场景/美术：{scene_line}只保留与{subject}身份相关的视觉线索，不继承无关图表、科技界面、文字或旧失败风格。",
            f"动作/情节：只呈现“{prompt_text}”这一项动作或状态；动物姿态自然完整，不新增额外角色或剧情。",
            "镜头/构图：主体完整可辨识，位于画面核心位置；参考图不是局部贴图素材，必须重绘为统一、连贯的完整主体。",
            "灯光：自然柔和、轮廓和关键特征清楚，不新增无来源强光或遮挡主体的氛围。",
            "运动/时间推进：单帧关键画面，只表现当前瞬间，不制造多阶段动作。",
            f"连续性：保持同一只{subject}的动物身份、毛色纹理、脸部辨识特征和体型比例；允许按用户要求改变场景和动作。",
            "负面约束：不要脸部裁剪贴图、不要水印、不要文字乱码、不要图表界面残留、不要身体畸形；未明确要求时不要人类身体、人类头发、人类服装或拟人身份。",
        ]
    )


def _is_animal_reference_request(prompt_text: str, reference_hint: str) -> bool:
    combined = f"{prompt_text} {reference_hint}".casefold()
    has_animal = any(term.casefold() in combined for term in ANIMAL_TERMS)
    if not has_animal:
        return False
    prompt_only = prompt_text.casefold()
    explicit_human_edit = any(term.casefold() in prompt_only for term in HUMAN_REFERENCE_TERMS)
    return not explicit_human_edit


def _animal_subject_name(text: str) -> str:
    lowered = text.casefold()
    if "黑色" in text and "狸花猫" in text:
        return "黑色狸花猫"
    if "狸花猫" in text or "tabby" in lowered:
        return "狸花猫"
    if "黑" in text and ("猫" in text or "cat" in lowered):
        return "黑猫"
    if "猫" in text or "cat" in lowered or "kitten" in lowered or "feline" in lowered:
        return "猫"
    if "狗" in text or "犬" in text or "dog" in lowered or "puppy" in lowered:
        return "狗"
    return "动物主体"


def _explicit_animal_stylization(text: str) -> bool:
    terms = (
        "拟人",
        "人形",
        "穿衣",
        "衣服",
        "服装",
        "外套",
        "衣",
        "饰品",
        "帽子",
        "卡通",
        "动画",
        "anthropomorphic",
        "humanoid",
        "clothes",
        "clothing", "wear", "wearing", "coat", "jacket",
        "outfit",
        "costume",
        "cartoon",
    )
    lowered = text.casefold()
    return any(term.casefold() in lowered for term in terms)


def deterministic_video_fallback_prompt(request: PromptOptimizationRequest, assembly: dict[str, Any]) -> str:
    slots = assembly.get("selected_slots") if isinstance(assembly, dict) else {}
    prompt = algorithm_video_fallback_prompt(
        prompt_text=request.prompt_text,
        node_parameters=request.node_parameters or {},
        slots=slots,
    )
    reject_unsafe_text(prompt)
    return prompt


def salvage_prompt_from_llm_article(value: str, request: PromptOptimizationRequest) -> str:
    candidate = extract_article_prompt_candidate(value)
    if not candidate:
        raise ValueError("enhancement missing required sections")
    negative = extract_article_negative_prompt(value)
    prompt = "\n".join(
        [
            f"意图：围绕“{compact(request.prompt_text, 160)}”生成可直接用于本节点的画面提示词。",
            f"角色/主体：{compact(candidate, 260)}",
            f"场景/美术：{compact(candidate, 260)}",
            f"动作/情节：{compact(request.prompt_text, 180)}",
            f"镜头/构图：{compact(candidate, 220)}",
            f"灯光：{compact(candidate, 220)}",
            "运动/时间推进：以当前节点目标为准，关键帧保持单帧可读；视频节点再强调短时间动作方向。",
            "连续性：保持上文主体、场景、服装、身份和项目风格一致，不漂移到无关题材。",
            f"负面约束：{negative or '不要水印、文字乱码、畸形肢体、身份漂移、无关角色或不合理背景元素。'}",
        ]
    )
    reject_unsafe_text(prompt)
    return prompt


def extract_article_prompt_candidate(value: str) -> str:
    lines = str(value or "").splitlines()
    candidates: list[tuple[int, str]] = []
    prefer_chinese = False
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if "中文" in line and "Prompt" in line:
            prefer_chinese = True
            continue
        cleaned = line.lstrip(">").strip().strip("*` ")
        if len(cleaned) < 40:
            continue
        lowered = cleaned.lower()
        if any(phrase in lowered for phrase in BANNED_GENERIC_PHRASES):
            continue
        if "negative prompt" in lowered or lowered.startswith(("low quality", "使用技巧", "要素 |")):
            continue
        if "|" in cleaned and cleaned.count("|") >= 2:
            continue
        score = len(cleaned)
        if prefer_chinese or contains_cjk(cleaned):
            score += 500
        if "prompt" in lowered:
            score -= 80
        candidates.append((score, cleaned))
    if not candidates:
        return ""
    return max(candidates, key=lambda item: item[0])[1]


def extract_article_negative_prompt(value: str) -> str:
    lowered = str(value or "").lower()
    if "negative prompt" not in lowered and "负向提示" not in str(value) and "负面" not in str(value):
        return ""
    fenced = re.findall(r"```(?:[a-zA-Z0-9_-]+)?\s*(.*?)```", str(value), flags=re.DOTALL)
    for block in fenced:
        text = " ".join(block.split())
        if len(text) >= 20:
            return compact(text, 220)
    return ""


__all__ = ("deterministic_chinese_fallback_prompt", "deterministic_i2i_fallback_prompt", "deterministic_video_fallback_prompt", "salvage_prompt_from_llm_article")
