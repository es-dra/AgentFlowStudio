from __future__ import annotations

import re
from typing import Any

from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_store import reject_unsafe_text


SCRIPT_GENERATION_MODE = "idea_to_script"
SCRIPT_GENERATION_VALIDATOR_VERSION = "script_generation_body_validator.v0.1"
SCRIPT_SURFACE_VALIDATOR_VERSION = "script_surface_body_validator.v0.1"

_SCRIPT_CONTRACT = "formal_script_before_storyboard_breakdown"
_WRAPPER_MARKERS = (
    "请把下面的一句话扩写成正式短视频剧本正文",
    "输出要求",
    "原始想法",
    "硬性要求",
    "只输出",
    "不要输出",
    "script_expansion_contract",
    "formal_script_before_storyboard_breakdown",
    "storyboard_placeholder_outline",
    "request_body.prompt_text",
    "source_idea",
)
_INSTRUCTION_LEAKAGE_MARKERS = (
    "prompt optimizer",
    "remote llm",
    "provider calls remain off",
    "do not claim provider",
    "knowledgebase",
    "creative_agent",
    "selected_slots",
)
_TEMPLATE_FILLER_MARKERS = (
    "推进主体",
    "展示变化",
    "收束结果",
    "主角或核心物体",
    "核心物体",
    "环境细节服务",
    "保留下一步拆分分镜",
    "Primary character",
    "Primary scene",
    "single clear creative direction",
)
_OPTIMIZER_LABEL_RE = re.compile(
    r"^\s*(?:"
    r"意图|角色/主体|人物/主体|主体|场景/美术|动作/情节|镜头/构图|灯光|"
    r"运动/时间推进|连续性|负面约束|Intent|Subject/Character|Scene/Production Design|"
    r"Action/Beat|Camera/Framing|Lighting|Motion/Temporal Progression|Continuity|"
    r"Negative Constraints"
    r")\s*[：:]",
    flags=re.IGNORECASE,
)
_SHOT_MARKER_RE = re.compile(r"^\s*(?:分镜|镜头|场景|scene|shot)\s*\d+", flags=re.IGNORECASE)


def is_script_generation_request(request: PromptOptimizationRequest) -> bool:
    params = request.node_parameters or {}
    explicit_script_contract = (
        str(params.get("script_generation_mode") or "") == SCRIPT_GENERATION_MODE
        or str(params.get("script_expansion_contract") or "") == _SCRIPT_CONTRACT
    )
    script_surface = request.generation_target == "script" and request.node_type == "script"
    return explicit_script_contract and script_surface


def is_script_surface_request(request: PromptOptimizationRequest) -> bool:
    if is_script_generation_request(request):
        return False
    params = request.node_parameters or {}
    script_hint = any(
        str(params.get(key) or "").strip()
        for key in ("scriptInputMode", "sourceTextNodeId", "scriptSegmentIndex")
    )
    structured_hint = isinstance(params.get("structuredShot"), dict) or isinstance(params.get("storyboardBreakdown"), dict)
    return bool(
        structured_hint
        or script_hint
        or (request.node_type in {"text", "script"} and looks_like_script_text(request.prompt_text))
    )


def source_idea_from_request(request: PromptOptimizationRequest) -> str:
    params = request.node_parameters or {}
    explicit = _clean(str(params.get("source_idea") or ""))
    if explicit:
        return explicit[:600]
    match = re.search(r"(?:原始想法|source idea)\s*[：:]\s*(.+)$", request.prompt_text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return _clean(match.group(1))[:600]
    return _clean(request.prompt_text)[:600]


def script_body_from_candidate(candidate: str, request: PromptOptimizationRequest) -> dict[str, Any]:
    source_idea = source_idea_from_request(request)
    text = _clean_body(candidate)
    discard_reason = _invalid_script_body_reason(text)
    if discard_reason:
        script_body = deterministic_script_body(source_idea)
        status = "fallback_used"
        fallback_used = True
    else:
        script_body = text
        status = "accepted"
        fallback_used = False
    reject_unsafe_text(script_body)
    return {
        "status": status,
        "script_body_mode": "formal_short_video_script_body",
        "validator_version": SCRIPT_GENERATION_VALIDATOR_VERSION,
        "source_idea": source_idea,
        "script_body": script_body,
        "fallback_used": fallback_used,
        "discard_reason": discard_reason,
    }


def script_surface_body_from_candidate(candidate: str, request: PromptOptimizationRequest) -> dict[str, Any]:
    source = _clean_body(request.prompt_text)
    text = _clean_body(candidate)
    discard_reason = _invalid_script_surface_reason(text, request)
    if discard_reason:
        script_body = source
        status = "fallback_used"
        fallback_used = True
    else:
        script_body = text
        status = "accepted"
        fallback_used = False
    reject_unsafe_text(script_body)
    return {
        "status": status,
        "script_body_mode": "script_surface_optimization_body",
        "validator_version": SCRIPT_SURFACE_VALIDATOR_VERSION,
        "source_idea": source[:600],
        "script_body": script_body,
        "fallback_used": fallback_used,
        "discard_reason": discard_reason,
    }


def public_script_generation_body(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if not value:
        return None
    return {
        "status": value.get("status"),
        "script_body_mode": value.get("script_body_mode"),
        "validator_version": value.get("validator_version"),
        "source_idea": value.get("source_idea"),
        "fallback_used": bool(value.get("fallback_used")),
        "discard_reason": value.get("discard_reason"),
    }


def deterministic_script_body(source_idea: str) -> str:
    idea = _clean(source_idea) or "一个人经历一个安静但发生转折的夜晚"
    profile = _story_profile(idea)
    script = "\n".join(
        [
            f"片名：《{profile['title']}》",
            "",
            (
                f"{profile['protagonist']}出现在{profile['scene']}。这一刻看似只是{idea}，"
                f"但{profile['mood']}的气氛已经压在画面里：{profile['atmosphere']}。"
            ),
            "",
            (
                f"时间缓慢推进，{profile['name']}先是保持原来的状态，随后被一个细小异常打断。"
                f"{profile['action_progression']}，让观众意识到这不是静止的概念展示，而是一段正在发生的故事。"
            ),
            "",
            (
                f"转折来自{profile['turn_trigger']}。{profile['discovery']}，"
                f"{profile['name']}必须在继续停留和立刻行动之间做出反应。"
            ),
            "",
            (
                f"结尾停在{profile['ending_image']}。"
                f"{profile['ending_hook']}，为下一步分镜拆分留下清楚的人物、场景、动作和悬念。"
            ),
        ]
    )
    reject_unsafe_text(script)
    return script


def _invalid_script_body_reason(text: str) -> str:
    if not text:
        return "empty_output"
    if len(text) > 8000:
        return "script_body_too_long"
    if any(marker.lower() in text.lower() for marker in _WRAPPER_MARKERS):
        return "prompt_wrapper_echo"
    if any(marker.lower() in text.lower() for marker in _INSTRUCTION_LEAKAGE_MARKERS):
        return "instruction_leakage"
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    optimizer_label_count = sum(1 for line in lines if _OPTIMIZER_LABEL_RE.match(line))
    if optimizer_label_count >= 2:
        return "optimizer_label_output"
    if any(marker in text for marker in _TEMPLATE_FILLER_MARKERS):
        return "template_filler"
    shot_marker_count = sum(1 for line in lines if _SHOT_MARKER_RE.match(line))
    if shot_marker_count >= 3:
        return "storyboard_outline"
    if "片名" not in text and "《" not in text:
        return "missing_script_title"
    if len(_clean(text)) < 120:
        return "script_body_too_thin"
    return ""


def _invalid_script_surface_reason(text: str, request: PromptOptimizationRequest) -> str:
    if not text:
        return "empty_output"
    if len(text) > 12000:
        return "script_body_too_long"
    if any(marker.lower() in text.lower() for marker in _WRAPPER_MARKERS):
        return "prompt_wrapper_echo"
    if any(marker.lower() in text.lower() for marker in _INSTRUCTION_LEAKAGE_MARKERS):
        return "instruction_leakage"
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    optimizer_label_count = sum(1 for line in lines if _OPTIMIZER_LABEL_RE.match(line))
    if optimizer_label_count >= 2:
        return "optimizer_label_output"
    if any(marker in text for marker in _TEMPLATE_FILLER_MARKERS):
        return "template_filler"
    if looks_like_script_text(request.prompt_text) and not looks_like_script_text(text) and len(_clean(text)) < 120:
        return "script_shape_lost"
    return ""


def looks_like_script_text(value: str) -> bool:
    text = _clean_body(value)
    if not text:
        return False
    markers = (
        "片名",
        "剧本",
        "镜号",
        "分镜",
        "镜头",
        "画面描述",
        "景别",
        "光影氛围",
        "运镜",
        "对白",
        "旁白",
        "音效",
        "时长",
    )
    marker_count = sum(1 for marker in markers if marker in text)
    if marker_count >= 2:
        return True
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    field_count = sum(
        1
        for line in lines
        if re.match(r"^(?:镜号|时长|画面描述|景别|光影氛围|运镜|对白/旁白|对白|旁白|音效|资产)\s*[：:]", line)
    )
    if field_count >= 2:
        return True
    if "《" in text and ("主角" in text or "场景" in text or "镜头" in text):
        return True
    return False


def _story_profile(idea: str) -> dict[str, str]:
    lowered = idea.casefold()
    if "睡" in idea or "sleep" in lowered:
        return {
            "title": "沉睡的门铃",
            "name": "沈眠",
            "protagonist": "主角沈眠独自躺在清晨还没亮透的出租屋里",
            "scene": "一间窗帘半掩、只剩空调低声的房间",
            "mood": "安静、压抑又带一点悬疑",
            "atmosphere": "灰蓝色天光爬上床沿，床头旧闹钟停在六点十七分",
            "action_progression": "她在梦中翻身，手指碰到枕边一张被折起的车票，呼吸忽然变得急促",
            "turn_trigger": "门外三下很轻的敲门声",
            "discovery": "门缝下没有人影，只有一枚还带着雨水的钥匙被慢慢推了进来",
            "ending_image": "沈眠坐起身握住钥匙、望向门口的背影",
            "ending_hook": "门外传来一个熟悉却不该出现的声音，低声叫出她的名字",
        }
    if "机器人" in idea or "robot" in lowered:
        return {
            "title": "屋顶星光协议",
            "name": "遥星R-17",
            "protagonist": "未来机器人遥星R-17站在风声很低的屋顶边缘",
            "scene": "远离城市中心的乡村屋顶平台",
            "mood": "孤独、沉静又带着诗意",
            "atmosphere": "屋檐下的旧灯泡微微摇晃，星光落在金属外壳上",
            "action_progression": "它抬起头校准星图，却发现胸口的旧信号灯第一次亮起",
            "turn_trigger": "天空中一颗本不该移动的星点",
            "discovery": "星点传回的不是坐标，而是一段来自多年以前的人类童声",
            "ending_image": "遥星R-17把手伸向夜空、信号灯持续闪烁的剪影",
            "ending_hook": "那段童声问它是否还记得回家的路",
        }
    if "猫" in idea or "cat" in lowered:
        return {
            "title": "窗边来客",
            "name": "狸花猫团团",
            "protagonist": "狸花猫团团蹲在一扇半开的旧木窗前",
            "scene": "雨后潮湿的小房间",
            "mood": "温柔、警觉又带一点奇遇感",
            "atmosphere": "窗台上有水珠，远处街灯把地面照成浅金色",
            "action_progression": "它先安静观察，随后用爪子拨动窗边掉落的小铃铛",
            "turn_trigger": "铃铛里传出的细小回声",
            "discovery": "回声像是在回应它的动作，带它看向窗外一条发光的脚印",
            "ending_image": "团团跃上窗台、回头望向房间的瞬间",
            "ending_hook": "脚印延伸到雨夜深处，像在邀请它跟上",
        }
    return {
        "title": _title_seed(idea),
        "name": "林澈",
        "protagonist": "主角林澈站在一处被晨光切开的安静空间里",
        "scene": "兼具现实细节和故事压力的室内场景",
        "mood": "克制、微妙又暗含转折",
        "atmosphere": "桌面上的小物件、窗外的声音和人物的停顿共同压低节奏",
        "action_progression": "他先试图维持平静，随后被一个与原本状态不相符的细节吸引",
        "turn_trigger": "一件原本不该移动的物品突然改变位置",
        "discovery": "那个细节把普通瞬间变成需要选择的故事节点",
        "ending_image": "林澈停在光影交界处、回望身后的动作",
        "ending_hook": "他发现自己并不是这个场景里唯一清醒的人",
    }


def _title_seed(text: str) -> str:
    compacted = re.sub(r"[\s,.;:!?，。！？；、：]+", "", text)
    return (compacted or "未完成的信号")[:12]


def _clean_body(value: Any) -> str:
    return str(value or "").strip()


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


__all__ = (
    "SCRIPT_GENERATION_MODE",
    "deterministic_script_body",
    "is_script_generation_request",
    "is_script_surface_request",
    "looks_like_script_text",
    "public_script_generation_body",
    "script_body_from_candidate",
    "script_surface_body_from_candidate",
    "source_idea_from_request",
)
