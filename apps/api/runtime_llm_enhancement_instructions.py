from __future__ import annotations

from agentflow.algorithms.creative_intent_control import (
    video_enhancement_instruction as algorithm_video_enhancement_instruction,
    video_strict_format_retry_instruction as algorithm_video_strict_format_retry_instruction,
)
from apps.api.runtime_llm_enhancement_constants import SECTION_ORDER
from apps.api.runtime_llm_enhancement_gate import prompt_optimization_mode
from apps.api.runtime_llm_enhancement_safety import visual_reference_hint
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_reference_intent import (
    ORIGINALIZE_REFERENCE_MODE,
    originalize_reference_policy,
    reference_transform_mode_for_request,
)


def enhancement_instruction(request: PromptOptimizationRequest, assembly: dict[str, object]) -> str:
    if is_script_expansion_request(request):
        return script_expansion_instruction(request)
    if request.node_type in {"text", "script"}:
        return text_enhancement_instruction(request)
    mode = prompt_optimization_mode(request)
    if mode in {"i2v", "t2v"}:
        return video_enhancement_instruction(request, mode=mode)
    if mode == "t2i":
        return t2i_visual_enhancement_instruction(request)
    return visual_enhancement_instruction(request)


def is_script_expansion_request(request: PromptOptimizationRequest) -> bool:
    params = request.node_parameters or {}
    return (
        request.generation_target == "script"
        and params.get("script_expansion_contract") == "formal_script_before_storyboard_breakdown"
    )


def script_expansion_instruction(request: PromptOptimizationRequest) -> str:
    params = request.node_parameters or {}
    source = str(params.get("source_idea") or request.prompt_text).strip()
    return "\n".join(
        [
            "你正在为 AFS Studio 扩写短视频剧本正文。",
            f"原始想法：{source}",
            "硬性要求：只输出剧本正文，不解释、不输出思考过程、不输出九段画面提示词。",
            "格式要求：先输出一行片名，格式为“片名：《标题》”；然后输出 2 到 4 段连续叙事正文。",
            "内容要求：明确角色、场景、情绪、动作变化和结尾；所有细节必须服务原始想法。",
            "禁止输出：意图、角色/主体、场景/美术、动作/情节、镜头/构图、灯光、运动/时间推进、连续性、负面约束。",
            "禁止输出：分镜 01/02/03/04、推进主体、展示变化、收束结果、占位句、模板说明、request.json、prompt.md、沙盒或文件读取错误。",
            "如果原始想法很短，可以合理补足剧情，但不要把系统指令或输出要求写进正文。",
        ]
    )


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
        "角色/主体：补足主体身份、外观、姿态和情绪；若原提示未指定，只做合理补充，不添加多余主角。",
        "场景/美术：补足空间、时间、环境元素、质感和视觉风格，让画面有清晰层次。",
        f"动作/情节：将“{request.prompt_text}”整理成单帧可读的动作或情境，不扩写成复杂剧情。",
        "镜头/构图：补足景别、视角、主体位置和前中后景关系，保持构图稳定清晰。",
        "灯光：根据画面情绪补足光源方向、明暗关系和色温氛围。",
        "运动/时间推进：以单帧关键画面为主，只保留服务画面的短时间感。",
        "连续性：保持原始提示词的主题、主体和情绪，不漂移到无关题材。",
        "负面约束：不要水印、文字乱码、畸形肢体、无关角色、不合理背景元素。",
    ]
    return "\n".join(
        [
            f"原始提示词：{request.prompt_text}",
            "硬性要求：当前是文生图提示词扩写，没有参考图。只优化提示词，不解释、不输出思考过程；可以补足光影、构图、质感和画面细节，但不要写成图生图的保守编辑指令。",
            "输出必须只有以下九行，标签不可改名：意图、角色/主体、场景/美术、动作/情节、镜头/构图、灯光、运动/时间推进、连续性、负面约束。",
            " ".join(parts),
        ]
    )


def visual_enhancement_instruction(request: PromptOptimizationRequest) -> str:
    if reference_transform_mode_for_request(request) == ORIGINALIZE_REFERENCE_MODE:
        return originalize_visual_enhancement_instruction(request)
    reference_hint = visual_reference_hint(request)
    reference_line = f"参考图线索：{reference_hint}" if reference_hint else "参考图线索：当前请求携带参考图，但没有可公开的文件名或资产签名；必须先判断它是主体参考还是风格参考。"
    reference_role_line = (
        "参考图用途：先判断参考图角色。只有当原始提示词明确要求“这个人物/这只猫/这张图主体/上游节点的主体/基于参考图编辑/保持同一主体”时，"
        "参考图才是主体参考；如果原始提示词明确指定新主体或全新主体，参考图就是风格参考或视觉线索。"
        "不要把参考图主体替换用户指定主体。"
        "对于人类角色，“这个人物”必须理解为参考图中的同一个人物；对于动物角色，“这只猫/这只动物”必须理解为参考图中的同一只动物。"
        "主体参考只保留与用户目标不冲突的主体身份线索，不要把参考图背景强行写成必须保留的场景。"
    )
    parts = [
        f"意图：围绕“{request.prompt_text}”完成本次生成。",
        "角色/主体：以原始提示词明确指定的主体为最高优先级；主体参考时保留参考图中的同一主体。若主体是猫或动物，保留毛色、斑纹、眼睛、耳朵、尾巴和体型比例，不要添加人类头发、服装或拟人身份；若主体是人类角色，再保留角色身份、脸部辨识度和服装。",
        "场景/美术：保持原提示中的场景信息；只有用户明确要求延续场景时才保留参考图场景，未指定时不要新增具体地点，不要继承无关图表、界面文字或旧背景。",
        f"动作/情节：只执行“{request.prompt_text}”这一项变化，不扩写新剧情。",
        "镜头/构图：关键帧清晰呈现主体变化，构图稳定，主体可辨识；参考图不是局部贴图素材，必须重绘为统一、连贯的完整主体。",
        "灯光：保持自然可读的光线，不改变参考图的主要光感。",
        "运动/时间推进：单帧关键画面，不制造多阶段动作。",
        "连续性：主体参考时保持参考图主体身份、可识别特征、体型比例和整体风格；风格参考时保持用户指定主体，只迁移画面质感和可读风格线索。",
        "负面约束：不要水印、文字乱码、主体畸形、身份漂移、服装漂移、背景大幅变化；动物主体不要人类头发、服装或拟人身体，除非用户明确要求。",
    ]
    return "\n".join(
        [
            f"原始提示词：{request.prompt_text}",
            reference_line,
            reference_role_line,
            "优先级：用户当前明确目标最高；参考图主体只提供身份和可识别特征；旧资产签名和默认锁定项不得覆盖用户当前明确要求。",
            "硬性要求：只优化提示词，不解释、不输出思考过程、不添加标题；保留用户明确要求，尤其是主体参考的图生图编辑只改变用户明确要求改变的部分。",
            "质量要求：输出不能照抄模板，必须吸收参考图线索；如果线索中有“校服周彤”这类人类角色/服装信息，角色或连续性段必须明确保留该身份和服装；如果线索是猫或动物，只保留动物主体特征，不要套用人类角色的发型、服装或身份模板。",
            "输出必须只有以下九行，标签不可改名：意图、角色/主体、场景/美术、动作/情节、镜头/构图、灯光、运动/时间推进、连续性、负面约束。",
            " ".join(parts),
        ]
    )


def originalize_visual_enhancement_instruction(request: PromptOptimizationRequest) -> str:
    reference_hint = visual_reference_hint(request)
    reference_line = f"参考图线索：{reference_hint}" if reference_hint else "参考图线索：当前请求携带参考图，但参考图只作为灵感来源。"
    parts = [
        f"意图：围绕“{request.prompt_text}”把参考图转化为新的原创资产或关键帧方向，目标是降低可识别 IP 相似度，而不是复刻参考图。",
        "角色/主体：只抽取参考图的高层类别、功能、气质和宽泛造型语言；重新设计身份、脸部/头部细节、轮廓、服饰/材质系统和标志性辨识点。",
        "场景/美术：可借鉴宽泛时代感、材质情绪和色彩关系，但不要复制原图独特场景构图、标志物、文字、logo、服装图案或 franchise 视觉符号。",
        f"动作/情节：执行用户当前目标“{request.prompt_text}”，动作和情境服务新设计，不延续参考图的经典姿势、名场面或固定剧情关系。",
        "镜头/构图：构图必须重新组织，避免贴近参考图的角度、姿势、画面布局、四视图排列或标志性剪影。",
        "灯光：保留可用的氛围方向和可读性，但重新设计光源位置、明暗层次和材质表现，避免形成原图复刻感。",
        "运动/时间推进：若是单帧，只表达当前新资产的可读状态；若后续用于视频，保留可动画的原创结构和动作余量。",
        "连续性：新资产内部要稳定一致；参考图只作为灵感证据，不作为身份、服装、比例、构图或未修改细节的锁定项。",
        "负面约束：不要复制已知角色、商标、logo、标志性服装/武器/构图/姿势，不要保留可识别 IP 组合，不要水印、文字乱码、畸形肢体或身份漂移。",
    ]
    return "\n".join(
        [
            f"原始提示词：{request.prompt_text}",
            reference_line,
            originalize_reference_policy(),
            "当前场景：图生图参考用于原创重生 / 降 IP 风险。模板仍用于稳定质量，但每段必须服务“重新设计”，不能写成保守局部修图。",
            "硬性要求：只优化提示词，不解释、不输出思考过程、不添加标题；参考图只能提供抽象灵感、材质情绪、功能方向和宽泛风格，不能作为复刻依据。",
            "输出必须只有以下九行，标签不可改名：意图、角色/主体、场景/美术、动作/情节、镜头/构图、灯光、运动/时间推进、连续性、负面约束。",
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
    labels = "、".join(SECTION_ORDER)
    return "\n".join(
        [
            "你正在为 AFS Studio 重新整理提示词优化结果。",
            "上一次输出没有满足格式要求。不要解释，不要输出 Markdown 标题，不要输出 negative prompt 分栏。",
            f"原始提示词：{request.prompt_text}",
            f"当前模式：{mode}；目标：{request.generation_target}；风格：{request.style or 'cinematic'}。",
            f"只输出九行，且必须按这个顺序使用标签：{labels}。",
            "每一行格式为“标签：内容”。",
            "角色/主体：明确主体身份、外观、姿态和需要保持的身份特征。",
            "场景/美术：明确空间、时间、环境元素、材质和视觉风格。",
            "动作/情节：只描述一个可生成的动作或情境。",
            "镜头/构图：明确景别、视角、主体位置和前中后景。",
            "灯光：明确光源方向、明暗关系和色温氛围。",
            "运动/时间推进：说明单帧或短时间感，不扩写成长剧情。",
            "连续性：保留原始提示和参考图中的身份、服装、场景和风格。",
            "负面约束：列出水印、乱码、畸形肢体、身份漂移等需要避免的内容。",
        ]
    )


def text_enhancement_instruction(request: PromptOptimizationRequest) -> str:
    parts = [
        f"意图：围绕“{request.prompt_text}”形成清晰、可继续扩写的创作方向。",
        f"角色/主体：以“{request.prompt_text}”中的主体为核心，不新增无关主角。",
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
            "输出必须只有以下九行，标签不可改名：意图、角色/主体、场景/美术、动作/情节、镜头/构图、灯光、运动/时间推进、连续性、负面约束。",
            " ".join(parts),
        ]
    )


__all__ = ("enhancement_instruction", "is_script_expansion_request", "strict_format_retry_instruction")
