from __future__ import annotations

REMOTE_TRUE_VALUES = {"1", "true", "yes", "on"}
PROMPT_OPTIMIZER_PROVIDER = "prompt_optimizer"
PROMPT_OPTIMIZER_MODEL_IDS = {
    "prompt-optimizer",
    "prompt_optimizer",
    "provider-configured",
    "provider_configured",
    "server-configured",
    "server_configured",
}
REQUIRED_SECTION_LABELS = (
    "意图",
    "角色/主体",
    "场景/美术",
    "镜头/构图",
    "灯光",
    "负面约束",
)
SECTION_ORDER = (
    "意图",
    "角色/主体",
    "场景/美术",
    "动作/情节",
    "镜头/构图",
    "灯光",
    "运动/时间推进",
    "连续性",
    "负面约束",
)
SECTION_LABEL_ALIASES = {
    "意图": ("意图", "目标", "创作意图"),
    "角色/主体": ("角色/主体", "人物/主体", "人物", "主体", "角色", "人物设定", "角色设定", "主体设定"),
    "场景/美术": ("场景/美术", "场景", "美术", "环境", "空间", "场景设定"),
    "动作/情节": ("动作/情节", "动作", "情节", "剧情", "行为"),
    "镜头/构图": ("镜头/构图", "镜头", "构图", "画面", "机位"),
    "灯光": ("灯光", "光线", "光影", "照明"),
    "运动/时间推进": ("运动/时间推进", "运动", "时间推进", "动态", "节奏"),
    "连续性": ("连续性", "连贯性", "保持项", "一致性"),
    "负面约束": ("负面约束", "负面", "负面提示", "禁止项", "反向提示词"),
}
BANNED_GENERIC_PHRASES = (
    "primary character",
    "primary scene",
    "stable identity",
    "user original prompt unclear",
    "用户原始提示词含义仍不明确",
    "主体角色",
    "主要场景",
)
TOOL_FAILURE_MARKERS = (
    "i couldn't read the files",
    "i could not read the files",
    "local command execution failed",
    "bwrap:",
    "failed rtm_newaddr",
    "operation not permitted",
    "no such file or directory",
    "permission denied",
)


__all__ = (
    "BANNED_GENERIC_PHRASES",
    "PROMPT_OPTIMIZER_MODEL_IDS",
    "PROMPT_OPTIMIZER_PROVIDER",
    "REMOTE_TRUE_VALUES",
    "REQUIRED_SECTION_LABELS",
    "SECTION_LABEL_ALIASES",
    "SECTION_ORDER",
    "TOOL_FAILURE_MARKERS",
)
