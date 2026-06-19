from __future__ import annotations

from agentflow.algorithms.creative_intent_control import (
    video_enhancement_instruction as algorithm_video_enhancement_instruction,
    video_strict_format_retry_instruction as algorithm_video_strict_format_retry_instruction,
)
from apps.api.runtime_llm_enhancement_constants import SECTION_ORDER
from apps.api.runtime_llm_enhancement_gate import prompt_optimization_mode
from apps.api.runtime_llm_enhancement_safety import visual_reference_hint
from apps.api.runtime_models import PromptOptimizationRequest


def enhancement_instruction(request: PromptOptimizationRequest, assembly: dict[str, object]) -> str:
    if request.node_type in {"text", "script"}:
        return text_enhancement_instruction(request)
    mode = prompt_optimization_mode(request)
    if mode in {"i2v", "t2v"}:
        return video_enhancement_instruction(request, mode=mode)
    if mode == "t2i":
        return t2i_visual_enhancement_instruction(request)
    return visual_enhancement_instruction(request)


def video_enhancement_instruction(request: PromptOptimizationRequest, *, mode: str) -> str:
    return algorithm_video_enhancement_instruction(
        prompt_text=request.prompt_text,
        style=request.style,
        node_parameters=request.node_parameters or {},
        mode=mode,
    )


def t2i_visual_enhancement_instruction(request: PromptOptimizationRequest) -> str:
    parts = [
        f"意图：围绕“{request.prompt_text}”扩写成可直接生图的完整画面提示词。",
        "人物/主体：补足主体身份、外观、姿态和情绪；若原提示未指定，只做合理补充，不添加多余主角。",
        "场景/美术：补足空间、时间、环境元素、质感和视觉风格，让画面有清晰层次。",
        f"动作/情节：将“{request.prompt_text}”整理成单帧可读的动作或情境，不扩写成复杂剧情。",
        "镜头/构图：补足景别、视角、主体位置和前中后景关系，保持构图稳定清晰。",
        "灯光：根据画面情绪补足光源方向、明暗关系和色温氛围。",
        "运动/时间推进：以单帧关键画面为主，只保留服务画面的短时间感。",
        "连续性：保持原始提示词的主题、主体和情绪，不漂移到无关题材。",
        "负面约束：不要水印、文字乱码、畸形肢体、无关人物、不合理背景元素。",
    ]
    return "\n".join(
        [
            f"原始提示词：{request.prompt_text}",
            "硬性要求：当前是文生图提示词扩写，没有参考图。只优化提示词，不解释、不输出思考过程；可以补足光影、构图、质感和画面细节，但不要写成图生图的保守编辑指令。",
            "输出必须只有以下九行，标签不可改名：意图、人物/主体、场景/美术、动作/情节、镜头/构图、灯光、运动/时间推进、连续性、负面约束。",
            " ".join(parts),
        ]
    )


def visual_enhancement_instruction(request: PromptOptimizationRequest) -> str:
    reference_hint = visual_reference_hint(request)
    reference_line = f"参考图线索：{reference_hint}" if reference_hint else "参考图线索：当前请求携带参考图，但没有可公开的文件名或资产签名；仍必须把“这个人物”理解为参考图主体。"
    parts = [
        f"意图：围绕“{request.prompt_text}”完成本次生成。",
        "人物/主体：保留原始提示词中的主体；若写到“这个人物”，必须理解为参考图中的同一个人物。若参考图线索包含角色名、服装或场景名，必须写入本段。",
        "场景/美术：保持参考图或原提示中的场景信息；未指定时不要新增具体地点。",
        f"动作/情节：只执行“{request.prompt_text}”这一项变化，不扩写新剧情。",
        "镜头/构图：关键帧清晰呈现主体变化，构图稳定，主体可辨识。",
        "灯光：保持自然可读的光线，不改变参考图的主要光感。",
        "运动/时间推进：单帧关键画面，不制造多阶段动作。",
        "连续性：保持参考图人物身份、脸部辨识度、服装、体型比例和整体风格；只改变用户明确要求改变的部分。",
        "负面约束：不要水印、文字乱码、五官畸形、身份漂移、服装漂移、背景大幅变化。",
    ]
    return "\n".join(
        [
            f"原始提示词：{request.prompt_text}",
            reference_line,
            "硬性要求：只优化提示词，不解释、不输出思考过程、不添加标题；保留用户明确要求，尤其是图生图时只改用户点名的部分。",
            "质量要求：输出不能照抄模板，必须吸收参考图线索；如果线索中有“校服周彤”这类角色/服装信息，人物或连续性段必须明确保留该身份和服装。",
            "输出必须只有以下九行，标签不可改名：意图、人物/主体、场景/美术、动作/情节、镜头/构图、灯光、运动/时间推进、连续性、负面约束。",
            " ".join(parts),
        ]
    )


def strict_format_retry_instruction(request: PromptOptimizationRequest) -> str:
    mode = prompt_optimization_mode(request)
    if mode in {"i2v", "t2v"}:
        return algorithm_video_strict_format_retry_instruction(
            prompt_text=request.prompt_text,
            style=request.style,
            mode=mode,
            section_order=SECTION_ORDER,
        )
    labels = "?".join(SECTION_ORDER)
    return "\n".join(
        [
            "???????? AFS Studio ???????????????????",
            "????????????????????? Markdown??????????????? negative prompt ????",
            f"??????{request.prompt_text}",
            f"?????{mode}????{request.generation_target}????{request.style or 'cinematic'}?",
            f"????????????????????{labels}?",
            "???????????????????",
            "??/?????????????????????????????",
            "??/???????????????????????",
            "??/???????????????????????",
            "??/??????????????????????",
            "???????????????????",
            "??/??????????????????????",
            "??????????????????????????",
            "????????????????",
        ]
    )


def text_enhancement_instruction(request: PromptOptimizationRequest) -> str:
    parts = [
        f"意图：围绕“{request.prompt_text}”形成清晰、可继续扩写的创作方向。",
        f"人物/主体：以“{request.prompt_text}”中的主体为核心，不新增无关主角。",
        "场景/美术：保留原始提示词中的场景信息；未指定时只补充服务主题的环境氛围。",
        f"动作/情节：围绕“{request.prompt_text}”展开一个单一、明确的情境，不扩写成完整长故事。",
        "镜头/构图：用画面化语言说明主体位置、视角和信息层次。",
        "灯光：根据情绪选择自然、可读的光线描述。",
        "运动/时间推进：保持节奏克制，说明当前瞬间或短段落的时间感。",
        "连续性：保留原始提示词的主题、主体和情绪，不漂移到无关题材。",
        "负面约束：不要模板化空话、不要新增无关角色、不要过度解释、不要水印或乱码。",
    ]
    return "\n".join(
        [
            f"原始提示词：{request.prompt_text}",
            "硬性要求：只优化提示词，不解释、不输出思考过程、不添加标题；保持主题清楚、可生成、可继续扩写。",
            "输出必须只有以下九行，标签不可改名：意图、人物/主体、场景/美术、动作/情节、镜头/构图、灯光、运动/时间推进、连续性、负面约束。",
            " ".join(parts),
        ]
    )


__all__ = ("enhancement_instruction", "strict_format_retry_instruction")
