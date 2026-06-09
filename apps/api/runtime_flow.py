from __future__ import annotations

from typing import Any

from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_workbench_state import build_workbench_state


NON_CLAIMS = ["not human acceptance", "not business validation", "not durable memory"]


def build_flow_summary(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    state = build_workbench_state(store, project_id)
    project = _object(state.get("project"))
    readiness = _object(state.get("project_readiness"))
    command = _object(_object(state.get("command_hub")).get("primary_command"))
    studio = _object(state.get("studio_workspace"))
    provider_gate = _object(state.get("provider_gate"))
    current_action = str(readiness.get("current_action") or command.get("backend_action") or "add_reference")
    project_status = str(project.get("status") or "in_progress")
    readiness_status = str(readiness.get("status") or "not_started")
    return {
        "project_id": str(state.get("project_id") or project_id),
        "target_status": "ready_for_next_round",
        "target_achieved": project_status == "ready_for_next_round",
        "project_status": project_status,
        "readiness_status": readiness_status,
        "current_action": current_action,
        "current_action_label": str(readiness.get("current_action_label") or command.get("label") or "Continue"),
        "next_command": _command(command),
        "studio_status": str(studio.get("status") or "not_started"),
        "provider_status": str(provider_gate.get("status") or studio.get("provider_status") or "ready_not_run"),
        "non_claims": NON_CLAIMS,
    }


def _command(command: dict[str, Any]) -> dict[str, Any]:
    return {
        "backend_action": str(command.get("backend_action") or ""),
        "label": str(command.get("label") or "Continue"),
        "ui_action": str(command.get("ui_action") or ""),
        "view": str(command.get("view") or "Create"),
        "enabled": command.get("enabled") is True,
        "blocked_reason": str(command.get("blocked_reason") or ""),
        "requires_input": [str(item) for item in _list(command.get("requires_input"))],
    }


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = ("build_flow_summary",)
