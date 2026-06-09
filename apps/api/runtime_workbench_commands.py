from __future__ import annotations

from typing import Any

from apps.api.runtime_workbench_readiness import ACTION_LABELS


NON_CLAIMS = ["not human acceptance", "not business validation", "not durable memory"]

ACTION_UI_MAP = {
    "add_reference": {
        "ui_action": "register-source-asset",
        "view": "Assets",
        "summary": "Add safe source summaries before drafting the production canvas.",
        "requires_input": ["source_asset_id", "source_asset_label", "source_asset_summary"],
    },
    "draft_canvas": {
        "ui_action": "draft-canvas",
        "view": "Create",
        "summary": "Create a first reviewable canvas from the current safe source material.",
        "requires_input": [],
    },
    "start_first_generation_check": {
        "ui_action": "run-asset-test",
        "view": "Create",
        "summary": "Run deterministic checks before any real provider smoke.",
        "requires_input": [],
    },
    "record_review_note": {
        "ui_action": "record-feedback",
        "view": "Review",
        "summary": "Record raw review evidence for the next pass.",
        "requires_input": ["feedback_note"],
    },
    "start_next_round": {
        "ui_action": "run-two-round",
        "view": "Review",
        "summary": "Reuse accepted context and review evidence in a second pass.",
        "requires_input": [],
    },
    "run_provider_preflight": {
        "ui_action": "run-provider-preflight",
        "view": "Jobs",
        "summary": "Check provider readiness without starting a real model run.",
        "requires_input": [],
    },
    "resolve_provider_preflight": {
        "ui_action": "",
        "view": "Jobs",
        "summary": "Provider capability gates remain blocked until explicitly authorized.",
        "requires_input": [],
        "blocked_reason": "Provider capability gate is still blocked.",
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
        "title": "Command hub",
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
        "label": ACTION_LABELS.get(backend_action, "Continue"),
        "backend_action": backend_action,
        "ui_action": ui_action,
        "view": str(config.get("view") or "Create"),
        "summary": str(config.get("summary") or "Continue the production flow."),
        "enabled": enabled,
        "blocked_reason": blocked_reason,
        "requires_input": list(config.get("requires_input") or []),
    }


def _summary(primary: dict[str, Any]) -> str:
    if primary.get("blocked_reason"):
        return str(primary["blocked_reason"])
    return str(primary.get("summary") or "Continue the production flow.")


__all__ = ("build_command_hub",)
