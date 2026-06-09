from __future__ import annotations

from typing import Any

from apps.api.runtime_workbench_readiness import ACTION_LABELS


NON_CLAIMS = ["not human acceptance", "not business validation", "not durable memory"]

ACTION_UI_MAP = {
    "add_reference": {
        "ui_action": "register-source-asset",
        "view": "Assets",
        "summary": "先添加安全素材摘要，再生成制作画布。",
        "requires_input": ["source_asset_id", "source_asset_label", "source_asset_summary"],
    },
    "draft_canvas": {
        "ui_action": "draft-canvas",
        "view": "Create",
        "summary": "基于当前安全素材生成第一版可审片画布。",
        "requires_input": [],
    },
    "start_first_generation_check": {
        "ui_action": "run-asset-test",
        "view": "Create",
        "summary": "真实模型试跑前先运行确定性检查。",
        "requires_input": [],
    },
    "record_review_note": {
        "ui_action": "record-review-decision",
        "view": "Review",
        "summary": "记录绑定候选结果的审片决定，用于下一轮。",
        "requires_input": ["selected_review_candidate", "review_decision", "review_decision_note"],
    },
    "start_next_round": {
        "ui_action": "run-two-round",
        "view": "Review",
        "summary": "在第二轮复用已接受的上下文和审片证据。",
        "requires_input": [],
    },
    "run_provider_preflight": {
        "ui_action": "run-provider-preflight",
        "view": "Jobs",
        "summary": "检查 Provider 准备状态，但不启动真实模型运行。",
        "requires_input": [],
    },
    "resolve_provider_preflight": {
        "ui_action": "",
        "view": "Jobs",
        "summary": "Provider 能力闸门在显式授权前保持阻塞。",
        "requires_input": [],
        "blocked_reason": "Provider 能力闸门仍处于阻塞状态。",
    },
}

COMMAND_ORDER = [
    "add_reference",
    "draft_canvas",
    "start_first_generation_check",
    "record_review_note",
    "start_next_round",
    "run_provider_preflight",
]


def build_command_hub(
    project_readiness: dict[str, Any],
    production_board: dict[str, Any],
) -> dict[str, Any]:
    current_action = str(project_readiness.get("current_action") or "add_reference")
    status = str(production_board.get("status") or project_readiness.get("status") or "not_started")
    commands = [_command(action, current_action=current_action) for action in COMMAND_ORDER]
    primary = _command(current_action, current_action=current_action)
    return {
        "status": status,
        "title": "操作指令",
        "summary": _summary(primary),
        "primary_command": primary,
        "commands": commands,
        "non_claims": NON_CLAIMS,
    }


def _command(backend_action: str, *, current_action: str) -> dict[str, Any]:
    config = ACTION_UI_MAP.get(backend_action, {})
    ui_action = str(config.get("ui_action") or "")
    blocked_reason = str(config.get("blocked_reason") or "")
    enabled = bool(ui_action) and backend_action == current_action and not blocked_reason
    return {
        "command_id": f"command:{backend_action}",
        "label": ACTION_LABELS.get(backend_action, "继续"),
        "backend_action": backend_action,
        "ui_action": ui_action,
        "view": str(config.get("view") or "Create"),
        "summary": str(config.get("summary") or "继续推进制作流程。"),
        "enabled": enabled,
        "blocked_reason": blocked_reason,
        "requires_input": list(config.get("requires_input") or []),
    }


def _summary(primary: dict[str, Any]) -> str:
    if primary.get("blocked_reason"):
        return str(primary["blocked_reason"])
    return str(primary.get("summary") or "继续推进制作流程。")


__all__ = ("build_command_hub",)
